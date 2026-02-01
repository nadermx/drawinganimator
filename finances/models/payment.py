import json
from datetime import timedelta

import requests
import stripe
from django.db import models
from django.utils import timezone
# Square SDK - disabled for now, using Stripe primarily
Client = None  # Placeholder - Square functions will need refactoring for new SDK

from accounts.models import CustomUser
from app.utils import Utils
from config import SQUARE_UP, STRIPE, PAYPAL_KEYS
from finances.models.plan import Plan


class Payment(models.Model):
    FAILED = 'failed'
    SUCCESS = 'success'
    PENDING = 'pending'
    REFUNDED = 'refunded'
    STATUS_CHOICES = (
        (FAILED, FAILED),
        (SUCCESS, SUCCESS),
        (PENDING, PENDING),
        (REFUNDED, REFUNDED),
    )
    SQUAREUP = 'squareup'
    STRIPE = 'stripe'
    PAYPAL = 'paypal'
    COINBASE = 'coinbase'
    PROCESSORS = (
        (SQUAREUP, SQUAREUP),
        (STRIPE, STRIPE),
        (PAYPAL, PAYPAL),
        (COINBASE, COINBASE),
    )
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    processor = models.CharField(max_length=20, null=True)
    amount = models.IntegerField(default=1)
    status = models.CharField(default='pending', max_length=100, choices=STATUS_CHOICES)
    payment_token = models.CharField(max_length=250, null=True)
    refund_token = models.CharField(max_length=250, null=True)
    customer_token = models.CharField(max_length=250, null=True)
    card_token = models.CharField(max_length=250, null=True)
    comments = models.TextField(null=True)
    payment_data = models.TextField(null=True)
    used_card_brand = models.CharField(max_length=50, null=True, blank=True)
    used_card_exp_month = models.CharField(max_length=50, null=True, blank=True)
    used_card_exp_year = models.CharField(max_length=50, null=True, blank=True)
    used_card_last_digits = models.CharField(max_length=50, null=True, blank=True)
    uuid = models.CharField(default=Utils.generate_hex_uuid, max_length=250)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.user.email if self.user else '-'

    @staticmethod
    def save_ipn_response(webhook):
        resource = webhook.get('resource')

        try:
            plan = Plan.objects.get(paypal_key=resource.get('plan_id'))
        except:
            return None, 'Plan not found'

        try:
            payment = Payment.objects.get(
                payment_token=resource.get('id')
            )
        except:
            return None, 'Payment not pending'

        payment.payment_data = webhook
        cancel_events = [
            'BILLING.SUBSCRIPTION.CANCELLED',
            'BILLING.SUBSCRIPTION.EXPIRED',
            'BILLING.SUBSCRIPTION.PAYMENT.FAILED',
            'BILLING.SUBSCRIPTION.SUSPENDED',
        ]

        if webhook.get('event_type') == 'BILLING.SUBSCRIPTION.ACTIVATED':
            if payment.status == Payment.PENDING:
                payment.status = Payment.SUCCESS
                payment.user.plan_subscribed = plan.code_name
                payment.user.is_plan_active = True
                payment.user.next_billing_date = timezone.now() + timedelta(days=31)
                payment.user.credits = int(payment.user.credits) + int(plan.credits)
                payment.user.save()
        elif webhook.get('event_type') in cancel_events:
            if payment.status == Payment.PENDING:
                payment.status = Payment.FAILED

            payment.user.is_plan_active = False
            payment.user.next_billing_date = None
            payment.user.save()

        payment.save()

        return 'ok', None

    @staticmethod
    def get_by_user(user):
        return Payment.objects.filter(
            user=user
        )

    @staticmethod
    def make_refund(uuid, email):
        if not uuid:
            return None, ['missing_payment_uuid']
        if not email:
            return None, ['missing_email']

        email = email.lower().strip()

        try:
            payment = Payment.objects.get(
                uuid=uuid,
                user__email=email
            )
        except:
            return None, ['payment_not_found']

        if payment.status != Payment.SUCCESS:
            return None, ['payment_not_success']

        if payment.processor == 'stripe':
            refund, errors = Payment.make_stripe_refund(payment.payment_token)

            if not refund:
                return None, errors
            else:
                payment.refund_token = refund.id
                payment.status = Payment.REFUNDED
                payment.save()
                payment.user.is_plan_active = False
                payment.user.next_billing_date = None
                payment.user.save()

                return payment, 'ok'
        elif payment.processor == 'squareup':
            refund, errors = Payment.make_square_refund(payment.payment_token, payment.amount)

            if not refund:
                return None, errors
            else:
                payment.refund_token = refund.get('id')
                payment.status = Payment.REFUNDED
                payment.save()
                payment.user.is_plan_active = False
                payment.user.next_billing_date = None
                payment.user.save()

                return payment, 'ok'
        elif payment.processor == 'paypal':
            refund, errors = Payment.make_paypal_refund(payment.payment_token)

            if not refund:
                return None, errors
            else:
                payment.refund_token = refund.get('id')
                payment.status = Payment.REFUNDED
                payment.save()
                payment.user.is_plan_active = False
                payment.user.next_billing_date = None
                payment.user.save()

                return payment, 'ok'
        else:
            return None, ['refund_not_for_this_processor']

    @staticmethod
    def make_stripe_refund(charge_id):
        try:
            stripe.api_key = STRIPE.get('sk')
            refund = stripe.Refund.create(
                charge=charge_id,
            )

            return refund, None
        except Exception as e:
            return None, ['Error making refund.']

    @staticmethod
    def coinbase_ipn(email=None, plan_codename=None, payment_code=None, event_type=None, webhook={}):
        processor = Payment.COINBASE

        try:
            user = CustomUser.objects.get(email=email)
        except Exception as e:
            return None, ['User not found: %s' % str(e)]

        try:
            plan = Plan.objects.get(code_name=plan_codename)
        except Exception as e:
            payment = Payment.objects.create(
                user=user,
                processor=processor,
                payment_token=payment_code,
                comments=event_type,
                status=Payment.FAILED,
                amount='0',
                payment_data=webhook
            )
            payment.save()
            return None, ['Plan not found: %s' % str(e)]

        if 'charge:failed' in event_type:
            payment = Payment.objects.create(
                user=user,
                processor=processor,
                payment_token=payment_code,
                comments=event_type,
                status=Payment.FAILED,
                amount=plan.price,
                payment_data=webhook
            )
            payment.save()
            return None, ['payment_failed']
        elif 'charge:confirmed' in event_type:
            payment = Payment(
                user=user,
                processor=processor,
                payment_token=payment_code,
                status=Payment.SUCCESS,
                amount=plan.price,
                payment_data=webhook
            )
            payment.save()
            return payment, 'ok'
        else:
            payment = Payment.objects.create(
                user=user,
                processor=processor,
                payment_token=payment_code,
                comments=event_type,
                status=Payment.FAILED,
                amount=plan.price,
                payment_data=webhook
            )
            payment.save()
            return None, ['payment_failed']

    @staticmethod
    def create_paypal_order_or_subscription(user, data):
        plan = data.get('plan')

        try:
            plan = Plan.objects.get(code_name=plan)
        except:
            return None, None, 'Plan not found'

        if plan.is_subscription:
            subs_link, errors = Payment.create_paypal_subscription(user, plan)
            return None, subs_link, errors
        else:
            order_id, errors = Payment.create_paypal_order(plan.price)
            return order_id, None, errors

    @staticmethod
    def create_paypal_subscription(user, plan):
        auth_values = (PAYPAL_KEYS.get('id'), PAYPAL_KEYS.get('secret'))
        r = requests.post(
            '%s/v1/billing/subscriptions' % PAYPAL_KEYS.get('api'),
            auth=auth_values,
            json={
                'plan_id': plan.paypal_key,
                'quantity': '1',
                'subscriber': {
                    'email_address': user.email,
                }
            }
        )
        payment = Payment.objects.create(
            user=user,
            processor='paypal',
            amount=plan.price
        )

        if r.status_code in [200, 201]:
            r = r.json()
            payment.payment_token = r.get('id')
            payment.save()
            subs_links = r.get('links')[0]
            subs_link = subs_links.get('href')

            return subs_link, 'ok'

        payment.status = Payment.FAILED
        payment.commends = r.content
        payment.payment_data = r.content
        payment.save()

        return None, r.content

    @staticmethod
    def create_paypal_order(amount=0):
        if not amount:
            return None, 'Invalid amount'

        amount = '%s.00' % amount
        auth_values = (PAYPAL_KEYS.get('id'), PAYPAL_KEYS.get('secret'))
        r = requests.post(
            '%s/v2/checkout/orders' % PAYPAL_KEYS.get('api'),
            auth=auth_values,
            json={
                'intent': 'CAPTURE',
                'payer': {
                    'payment_method': 'paypal'
                },
                'purchase_units': [{
                    'amount': {
                        'value': amount,
                        'currency_code': 'USD'
                    }
                }]
            }
        )

        if r.status_code in [200, 201]:
            r = r.json()
            return r.get('id'), 'ok'

        return None, r.content

    @staticmethod
    def make_paypal_refund(payment_id):
        auth_values = (PAYPAL_KEYS.get('id'), PAYPAL_KEYS.get('secret'))
        r = requests.get(
            '%s/v2/checkout/orders/%s' % (
                PAYPAL_KEYS.get('api'),
                payment_id
            ),
            auth=auth_values,
            json={}
        )

        if r.status_code not in [200, 201]:
            return None, ['error_making_paypal_refund']

        capture_id = None
        data = r.json()
        purchase_unit = data.get('purchase_units')[0]
        payments = purchase_unit.get('payments')

        for item in payments.get('captures'):
            if item.get('status') == 'COMPLETED':
                capture_id = item.get('id')
                break

        if not capture_id:
            return None, ['error_making_paypal_refund']

        r = requests.post(
            '%s/v2/payments/captures/%s/refund' % (
                PAYPAL_KEYS.get('api'),
                capture_id
            ),
            auth=auth_values,
            json={}
        )

        if r.status_code not in [200, 201]:
            return None, ['error_making_paypal_refund']

        return r.json(), None

    @staticmethod
    def make_charge_paypal(user, paypal_nonce=None, amount=0, settings={}):
        processor = Payment.PAYPAL
        i18n = settings.get('i18n')

        if not user:
            return None, [i18n.get('user_not_found', 'user_not_found')]

        if not paypal_nonce:
            return None, [i18n.get('missing_nonce', 'missing_nonce')]

        if not amount:
            return None, [i18n.get('empty_amount', 'empty_amount')]

        auth_values = (PAYPAL_KEYS.get('id'), PAYPAL_KEYS.get('secret'))
        r = requests.post(
            '%s/v2/checkout/orders/%s/capture' % (
                PAYPAL_KEYS.get('api'),
                paypal_nonce
            ),
            auth=auth_values,
            json={}
        )

        if r.status_code not in [200, 201]:
            payment = Payment.objects.create(
                user=user,
                processor=processor,
                payment_token=paypal_nonce,
                comments=json.dumps(r.content.decode()),
                status=Payment.FAILED,
                amount=amount,
                payment_data=json.dumps(r.json())
            )
            payment.save()

            return None, ['error_authorizing_paypal_payment']

        r = r.json()
        payment = Payment(
            user=user,
            processor=processor,
            payment_token=r.get('id'),
            status=Payment.SUCCESS,
            amount=amount,
        )
        payment.save()

        return payment, 'ok'

    @staticmethod
    def create_stripe_customer(email, token):
        try:
            stripe.api_key = STRIPE.get('sk')
            customer = stripe.Customer.create(
                email=email,
                source=token
            )

            return customer, None
        except Exception as e:
            return None, ['Error creating Stripe customer']

    @staticmethod
    def create_stripe_charge(customer, amount):
        try:
            stripe.api_key = STRIPE.get('sk')
            charge = stripe.Charge.create(
                amount=amount * 100,
                currency='usd',
                customer=customer,
                description='EstaCaido.com'
            )

            return charge, None
        except stripe.error.CardError as e:
            return None, ['A payment error occurred.']
        except stripe.error.InvalidRequestError as e:
            return None, ['An invalid request occurred.']
        except Exception as e:
            return None, ['Another problem occurred, maybe unrelated to Stripe.']

    @staticmethod
    def make_charge_stripe_customer(user, amount=0):
        processor = 'stripe'
        stripe_charge, errors = Payment.create_stripe_charge(user.payment_nonce, amount)

        if not stripe_charge:
            payment = Payment.objects.create(
                user=user,
                processor=processor,
                customer_token=user.payment_nonce,
                card_token=user.payment_nonce,
                comments='\n'.join(errors),
                status=Payment.FAILED,
                amount=amount,
                used_card_brand=stripe_charge.source.brand,
                used_card_exp_month=stripe_charge.source.exp_month,
                used_card_exp_year=stripe_charge.source.exp_year,
                used_card_last_digits=stripe_charge.source.last4,
            )
            payment.save()

            return None, errors

        payment = Payment(
            user=user,
            processor=processor,
            customer_token=user.payment_nonce,
            card_token=user.payment_nonce,
            payment_token=stripe_charge.id,
            status=Payment.SUCCESS,
            amount=amount,
            used_card_brand=stripe_charge.source.brand,
            used_card_exp_month=stripe_charge.source.exp_month,
            used_card_exp_year=stripe_charge.source.exp_year,
            used_card_last_digits=stripe_charge.source.last4,
        )
        payment.save()

        return payment, 'ok'

    @staticmethod
    def make_charge_stripe(user, stripe_token=None, amount=0, settings={}):
        i18n = settings.get('i18n', {})
        processor = Payment.STRIPE

        if 'tok_' not in stripe_token:
            return None, ['Payment not found']
        if not user:
            return None, [i18n.get('user_not_found', 'user_not_found')]
        if not stripe_token:
            return None, [i18n.get('missing_nonce', 'missing_nonce')]
        if not amount:
            return None, [i18n.get('empty_amount', 'empty_amount')]

        stripe_customer, errors = Payment.create_stripe_customer(user.email, stripe_token)

        if not stripe_customer:
            payment = Payment.objects.create(
                user=user,
                processor=processor,
                payment_token=stripe_token,
                comments='\n'.join(errors),
                status=Payment.FAILED,
                amount=amount,
            )
            payment.save()

            return None, errors

        stripe_charge, errors = Payment.create_stripe_charge(stripe_customer, amount)

        if not stripe_charge:
            payment = Payment.objects.create(
                user=user,
                processor=processor,
                customer_token=stripe_customer.id,
                card_token=stripe_customer.id,
                payment_token=stripe_token,
                comments='\n'.join(errors),
                status=Payment.FAILED,
                amount=amount
            )
            payment.save()

            return None, errors

        payment = Payment(
            user=user,
            processor=processor,
            customer_token=stripe_customer.id,
            card_token=stripe_customer.id,
            payment_token=stripe_charge.id,
            status=Payment.SUCCESS,
            amount=amount,
            used_card_brand=stripe_charge.source.brand,
            used_card_exp_month=stripe_charge.source.exp_month,
            used_card_exp_year=stripe_charge.source.exp_year,
            used_card_last_digits=stripe_charge.source.last4,
        )
        payment.save()

        return payment, 'ok'

    @staticmethod
    def make_square_refund(payment_id, amount):
        client = Client(
            access_token=SQUARE_UP.get('secret'),
            environment=SQUARE_UP.get('env'),
        )
        body = {
            'idempotency_key': Utils.generate_uuid(),
            'amount_money': {
                'amount': amount * 100,
                'currency': 'USD'
            },
            'app_fee_money': {
                'amount': 0,
                'currency': 'USD'
            },
            'payment_id': payment_id,
            'reason': 'Customer requests a refund'
        }
        result = client.refunds.refund_payment(body)

        if result.is_error():
            msg = []

            for item in result.errors:
                msg.append(item.get('detail'))

            return None, msg

        return result.body.get('refund'), 'ok'

    @staticmethod
    def make_charge_square(user, nonce=None, amount=0, settings={}):
        i18n = settings.get('i18n')
        processor = Payment.SQUAREUP

        if not user:
            return None, [i18n.get('user_not_found', 'user_not_found')]

        if not nonce:
            return None, [i18n.get('missing_nonce', 'missing_nonce')]

        if not amount:
            return None, [i18n.get('empty_amount', 'empty_amount')]

        client = Client(
            access_token=SQUARE_UP.get('secret'),
            environment=SQUARE_UP.get('env'),
        )
        body = {
            'email_address': user.email,
            'note': 'EstaCaido.com'
        }
        result = client.customers.create_customer(body)

        if result.is_error():
            payment = Payment.objects.create(
                user=user,
                processor=processor,
                payment_token=nonce,
                comments=json.dumps(result.errors),
                status=Payment.FAILED,
                amount=amount,
                payment_data=json.dumps(result)
            )
            msg = []

            for item in result.errors:
                msg.append(i18n.get(item.get('code'), item.get('detail')))

            payment.comments = msg
            payment.save()

            return None, msg

        customer_id = result.body.get('customer').get('id')
        body = {
            'card_nonce': nonce
        }
        result = client.customers.create_customer_card(customer_id, body)

        if result.is_error():
            payment = Payment.objects.create(
                user=user,
                processor=processor,
                customer_token=customer_id,
                payment_token=nonce,
                status=Payment.FAILED,
                amount=amount
            )
            msg = []

            for item in result.errors:
                msg.append(i18n.get(item.get('code'), item.get('detail')))

            payment.comments = msg
            payment.save()

            return None, msg

        card_id = result.body.get('card').get('id')
        card_brand = result.body.get('card').get('card_brand')
        exp_month = str(result.body.get('card').get('exp_month'))
        exp_year = str(result.body.get('card').get('exp_year'))
        last_digits = result.body.get('card').get('last_4')
        body = {
            'source_id': card_id,
            'idempotency_key': Utils.generate_uuid(),
            'amount_money': {
                'amount': amount * 100,
                'currency': 'USD'
            },
            'app_fee_money': {
                'amount': 0,
                'currency': 'USD'
            },
            'autocomplete': True,
            'customer_id': customer_id,
            'note': 'Making Payment'
        }
        result = client.payments.create_payment(body)

        if result.is_error():
            payment = Payment.objects.create(
                user=user,
                processor=processor,
                customer_token=customer_id,
                card_token=card_id,
                payment_token=nonce,
                status=Payment.FAILED,
                amount=amount,
                used_card_brand=card_brand,
                used_card_exp_month=exp_month,
                used_card_exp_year=exp_year,
                used_card_last_digits=last_digits
            )
            msg = []

            for item in result.errors:
                msg.append(i18n.get(item.get('code'), item.get('detail')))

            payment.comments = msg
            payment.save()

            return None, msg

        payment_id = result.body.get('payment').get('id')
        payment = Payment(
            user=user,
            processor=processor,
            customer_token=customer_id,
            card_token=card_id,
            payment_token=payment_id,
            status=Payment.SUCCESS,
            amount=amount,
            used_card_brand=card_brand,
            used_card_exp_month=exp_month,
            used_card_exp_year=exp_year,
            used_card_last_digits=last_digits
        )
        payment.save()

        return payment, 'ok'

    @staticmethod
    def make_charge_square_customer(user, amount=0):
        processor = Payment.SQUAREUP
        client = Client(
            access_token=SQUARE_UP.get('secret'),
            environment=SQUARE_UP.get('env'),
        )
        body = {
            'source_id': user.card_nonce,
            'idempotency_key': Utils.generate_uuid(),
            'amount_money': {
                'amount': amount * 100,
                'currency': 'USD'
            },
            'app_fee_money': {
                'amount': 0,
                'currency': 'USD'
            },
            'autocomplete': True,
            'customer_id': user.payment_nonce,
            'note': 'Making Payment'
        }
        result = client.payments.create_payment(body)

        if result.is_error():
            payment = Payment.objects.create(
                user=user,
                processor=processor,
                card_token=user.card_nonce,
                customer_token=user.payment_nonce,
                status=Payment.FAILED,
                amount=amount
            )
            msg = []

            for item in result.errors:
                msg.append(item.get('detail'))

            payment.comments = msg
            payment.save()

            return None, msg

        payment_id = result.body.get('payment').get('id')
        payment = Payment(
            user=user,
            processor=processor,
            card_token=user.card_nonce,
            customer_token=user.payment_nonce,
            payment_token=payment_id,
            status=Payment.SUCCESS,
            amount=amount,
        )
        payment.save()

        return payment, 'ok'

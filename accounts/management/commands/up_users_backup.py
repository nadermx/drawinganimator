import json

from django.core.management import BaseCommand

from accounts.models import CustomUser
from app.utils import Utils
from finances.models.payment import Payment


class Command(BaseCommand):
    help = 'up_users_backup'

    def handle(self, *args, **options):
        with open('./accounts/json/users.json') as f:
            busers = json.load(f)

        for buser in busers:
            plan_codename = None
            credits = 0

            if buser.get('plan_subscribed') == 'daypass':
                plan_codename = 'plan1'
                credits = 300
            elif buser.get('plan_subscribed') == 'month':
                plan_codename = 'plan2'
                credits = 600
            elif buser.get('plan_subscribed') == 'year':
                plan_codename = 'plan3'
                credits = 5400
            elif buser.get('plan_subscribed') == 'lifetime':
                plan_codename = 'plan4'
                credits = 18400

            processor = None
            payment_nonce = None

            if buser.get('paypal_subscription_id'):
                processor = 'paypal'
                payment_nonce = buser.get('paypal_subscription_id')
            elif buser.get('customer_id'):
                processor = 'paypal'
                payment_nonce = buser.get('customer_id')

            next_bill_at = buser.get('next_bill_at')

            if next_bill_at == 'None':
                next_bill_at = None
            else:
                next_bill_at = next_bill_at.split(' ')[0]

            try:
                user = CustomUser.objects.get(
                    email=buser.get('email')
                )
            except:
                user = CustomUser.objects.create(
                    email=buser.get('email'),
                    is_active=True,
                    is_confirm=buser.get('verified'),
                    api_token=buser.get('api_key'),
                    card_nonce=buser.get('suscribed_card'),
                    payment_nonce=payment_nonce,
                    processor=processor,
                    credits=credits,
                    next_billing_date=next_bill_at,
                    plan_subscribed=plan_codename,
                    is_plan_active=buser.get('is_plan_active')
                )
                user.set_password(Utils.generate_hex_uuid())
                user.save()

            for bpayment in buser.get('payments'):
                payment_data = None
                status = bpayment.get('status')

                if bpayment.get('paypal_info'):
                    pprocessor = Payment.PAYPAL
                    payment_data = bpayment.get('paypal_info')
                else:
                    pprocessor = Payment.SQUAREUP

                if status == 'completed':
                    status = Payment.SUCCESS

                created_at = bpayment.get('day').split(' ')[0]
                payment = Payment.objects.create(
                    user=user,
                    processor=pprocessor,
                    amount=bpayment.get('amount'),
                    status=status,
                    payment_token=bpayment.get('payment_token'),
                    customer_token=bpayment.get('customer_token'),
                    card_token=bpayment.get('card_token'),
                    comments=bpayment.get('payment_comment'),
                    payment_data=payment_data,
                    used_card_brand=bpayment.get('used_card_brand'),
                    used_card_exp_month=bpayment.get('used_card_exp_month'),
                    used_card_exp_year=bpayment.get('used_card_exp_year'),
                    used_card_last_digits=bpayment.get('used_card_last_digits'),
                    created_at=created_at
                )
                payment.save()

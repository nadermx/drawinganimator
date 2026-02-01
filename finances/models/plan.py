import requests
from django.db import models
from django.utils.text import slugify

from config import PAYPAL_KEYS


class Plan(models.Model):
    code_name = models.CharField(max_length=250, unique=True)
    price = models.IntegerField(default=1)
    label_price = models.IntegerField(null=True, blank=True)
    credits = models.IntegerField(default=0)
    paypal_product_key = models.CharField(max_length=250, null=True, blank=True)
    paypal_key = models.CharField(max_length=250, null=True, blank=True)
    coinbase_key = models.CharField(max_length=250, null=True, blank=True)
    stripe_key = models.CharField(max_length=250, null=True, blank=True)
    square_key = models.CharField(max_length=250, null=True, blank=True)
    days = models.IntegerField(null=True, blank=True)
    yearly_subscription = models.BooleanField(default=False)
    is_subscription = models.BooleanField(default=False)
    is_api_plan = models.BooleanField(default=False)

    def __str__(self):
        return self.code_name

    def save(self, *args, **kwargs):
        self.code_name = slugify(self.code_name)
        super().save(*args, **kwargs)

    @staticmethod
    def create_paypal_product():
        product_name = 'Services'
        params = {
            'name': product_name,
            'description': product_name,
            'type': 'SERVICE',
            'category': 'SOFTWARE'
        }
        auth_values = (PAYPAL_KEYS.get('id'), PAYPAL_KEYS.get('secret'))
        r = requests.post(
            '%s/v1/catalogs/products' % PAYPAL_KEYS.get('api'),
            auth=auth_values,
            json=params
        ).json()

        if r.get('id'):
            for plan in Plan.objects.all():
                plan.paypal_product_key = r.get('id')
                plan.save()

            print('Product created')
        else:
            print('Product not created')

    @staticmethod
    def create_update_paypal_billing_plans():
        plans = Plan.objects.filter(
            is_subscription=True
        )

        for plan in plans.filter():
            params = {
                'product_id': plan.paypal_product_key,
                'name': '%s credits' % plan.credits,
                'description': 'service',
                'status': 'ACTIVE',
                'billing_cycles': [
                    {
                        'frequency': {
                            'interval_unit': 'MONTH',
                            'interval_count': 12 if plan.yearly_subscription else 1
                        },
                        'tenure_type': 'REGULAR',
                        'sequence': 1,
                        'total_cycles': 0,
                        'pricing_scheme': {
                            'fixed_price': {
                                'value': '%s' % plan.price,
                                'currency_code': 'USD'
                            }
                        }
                    }
                ],
                'payment_preferences': {
                    'auto_bill_outstanding': False,
                    'setup_fee_failure_action': 'CONTINUE',
                    'payment_failure_threshold': 3
                }
            }
            auth_values = (PAYPAL_KEYS.get('id'), PAYPAL_KEYS.get('secret'))
            r = requests.post(
                '%s/v1/billing/plans' % PAYPAL_KEYS.get('api'),
                auth=auth_values,
                json=params
            ).json()

            if r.get('id'):
                plan.paypal_key = r.get('id')
                plan.save()
                print('Plan created')
            else:
                print(r)
                print('Plan not created')

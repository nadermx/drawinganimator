import json

from django.core.management import BaseCommand

from finances.models.plan import Plan


class Command(BaseCommand):
    help = 'set_plans'

    def handle(self, *args, **options):
        with open('./finances/json/plans.json') as f:
            plans = json.load(f)

        for index, key in enumerate(plans):
            item = plans.get(key)
            Plan.objects.update_or_create(
                code_name=item.get('code_name'),
                defaults={
                    'price': item.get('price'),
                    'credits': item.get('credits'),
                    'coinbase_key': item.get('coinbase'),
                    'is_subscription': True if item.get('subscription') is True else False,
                    'is_api_plan': True if item.get('api_plan') is True else False,
                    'days': 0 if not item.get('days') else item.get('days'),
                    'yearly_subscription': True if item.get('yearly') is True else False,
                    'label_price': item.get('label_price')
                }
            )

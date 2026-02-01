from django.core.management import BaseCommand

from finances.models.plan import Plan


class Command(BaseCommand):
    help = 'create_paypal_plans'

    def handle(self, *args, **options):
        Plan.create_update_paypal_billing_plans()

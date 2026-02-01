from django.core.management import BaseCommand

from finances.models.plan import Plan


class Command(BaseCommand):
    help = 'create_paypal_product'

    def handle(self, *args, **options):
        Plan.create_paypal_product()

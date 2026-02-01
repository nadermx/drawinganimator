from django.core.management import BaseCommand
from django.utils import timezone

from accounts.models import CustomUser


class Command(BaseCommand):
    help = 'rebill'

    def handle(self, *args, **options):
        today = timezone.now().date()
        print('Running script %s' % today)

        for account in CustomUser.objects.filter(next_billing_date=today):
            account.make_rebill()
            print('here')

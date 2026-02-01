from django.core.management import BaseCommand
from django.utils import timezone

from accounts.models import CustomUser


class Command(BaseCommand):
    help = 'expire_pro_users'

    def handle(self, *args, **options):
        now = timezone.now()

        for user in CustomUser.objects.filter(
                is_plan_active=True,
                next_billing_date__isnull=False
        ):
            if user.next_billing_date < now:
                user.is_plan_active = False
                user.next_billing_date = None
                user.save()

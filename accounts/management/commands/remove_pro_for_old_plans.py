from django.core.management import BaseCommand

from accounts.models import CustomUser


class Command(BaseCommand):
    help = 'remove_pro_for_old_plans'

    def handle(self, *args, **options):
        for user in CustomUser.objects.filter(
                is_plan_active=True,
                next_billing_date__isnull=True
        ):
            user.is_plan_active = False
            user.save()

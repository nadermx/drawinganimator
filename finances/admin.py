from django.contrib import admin

from finances.models.payment import Payment
from finances.models.plan import Plan


class PlanAdmin(admin.ModelAdmin):
    list_display = (
        'code_name',
        'price',
        'credits',
        'days',
        'is_subscription',
        'is_api_plan',
        'yearly_subscription'
    )


class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'processor',
        'amount',
        'status',
        'created_at'
    )
    search_fields = (
        'uuid',
    )


admin.site.register(Plan, PlanAdmin)
admin.site.register(Payment, PaymentAdmin)

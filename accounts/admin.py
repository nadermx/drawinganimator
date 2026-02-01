from django.contrib import admin
from accounts.models import CustomUser


class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'verification_code',
        'is_staff',
        'is_confirm',
        'lang',
        'created_at',
        'is_plan_active',
        'plan_subscribed',
        'next_billing_date',
    )
    readonly_fields = (
        'restore_password_token',
    )
    search_fields = (
        'email',
    )


admin.site.register(CustomUser, CustomUserAdmin)

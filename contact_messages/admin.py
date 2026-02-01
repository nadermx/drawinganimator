from django.contrib import admin

from contact_messages.models.message import Message


class MessageAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'user',
        'message',
        'created_at',
    )
    readonly_fields = (
        'email',
        'user',
        'message',
        'responded_at',
        'created_at'
    )


admin.site.register(Message, MessageAdmin)

from django.core.validators import validate_email
from django.db import models
from django.utils import timezone

from accounts.models import CustomUser
from app.utils import Utils
from config import PROJECT_NAME, ROOT_DOMAIN
from translations.models.translation import Translation


class Message(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True)
    email = models.EmailField(max_length=250)
    message = models.TextField()
    response_message = models.TextField(null=True, blank=True)
    prevent_mailing = models.BooleanField(default=False)
    responded_at = models.DateField(null=True, blank=True)
    created_at = models.DateField(default=timezone.now)

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.response_message and not self.prevent_mailing:
            self.prevent_mailing = True
            self.responded_at = timezone.now()
            i18n = Translation.get_text_by_lang('en')
            Utils.send_email(
                recipients=[self.email],
                subject=PROJECT_NAME,
                template='response-contact-message',
                data={
                    'message': self,
                    'i18n': i18n,
                    'project_name': PROJECT_NAME,
                    'root_domain': ROOT_DOMAIN
                }
            )
            self.save()

    @staticmethod
    def save_message(user, data, settings={}):
        if not user.is_authenticated:
            user = None

        i18n = settings.get('i18n')
        email = data.get('email')
        message = data.get('message')
        errors = []

        if not email:
            errors.append(i18n.get('missing_email', 'missing_email'))
        else:
            email = email.lower()

            try:
                validate_email(email)
            except:
                errors.append(i18n.get('invalid_email', 'invalid_email'))

        if not message:
            errors.append(i18n.get('missing_message', 'missing_message'))

        if len(errors):
            return None, errors

        message = Message.objects.create(
            user=user,
            email=email,
            message=message
        )
        message.save()

        return message, None

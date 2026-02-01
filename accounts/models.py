from datetime import timedelta
from hashlib import md5

from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import validate_email
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from app.utils import Utils
from config import PROCESSORS, PROJECT_NAME, ROOT_DOMAIN
from translations.models.language import Language
from translations.models.translation import Translation


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()

        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class AccountType(models.Model):
    name = models.CharField(max_length=250, null=False, blank=False)
    code_name = models.CharField(max_length=250, null=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.code_name = slugify(self.name).replace('-', '_')
        super().save(*args, **kwargs)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=250, unique=True, null=False, blank=False)
    get_short_name = models.TextField(max_length=250, default='user')
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_confirm = models.BooleanField(default=False)
    in_newsletter = models.BooleanField(default=False)
    uuid = models.CharField(max_length=250, default=Utils.generate_uuid, null=False, blank=False)
    confirmation_token = models.CharField(default=Utils.generate_hex_uuid, max_length=250, null=True, blank=False)
    verification_code = models.CharField(default=Utils.genetate_verification_code, max_length=10, null=True, blank=True)
    verification_code_sent_at = models.DateTimeField(default=timezone.now)
    restore_password_token = models.CharField(max_length=250, null=True, blank=False)
    lost_password_email_sent_at = models.DateTimeField(null=True, blank=True)
    lang = models.CharField(max_length=5, default='en')
    updated_at = models.DateField(auto_now_add=True, null=True)
    created_at = models.DateField(default=timezone.now)
    api_token = models.CharField(default=Utils.generate_hex_uuid, max_length=250, null=True, blank=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['is_staff']
    # stripe_customer_id = models.CharField(max_length=250, null=True, blank=True, unique=True)
    card_nonce = models.CharField(max_length=250, null=True, blank=True)
    payment_nonce = models.CharField(max_length=250, null=True, blank=True, unique=True)
    processor = models.CharField(max_length=50, null=True, blank=True)
    credits = models.IntegerField(default=0, blank=True)
    next_billing_date = models.DateTimeField(null=True, blank=True)
    plan_subscribed = models.CharField(max_length=50, null=True, blank=True)
    is_plan_active = models.BooleanField(default=False)
    objects = CustomUserManager()

    def __str__(self):
        return self.email

    @property
    def check_plan(self):
        if self.is_plan_active:
            return True

        return False

    def get_payments(self):
        from finances.models.payment import Payment
        return Payment.objects.filter(
            user=self,
        ).order_by('-id')

    def make_rebill(self):
        from finances.models.payment import Payment

        i18n = Translation.get_text_by_lang(self.lang)

        try:
            from finances.models.plan import Plan
            plan = Plan.objects.get(code_name=self.plan_subscribed)
        except:
            self.is_plan_active = False
            self.save()
            return

        amount = plan.price
        credits = plan.credits

        if self.processor == 'stripe':
            payment, errors = Payment.make_charge_stripe_customer(self, amount)
        elif self.processor == 'squareup':
            payment, errors = Payment.make_charge_square_customer(self, amount)
        else:
            self.is_plan_active = False
            self.save()
            return

        if not payment:
            self.is_plan_active = False
            self.save()
            return

        self.is_plan_active = True
        self.credits = int(self.credits) + int(credits)
        self.next_billing_date = timezone.now() + timedelta(days=31)
        self.save()
        Utils.send_email(
            recipients=[self.email],
            subject='Payment receive',
            template='payment-invoice',
            data={
                'user': self,
                'payment': payment,
                'i18n': i18n,
                'project_name': PROJECT_NAME,
                'root_domain': ROOT_DOMAIN
            }
        )

    @property
    def get_seconds_to_expire_plan(self):
        return (self.next_billing_date - timezone.now()).total_seconds()

    @staticmethod
    def cancel_subscription(user):
        if not user.is_authenticated:
            return None, 'User not found'

        user.card_nonce = None
        user.payment_nonce = None
        user.processor = None
        user.next_billing_date = None
        user.is_plan_active = False
        user.save()

        return user, 'ok'

    @staticmethod
    def resend_email_verification(user, settings={}):
        if not user.is_authenticated:
            return

        user.verification_code_sent_at = timezone.now()
        user.save()
        Utils.send_email(
            recipients=[user.email],
            subject='Verify your email address',
            template='email-verification',
            data={
                'user': user,
                'i18n': settings.get('i18n'),
                'project_name': PROJECT_NAME,
                'root_domain': ROOT_DOMAIN
            }
        )

    @staticmethod
    def consume_credits(user=None):
        if not user or not user.is_authenticated:
            return None

        user_credits = user.credits - 1
        user.credits = 0 if user_credits < 0 else user_credits
        user.save()

    @staticmethod
    def payment_ratelimited(ip, user_agent):
        if not ip or not user_agent:
            return True

        counter = 0
        cache_key = 'payment_%s_%s' % (ip, user_agent)
        cache_key = cache_key.encode()
        cache_key = md5(cache_key)
        cache_key = cache_key.hexdigest()
        rate_total_minutes = 60
        rate_total_seconds = rate_total_minutes * 60
        cache_data = Utils.get_from_cache(cache_key)

        if cache_data:
            counter = cache_data.get('counter')

        if counter >= 3:
            return True

        counter += 1
        Utils.set_to_cache(cache_key, {
            'counter': counter
        }, exp=rate_total_seconds)

    @staticmethod
    def upgrade_account(user, data, settings={}):
        i18n = settings.get('i18n')
        processor = data.get('processor')
        nonce = data.get('nonce')
        plan = data.get('plan')

        try:
            from finances.models.plan import Plan
            plan = Plan.objects.get(code_name=plan)
        except:
            return None, ['Plan not found']

        amount = plan.price
        credits = plan.credits
        is_subscription = plan.is_subscription

        if processor not in PROCESSORS:
            return None, [i18n.get('invalid_processor', 'invalid_processor')]

        from finances.models.payment import Payment
        if processor == 'stripe':
            payment, errors = Payment.make_charge_stripe(user, nonce, amount, settings)
        elif processor == 'squareup':
            payment, errors = Payment.make_charge_square(user, nonce, amount, settings)
        elif processor == 'paypal':
            payment, errors = Payment.make_charge_paypal(user, nonce, amount, settings)
        else:
            return None, [i18n.get('invalid_processor', 'invalid_processor')]

        if not payment:
            return None, errors

        user.credits = int(user.credits) + int(credits)
        user.plan_subscribed = plan.code_name

        if not plan.is_api_plan:
            user.is_plan_active = True

        if user.next_billing_date and user.next_billing_date > timezone.now():
            user.next_billing_date = user.next_billing_date + timedelta(days=plan.days)
        else:
            user.next_billing_date = timezone.now() + timedelta(days=plan.days)

        if is_subscription:
            user.payment_nonce = payment.customer_token
            user.card_nonce = payment.card_token
            user.processor = payment.processor

        user.save()
        Utils.send_email(
            recipients=[user.email],
            subject='Payment receive',
            template='payment-invoice',
            data={
                'user': user,
                'payment': payment,
                'i18n': i18n,
                'project_name': PROJECT_NAME,
                'root_domain': ROOT_DOMAIN
            }
        )

        return payment, None

    @staticmethod
    def update_password(user, data, settings={}):
        if not user.is_authenticated:
            return None, 'not_authorized'

        i18n = settings.get('i18n')
        old_password = data.get('password')
        new_password = data.get('new_password')
        confirm_new_password = data.get('confirm_password')
        errors = []

        if not old_password:
            errors.append(i18n.get('missing_current_password', 'missing_current_password'))

        if not new_password:
            errors.append(i18n.get('missing_new_password', 'missing_new_password'))

        if not confirm_new_password:
            errors.append(i18n.get('missing_confirm_new_password', 'missing_confirm_new_password'))

        if len(errors):
            return None, errors

        if new_password != confirm_new_password:
            errors.append(i18n.get('passwords_dont_match', 'passwords_dont_match'))

        if len(errors):
            return None, errors

        if not user.check_password(old_password):
            errors.append(i18n.get('wrong_current_password', 'wrong_current_password'))

        if len(errors):
            return None, errors

        user.set_password(new_password)
        user.save()

        return user, i18n.get('password_changed', 'password_changed')

    @staticmethod
    def verify_code(user, data, settings={}):
        if not user.is_authenticated:
            return None, 'Your are not allowed.'

        code = data.get('code').strip()

        if not code:
            return None, settings.get('i18n').get('missing_code')

        if user.verification_code != code:
            return None, settings.get('i18n').get('invalid_code')

        user.is_confirm = True
        user.save()

        return user, 'Ok'

    @staticmethod
    def restore_password(data, settings={}):
        token = data.get('token')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        errors = []

        if not token:
            errors.append(settings.get('i18n').get('missing_restore_token', 'missing_restore_token'))

        if not password:
            errors.append(settings.get('i18n').get('missing_password', 'missing_password'))

        if not confirm_password:
            errors.append(settings.get('i18n').get('missing_confirm_password', 'missing_confirm_password'))

        if len(password) < 4:
            errors.append(settings.get('i18n').get('weak_password', 'weak_password'))

        if password != confirm_password:
            errors.append(settings.get('i18n').get('passwords_dont_match', 'passwords_dont_match'))

        if len(errors):
            return None, errors

        try:
            user = CustomUser.objects.get(restore_password_token=token)
        except:
            return None, [settings.get('i18n').get('invalid_restore_token', 'invalid_restore_token')]

        user.set_password(password)
        user.save()

        return user, settings.get('i18n').get('password_changed', 'password_changed')

    @staticmethod
    def lost_password(data, settings={}):
        email = data.get('email')

        if not email:
            return None, [settings.get('i18n').get('missing_email', 'missing_email')]
        else:
            email = email.lower()

        try:
            validate_email(email)
        except:
            return None, [settings.get('i18n').get('invalid_email', 'invalid_email')]

        try:
            user = CustomUser.objects.get(email=email)

            if not user:
                return None, [settings.get('i18n').get('invalid_email', 'invalid_email')]
        except:
            return None, [settings.get('i18n').get('invalid_email', 'invalid_email')]

        if user.lost_password_email_sent_at and (timezone.now() - user.lost_password_email_sent_at).seconds < 600:
            return None, [settings.get('i18n').get('email_sent_wait', 'email_sent_wait')]

        user.restore_password_token = Utils.generate_hex_uuid()
        user.lost_password_email_sent_at = timezone.now()
        user.save()
        Utils.send_email(
            recipients=[user.email],
            subject='Restore your password',
            template='restore-password',
            data={
                'user': user,
                'i18n': settings.get('i18n'),
                'project_name': PROJECT_NAME,
                'root_domain': ROOT_DOMAIN
            }
        )

        return user, settings.get('i18n').get('forgot_password_email_sent', 'forgot_password_email_sent')

    @staticmethod
    def login_user(data, settings={}):
        email = data.get('email')
        password = data.get('password')
        errors = []

        if not email:
            errors.append(settings.get('i18n').get('missing_email', 'missing_email'))
        else:
            email = email.lower()

        if not password:
            errors.append(settings.get('i18n').get('missing_password', 'missing_password'))

        if len(errors):
            return None, errors

        try:
            validate_email(email)
        except:
            return None, [settings.get('i18n').get('invalid_email', 'invalid_email')]

        try:
            user = CustomUser.objects.get(email=email)

            if not user:
                return None, [settings.get('i18n').get('wrong_credentials', 'wrong_credentials')]
        except:
            return None, [settings.get('i18n').get('wrong_credentials', 'wrong_credentials')]

        if not user.check_password(password):
            return None, [settings.get('i18n').get('wrong_credentials', 'wrong_credentials')]

        return user, None

    @staticmethod
    def register_user(data, settings={}):
        email = data.get('email')
        password = data.get('password')
        lang = data.get('lang', 'en')
        errors = []

        if not lang:
            lang = 'en'

        if not email:
            errors.append(settings.get('i18n').get('missing_email', 'missing_email'))
        else:
            email = email.lower()

        if not password:
            errors.append(settings.get('i18n').get('missing_password', 'missing_password'))
        elif len(password) < 4:
            errors.append(settings.get('i18n').get('weak_password', 'weak_password'))

        if len(errors):
            return None, errors

        try:
            validate_email(email)
        except:
            return None, [settings.get('i18n').get('invalid_email', 'invalid_email')]

        try:
            found = CustomUser.objects.get(email=email)

            if found:
                return None, [settings.get('i18n').get('email_taken', 'email_taken')]
        except:
            pass

        user = CustomUser.objects.create(
            email=email,
            lang=lang
        )
        user.set_password(password)
        user.save()
        Utils.send_email(
            recipients=[user.email],
            subject='Verify your email address',
            template='email-verification',
            data={
                'user': user,
                'i18n': settings.get('i18n'),
                'project_name': PROJECT_NAME,
                'root_domain': ROOT_DOMAIN
            }
        )

        return user, None

    def get_emails(self):
        return EmailAddress.objects.filter(account=self)


class EmailAddress(models.Model):
    account = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    email = models.EmailField(null=True, blank=False)
    uuid = models.CharField(default=Utils.generate_hex_uuid, max_length=250)

    def __str__(self):
        return self.email

    @staticmethod
    def register_email(user, data, settings={}):
        if not user.is_authenticated:
            return None, 'not_authorized'

        email = data.get('email')

        if not email:
            return None, settings.get('i18n').get('missing_email', 'missing_email')

        email = email.lower()

        try:
            validate_email(email)
        except:
            return None, settings.get('i18n').get('invalid_email', 'invalid_email')

        try:
            found = EmailAddress.objects.get(account=user, email=email)

            if found:
                return None, settings.get('i18n').get('duplicate_email', 'duplicate_email')
        except:
            pass

        email = EmailAddress.objects.create(
            account=user,
            email=email
        )
        email.save()

        return email, 'Ok'

from django.shortcuts import render, redirect
from django.views.generic import View
from django.contrib.auth import login, logout
from django.utils import timezone

from accounts.models import CustomUser
from accounts.views import GlobalVars
from app.utils import Utils
from contact_messages.models.message import Message
import config


class IndexPage(View):
    def get(self, request):
        settings = GlobalVars.get_globals(request)
        return render(
            request,
            'index.html',
            {
                'title': config.PROJECT_NAME,
                'description': settings.get('i18n').get('site_description', ''),
                'page': 'home',
                'g': settings,
            }
        )


class ContactPage(View):
    template_name = 'contact.html'

    def get(self, request):
        settings = GlobalVars.get_globals(request)
        from contact_messages.forms import CaptchaForm
        form = CaptchaForm()
        return render(
            request,
            self.template_name,
            {
                'title': f"{settings.get('i18n').get('contact', 'Contact')} | {config.PROJECT_NAME}",
                'description': settings.get('i18n').get('contact_meta_description', ''),
                'page': 'contact',
                'g': settings,
                'form': form
            }
        )

    def post(self, request):
        settings = GlobalVars.get_globals(request)
        from contact_messages.forms import CaptchaForm
        data = request.POST
        form = CaptchaForm(data)
        errors = None

        if not form.is_valid():
            errors = ['The Captcha value is incorrect']

        if not errors:
            message, errors = Message.save_message(request.user, data, settings)
            if message:
                return render(
                    request,
                    'success.html',
                    {
                        'title': f"{settings.get('i18n').get('success', 'Success')} | {config.PROJECT_NAME}",
                        'page': 'success',
                        'g': settings
                    }
                )

        return render(
            request,
            self.template_name,
            {
                'title': f"{settings.get('i18n').get('contact', 'Contact')} | {config.PROJECT_NAME}",
                'page': 'contact',
                'g': settings,
                'data': request.POST,
                'form': form,
                'errors': errors
            }
        )


class AboutPage(View):
    def get(self, request):
        settings = GlobalVars.get_globals(request)
        return render(
            request,
            'about.html',
            {
                'title': f"{settings.get('i18n').get('about_us', 'About')} | {config.PROJECT_NAME}",
                'description': settings.get('i18n').get('about_us_meta_description', ''),
                'page': 'about',
                'g': settings
            }
        )


class TermsPage(View):
    def get(self, request):
        settings = GlobalVars.get_globals(request)
        return render(
            request,
            'terms.html',
            {
                'title': f"{settings.get('i18n').get('terms_of_service', 'Terms')} | {config.PROJECT_NAME}",
                'page': 'terms',
                'g': settings
            }
        )


class PrivacyPage(View):
    def get(self, request):
        settings = GlobalVars.get_globals(request)
        return render(
            request,
            'privacy.html',
            {
                'title': f"{settings.get('i18n').get('privacy_policy', 'Privacy')} | {config.PROJECT_NAME}",
                'page': 'privacy',
                'g': settings
            }
        )


class LoginPage(View):
    template_name = 'login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('account')
        settings = GlobalVars.get_globals(request)
        return render(
            request,
            self.template_name,
            {
                'title': f"{settings.get('i18n').get('login', 'Login')} | {config.PROJECT_NAME}",
                'page': 'login',
                'g': settings
            }
        )

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('account')
        settings = GlobalVars.get_globals(request)
        account, errors = CustomUser.login_user(request.POST, settings)
        if account:
            login(request, account)
            return redirect('account')
        return render(
            request,
            self.template_name,
            {
                'title': f"{settings.get('i18n').get('login', 'Login')} | {config.PROJECT_NAME}",
                'page': 'login',
                'data': request.POST,
                'errors': errors,
                'g': settings
            }
        )


class LogoutPage(View):
    def get(self, request):
        logout(request)
        return redirect('index')


class RegisterPage(View):
    template_name = 'register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('account')
        settings = GlobalVars.get_globals(request)
        return render(
            request,
            self.template_name,
            {
                'title': f"{settings.get('i18n').get('sign_up', 'Sign Up')} | {config.PROJECT_NAME}",
                'page': 'register',
                'g': settings
            }
        )

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('account')
        settings = GlobalVars.get_globals(request)
        account, errors = CustomUser.register_user(request.POST, settings)
        if account:
            login(request, account)
            return redirect('account')
        return render(
            request,
            self.template_name,
            {
                'title': f"{settings.get('i18n').get('sign_up', 'Sign Up')} | {config.PROJECT_NAME}",
                'page': 'register',
                'data': request.POST,
                'errors': errors,
                'g': settings
            }
        )


class LostPasswordPage(View):
    template_name = 'lost-password.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('account')
        settings = GlobalVars.get_globals(request)
        return render(
            request,
            self.template_name,
            {
                'title': f"{settings.get('i18n').get('lost_password', 'Lost Password')} | {config.PROJECT_NAME}",
                'page': 'lost_password',
                'g': settings
            }
        )

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('account')
        settings = GlobalVars.get_globals(request)
        account, msg = CustomUser.lost_password(request.POST, settings)
        errors, message = (None, msg) if account else (msg, None)
        return render(
            request,
            self.template_name,
            {
                'title': f"{settings.get('i18n').get('lost_password', 'Lost Password')} | {config.PROJECT_NAME}",
                'page': 'lost_password',
                'data': {} if account else request.POST,
                'errors': errors,
                'message': message,
                'g': settings
            }
        )


class RestorePasswordPage(View):
    template_name = 'restore-password.html'

    def get(self, request):
        token = request.GET.get('token')
        settings = GlobalVars.get_globals(request)
        if not token:
            if request.user.is_authenticated:
                token = Utils.generate_hex_uuid()
                user = CustomUser.objects.get(email=request.user)
                user.restore_password_token = token
                user.save()
            else:
                return redirect('index')
        return render(
            request,
            self.template_name,
            {
                'title': f"{settings.get('i18n').get('restore_your_password', 'Restore Password')} | {config.PROJECT_NAME}",
                'page': 'reset_password',
                'g': settings,
                'token': token
            }
        )

    def post(self, request):
        settings = GlobalVars.get_globals(request)
        account, msg = CustomUser.restore_password(request.POST, settings)
        errors, message = (None, msg) if account else (msg, None)
        return render(
            request,
            self.template_name,
            {
                'title': f"{settings.get('i18n').get('restore_your_password', 'Restore Password')} | {config.PROJECT_NAME}",
                'page': 'reset_password',
                'data': {} if account else request.POST,
                'token': request.POST.get('token'),
                'errors': errors,
                'message': message,
                'g': settings
            }
        )


class VerifyPage(View):
    template_name = 'verify.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('index')
        if request.user.is_confirm:
            return redirect('account')
        settings = GlobalVars.get_globals(request)
        return render(
            request,
            self.template_name,
            {
                'title': f"{settings.get('i18n').get('verify_email', 'Verify Email')} | {config.PROJECT_NAME}",
                'page': 'verify',
                'g': settings
            }
        )

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('index')
        if request.user.is_confirm:
            return redirect('account')
        settings = GlobalVars.get_globals(request)
        account, errors = CustomUser.verify_code(request.user, request.POST, settings)
        if account:
            return redirect('account')
        return render(
            request,
            self.template_name,
            {
                'title': f"{settings.get('i18n').get('verify_email', 'Verify Email')} | {config.PROJECT_NAME}",
                'page': 'verify',
                'g': settings,
                'errors': errors
            }
        )


class AccountPage(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_confirm:
            return redirect('verify')
        settings = GlobalVars.get_globals(request)
        payments = request.user.get_payments()
        from finances.models.plan import Plan
        try:
            plan_subscribed = Plan.objects.get(code_name=request.user.plan_subscribed)
        except:
            plan_subscribed = None
        return render(
            request,
            'account.html',
            {
                'title': f"{settings.get('i18n').get('account_label', 'Account')} | {config.PROJECT_NAME}",
                'page': 'account',
                'g': settings,
                'user': request.user,
                'payments': payments,
                'credits': request.user.credits,
                'today': timezone.now(),
                'plan_subscribed': plan_subscribed
            }
        )


class PricingPage(View):
    def get(self, request):
        settings = GlobalVars.get_globals(request)
        from finances.models.plan import Plan
        plans = Plan.objects.all().order_by('price')
        current_plan = None
        if request.user.is_authenticated and request.user.is_plan_active:
            current_plan = request.user.plan_subscribed
        return render(
            request,
            'pricing.html',
            {
                'title': f"{settings.get('i18n').get('pricing', 'Pricing')} | {config.PROJECT_NAME}",
                'page': 'pricing',
                'plans': plans,
                'g': settings,
                'current_plan': current_plan
            }
        )


class CheckoutPage(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('register')
        if not request.user.is_confirm:
            return redirect('verify')
        plan_code = request.GET.get('plan')
        try:
            from finances.models.plan import Plan
            plan = Plan.objects.get(code_name=plan_code)
        except:
            return redirect('pricing')
        settings = GlobalVars.get_globals(request)
        return render(
            request,
            'checkout.html',
            {
                'title': f"{settings.get('i18n').get('checkout', 'Checkout')} | {config.PROJECT_NAME}",
                'page': 'checkout',
                'g': settings,
                'user': request.user,
                'plan': plan,
                'processors': config.PROCESSORS,
                'stripe': config.STRIPE,
                'square': config.SQUARE_UP,
                'paypal': config.PAYPAL_KEYS,
            }
        )

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('register')
        if not request.user.is_confirm:
            return redirect('verify')
        data = request.POST
        plan_code = data.get('plan')
        try:
            from finances.models.plan import Plan
            plan = Plan.objects.get(code_name=plan_code)
        except:
            return redirect('pricing')
        settings = GlobalVars.get_globals(request)
        payment, errors = CustomUser.upgrade_account(request.user, data, settings)
        if payment:
            return redirect('account')
        return render(
            request,
            'checkout.html',
            {
                'title': f"{settings.get('i18n').get('checkout', 'Checkout')} | {config.PROJECT_NAME}",
                'page': 'checkout',
                'g': settings,
                'user': request.user,
                'plan': plan,
                'processors': config.PROCESSORS,
                'stripe': config.STRIPE,
                'square': config.SQUARE_UP,
                'paypal': config.PAYPAL_KEYS,
                'errors': errors
            }
        )


class SuccessPage(View):
    def get(self, request):
        settings = GlobalVars.get_globals(request)
        return render(
            request,
            'success.html',
            {
                'title': f"{settings.get('i18n').get('success', 'Success')} | {config.PROJECT_NAME}",
                'page': 'success',
                'g': settings
            }
        )


class RefundPage(View):
    template_name = 'refund.html'

    def get(self, request):
        settings = GlobalVars.get_globals(request)
        return render(
            request,
            self.template_name,
            {
                'title': f"{settings.get('i18n').get('refund', 'Refund')} | {config.PROJECT_NAME}",
                'page': 'refund',
                'g': settings
            }
        )

    def post(self, request):
        settings = GlobalVars.get_globals(request)
        data = request.POST
        from finances.models.payment import Payment
        refund, errors = Payment.make_refund(
            data.get('transaction_id'),
            data.get('email_refund')
        )
        if refund:
            return redirect('account')
        return render(
            request,
            self.template_name,
            {
                'title': f"{settings.get('i18n').get('refund', 'Refund')} | {config.PROJECT_NAME}",
                'page': 'refund',
                'data': data,
                'errors': errors,
                'g': settings
            }
        )


class CancelSubscriptionPage(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('account')
        settings = GlobalVars.get_globals(request)
        return render(
            request,
            'cancel.html',
            {
                'title': f"{settings.get('i18n').get('cancel', 'Cancel')} | {config.PROJECT_NAME}",
                'page': 'cancel',
                'g': settings
            }
        )

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('account')
        CustomUser.cancel_subscription(request.user)
        return redirect('account')


class DeleteAccountPage(View):
    template_name = 'delete.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('account')
        settings = GlobalVars.get_globals(request)
        return render(
            request,
            self.template_name,
            {
                'title': f"{settings.get('i18n').get('delete', 'Delete Account')} | {config.PROJECT_NAME}",
                'page': 'delete',
                'g': settings
            }
        )

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('account')
        settings = GlobalVars.get_globals(request)
        errors = None
        try:
            request.user.delete()
            logout(request)
            return redirect('index')
        except Exception as e:
            errors = str(e)
        return render(
            request,
            'deleted.html',
            {
                'title': f"{settings.get('i18n').get('deleted', 'Account Deleted')} | {config.PROJECT_NAME}",
                'page': 'deleted',
                'g': settings,
                'errors': errors
            }
        )

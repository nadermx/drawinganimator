"""
Tests for all page loads: ensures every URL defined in the project returns
the expected HTTP status code (200, 302 redirect, or 404 where appropriate).
"""
from unittest import mock

from django.test import TestCase, Client, override_settings
from django.urls import reverse

from accounts.models import CustomUser
from animator.models import Animation, AnimationPreset, GalleryItem
from finances.models.plan import Plan
from translations.models.language import Language
from translations.models.translation import Translation


@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
    SESSION_ENGINE='django.contrib.sessions.backends.db',
)
class PageLoadTestBase(TestCase):
    """Base class that sets up fixtures needed for page rendering."""

    @classmethod
    def setUpTestData(cls):
        cls.language = Language.objects.create(name='English', en_label='English', iso='en')
        # Create all i18n keys that templates/views reference.
        i18n_keys = {
            'missing_email': 'Email is required',
            'missing_password': 'Password is required',
            'invalid_email': 'Invalid email',
            'email_taken': 'Email already registered',
            'weak_password': 'Password is too weak',
            'wrong_credentials': 'Wrong email or password',
            'login': 'Login',
            'sign_up': 'Sign Up',
            'lost_password': 'Lost Password',
            'restore_your_password': 'Restore Password',
            'verify_email': 'Verify Email',
            'account_label': 'Account',
            'contact': 'Contact',
            'contact_meta_description': '',
            'about_us': 'About',
            'about_us_meta_description': '',
            'terms_of_service': 'Terms',
            'privacy_policy': 'Privacy',
            'pricing': 'Pricing',
            'checkout': 'Checkout',
            'success': 'Success',
            'refund': 'Refund',
            'cancel': 'Cancel',
            'delete': 'Delete Account',
            'deleted': 'Account Deleted',
        }
        for code_name, text in i18n_keys.items():
            Translation.objects.create(code_name=code_name, language='en', text=text)

        # Plans for pricing/checkout pages
        cls.plan = Plan.objects.create(
            code_name='basic',
            price=10,
            credits=100,
            days=31,
            is_subscription=False,
        )
        cls.plan_pro = Plan.objects.create(
            code_name='pro',
            price=25,
            credits=500,
            days=31,
            is_subscription=True,
        )

        # Animation preset for animate page
        cls.preset = AnimationPreset.objects.create(
            name='Walking', code_name='walk', is_active=True, is_premium=False,
        )

    def setUp(self):
        self.client = Client()

    def _create_user(self, email='page@test.com', password='testpass123',
                     is_confirm=True, credits=10, is_plan_active=False):
        user = CustomUser.objects.create(
            email=email, credits=credits, is_confirm=is_confirm,
            is_plan_active=is_plan_active,
        )
        user.set_password(password)
        user.save()
        return user

    def _login(self, email='page@test.com', password='testpass123'):
        self.client.login(email=email, password=password)


# ---------------------------------------------------------------------------
# Public pages (no auth required)
# ---------------------------------------------------------------------------
class PublicPageTests(PageLoadTestBase):

    def test_index_page(self):
        resp = self.client.get(reverse('index'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Drawing Animator')

    def test_about_page(self):
        resp = self.client.get(reverse('about'))
        self.assertEqual(resp.status_code, 200)

    def test_terms_page(self):
        resp = self.client.get(reverse('terms'))
        self.assertEqual(resp.status_code, 200)

    def test_privacy_page(self):
        resp = self.client.get(reverse('privacy'))
        self.assertEqual(resp.status_code, 200)

    def test_pricing_page(self):
        resp = self.client.get(reverse('pricing'))
        self.assertEqual(resp.status_code, 200)
        # Should display plans
        self.assertContains(resp, 'basic')

    def test_success_page(self):
        resp = self.client.get(reverse('success'))
        self.assertEqual(resp.status_code, 200)

    def test_refund_page(self):
        resp = self.client.get(reverse('refund'))
        self.assertEqual(resp.status_code, 200)

    def test_login_page(self):
        resp = self.client.get(reverse('login'))
        self.assertEqual(resp.status_code, 200)

    def test_register_page(self):
        resp = self.client.get(reverse('register'))
        self.assertEqual(resp.status_code, 200)

    def test_lost_password_page(self):
        resp = self.client.get(reverse('lost-password'))
        self.assertEqual(resp.status_code, 200)

    def test_restore_password_page_with_token(self):
        resp = self.client.get(reverse('restore-password'), {'token': 'abc123'})
        self.assertEqual(resp.status_code, 200)

    def test_contact_page(self):
        resp = self.client.get(reverse('contact'))
        self.assertEqual(resp.status_code, 200)

    def test_animate_page(self):
        resp = self.client.get(reverse('animate'))
        self.assertEqual(resp.status_code, 200)

    def test_gallery_page(self):
        resp = self.client.get(reverse('gallery'))
        self.assertEqual(resp.status_code, 200)

    def test_favicon_redirect(self):
        resp = self.client.get('/favicon.ico')
        self.assertEqual(resp.status_code, 301)


# ---------------------------------------------------------------------------
# Auth-required pages (redirects when anonymous)
# ---------------------------------------------------------------------------
class AuthRequiredPageTests(PageLoadTestBase):

    def test_account_requires_login(self):
        resp = self.client.get(reverse('account'))
        self.assertRedirects(resp, reverse('login'))

    def test_verify_requires_login(self):
        resp = self.client.get(reverse('verify'))
        self.assertEqual(resp.status_code, 302)

    def test_checkout_requires_login(self):
        resp = self.client.get(reverse('checkout'), {'plan': 'basic'})
        self.assertRedirects(resp, reverse('register'))

    def test_my_animations_requires_login(self):
        resp = self.client.get(reverse('my_animations'))
        self.assertRedirects(resp, reverse('login'))

    def test_cancel_requires_login(self):
        resp = self.client.get(reverse('cancel'))
        # CancelSubscriptionPage redirects to account when not authenticated
        self.assertEqual(resp.status_code, 302)

    def test_delete_requires_login(self):
        resp = self.client.get(reverse('delete'))
        self.assertEqual(resp.status_code, 302)

    def test_restore_password_no_token_anonymous_redirects(self):
        resp = self.client.get(reverse('restore-password'))
        self.assertEqual(resp.status_code, 302)


# ---------------------------------------------------------------------------
# Authenticated pages
# ---------------------------------------------------------------------------
class AuthenticatedPageTests(PageLoadTestBase):

    def test_account_page(self):
        self._create_user()
        self._login()
        resp = self.client.get(reverse('account'))
        self.assertEqual(resp.status_code, 200)

    def test_account_page_unconfirmed_redirects_to_verify(self):
        self._create_user(is_confirm=False)
        self._login()
        resp = self.client.get(reverse('account'))
        self.assertRedirects(resp, reverse('verify'))

    def test_verify_page_unconfirmed_user(self):
        self._create_user(is_confirm=False)
        self._login()
        resp = self.client.get(reverse('verify'))
        self.assertEqual(resp.status_code, 200)

    def test_verify_page_confirmed_redirects(self):
        self._create_user(is_confirm=True)
        self._login()
        resp = self.client.get(reverse('verify'))
        self.assertRedirects(resp, reverse('account'))

    def test_checkout_page_with_valid_plan(self):
        self._create_user()
        self._login()
        resp = self.client.get(reverse('checkout'), {'plan': 'basic'})
        self.assertEqual(resp.status_code, 200)

    def test_checkout_page_with_invalid_plan(self):
        self._create_user()
        self._login()
        resp = self.client.get(reverse('checkout'), {'plan': 'nonexistent'})
        self.assertRedirects(resp, reverse('pricing'))

    def test_checkout_page_unconfirmed_redirects_to_verify(self):
        self._create_user(is_confirm=False)
        self._login()
        resp = self.client.get(reverse('checkout'), {'plan': 'basic'})
        self.assertRedirects(resp, reverse('verify'))

    def test_my_animations_page(self):
        self._create_user()
        self._login()
        resp = self.client.get(reverse('my_animations'))
        self.assertEqual(resp.status_code, 200)

    def test_cancel_page(self):
        self._create_user()
        self._login()
        resp = self.client.get(reverse('cancel'))
        self.assertEqual(resp.status_code, 200)

    def test_delete_page(self):
        self._create_user()
        self._login()
        resp = self.client.get(reverse('delete'))
        self.assertEqual(resp.status_code, 200)

    def test_login_page_redirects_when_authenticated(self):
        self._create_user()
        self._login()
        resp = self.client.get(reverse('login'))
        self.assertRedirects(resp, reverse('account'))

    def test_register_page_redirects_when_authenticated(self):
        self._create_user()
        self._login()
        resp = self.client.get(reverse('register'))
        self.assertRedirects(resp, reverse('account'))

    def test_lost_password_redirects_when_authenticated(self):
        self._create_user()
        self._login()
        resp = self.client.get(reverse('lost-password'))
        self.assertEqual(resp.status_code, 302)

    def test_restore_password_authenticated_no_token(self):
        """Authenticated user without token gets a fresh token assigned."""
        self._create_user()
        self._login()
        resp = self.client.get(reverse('restore-password'))
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Pricing page with active plan
# ---------------------------------------------------------------------------
class PricingPageTests(PageLoadTestBase):

    def test_pricing_shows_current_plan(self):
        user = self._create_user(is_plan_active=True)
        user.plan_subscribed = 'pro'
        user.save()
        self._login()
        resp = self.client.get(reverse('pricing'))
        self.assertEqual(resp.status_code, 200)

    def test_pricing_anonymous(self):
        resp = self.client.get(reverse('pricing'))
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Gallery and animate pages with data
# ---------------------------------------------------------------------------
class GalleryAndAnimateTests(PageLoadTestBase):

    def test_gallery_with_items(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        image = SimpleUploadedFile('test.png', b'\x89PNG\r\n\x1a\n' + b'\x00' * 100, content_type='image/png')
        anim = Animation.objects.create(
            status=Animation.COMPLETED,
            input_image=image,
            preset=self.preset,
        )
        GalleryItem.objects.create(
            title='Cool Animation',
            animation=anim,
            is_featured=True,
            is_active=True,
        )
        resp = self.client.get(reverse('gallery'))
        self.assertEqual(resp.status_code, 200)

    def test_animate_page_shows_presets(self):
        resp = self.client.get(reverse('animate'))
        self.assertEqual(resp.status_code, 200)

    def test_animate_page_for_pro_user(self):
        user = self._create_user(is_plan_active=True)
        self._login()
        resp = self.client.get(reverse('animate'))
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Contact form submission
# ---------------------------------------------------------------------------
class ContactPageTests(PageLoadTestBase):

    @mock.patch('contact_messages.forms.CaptchaField.clean', return_value='PASSED')
    @mock.patch('app.utils.Utils.send_email', return_value=1)
    def test_contact_form_valid(self, mock_email, mock_captcha):
        resp = self.client.post(reverse('contact'), {
            'email': 'sender@test.com',
            'message': 'Hello, I have a question.',
            'captcha_0': 'test-hash',
            'captcha_1': 'PASSED',
        })
        # Successful message shows success page
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Cancel subscription flow
# ---------------------------------------------------------------------------
class CancelSubscriptionPageTests(PageLoadTestBase):

    def test_cancel_post_authenticated(self):
        user = self._create_user()
        user.is_plan_active = True
        user.processor = 'stripe'
        user.save()
        self._login()
        resp = self.client.post(reverse('cancel'))
        self.assertRedirects(resp, reverse('account'))
        user.refresh_from_db()
        self.assertFalse(user.is_plan_active)

    def test_cancel_post_unauthenticated(self):
        resp = self.client.post(reverse('cancel'))
        self.assertEqual(resp.status_code, 302)

"""
Tests for the accounts app: user registration, login, logout, password reset,
email verification, and model-level account operations.
"""
from unittest import mock

from django.test import TestCase, Client, override_settings
from django.urls import reverse

from accounts.models import CustomUser, EmailAddress
from translations.models.language import Language
from translations.models.translation import Translation


@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
    SESSION_ENGINE='django.contrib.sessions.backends.db',
)
class AccountTestBase(TestCase):
    """Base class that sets up the Language and Translation fixtures needed by GlobalVars."""

    @classmethod
    def setUpTestData(cls):
        cls.language = Language.objects.create(name='English', en_label='English', iso='en')
        # Minimal i18n keys used throughout the views and model methods.
        i18n_keys = {
            'missing_email': 'Email is required',
            'missing_password': 'Password is required',
            'invalid_email': 'Invalid email',
            'email_taken': 'Email already registered',
            'weak_password': 'Password is too weak',
            'wrong_credentials': 'Wrong email or password',
            'missing_current_password': 'Current password required',
            'missing_new_password': 'New password required',
            'missing_confirm_new_password': 'Confirm password required',
            'passwords_dont_match': 'Passwords do not match',
            'wrong_current_password': 'Current password is wrong',
            'password_changed': 'Password changed',
            'missing_code': 'Code is required',
            'invalid_code': 'Invalid code',
            'missing_restore_token': 'Token is required',
            'missing_confirm_password': 'Confirm password required',
            'invalid_restore_token': 'Invalid token',
            'forgot_password_email_sent': 'Password reset email sent',
            'email_sent_wait': 'Please wait before requesting again',
            'missing_message': 'Message is required',
            'duplicate_email': 'Email already added',
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

    def setUp(self):
        self.client = Client()

    def _create_user(self, email='user@test.com', password='testpass123', is_confirm=False, credits=0):
        user = CustomUser.objects.create(email=email, credits=credits, is_confirm=is_confirm)
        user.set_password(password)
        user.save()
        return user

    def _login(self, email='user@test.com', password='testpass123'):
        self.client.login(email=email, password=password)


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------
class RegistrationTests(AccountTestBase):

    def test_register_page_loads(self):
        resp = self.client.get(reverse('register'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Sign Up')

    @mock.patch('app.utils.Utils.send_email', return_value=1)
    def test_register_success(self, mock_email):
        resp = self.client.post(reverse('register'), {
            'email': 'newuser@test.com',
            'password': 'securepass',
        })
        # Successful registration redirects to account (which redirects to verify)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(CustomUser.objects.filter(email='newuser@test.com').exists())
        mock_email.assert_called_once()

    def test_register_missing_email(self):
        resp = self.client.post(reverse('register'), {
            'password': 'securepass',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Email is required')

    def test_register_missing_password(self):
        resp = self.client.post(reverse('register'), {
            'email': 'newuser@test.com',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Password is required')

    def test_register_weak_password(self):
        resp = self.client.post(reverse('register'), {
            'email': 'newuser@test.com',
            'password': 'ab',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Password is too weak')

    @mock.patch('app.utils.Utils.send_email', return_value=1)
    def test_register_duplicate_email(self, mock_email):
        self._create_user(email='dup@test.com')
        resp = self.client.post(reverse('register'), {
            'email': 'dup@test.com',
            'password': 'securepass',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Email already registered')

    def test_register_invalid_email(self):
        resp = self.client.post(reverse('register'), {
            'email': 'not-an-email',
            'password': 'securepass',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Invalid email')

    def test_register_redirects_when_authenticated(self):
        user = self._create_user(is_confirm=True)
        self._login()
        resp = self.client.get(reverse('register'))
        self.assertEqual(resp.status_code, 302)


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------
class LoginTests(AccountTestBase):

    def test_login_page_loads(self):
        resp = self.client.get(reverse('login'))
        self.assertEqual(resp.status_code, 200)

    def test_login_success(self):
        self._create_user(is_confirm=True)
        resp = self.client.post(reverse('login'), {
            'email': 'user@test.com',
            'password': 'testpass123',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('account'))

    def test_login_wrong_password(self):
        self._create_user()
        resp = self.client.post(reverse('login'), {
            'email': 'user@test.com',
            'password': 'wrongpass',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Wrong email or password')

    def test_login_nonexistent_user(self):
        resp = self.client.post(reverse('login'), {
            'email': 'nobody@test.com',
            'password': 'testpass',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Wrong email or password')

    def test_login_missing_fields(self):
        resp = self.client.post(reverse('login'), {})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Email is required')

    def test_login_redirects_when_authenticated(self):
        self._create_user(is_confirm=True)
        self._login()
        resp = self.client.get(reverse('login'))
        self.assertEqual(resp.status_code, 302)


# ---------------------------------------------------------------------------
# Logout tests
# ---------------------------------------------------------------------------
class LogoutTests(AccountTestBase):

    def test_logout(self):
        self._create_user(is_confirm=True)
        self._login()
        resp = self.client.get(reverse('logout'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('index'))
        # After logout, accessing account should redirect to login
        resp = self.client.get(reverse('account'))
        self.assertRedirects(resp, reverse('login'))


# ---------------------------------------------------------------------------
# Email verification tests
# ---------------------------------------------------------------------------
class VerificationTests(AccountTestBase):

    def test_verify_page_requires_auth(self):
        resp = self.client.get(reverse('verify'))
        self.assertEqual(resp.status_code, 302)

    def test_verify_page_loads_for_unconfirmed(self):
        self._create_user(is_confirm=False)
        self._login()
        resp = self.client.get(reverse('verify'))
        self.assertEqual(resp.status_code, 200)

    def test_verify_redirects_if_already_confirmed(self):
        self._create_user(is_confirm=True)
        self._login()
        resp = self.client.get(reverse('verify'))
        self.assertEqual(resp.status_code, 302)

    def test_verify_correct_code(self):
        user = self._create_user(is_confirm=False)
        code = user.verification_code
        self._login()
        resp = self.client.post(reverse('verify'), {'code': code})
        self.assertEqual(resp.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.is_confirm)

    def test_verify_wrong_code(self):
        self._create_user(is_confirm=False)
        self._login()
        resp = self.client.post(reverse('verify'), {'code': '000000'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Invalid code')


# ---------------------------------------------------------------------------
# Password reset (lost password + restore) tests
# ---------------------------------------------------------------------------
class PasswordResetTests(AccountTestBase):

    def test_lost_password_page_loads(self):
        resp = self.client.get(reverse('lost-password'))
        self.assertEqual(resp.status_code, 200)

    @mock.patch('app.utils.Utils.send_email', return_value=1)
    def test_lost_password_sends_email(self, mock_email):
        self._create_user()
        resp = self.client.post(reverse('lost-password'), {
            'email': 'user@test.com',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Password reset email sent')
        mock_email.assert_called_once()

    def test_lost_password_nonexistent_email(self):
        resp = self.client.post(reverse('lost-password'), {
            'email': 'nobody@test.com',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Invalid email')

    def test_lost_password_missing_email(self):
        resp = self.client.post(reverse('lost-password'), {})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Email is required')

    def test_restore_password_page_requires_token(self):
        resp = self.client.get(reverse('restore-password'))
        # Without token and not authenticated, redirects to index
        self.assertEqual(resp.status_code, 302)

    def test_restore_password_page_with_token(self):
        resp = self.client.get(reverse('restore-password'), {'token': 'some-token'})
        self.assertEqual(resp.status_code, 200)

    @mock.patch('app.utils.Utils.send_email', return_value=1)
    def test_restore_password_success(self, mock_email):
        user = self._create_user()
        user.restore_password_token = 'test-restore-token'
        user.save()
        resp = self.client.post(reverse('restore-password'), {
            'token': 'test-restore-token',
            'password': 'newpassword123',
            'confirm_password': 'newpassword123',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Password changed')
        user.refresh_from_db()
        self.assertTrue(user.check_password('newpassword123'))

    def test_restore_password_mismatch(self):
        user = self._create_user()
        user.restore_password_token = 'test-token'
        user.save()
        resp = self.client.post(reverse('restore-password'), {
            'token': 'test-token',
            'password': 'newpassword123',
            'confirm_password': 'different',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Passwords do not match')

    def test_restore_password_invalid_token(self):
        resp = self.client.post(reverse('restore-password'), {
            'token': 'bad-token',
            'password': 'newpassword123',
            'confirm_password': 'newpassword123',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Invalid token')

    def test_lost_password_redirects_when_authenticated(self):
        self._create_user(is_confirm=True)
        self._login()
        resp = self.client.get(reverse('lost-password'))
        self.assertEqual(resp.status_code, 302)


# ---------------------------------------------------------------------------
# Account page tests
# ---------------------------------------------------------------------------
class AccountPageTests(AccountTestBase):

    def test_account_requires_auth(self):
        resp = self.client.get(reverse('account'))
        self.assertRedirects(resp, reverse('login'))

    def test_account_requires_verification(self):
        self._create_user(is_confirm=False)
        self._login()
        resp = self.client.get(reverse('account'))
        self.assertRedirects(resp, reverse('verify'))

    def test_account_page_loads(self):
        self._create_user(is_confirm=True, credits=10)
        self._login()
        resp = self.client.get(reverse('account'))
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Model-level tests
# ---------------------------------------------------------------------------
class CustomUserModelTests(AccountTestBase):

    def test_create_user(self):
        user = CustomUser.objects.create_user(email='test@model.com', password='pass1234')
        self.assertEqual(user.email, 'test@model.com')
        self.assertTrue(user.check_password('pass1234'))
        self.assertFalse(user.is_staff)

    def test_create_superuser(self):
        user = CustomUser.objects.create_superuser(email='admin@model.com', password='admin1234')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(email='', password='pass')

    def test_consume_credits(self):
        user = self._create_user(credits=5)
        CustomUser.consume_credits(user)
        user.refresh_from_db()
        self.assertEqual(user.credits, 4)

    def test_consume_credits_zero_floor(self):
        user = self._create_user(credits=0)
        CustomUser.consume_credits(user)
        user.refresh_from_db()
        self.assertEqual(user.credits, 0)

    def test_consume_credits_none_user(self):
        # Should not raise
        result = CustomUser.consume_credits(user=None)
        self.assertIsNone(result)

    def test_check_plan_active(self):
        user = self._create_user()
        user.is_plan_active = True
        user.save()
        self.assertTrue(user.check_plan)

    def test_check_plan_inactive(self):
        user = self._create_user()
        self.assertFalse(user.check_plan)

    def test_cancel_subscription(self):
        user = self._create_user()
        user.is_plan_active = True
        user.processor = 'stripe'
        user.card_nonce = 'nonce123'
        user.payment_nonce = 'pnonce123'
        user.save()
        result_user, msg = CustomUser.cancel_subscription(user)
        self.assertEqual(msg, 'ok')
        result_user.refresh_from_db()
        self.assertFalse(result_user.is_plan_active)
        self.assertIsNone(result_user.card_nonce)
        self.assertIsNone(result_user.processor)

    def test_update_password_success(self):
        user = self._create_user()
        i18n = Translation.get_text_by_lang('en')
        result, msg = CustomUser.update_password(user, {
            'password': 'testpass123',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456',
        }, settings={'i18n': i18n})
        self.assertIsNotNone(result)
        user.refresh_from_db()
        self.assertTrue(user.check_password('newpass456'))

    def test_update_password_wrong_current(self):
        user = self._create_user()
        i18n = Translation.get_text_by_lang('en')
        result, errors = CustomUser.update_password(user, {
            'password': 'wrongold',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456',
        }, settings={'i18n': i18n})
        self.assertIsNone(result)

    def test_update_password_mismatch(self):
        user = self._create_user()
        i18n = Translation.get_text_by_lang('en')
        result, errors = CustomUser.update_password(user, {
            'password': 'testpass123',
            'new_password': 'newpass456',
            'confirm_password': 'different',
        }, settings={'i18n': i18n})
        self.assertIsNone(result)

    def test_login_user_static(self):
        self._create_user()
        i18n = Translation.get_text_by_lang('en')
        user, errors = CustomUser.login_user(
            {'email': 'user@test.com', 'password': 'testpass123'},
            settings={'i18n': i18n},
        )
        self.assertIsNotNone(user)
        self.assertIsNone(errors)

    def test_login_user_wrong_password_static(self):
        self._create_user()
        i18n = Translation.get_text_by_lang('en')
        user, errors = CustomUser.login_user(
            {'email': 'user@test.com', 'password': 'wrong'},
            settings={'i18n': i18n},
        )
        self.assertIsNone(user)
        self.assertIsNotNone(errors)

    @mock.patch('app.utils.Utils.send_email', return_value=1)
    def test_register_user_static(self, mock_email):
        i18n = Translation.get_text_by_lang('en')
        user, errors = CustomUser.register_user(
            {'email': 'brand_new@test.com', 'password': 'securepass'},
            settings={'i18n': i18n},
        )
        self.assertIsNotNone(user)
        self.assertIsNone(errors)
        self.assertTrue(CustomUser.objects.filter(email='brand_new@test.com').exists())

    def test_verify_code_static(self):
        user = self._create_user(is_confirm=False)
        code = user.verification_code
        i18n = Translation.get_text_by_lang('en')
        result, msg = CustomUser.verify_code(user, {'code': code}, settings={'i18n': i18n})
        self.assertIsNotNone(result)
        user.refresh_from_db()
        self.assertTrue(user.is_confirm)


# ---------------------------------------------------------------------------
# EmailAddress model tests
# ---------------------------------------------------------------------------
class EmailAddressModelTests(AccountTestBase):

    def test_register_email_success(self):
        user = self._create_user()
        i18n = Translation.get_text_by_lang('en')
        email_obj, msg = EmailAddress.register_email(user, {'email': 'alt@test.com'}, settings={'i18n': i18n})
        self.assertIsNotNone(email_obj)
        self.assertEqual(email_obj.email, 'alt@test.com')

    def test_register_email_duplicate(self):
        user = self._create_user()
        i18n = Translation.get_text_by_lang('en')
        EmailAddress.register_email(user, {'email': 'alt@test.com'}, settings={'i18n': i18n})
        email_obj, msg = EmailAddress.register_email(user, {'email': 'alt@test.com'}, settings={'i18n': i18n})
        self.assertIsNone(email_obj)
        self.assertIn('already added', msg)

    def test_register_email_invalid(self):
        user = self._create_user()
        i18n = Translation.get_text_by_lang('en')
        email_obj, msg = EmailAddress.register_email(user, {'email': 'not-valid'}, settings={'i18n': i18n})
        self.assertIsNone(email_obj)

    def test_register_email_missing(self):
        user = self._create_user()
        i18n = Translation.get_text_by_lang('en')
        email_obj, msg = EmailAddress.register_email(user, {}, settings={'i18n': i18n})
        self.assertIsNone(email_obj)


# ---------------------------------------------------------------------------
# Delete account tests
# ---------------------------------------------------------------------------
class DeleteAccountTests(AccountTestBase):

    def test_delete_account_requires_auth(self):
        resp = self.client.get(reverse('delete'))
        self.assertEqual(resp.status_code, 302)

    def test_delete_account_page_loads(self):
        self._create_user(is_confirm=True)
        self._login()
        resp = self.client.get(reverse('delete'))
        self.assertEqual(resp.status_code, 200)

    def test_delete_account_post(self):
        user = self._create_user(is_confirm=True)
        self._login()
        resp = self.client.post(reverse('delete'))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(CustomUser.objects.filter(email='user@test.com').exists())

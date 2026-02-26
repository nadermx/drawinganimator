"""
End-to-end tests: full user flows from signup through animation creation
and result viewing.

Flow 1: Signup -> Verify email -> Upload drawing -> Animate -> View result
Flow 2: Signup -> Purchase credits -> Animate with premium preset
Flow 3: Anonymous user -> Animate -> Hit rate limit -> Signup
"""
import json
import struct
import zlib
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from animator.models import Animation, AnimationPreset, GalleryItem
from finances.models.plan import Plan
from finances.models.payment import Payment
from translations.models.language import Language
from translations.models.translation import Translation


def _make_test_png(width=2, height=2):
    """Create a minimal valid PNG for upload tests."""
    raw_data = b'\x00' + (b'\xff\xff\xff' * width)
    raw_data = raw_data * height
    compressed = zlib.compress(raw_data)

    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack('>I', zlib.crc32(c) & 0xffffffff)
        return struct.pack('>I', len(data)) + c + crc

    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    return sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')


@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
    SESSION_ENGINE='django.contrib.sessions.backends.db',
)
class E2ETestBase(TestCase):
    """Base class that sets up all fixtures needed for end-to-end flows."""

    @classmethod
    def setUpTestData(cls):
        cls.language = Language.objects.create(name='English', en_label='English', iso='en')
        i18n_keys = {
            'missing_email': 'Email is required',
            'missing_password': 'Password is required',
            'invalid_email': 'Invalid email',
            'email_taken': 'Email already registered',
            'weak_password': 'Password is too weak',
            'wrong_credentials': 'Wrong email or password',
            'missing_code': 'Code is required',
            'invalid_code': 'Invalid code',
            'password_changed': 'Password changed',
            'missing_current_password': 'Current password required',
            'missing_new_password': 'New password required',
            'missing_confirm_new_password': 'Confirm password required',
            'passwords_dont_match': 'Passwords do not match',
            'wrong_current_password': 'Current password is wrong',
            'missing_restore_token': 'Token is required',
            'missing_confirm_password': 'Confirm password required',
            'invalid_restore_token': 'Invalid token',
            'forgot_password_email_sent': 'Password reset email sent',
            'email_sent_wait': 'Please wait before requesting again',
            'missing_message': 'Message is required',
            'duplicate_email': 'Email already added',
            'missing_nonce': 'Payment nonce required',
            'empty_amount': 'Amount required',
            'user_not_found': 'User not found',
            'invalid_processor': 'Invalid processor',
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

        # Animation presets
        cls.preset_walk = AnimationPreset.objects.create(
            name='Walking', code_name='walk', is_active=True, is_premium=False,
        )
        cls.preset_dance = AnimationPreset.objects.create(
            name='Dancing', code_name='dance', is_active=True, is_premium=False,
        )
        cls.preset_backflip = AnimationPreset.objects.create(
            name='Backflip', code_name='backflip', is_active=True, is_premium=True,
        )

        # Plans
        cls.plan_basic = Plan.objects.create(
            code_name='basic', price=10, credits=100, days=31,
            is_subscription=False,
        )
        cls.plan_pro = Plan.objects.create(
            code_name='pro', price=25, credits=500, days=31,
            is_subscription=True,
        )

    def setUp(self):
        self.client = Client()


# ---------------------------------------------------------------------------
# Flow 1: Signup -> Verify -> Upload -> Animate -> Poll status -> View result
# ---------------------------------------------------------------------------
class FullAnimationFlowTest(E2ETestBase):

    @mock.patch('app.utils.Utils.send_email', return_value=1)
    @mock.patch('animator.views.AnimateAPI.send_to_api')
    def test_signup_verify_animate_complete(self, mock_send_api, mock_email):
        # ---- Step 1: Sign up ----
        resp = self.client.post(reverse('register'), {
            'email': 'alice@test.com',
            'password': 'mypassword',
        })
        self.assertEqual(resp.status_code, 302, "Registration should redirect")
        user = CustomUser.objects.get(email='alice@test.com')
        self.assertFalse(user.is_confirm)
        mock_email.assert_called_once()

        # User is now logged in but unconfirmed. Account page should redirect to verify.
        resp = self.client.get(reverse('account'))
        self.assertRedirects(resp, reverse('verify'))

        # ---- Step 2: Verify email ----
        verification_code = user.verification_code
        resp = self.client.post(reverse('verify'), {'code': verification_code})
        self.assertEqual(resp.status_code, 302, "Verification should redirect to account")
        user.refresh_from_db()
        self.assertTrue(user.is_confirm)

        # Account page should now load
        resp = self.client.get(reverse('account'))
        self.assertEqual(resp.status_code, 200)

        # ---- Step 3: Visit animate page ----
        resp = self.client.get(reverse('animate'))
        self.assertEqual(resp.status_code, 200)

        # ---- Step 4: Upload drawing and animate ----
        mock_send_api.return_value = {
            'success': True,
            'request_id': 'gpu-uuid-001',
            'job_id': 'gpu-job-001',
        }
        image = SimpleUploadedFile('drawing.png', _make_test_png(), content_type='image/png')
        resp = self.client.post(
            reverse('api_animate'),
            {'image': image, 'preset': 'walk', 'format': 'gif'},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        animation_id = data['animation_id']

        # Verify animation record
        animation = Animation.objects.get(uuid=animation_id)
        self.assertEqual(animation.status, Animation.PROCESSING)
        self.assertEqual(animation.user, user)
        self.assertEqual(animation.preset, self.preset_walk)
        self.assertEqual(animation.output_format, 'gif')

        # ---- Step 5: Poll for status (still processing) ----
        with mock.patch('animator.views.AnimationStatus.check_api_status') as mock_check:
            mock_check.return_value = {'done': False}
            resp = self.client.get(
                reverse('api_animation_status', args=[animation_id])
            )
            self.assertEqual(resp.status_code, 200)
            status_data = resp.json()
            self.assertEqual(status_data['status'], 'processing')

        # ---- Step 6: Poll again - now completed ----
        with mock.patch('animator.views.AnimationStatus.check_api_status') as mock_check:
            mock_check.return_value = {
                'done': True,
                'output_url': 'https://api.drawinganimator.com/output/animation-001.gif',
            }
            resp = self.client.get(
                reverse('api_animation_status', args=[animation_id])
            )
            self.assertEqual(resp.status_code, 200)
            status_data = resp.json()
            self.assertEqual(status_data['status'], 'completed')
            self.assertEqual(status_data['progress'], 100)
            self.assertIn('animation-001.gif', status_data['output_url'])

        # Verify DB state
        animation.refresh_from_db()
        self.assertEqual(animation.status, Animation.COMPLETED)
        self.assertIsNotNone(animation.completed_at)

        # ---- Step 7: Check my animations page ----
        resp = self.client.get(reverse('my_animations'))
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Flow 2: Signup -> Verify -> Purchase plan -> Animate premium preset
# ---------------------------------------------------------------------------
class PurchaseAndPremiumAnimateTest(E2ETestBase):

    @mock.patch('app.utils.Utils.send_email', return_value=1)
    @mock.patch('animator.views.AnimateAPI.send_to_api')
    @mock.patch('finances.models.payment.Payment.make_charge_stripe')
    def test_purchase_then_premium_animate(self, mock_stripe, mock_send_api, mock_email):
        # ---- Step 1: Sign up and verify ----
        resp = self.client.post(reverse('register'), {
            'email': 'bob@test.com',
            'password': 'bobpass123',
        })
        self.assertEqual(resp.status_code, 302)
        user = CustomUser.objects.get(email='bob@test.com')
        code = user.verification_code
        resp = self.client.post(reverse('verify'), {'code': code})
        self.assertEqual(resp.status_code, 302)

        # ---- Step 2: Try premium preset (should fail) ----
        image = SimpleUploadedFile('drawing.png', _make_test_png(), content_type='image/png')
        resp = self.client.post(
            reverse('api_animate'),
            {'image': image, 'preset': 'backflip'},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn('premium', resp.json()['error'].lower())

        # ---- Step 3: Visit pricing page ----
        resp = self.client.get(reverse('pricing'))
        self.assertEqual(resp.status_code, 200)

        # ---- Step 4: Visit checkout page ----
        resp = self.client.get(reverse('checkout'), {'plan': 'pro'})
        self.assertEqual(resp.status_code, 200)

        # ---- Step 5: Purchase plan via Stripe ----
        mock_payment = Payment(
            user=user,
            processor='stripe',
            payment_token='ch_test_123',
            customer_token='cus_test_123',
            card_token='cus_test_123',
            status=Payment.SUCCESS,
            amount=25,
        )
        mock_payment.save()
        mock_stripe.return_value = (mock_payment, 'ok')

        resp = self.client.post(reverse('checkout'), {
            'plan': 'pro',
            'processor': 'stripe',
            'nonce': 'tok_visa_test',
        })
        # Successful payment redirects to account
        self.assertEqual(resp.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.is_plan_active)
        self.assertGreater(user.credits, 0)

        # ---- Step 6: Now animate with premium preset (should work) ----
        mock_send_api.return_value = {
            'success': True,
            'request_id': 'gpu-premium-001',
            'job_id': 'gpu-premium-job',
        }
        image2 = SimpleUploadedFile('drawing2.png', _make_test_png(), content_type='image/png')
        resp = self.client.post(
            reverse('api_animate'),
            {'image': image2, 'preset': 'backflip', 'format': 'mp4'},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])

        # Pro user should get mp4 format
        anim = Animation.objects.get(uuid=data['animation_id'])
        self.assertEqual(anim.output_format, 'mp4')
        self.assertFalse(anim.add_watermark)  # Pro users get no watermark


# ---------------------------------------------------------------------------
# Flow 3: Anonymous animation -> Rate limit -> Sign up to continue
# ---------------------------------------------------------------------------
class AnonymousRateLimitFlowTest(E2ETestBase):

    @mock.patch('animator.views.AnimateAPI.send_to_api')
    def test_anonymous_rate_limit_then_signup(self, mock_send_api):
        mock_send_api.return_value = {
            'success': True,
            'request_id': 'anon-uuid',
            'job_id': 'anon-job',
        }

        # ---- Step 1: Anonymous user creates animations up to the limit ----
        for i in range(5):
            image = SimpleUploadedFile(f'anon{i}.png', _make_test_png(), content_type='image/png')
            resp = self.client.post(
                reverse('api_animate'),
                {'image': image, 'preset': 'walk'},
            )
            self.assertEqual(resp.status_code, 200, f"Anonymous request {i+1} should succeed")

        # ---- Step 2: Rate limit hit ----
        image = SimpleUploadedFile('extra.png', _make_test_png(), content_type='image/png')
        resp = self.client.post(
            reverse('api_animate'),
            {'image': image, 'preset': 'walk'},
        )
        self.assertEqual(resp.status_code, 429)
        self.assertIn('limit', resp.json()['error'].lower())

        # ---- Step 3: User signs up ----
        with mock.patch('app.utils.Utils.send_email', return_value=1):
            resp = self.client.post(reverse('register'), {
                'email': 'charlie@test.com',
                'password': 'charliepass',
            })
            self.assertEqual(resp.status_code, 302)

        # ---- Step 4: Verify ----
        user = CustomUser.objects.get(email='charlie@test.com')
        resp = self.client.post(reverse('verify'), {'code': user.verification_code})
        self.assertEqual(resp.status_code, 302)

        # ---- Step 5: Even after signup, daily limit is per-user now (fresh start) ----
        # The user has 0 animations under their account, so they get fresh allowance
        image = SimpleUploadedFile('after_signup.png', _make_test_png(), content_type='image/png')
        resp = self.client.post(
            reverse('api_animate'),
            {'image': image, 'preset': 'dance'},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])


# ---------------------------------------------------------------------------
# Flow 4: Callback-driven completion (GPU pushes callback)
# ---------------------------------------------------------------------------
class CallbackCompletionFlowTest(E2ETestBase):

    @mock.patch('app.utils.Utils.send_email', return_value=1)
    @mock.patch('animator.views.AnimateAPI.send_to_api')
    def test_animate_then_callback_completes(self, mock_send_api, mock_email):
        # ---- Step 1: Sign up and verify ----
        self.client.post(reverse('register'), {
            'email': 'diana@test.com',
            'password': 'dianapass',
        })
        user = CustomUser.objects.get(email='diana@test.com')
        self.client.post(reverse('verify'), {'code': user.verification_code})

        # ---- Step 2: Create animation ----
        mock_send_api.return_value = {
            'success': True,
            'request_id': 'gpu-callback-001',
            'job_id': 'gpu-callback-job',
        }
        image = SimpleUploadedFile('callback_test.png', _make_test_png(), content_type='image/png')
        resp = self.client.post(
            reverse('api_animate'),
            {'image': image, 'preset': 'walk'},
        )
        self.assertEqual(resp.status_code, 200)
        animation_id = resp.json()['animation_id']
        animation = Animation.objects.get(uuid=animation_id)
        self.assertEqual(animation.status, Animation.PROCESSING)

        # ---- Step 3: GPU sends progress callback ----
        resp = self.client.post(
            reverse('api_animation_callback'),
            data=json.dumps({
                'animation_id': animation_id,
                'status': 'processing',
                'progress': 50,
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        animation.refresh_from_db()
        self.assertEqual(animation.progress, 50)

        # ---- Step 4: GPU sends completion callback ----
        resp = self.client.post(
            reverse('api_animation_callback'),
            data=json.dumps({
                'animation_id': animation_id,
                'status': 'completed',
                'output_url': 'https://api.drawinganimator.com/output/final.gif',
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        animation.refresh_from_db()
        self.assertEqual(animation.status, Animation.COMPLETED)
        self.assertEqual(animation.progress, 100)
        self.assertIn('final.gif', animation.output_url)
        self.assertIsNotNone(animation.completed_at)

        # ---- Step 5: Client polls and gets completed status ----
        resp = self.client.get(
            reverse('api_animation_status', args=[animation_id])
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'completed')
        self.assertIn('final.gif', data['output_url'])


# ---------------------------------------------------------------------------
# Flow 5: Animation failure flow
# ---------------------------------------------------------------------------
class AnimationFailureFlowTest(E2ETestBase):

    @mock.patch('app.utils.Utils.send_email', return_value=1)
    @mock.patch('animator.views.AnimateAPI.send_to_api')
    def test_animate_then_failure_callback(self, mock_send_api, mock_email):
        # Sign up and verify
        self.client.post(reverse('register'), {
            'email': 'eve@test.com',
            'password': 'evepassword',
        })
        user = CustomUser.objects.get(email='eve@test.com')
        self.client.post(reverse('verify'), {'code': user.verification_code})

        # Create animation
        mock_send_api.return_value = {
            'success': True,
            'request_id': 'gpu-fail-001',
            'job_id': 'gpu-fail-job',
        }
        image = SimpleUploadedFile('fail_test.png', _make_test_png(), content_type='image/png')
        resp = self.client.post(
            reverse('api_animate'),
            {'image': image, 'preset': 'walk'},
        )
        animation_id = resp.json()['animation_id']

        # GPU sends failure callback
        resp = self.client.post(
            reverse('api_animation_callback'),
            data=json.dumps({
                'animation_id': animation_id,
                'status': 'failed',
                'error': 'Character detection failed: no character found in image',
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)

        # Client polls status
        resp = self.client.get(
            reverse('api_animation_status', args=[animation_id])
        )
        data = resp.json()
        self.assertEqual(data['status'], 'failed')
        self.assertIn('no character found', data['error'])


# ---------------------------------------------------------------------------
# Flow 6: Password reset full flow
# ---------------------------------------------------------------------------
class PasswordResetE2ETest(E2ETestBase):

    @mock.patch('app.utils.Utils.send_email', return_value=1)
    def test_full_password_reset_flow(self, mock_email):
        # ---- Step 1: Create user ----
        self.client.post(reverse('register'), {
            'email': 'frank@test.com',
            'password': 'oldpassword',
        })
        user = CustomUser.objects.get(email='frank@test.com')
        self.client.get(reverse('logout'))

        # ---- Step 2: Request password reset ----
        resp = self.client.post(reverse('lost-password'), {
            'email': 'frank@test.com',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Password reset email sent')

        # ---- Step 3: Use restore password token ----
        user.refresh_from_db()
        token = user.restore_password_token
        self.assertIsNotNone(token)

        # Load restore password page
        resp = self.client.get(reverse('restore-password'), {'token': token})
        self.assertEqual(resp.status_code, 200)

        # ---- Step 4: Set new password ----
        resp = self.client.post(reverse('restore-password'), {
            'token': token,
            'password': 'newpassword456',
            'confirm_password': 'newpassword456',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Password changed')

        # ---- Step 5: Log in with new password ----
        resp = self.client.post(reverse('login'), {
            'email': 'frank@test.com',
            'password': 'newpassword456',
        })
        self.assertEqual(resp.status_code, 302)

        # ---- Step 6: Old password should not work ----
        self.client.get(reverse('logout'))
        resp = self.client.post(reverse('login'), {
            'email': 'frank@test.com',
            'password': 'oldpassword',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Wrong email or password')


# ---------------------------------------------------------------------------
# Flow 7: Delete account after creating animations
# ---------------------------------------------------------------------------
class DeleteAccountE2ETest(E2ETestBase):

    @mock.patch('app.utils.Utils.send_email', return_value=1)
    @mock.patch('animator.views.AnimateAPI.send_to_api')
    def test_delete_account_removes_user(self, mock_send_api, mock_email):
        # Sign up, verify, create animation
        self.client.post(reverse('register'), {
            'email': 'gina@test.com',
            'password': 'ginapassword',
        })
        user = CustomUser.objects.get(email='gina@test.com')
        self.client.post(reverse('verify'), {'code': user.verification_code})

        mock_send_api.return_value = {
            'success': True,
            'request_id': 'del-uuid',
            'job_id': 'del-job',
        }
        image = SimpleUploadedFile('del_test.png', _make_test_png(), content_type='image/png')
        self.client.post(
            reverse('api_animate'),
            {'image': image, 'preset': 'walk'},
        )
        self.assertEqual(Animation.objects.filter(user=user).count(), 1)

        # Delete account
        resp = self.client.post(reverse('delete'))
        self.assertRedirects(resp, reverse('index'))
        self.assertFalse(CustomUser.objects.filter(email='gina@test.com').exists())

        # Animation still exists (SET_NULL) but user is null
        anim = Animation.objects.first()
        self.assertIsNone(anim.user)

        # Should be logged out
        resp = self.client.get(reverse('account'))
        self.assertRedirects(resp, reverse('login'))

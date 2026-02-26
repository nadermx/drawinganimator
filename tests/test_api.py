"""
Tests for API endpoints: CreditsConsume, RateLimit, ResendVerificationEmail,
CancelSubscription, AnimateAPI, AnimationStatus, and animation_callback.
"""
import json
from io import BytesIO
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from accounts.models import CustomUser
from animator.models import Animation, AnimationPreset
from finances.models.plan import Plan
from translations.models.language import Language
from translations.models.translation import Translation


def _create_test_image(name='test.png', size=(100, 100), content_type='image/png'):
    """Create a minimal valid PNG file for upload tests."""
    # Minimal 1x1 PNG binary
    import struct
    import zlib

    def _make_png():
        width, height = size
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

    return SimpleUploadedFile(name, _make_png(), content_type=content_type)


@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
    SESSION_ENGINE='django.contrib.sessions.backends.db',
)
class APITestBase(TestCase):
    """Base for API tests with common fixtures."""

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
            'login': 'Login',
            'sign_up': 'Sign Up',
            'account_label': 'Account',
            'verify_email': 'Verify Email',
            'contact': 'Contact',
            'contact_meta_description': '',
        }
        for code_name, text in i18n_keys.items():
            Translation.objects.create(code_name=code_name, language='en', text=text)

        # Create animation presets
        cls.preset_walk = AnimationPreset.objects.create(
            name='Walking', code_name='walk', is_active=True, is_premium=False,
        )
        cls.preset_premium = AnimationPreset.objects.create(
            name='Backflip', code_name='backflip', is_active=True, is_premium=True,
        )

    def setUp(self):
        self.client = Client()

    def _create_user(self, email='api@test.com', password='testpass123', is_confirm=True, credits=10):
        user = CustomUser.objects.create(email=email, credits=credits, is_confirm=is_confirm)
        user.set_password(password)
        user.save()
        return user

    def _login(self, email='api@test.com', password='testpass123'):
        self.client.login(email=email, password=password)


# ---------------------------------------------------------------------------
# CreditsConsume API tests
# ---------------------------------------------------------------------------
class CreditsConsumeAPITests(APITestBase):

    def test_consume_credits_authenticated(self):
        user = self._create_user(credits=5)
        self._login()
        resp = self.client.post(
            reverse('credits-consume'),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.credits, 4)

    def test_consume_credits_zero_floor(self):
        user = self._create_user(credits=0)
        self._login()
        resp = self.client.post(
            reverse('credits-consume'),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.credits, 0)

    def test_consume_credits_unauthenticated(self):
        """Unauthenticated consume should still return 200 (consume_credits handles None)."""
        resp = self.client.post(
            reverse('credits-consume'),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# RateLimit API tests
# ---------------------------------------------------------------------------
class RateLimitAPITests(APITestBase):

    def _post_rate_limit(self, files_data=None, user=None):
        if files_data is None:
            files_data = [{'size': 1024}]
        return self.client.post(
            reverse('rate-limit'),
            data=json.dumps({'files_data': files_data}),
            content_type='application/json',
            HTTP_USER_AGENT='TestAgent/1.0',
        )

    def test_rate_limit_anonymous_first_request(self):
        resp = self._post_rate_limit()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('status'))
        self.assertEqual(data.get('counter'), 1)

    def test_rate_limit_pro_user_bypasses(self):
        user = self._create_user(credits=100)
        user.is_plan_active = True
        user.save()
        self._login()
        resp = self._post_rate_limit()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('status'))
        self.assertEqual(data.get('counter'), 0)

    def test_rate_limit_user_with_credits_passes(self):
        self._create_user(credits=5)
        self._login()
        resp = self._post_rate_limit()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('status'))

    def test_rate_limit_file_size_exceeded_anonymous(self):
        # FILES_LIMIT is 52428800 (50MB). Send a file bigger than that.
        resp = self._post_rate_limit(files_data=[{'size': 60000000}])
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertTrue(data.get('limit_exceeded'))

    def test_rate_limit_file_size_exceeded_no_credits(self):
        self._create_user(credits=0)
        self._login()
        resp = self._post_rate_limit(files_data=[{'size': 60000000}])
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertTrue(data.get('limit_exceeded'))


# ---------------------------------------------------------------------------
# ResendVerificationEmail API tests
# ---------------------------------------------------------------------------
class ResendVerificationEmailTests(APITestBase):

    @mock.patch('app.utils.Utils.send_email', return_value=1)
    def test_resend_verification_authenticated(self, mock_email):
        self._create_user(is_confirm=False)
        self._login()
        resp = self.client.post(
            reverse('resend-verification'),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        mock_email.assert_called_once()

    def test_resend_verification_unauthenticated(self):
        """Unauthenticated resend should still succeed (model method handles it gracefully)."""
        resp = self.client.post(
            reverse('resend-verification'),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# CancelSubscription API tests
# ---------------------------------------------------------------------------
class CancelSubscriptionAPITests(APITestBase):

    def test_cancel_subscription_success(self):
        user = self._create_user()
        user.is_plan_active = True
        user.processor = 'stripe'
        user.card_nonce = 'nonce'
        user.payment_nonce = 'pay_nonce'
        user.save()
        self._login()
        resp = self.client.post(
            reverse('cancel-subscription'),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        user.refresh_from_db()
        self.assertFalse(user.is_plan_active)

    def test_cancel_subscription_unauthenticated(self):
        resp = self.client.post(
            reverse('cancel-subscription'),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# AnimateAPI tests
# ---------------------------------------------------------------------------
class AnimateAPITests(APITestBase):

    @mock.patch('animator.views.AnimateAPI.send_to_api')
    def test_animate_success(self, mock_send):
        mock_send.return_value = {
            'success': True,
            'request_id': 'fake-uuid-123',
            'job_id': 'fake-job-123',
        }
        image = _create_test_image()
        resp = self.client.post(
            reverse('api_animate'),
            {'image': image, 'preset': 'walk', 'format': 'gif'},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertIn('animation_id', data)
        self.assertEqual(data.get('status'), 'processing')
        # Verify animation record was created
        anim = Animation.objects.get(uuid=data['animation_id'])
        self.assertEqual(anim.status, Animation.PROCESSING)

    @mock.patch('animator.views.AnimateAPI.send_to_api')
    def test_animate_api_failure(self, mock_send):
        mock_send.return_value = {
            'success': False,
            'error': 'GPU overloaded',
        }
        image = _create_test_image()
        resp = self.client.post(
            reverse('api_animate'),
            {'image': image, 'preset': 'walk'},
        )
        self.assertEqual(resp.status_code, 500)
        data = resp.json()
        self.assertFalse(data.get('success'))

    @mock.patch('animator.views.AnimateAPI.send_to_api')
    def test_animate_api_exception(self, mock_send):
        mock_send.side_effect = Exception('Connection refused')
        image = _create_test_image()
        resp = self.client.post(
            reverse('api_animate'),
            {'image': image, 'preset': 'walk'},
        )
        self.assertEqual(resp.status_code, 500)
        data = resp.json()
        self.assertFalse(data.get('success'))

    def test_animate_no_image(self):
        resp = self.client.post(reverse('api_animate'), {'preset': 'walk'})
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertFalse(data.get('success'))
        self.assertIn('No image', data.get('error', ''))

    def test_animate_invalid_file_type(self):
        bad_file = SimpleUploadedFile('test.txt', b'not an image', content_type='text/plain')
        resp = self.client.post(
            reverse('api_animate'),
            {'image': bad_file, 'preset': 'walk'},
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn('Invalid file type', data.get('error', ''))

    def test_animate_file_too_large(self):
        # Create a file that exceeds 10MB limit
        big_content = b'\x89PNG\r\n\x1a\n' + (b'\x00' * (11 * 1024 * 1024))
        big_file = SimpleUploadedFile('big.png', big_content, content_type='image/png')
        resp = self.client.post(
            reverse('api_animate'),
            {'image': big_file, 'preset': 'walk'},
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn('too large', data.get('error', ''))

    @mock.patch('animator.views.AnimateAPI.send_to_api')
    def test_animate_premium_preset_denied_for_free_user(self, mock_send):
        image = _create_test_image()
        resp = self.client.post(
            reverse('api_animate'),
            {'image': image, 'preset': 'backflip'},
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.json()
        self.assertIn('premium', data.get('error', '').lower())

    @mock.patch('animator.views.AnimateAPI.send_to_api')
    def test_animate_premium_preset_allowed_for_pro(self, mock_send):
        mock_send.return_value = {
            'success': True,
            'request_id': 'fake-uuid-pro',
            'job_id': 'fake-job-pro',
        }
        user = self._create_user()
        user.is_plan_active = True
        user.save()
        self._login()
        image = _create_test_image()
        resp = self.client.post(
            reverse('api_animate'),
            {'image': image, 'preset': 'backflip', 'format': 'mp4'},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))

    @mock.patch('animator.views.AnimateAPI.send_to_api')
    def test_animate_mp4_format_downgraded_for_free(self, mock_send):
        mock_send.return_value = {
            'success': True,
            'request_id': 'uuid-fmt',
            'job_id': 'job-fmt',
        }
        image = _create_test_image()
        resp = self.client.post(
            reverse('api_animate'),
            {'image': image, 'preset': 'walk', 'format': 'mp4'},
        )
        self.assertEqual(resp.status_code, 200)
        anim = Animation.objects.get(uuid=resp.json()['animation_id'])
        # Free users get gif, not mp4
        self.assertEqual(anim.output_format, 'gif')

    @mock.patch('animator.views.AnimateAPI.send_to_api')
    def test_animate_rate_limit_enforced(self, mock_send):
        """After RATE_LIMIT animations in a day, should be rejected."""
        mock_send.return_value = {
            'success': True,
            'request_id': 'uuid-rl',
            'job_id': 'job-rl',
        }
        # config.RATE_LIMIT is 5 for free tier
        for i in range(5):
            image = _create_test_image(name=f'test{i}.png')
            resp = self.client.post(
                reverse('api_animate'),
                {'image': image, 'preset': 'walk'},
            )
            self.assertEqual(resp.status_code, 200, f"Request {i+1} should succeed")

        # 6th request should be rate limited
        image = _create_test_image(name='test_extra.png')
        resp = self.client.post(
            reverse('api_animate'),
            {'image': image, 'preset': 'walk'},
        )
        self.assertEqual(resp.status_code, 429)


# ---------------------------------------------------------------------------
# AnimationStatus API tests
# ---------------------------------------------------------------------------
class AnimationStatusAPITests(APITestBase):

    def test_status_completed_animation(self):
        anim = Animation.objects.create(
            status=Animation.COMPLETED,
            output_url='https://api.drawinganimator.com/output/test.gif',
            progress=100,
            input_image=_create_test_image(),
            preset=self.preset_walk,
        )
        resp = self.client.get(
            reverse('api_animation_status', args=[anim.uuid])
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('status'), 'completed')
        self.assertEqual(data.get('progress'), 100)
        self.assertIn('output_url', data)

    def test_status_failed_animation(self):
        anim = Animation.objects.create(
            status=Animation.FAILED,
            error_message='GPU out of memory',
            input_image=_create_test_image(),
            preset=self.preset_walk,
        )
        resp = self.client.get(
            reverse('api_animation_status', args=[anim.uuid])
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'failed')
        self.assertIn('GPU out of memory', data.get('error', ''))

    def test_status_not_found(self):
        resp = self.client.get(
            reverse('api_animation_status', args=['nonexistent-uuid'])
        )
        self.assertEqual(resp.status_code, 404)

    @mock.patch('animator.views.AnimationStatus.check_api_status')
    def test_status_processing_polls_api(self, mock_check):
        mock_check.return_value = {'done': False}
        anim = Animation.objects.create(
            status=Animation.PROCESSING,
            api_request_id='api-uuid-123',
            progress=20,
            input_image=_create_test_image(),
            preset=self.preset_walk,
        )
        resp = self.client.get(
            reverse('api_animation_status', args=[anim.uuid])
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'processing')
        mock_check.assert_called_once_with('api-uuid-123')

    @mock.patch('animator.views.AnimationStatus.check_api_status')
    def test_status_processing_becomes_completed(self, mock_check):
        mock_check.return_value = {
            'done': True,
            'output_url': 'https://api.drawinganimator.com/output/result.gif',
        }
        anim = Animation.objects.create(
            status=Animation.PROCESSING,
            api_request_id='api-uuid-456',
            progress=50,
            input_image=_create_test_image(),
            preset=self.preset_walk,
        )
        resp = self.client.get(
            reverse('api_animation_status', args=[anim.uuid])
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'completed')
        anim.refresh_from_db()
        self.assertEqual(anim.status, Animation.COMPLETED)
        self.assertEqual(anim.progress, 100)

    @mock.patch('animator.views.AnimationStatus.check_api_status')
    def test_status_processing_becomes_failed(self, mock_check):
        mock_check.return_value = {
            'failed': True,
            'error': 'Processing failed on GPU',
        }
        anim = Animation.objects.create(
            status=Animation.PROCESSING,
            api_request_id='api-uuid-789',
            progress=30,
            input_image=_create_test_image(),
            preset=self.preset_walk,
        )
        resp = self.client.get(
            reverse('api_animation_status', args=[anim.uuid])
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'failed')
        anim.refresh_from_db()
        self.assertEqual(anim.status, Animation.FAILED)


# ---------------------------------------------------------------------------
# animation_callback endpoint tests
# ---------------------------------------------------------------------------
class AnimationCallbackTests(APITestBase):

    def _create_animation(self, **kwargs):
        defaults = {
            'status': Animation.PROCESSING,
            'input_image': _create_test_image(),
            'preset': self.preset_walk,
        }
        defaults.update(kwargs)
        return Animation.objects.create(**defaults)

    def test_callback_completed(self):
        anim = self._create_animation()
        resp = self.client.post(
            reverse('api_animation_callback'),
            data=json.dumps({
                'animation_id': anim.uuid,
                'status': 'completed',
                'output_url': 'https://api.drawinganimator.com/output/done.gif',
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        anim.refresh_from_db()
        self.assertEqual(anim.status, Animation.COMPLETED)
        self.assertEqual(anim.output_url, 'https://api.drawinganimator.com/output/done.gif')
        self.assertEqual(anim.progress, 100)

    def test_callback_failed(self):
        anim = self._create_animation()
        resp = self.client.post(
            reverse('api_animation_callback'),
            data=json.dumps({
                'animation_id': anim.uuid,
                'status': 'failed',
                'error': 'Out of memory',
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        anim.refresh_from_db()
        self.assertEqual(anim.status, Animation.FAILED)
        self.assertIn('Out of memory', anim.error_message)

    def test_callback_processing_progress(self):
        anim = self._create_animation()
        resp = self.client.post(
            reverse('api_animation_callback'),
            data=json.dumps({
                'animation_id': anim.uuid,
                'status': 'processing',
                'progress': 65,
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        anim.refresh_from_db()
        self.assertEqual(anim.progress, 65)
        self.assertEqual(anim.status, Animation.PROCESSING)  # Still processing

    def test_callback_not_found(self):
        resp = self.client.post(
            reverse('api_animation_callback'),
            data=json.dumps({
                'animation_id': 'nonexistent',
                'status': 'completed',
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 404)

    def test_callback_invalid_json(self):
        resp = self.client.post(
            reverse('api_animation_callback'),
            data='this is not json',
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

import json
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views import View
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from accounts.views import GlobalVars
from animator.models import Animation, AnimationPreset, GalleryItem
import config


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class AnimatePage(View):
    """Main animation page - upload and animate drawings."""

    def get(self, request):
        settings = GlobalVars.get_globals(request)
        presets = AnimationPreset.objects.filter(is_active=True)

        # Check daily limit for free users
        ip = get_client_ip(request)
        session_key = request.session.session_key or ''
        daily_count = Animation.get_user_daily_count(
            user=request.user if request.user.is_authenticated else None,
            session_key=session_key,
            ip_address=ip
        )

        # Determine limits
        is_pro = request.user.is_authenticated and request.user.is_plan_active
        daily_limit = config.RATE_LIMIT_PRO if is_pro else config.RATE_LIMIT
        remaining = max(0, daily_limit - daily_count)

        return render(request, 'animate.html', {
            'title': f"Animate Your Drawing | {config.PROJECT_NAME}",
            'description': 'Bring your drawings to life with AI-powered animation. Upload any sketch and watch it walk, dance, or jump!',
            'page': 'animate',
            'g': settings,
            'presets': presets,
            'is_pro': is_pro,
            'daily_count': daily_count,
            'daily_limit': daily_limit,
            'remaining': remaining,
        })


class AnimateAPI(View):
    """API endpoint for creating animations."""

    def post(self, request):
        settings = GlobalVars.get_globals(request)
        ip = get_client_ip(request)
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        # Check rate limit
        is_pro = request.user.is_authenticated and request.user.is_plan_active
        daily_limit = config.RATE_LIMIT_PRO if is_pro else config.RATE_LIMIT
        daily_count = Animation.get_user_daily_count(
            user=request.user if request.user.is_authenticated else None,
            session_key=session_key,
            ip_address=ip
        )

        if daily_count >= daily_limit:
            return JsonResponse({
                'success': False,
                'error': 'Daily limit reached. Upgrade to Pro for unlimited animations!'
            }, status=429)

        # Get uploaded image
        image_file = request.FILES.get('image')
        if not image_file:
            return JsonResponse({
                'success': False,
                'error': 'No image uploaded'
            }, status=400)

        # Validate file type
        allowed_types = ['image/png', 'image/jpeg', 'image/webp', 'image/gif']
        if image_file.content_type not in allowed_types:
            return JsonResponse({
                'success': False,
                'error': 'Invalid file type. Please upload PNG, JPEG, or WebP.'
            }, status=400)

        # Validate file size (max 10MB)
        if image_file.size > 10 * 1024 * 1024:
            return JsonResponse({
                'success': False,
                'error': 'File too large. Maximum size is 10MB.'
            }, status=400)

        # Get preset
        preset_code = request.POST.get('preset', 'walk')
        try:
            preset = AnimationPreset.objects.get(code_name=preset_code, is_active=True)
        except AnimationPreset.DoesNotExist:
            preset = AnimationPreset.objects.filter(is_active=True).first()

        # Check premium access
        if preset and preset.is_premium and not is_pro:
            return JsonResponse({
                'success': False,
                'error': 'This animation style is premium only. Upgrade to Pro!'
            }, status=403)

        # Get output format
        output_format = request.POST.get('format', 'gif')
        if output_format not in ['gif', 'mp4', 'webm']:
            output_format = 'gif'

        # MP4/WebM only for pro users
        if output_format in ['mp4', 'webm'] and not is_pro:
            output_format = 'gif'

        # Create animation record
        animation = Animation.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=session_key,
            input_image=image_file,
            preset=preset,
            output_format=output_format,
            add_watermark=not is_pro,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            status=Animation.PENDING
        )

        # Send to API backend for processing
        try:
            result = self.send_to_api(animation)
            if result.get('success'):
                animation.status = Animation.PROCESSING
                animation.api_request_id = result.get('request_id', '')
                animation.job_id = result.get('job_id', '')
                animation.started_at = timezone.now()
                animation.save()

                return JsonResponse({
                    'success': True,
                    'animation_id': animation.uuid,
                    'status': 'processing',
                    'message': 'Animation started! Check back in a few seconds.'
                })
            else:
                animation.status = Animation.FAILED
                animation.error_message = result.get('error', 'Unknown error')
                animation.save()
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Failed to start animation')
                }, status=500)

        except Exception as e:
            animation.status = Animation.FAILED
            animation.error_message = str(e)
            animation.save()
            return JsonResponse({
                'success': False,
                'error': 'Failed to process animation. Please try again.'
            }, status=500)

    def send_to_api(self, animation):
        """Send animation request to the API backend."""
        api_url = f"{config.API_BACKEND}/v1/animate/"

        # Read the image file
        animation.input_image.seek(0)
        files = {
            'files': (animation.input_image.name, animation.input_image.read(), 'image/png')
        }

        # Map animation preset to motion parameter
        motion = animation.preset.code_name if animation.preset else 'walk'

        data = {
            'motion': motion,
            'output_format': animation.output_format,
            'duration': animation.duration,
            'fps': animation.fps,
            'source': 'drawinganimator',  # Identify source for credit validation
        }

        headers = {}
        if config.API_KEY:
            headers['Authorization'] = config.API_KEY

        try:
            response = requests.post(api_url, files=files, data=data, headers=headers, timeout=30)
            result = response.json()

            # Map api.imageeditor.ai response format to our expected format
            if 'uuid' in result:
                return {
                    'success': True,
                    'request_id': result.get('uuid'),
                    'job_id': result.get('uuid'),
                }
            elif 'error' in result:
                return {'success': False, 'error': result.get('error')}
            else:
                return {'success': True, 'request_id': result.get('uuid', '')}

        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': str(e)}


class AnimationStatus(View):
    """Check animation status by polling the API backend."""

    def get(self, request, animation_id):
        try:
            animation = Animation.objects.get(uuid=animation_id)
        except Animation.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Animation not found'
            }, status=404)

        # If still processing, poll the API backend for status
        if animation.status == Animation.PROCESSING and animation.api_request_id:
            try:
                api_result = self.check_api_status(animation.api_request_id)
                if api_result:
                    if api_result.get('done'):
                        # Animation completed
                        output_url = api_result.get('output_url') or api_result.get('url')
                        if output_url:
                            animation.status = Animation.COMPLETED
                            animation.output_url = output_url
                            animation.completed_at = timezone.now()
                            animation.progress = 100
                            animation.save()
                    elif api_result.get('failed'):
                        animation.status = Animation.FAILED
                        animation.error_message = api_result.get('error', 'Processing failed')
                        animation.completed_at = timezone.now()
                        animation.save()
                    else:
                        # Still processing - estimate progress
                        animation.progress = min(animation.progress + 10, 90)
                        animation.save()
            except Exception:
                pass  # Ignore API errors, just return current status

        response_data = {
            'success': True,
            'status': animation.status,
            'progress': animation.progress,
        }

        if animation.status == Animation.COMPLETED:
            response_data['output_url'] = animation.output_url or (
                request.build_absolute_uri(animation.output_file.url) if animation.output_file else None
            )
            response_data['thumbnail_url'] = (
                request.build_absolute_uri(animation.thumbnail.url) if animation.thumbnail else None
            )

        if animation.status == Animation.FAILED:
            response_data['error'] = animation.error_message or 'Animation failed'

        return JsonResponse(response_data)

    def check_api_status(self, api_uuid):
        """Poll api.imageeditor.ai for animation status."""
        api_url = f"{config.API_BACKEND}/v1/animate/results/"

        headers = {}
        if config.API_KEY:
            headers['Authorization'] = config.API_KEY

        try:
            response = requests.post(
                api_url,
                data={'uuid': api_uuid},
                headers=headers,
                timeout=10
            )
            result = response.json()

            # Parse api.imageeditor.ai response format
            if result.get('files'):
                # Check if any file is complete
                for file_data in result.get('files', []):
                    if file_data.get('outputfile'):
                        return {
                            'done': True,
                            'output_url': file_data.get('outputfile'),
                        }
                    elif file_data.get('failed'):
                        return {
                            'failed': True,
                            'error': file_data.get('error', 'Processing failed'),
                        }
                # Still processing
                return {'done': False}
            elif result.get('failed'):
                return {
                    'failed': True,
                    'error': result.get('errors', ['Processing failed'])[0] if result.get('errors') else 'Processing failed',
                }

            return {'done': False}
        except Exception:
            return None


@csrf_exempt
@require_http_methods(["POST"])
def animation_callback(request):
    """Callback endpoint for API to report animation completion."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    animation_id = data.get('animation_id')
    status = data.get('status')
    output_url = data.get('output_url')
    error = data.get('error')

    try:
        animation = Animation.objects.get(uuid=animation_id)
    except Animation.DoesNotExist:
        return JsonResponse({'error': 'Animation not found'}, status=404)

    if status == 'completed':
        animation.status = Animation.COMPLETED
        animation.output_url = output_url
        animation.completed_at = timezone.now()
        animation.progress = 100
    elif status == 'failed':
        animation.status = Animation.FAILED
        animation.error_message = error or 'Processing failed'
        animation.completed_at = timezone.now()
    elif status == 'processing':
        animation.progress = data.get('progress', 0)

    animation.save()
    return JsonResponse({'success': True})


class GalleryPage(View):
    """Gallery of example animations."""

    def get(self, request):
        settings = GlobalVars.get_globals(request)
        gallery_items = GalleryItem.objects.filter(is_active=True).select_related('animation', 'animation__preset')

        featured = gallery_items.filter(is_featured=True)[:6]
        all_items = gallery_items[:24]

        return render(request, 'gallery.html', {
            'title': f"Animation Gallery | {config.PROJECT_NAME}",
            'description': 'See examples of animated drawings. Get inspired and create your own!',
            'page': 'gallery',
            'g': settings,
            'featured': featured,
            'gallery_items': all_items,
        })


class MyAnimations(View):
    """User's animation history."""

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')

        settings = GlobalVars.get_globals(request)
        animations = Animation.objects.filter(user=request.user).order_by('-created_at')[:50]

        return render(request, 'my-animations.html', {
            'title': f"My Animations | {config.PROJECT_NAME}",
            'page': 'my_animations',
            'g': settings,
            'animations': animations,
        })

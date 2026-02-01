from hashlib import md5
from translations.models.translation import Translation
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.cache import cache
from accounts.models import CustomUser
from app.utils import Utils
from config import RATE_LIMIT, FILES_LIMIT, SCRIPT_VERSION


class GlobalVars:
    @staticmethod
    def get_globals(request):
        lang_iso = Utils.get_language(request)
        # Utils.clear_cache()
        languages = cache.get('languages')

        if not languages:
            from translations.models.language import Language
            languages = Language.objects.all()
            cache.set('languages', languages)

        try:
            lang = languages.get(iso=lang_iso)
        except:
            lang = languages.get(iso='en')

        request.session['lang'] = lang.iso

        return {
            'lang': lang,
            'i18n': Translation.get_text_by_lang(lang.iso),
            'languages': languages,
            'scripts_version': SCRIPT_VERSION,
        }
class RateLimit(APIView):
    def post(self, request):
        ip = Utils.get_ip(request)
        user_agent = request.headers['User_Agent']
        cache_key = '%s %s' % (ip, user_agent)
        cache_key = cache_key.encode()
        cache_key = md5(cache_key)
        cache_key = cache_key.hexdigest()
        rate_total_minutes = 60
        rate_total_seconds = rate_total_minutes * 60
        counter = 0
        data = request.data
        files_data = data.get('files_data')
        total_size = 0

        for item in files_data:
            total_size += int(item.get('size'))

        if request.user.is_authenticated and request.user.is_plan_active:
            return JsonResponse({
                'status': True,
                'ip': ip,
                'cache_key': cache_key,
                'counter': counter
            })

        if not request.user.is_authenticated or request.user.credits <= 0:
            if total_size > FILES_LIMIT:
                return JsonResponse({
                    'limit_exceeded': True,
                    'ip': ip,
                    'counter': counter,
                    'cache_key': cache_key,
                    'until': Utils.get_expire_info_cache(cache_key)
                }, status=400)

        if ip:
            cache_data = Utils.get_from_cache(cache_key)

            if cache_data:
                counter = cache_data.get('counter')

            if request.user.is_authenticated:
                if request.user.credits > 0:
                    return JsonResponse({'status': True})

                if counter >= RATE_LIMIT:
                    return JsonResponse({
                        'no_credits': True,
                        'ip': ip,
                        'cache_key': cache_key,
                        'counter': counter,
                        'until': Utils.get_expire_info_cache(cache_key),
                        'next_billing': request.user.next_billing_date
                    }, status=400)
            else:
                if counter >= RATE_LIMIT:
                    return JsonResponse({
                        'rate_limit': True,
                        'ip': ip,
                        'counter': counter,
                        'cache_key': cache_key,
                        'until': Utils.get_expire_info_cache(cache_key)
                    }, status=400)

            counter += 1
            Utils.set_to_cache(cache_key, {
                'counter': counter
            }, exp=rate_total_seconds)

        return JsonResponse({
            'status': True,
            'ip': ip,
            'cache_key': cache_key,
            'counter': counter
        })


class CreditsConsume(APIView):
    def post(self, request):
        CustomUser.consume_credits(request.user)

        return Response({'status': True})


class ResendVerificationEmail(APIView):
    def post(self, request):
        settings = GlobalVars.get_globals(request)
        CustomUser.resend_email_verification(request.user, settings)

        return Response('<div class="alert alert-success">Your verification code was sent. Check spam.</div>')


class CancelSubscription(APIView):
    def post(self, request):
        account, errors = CustomUser.cancel_subscription(request.user)

        if not account:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': True})

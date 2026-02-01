import uuid
from random import randint
import re
import logging

from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings

from config import GOOGLE_API, PROJECT_NAME

logger = logging.getLogger(__name__)


class Utils:
    @staticmethod
    def is_valid_domain(domain):
        """Check if the given string is a valid domain name."""
        pattern = r"^(?:https?://)?(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
        match = re.match(pattern, domain)
        return match is not None

    @staticmethod
    def genetate_verification_code():
        return ''.join(['%s' % randint(0, 9) for _ in range(6)])

    @staticmethod
    def send_email(recipients=None, subject=None, template=None, data=None):
        """
        Send email using Django's native email backend.

        Uses SMTP configured in settings/config.py. For production, set up Postfix
        with DKIM/SPF/DMARC on your server.

        Args:
            recipients: List of email addresses
            subject: Email subject line
            template: Template name (without path/extension, e.g., 'email-verification')
            data: Context dict for template rendering

        Returns:
            Number of emails sent (1 on success, 0 on failure)
        """
        if not recipients or not subject or not template:
            logger.error("send_email: Missing required parameters")
            return 0

        try:
            # Render the HTML template
            template_obj = get_template(f'mailing/{template}.html')
            html_content = template_obj.render(data or {})

            # Create email with HTML content
            email = EmailMultiAlternatives(
                subject=subject,
                body=html_content,  # Fallback plain text (same as HTML for now)
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipients if isinstance(recipients, list) else [recipients],
            )
            email.attach_alternative(html_content, "text/html")

            # Send the email
            result = email.send(fail_silently=False)

            if result:
                logger.info(f"Email sent successfully to {recipients}")
            return result

        except Exception as e:
            logger.error(f"Failed to send email to {recipients}: {str(e)}")
            return 0

    @staticmethod
    def google_translation_request(lang, text, lang_source='en'):
        """Make a Google Translate API request."""
        import requests
        meta_url = f'https://www.googleapis.com/language/translate/v2?key={GOOGLE_API}&source={lang_source}&target={lang}&q={text}'
        return {
            'request': requests.get(meta_url),
            'lang': lang
        }

    @staticmethod
    def get_language(request):
        """Get the user's preferred language from request."""
        lang = request.GET.get('lang')
        if lang:
            data = lang.split('-')
            lang = data[0]

        if not lang:
            lang = request.session.get('lang')

        if not lang:
            http_accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
            if http_accept_language:
                lang = http_accept_language.split('-')[0]

        if not lang:
            lang = 'en'

        return lang

    @staticmethod
    def generate_hex_uuid():
        return uuid.uuid4().hex

    @staticmethod
    def generate_uuid():
        return str(uuid.uuid4())

    @staticmethod
    def get_ip(request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('HTTP_X_REAL_IP')
            if not ip:
                ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def clear_cache():
        cache.clear()

    @staticmethod
    def get_expire_info_cache(key):
        return cache.ttl(key)

    @staticmethod
    def get_from_cache(key):
        return cache.get(key)

    @staticmethod
    def set_to_cache(key, value, exp=60 * 60 * 24 * 30):
        cache.set(key, value, timeout=exp)

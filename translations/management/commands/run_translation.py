from multiprocessing.pool import ThreadPool

import requests
from django.core.management import BaseCommand

from translations.models.language import Language
from translations.models.textbase import TextBase
from translations.models.translation import Translation
from config import GOOGLE_API

class Command(BaseCommand):
    help = 'Start translating'

    def handle(self, *args, **options):
        pool = ThreadPool(processes=5)
        variables = TextBase.objects.filter(translated=False)
        langs = Language.objects.all()

        if not len(variables):
            print('Nothing to translate')
            return

        for item in variables:
            item.translated = True
            item.save()
            async_results = [
                pool.apply_async(self.google_translation_request, (lang.iso, item.text)) for lang in langs
            ]

            for ar in async_results:
                results = ar.get()
                result = results.get('request')
                lang = results.get('lang')

                try:
                    r = result.json()
                    meta = '%s' % r['data']['translations'][0]['translatedText']
                    meta = meta.replace('&#39;', "'").replace('&quot;', '"')
                except Exception as e:
                    print('run_translation: %s' % str(e))
                    meta = item.text

                params = {
                    'language': lang,
                    'code_name': item.code_name,
                    'text': meta
                }
                var, msg = Translation.register_text_translated(params)

                if var:
                    print('Translated text saved: %s' % var.text)
                else:
                    print('Translated text not saved: %s' % msg)

    @staticmethod
    def google_translation_request(lang, text, lang_source='en'):
        meta_url = 'https://www.googleapis.com/language/translate/v2?key=%s&source=%s&target=%s&q=%s' % (
            GOOGLE_API,
            lang_source,
            lang,
            text
        )

        return {
            'request': requests.get(meta_url),
            'lang': lang
        }

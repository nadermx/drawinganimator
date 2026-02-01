import json

from django.core.management import BaseCommand

from translations.models.textbase import TextBase
from translations.models.translation import Translation


class Command(BaseCommand):
    help = 'Set text backup'

    def handle(self, *args, **options):
        with open('./translations/json/textbase.json') as textbase:
            texts = json.load(textbase)

        for item in texts:
            try:
                text = TextBase.objects.get(code_name=item.get('code_name'))
                print('Text %s updated' % item.get('code_name'))
            except:
                text = TextBase.objects.create(
                    code_name=item.get('code_name'),
                    text=item.get('text'),
                    translated=False
                )
                print('Text %s saved' % item.get('code_name'))

            text.text = item.get('text')
            text.translated = True
            text.save()

        with open('./translations/json/translation.json') as translation:
            translations = json.load(translation)

        for item in translations:
            try:
                text = Translation.objects.get(code_name=item.get('code_name'), language=item.get('language'))
                print('Translation %s updated' % item.get('code_name'))
            except:
                text = Translation.objects.create(
                    code_name=item.get('code_name'),
                    language=item.get('language'),
                    text=item.get('text'),
                )
                print('Translation %s created' % item.get('code_name'))

            text.text = item.get('text')
            text.save()
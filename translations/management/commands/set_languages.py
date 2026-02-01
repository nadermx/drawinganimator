import json

from django.core.management import BaseCommand

from translations.models.language import Language


class Command(BaseCommand):
    help = 'Set all languages available'

    def handle(self, *args, **options):
        with open('./translations/json/languages.json') as languages:
            langs = json.load(languages)

        for item in langs:
            try:
                language = Language.objects.create(
                    name=item.get('text'),
                    iso=item.get('iso'),
                    en_label=item.get('en_label')
                )
                language.save()
                print('Language %s saved' % item.get('text'))
            except Exception as e:
                print(str(e))
                continue

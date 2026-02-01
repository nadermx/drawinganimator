from django.core.management import BaseCommand
from translations.models.translation import Translation
from translations.models.textbase import TextBase

class Command(BaseCommand):
    help = 'test delete'

    def handle(self, *args, **options):
        textbase = TextBase.objects.all()
        translation = Translation.objects.all()
        for t in translation:
            if textbase.filter(code_name=t.code_name).exists():
                print("not deleted", t.code_name)
                continue
            t.delete()
        return

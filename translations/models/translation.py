from django.db import models


class Translation(models.Model):
    code_name = models.CharField(max_length=250)
    language = models.CharField(max_length=10)
    text = models.TextField()

    class Meta:
        unique_together = ('language', 'code_name', )

    def __str__(self):
        return self.code_name

    @staticmethod
    def get_text_by_lang(lang):
        i18n = {}
        text = Translation.objects.filter(language=lang)

        if not text:
            text = Translation.objects.filter(language='en')

        for i in text:
            i18n[i.code_name] = i.text

        return i18n

    @staticmethod
    def register_text_translated(data):
        language = data.get('language')
        code_name = data.get('code_name')
        text = data.get('text')

        try:
            translation = Translation.objects.get(code_name=code_name, language=language)
        except:
            translation = Translation(
                code_name=code_name,
                language=language
            )

        translation.text = text
        translation.save()

        return translation, 'ok'

from django.db import models


class Language(models.Model):
    name = models.CharField(max_length=250)
    en_label = models.CharField(max_length=250)
    iso = models.CharField(max_length=5, unique=True)

    def __str__(self):
        return self.name

from django.contrib.auth.models import User
from django.db import models


class Profil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telephone = models.CharField(max_length=30)

    def __str__(self):
        return self.user.email
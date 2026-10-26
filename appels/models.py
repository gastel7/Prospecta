from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class SaisieJour(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saisies')
    date = models.DateField(default=timezone.localdate)
    nb_appeles = models.PositiveIntegerField()
    nb_joignables = models.PositiveIntegerField()

    class Meta:
        unique_together = ('utilisateur', 'date')   # une saisie par assistant et par jour

    def nb_injoignables(self):
        return self.nb_appeles - self.nb_joignables

    def __str__(self):
        return f"Saisie de {self.utilisateur} du {self.date:%d/%m/%Y}"


class ResultatCanal(models.Model):
    CANAL_CHOIX = [
        ('rappel', 'À rappeler'),
        ('courrier', 'Courrier'),
        ('mail', 'Mail'),
        ('rdv', 'RDV'),
        ('whatsapp', 'WhatsApp'),
    ]

    saisie = models.ForeignKey(SaisieJour, on_delete=models.CASCADE, related_name='resultats')
    canal = models.CharField(max_length=20, choices=CANAL_CHOIX)
    effectif = models.PositiveIntegerField()
    attente = models.PositiveIntegerField(default=0)
    accord = models.PositiveIntegerField(default=0)   # = clients

    def refus(self):
        return self.effectif - self.accord - self.attente

    def __str__(self):
        return f"{self.get_canal_display()} ({self.saisie.date:%d/%m/%Y})"
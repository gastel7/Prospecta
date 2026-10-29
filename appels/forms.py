from django import forms
from django.utils import timezone


class CsvImportForm(forms.Form):
    csv_file = forms.FileField(label="Sélectionnez un fichier CSV")


class SaisieTotalForm(forms.Form):
    date = forms.DateField(
        label="Date de la saisie",
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    nb_appeles = forms.IntegerField(
        label="Combien de contacts avez-vous appelés ce jour-là ?",
        min_value=0,
    )
    nb_joignables = forms.IntegerField(
        label="Combien ont été joignables ?",
        min_value=0,
    )

    def clean_date(self):
        jour = self.cleaned_data['date']
        if jour > timezone.localdate():
            raise forms.ValidationError("La date ne peut pas être dans le futur.")
        return jour

    def clean(self):
        data = super().clean()
        appeles = data.get('nb_appeles')
        joignables = data.get('nb_joignables')
        if appeles is not None and joignables is not None and joignables > appeles:
            self.add_error('nb_joignables', "Il ne peut pas y avoir plus de joignables que d'appels.")
        return data

    

class EffectifCanalForm(forms.Form):
    effectif = forms.IntegerField(label="Combien ont choisi ce canal ?", min_value=0)

    def __init__(self, *args, restants=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.restants = restants
        self.fields['effectif'].label = f"Parmi les {restants} restants, combien ont choisi ce canal ?"

    def clean_effectif(self):
        effectif = self.cleaned_data['effectif']
        if effectif > self.restants:
            raise forms.ValidationError(f"Il ne reste que {self.restants} prospect(s).")
        return effectif


class ResultatCanalForm(forms.Form):
    attente = forms.IntegerField(label="Combien sont en attente ?", min_value=0)
    accord = forms.IntegerField(label="Combien sont d'accord (clients) ?", min_value=0)

    def __init__(self, *args, effectif=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.effectif = effectif

    def clean(self):
        data = super().clean()
        attente = data.get('attente')
        accord = data.get('accord')
        if attente is not None and accord is not None and attente + accord > self.effectif:
            raise forms.ValidationError(f"En attente + d'accord ne peut pas dépasser {self.effectif}.")
        return data
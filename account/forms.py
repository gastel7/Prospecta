from django import forms
from django.contrib.auth.models import User


class InscriptionForm(forms.Form):
    last_name = forms.CharField(label="Nom", max_length=150)
    first_name = forms.CharField(label="Prénom", max_length=150)
    email = forms.EmailField(label="Email")
    telephone = forms.CharField(label="Téléphone", max_length=30)
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmer le mot de passe", widget=forms.PasswordInput)

    # Vérifie que l'email n'est pas déjà pris
    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("Cet email est déjà utilisé.")
        return email

    # Vérifie que les 2 mots de passe sont identiques
    def clean(self):
        data = super().clean()
        if data.get('password') != data.get('password2'):
            self.add_error('password2', "Les mots de passe ne sont pas identiques.")
        return data


class ConnexionForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
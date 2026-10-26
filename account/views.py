from django.shortcuts import render

# Create your views here.
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import render, redirect

from .forms import InscriptionForm, ConnexionForm
from .models import Profil


def inscription(request):
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # L'email sert aussi de username
            user = User.objects.create_user(
                username=data['email'],
                email=data['email'],
                password=data['password'],
                first_name=data['first_name'],
                last_name=data['last_name'],
            )
            Profil.objects.create(user=user, telephone=data['telephone'])
            login(request, user)
            return redirect('appels:saisie_total')
    else:
        form = InscriptionForm()
    return render(request, 'account/inscription.html', {'form': form})


def connexion(request):
    erreur = None
    if request.method == 'POST':
        form = ConnexionForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['email'].lower(),
                password=form.cleaned_data['password'],
            )
            if user is not None:
                login(request, user)
                return redirect('appels:saisie_total')
            erreur = "Email ou mot de passe incorrect."
    else:
        form = ConnexionForm()
    return render(request, 'account/connexion.html', {'form': form, 'erreur': erreur})


def deconnexion(request):
    if request.method == 'POST':
        logout(request)
    return redirect('account:connexion')
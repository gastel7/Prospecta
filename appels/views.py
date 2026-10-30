from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone
import csv
from django.contrib import messages
from django.http import HttpResponse

from .models import SaisieJour  # Ajustez le chemin de l'import si nécessaire
from datetime import date as date_type

from .forms import SaisieTotalForm, EffectifCanalForm, ResultatCanalForm, CsvImportForm
from .models import SaisieJour, ResultatCanal

CANAUX = [code for code, _ in ResultatCanal.CANAL_CHOIX]
LIBELLES = dict(ResultatCanal.CANAL_CHOIX)


def _etat(request):
    return request.session.get('saisie', {'resultats': {}})


def _restants(etat, sauf=None):
    deja = sum(r['effectif'] for code, r in etat['resultats'].items() if code != sauf)
    return etat['nb_joignables'] - deja


def _apres_canal(request, canal):
    if request.session.pop('depuis_bilan', False):
        return redirect('appels:saisie_bilan')
    i = CANAUX.index(canal)
    if i + 1 < len(CANAUX):
        return redirect('appels:saisie_canal', canal=CANAUX[i + 1])
    return redirect('appels:saisie_bilan')


def _page_precedente(canal):
    i = CANAUX.index(canal)
    if i == 0:
        return redirect('appels:saisie_total')
    return redirect('appels:saisie_canal', canal=CANAUX[i - 1])

@login_required
def saisie_total(request):
    etat = _etat(request)
    modif = etat.get('modif', False)

    if modif:
        initial = {
            'date': etat['date'],
            'nb_appeles': etat['nb_appeles'],
            'nb_joignables': etat['nb_joignables'],
        }
    else:
        initial = {'date': timezone.localdate()}

    if request.method == 'POST':
        form = SaisieTotalForm(request.POST, initial=initial)
    else:
        form = SaisieTotalForm(initial=initial)

    if modif:
        form.fields['date'].disabled = True   # on ne change pas le jour d'une saisie existante

    if request.method == 'POST' and form.is_valid():
        jour = form.cleaned_data['date']
        # Si cette journée existe déjà, on la modifie au lieu d'en créer une deuxième
        if not modif and SaisieJour.objects.filter(utilisateur=request.user, date=jour).exists():
            return redirect('appels:modifier_saisie', jour=jour.isoformat())
        request.session['saisie'] = {
            'modif': modif,
            'date': jour.isoformat(),
            'nb_appeles': form.cleaned_data['nb_appeles'],
            'nb_joignables': form.cleaned_data['nb_joignables'],
            'resultats': etat['resultats'] if modif else {},
        }
        return redirect('appels:saisie_canal', canal=CANAUX[0])

    return render(request, 'appels/saisie_total.html', {'form': form, 'modif': modif})


@login_required
def saisie_canal(request, canal):
    etat = _etat(request)
    if 'nb_joignables' not in etat or canal not in CANAUX:
        return redirect('appels:saisie_total')

    if request.GET.get('depuis') == 'bilan':
        request.session['depuis_bilan'] = True

    restants = _restants(etat, sauf=canal)
    if request.method == 'POST':
        if 'retour' in request.POST:
            return _page_precedente(canal)
        form = EffectifCanalForm(request.POST, restants=restants)
        if form.is_valid():
            effectif = form.cleaned_data['effectif']
            resultat = etat['resultats'].get(canal, {'attente': 0, 'accord': 0})
            resultat['effectif'] = effectif
            etat['resultats'][canal] = resultat
            request.session['saisie'] = etat
            if effectif > 0:
                return redirect('appels:saisie_resultat', canal=canal)
            return _apres_canal(request, canal)
    else:
        actuel = etat['resultats'].get(canal, {})
        form = EffectifCanalForm(initial={'effectif': actuel.get('effectif')}, restants=restants)

    return render(request, 'appels/saisie_canal.html', {
        'form': form,
        'canal': canal,
        'libelle': LIBELLES[canal],
        'restants': restants,
    })


@login_required
def saisie_resultat(request, canal):
    etat = _etat(request)
    resultat = etat['resultats'].get(canal)
    if not resultat or resultat['effectif'] == 0:
        return redirect('appels:saisie_canal', canal=canal)

    if request.method == 'POST':
        if 'retour' in request.POST:
            return redirect('appels:saisie_canal', canal=canal)
        form = ResultatCanalForm(request.POST, effectif=resultat['effectif'])
        if form.is_valid():
            resultat['attente'] = form.cleaned_data['attente']
            resultat['accord'] = form.cleaned_data['accord']
            request.session['saisie'] = etat
            return _apres_canal(request, canal)
    else:
        form = ResultatCanalForm(initial=resultat, effectif=resultat['effectif'])

    return render(request, 'appels/saisie_resultat.html', {
        'form': form,
        'canal': canal,
        'libelle': LIBELLES[canal],
        'effectif': resultat['effectif'],
    })


@login_required
def saisie_bilan(request):
    etat = _etat(request)
    if 'nb_joignables' not in etat:
        return redirect('appels:saisie_total')

    restants = _restants(etat)
    erreur = None
    if restants > 0:
        erreur = f"Il reste {restants} prospect(s) sans canal. Ajoute-les à un canal ci-dessous."
    elif restants < 0:
        erreur = "Les canaux dépassent le nombre de joignables. Corrige les canaux."

    lignes = []
    for code in CANAUX:
        r = etat['resultats'].get(code)
        if r and r['effectif'] > 0:
            lignes.append({
                'libelle': LIBELLES[code],
                'effectif': r['effectif'],
                'attente': r['attente'],
                'accord': r['accord'],
                'refus': r['effectif'] - r['accord'] - r['attente'],
            })
    total_clients = sum(l['accord'] for l in lignes)

    if request.method == 'POST':
        if 'retour' in request.POST:
            return redirect('appels:saisie_canal', canal=CANAUX[-1])
        if not erreur:
            with transaction.atomic():
                saisie, _ = SaisieJour.objects.update_or_create(
                    utilisateur=request.user,
                    date=date_type.fromisoformat(etat['date']),
                    defaults={
                        'nb_appeles': etat['nb_appeles'],
                        'nb_joignables': etat['nb_joignables'],
                    },
                )
                saisie.resultats.all().delete()
                for code in CANAUX:
                    r = etat['resultats'].get(code)
                    if r and r['effectif'] > 0:
                        ResultatCanal.objects.create( saisie=saisie, canal=code, effectif=r['effectif'], attente=r['attente'],accord=r['accord'],)
            
            request.session.pop('saisie', None)
            return redirect('appels:fin_saisie', jour=etat['date'])

    context = { 
        'lignes': lignes,
        'total_clients': total_clients,
        'erreur': erreur,
        'restants': restants,
        'canaux': [(code, LIBELLES[code]) for code in CANAUX],
        'jour': date_type.fromisoformat(etat['date']),

    }

    return render(request, 'appels/saisie_bilan.html', context)

@login_required
def fin_saisie(request, jour):
    saisie = SaisieJour.objects.filter(
        utilisateur=request.user,
        date=date_type.fromisoformat(jour),
    ).first()
    if not saisie:
        return redirect('appels:saisie_total')
    return render(request, 'appels/fin_saisie.html', {
        'saisie': saisie,
        'termine': request.GET.get('ok') == '1',
        'total_clients': sum(r.accord for r in saisie.resultats.all()),
    })


@login_required
def modifier_saisie(request, jour):
    saisie = SaisieJour.objects.filter(
        utilisateur=request.user,
        date=date_type.fromisoformat(jour),
    ).first()
    if not saisie:
        return redirect('appels:saisie_total')
    request.session['saisie'] = {
        'modif': True,
        'date': saisie.date.isoformat(),
        'nb_appeles': saisie.nb_appeles,
        'nb_joignables': saisie.nb_joignables,
        'resultats': {
            r.canal: {'effectif': r.effectif, 'attente': r.attente, 'accord': r.accord}
            for r in saisie.resultats.all()
        },
    }
    return redirect('appels:saisie_total')


@login_required
def liste_saisies(request):
    saisies = (SaisieJour.objects
               .filter(utilisateur=request.user)
               .prefetch_related('resultats')
               .order_by('-date'))
    lignes = []
    for s in saisies:
        resultats = list(s.resultats.all())
        lignes.append({
            'saisie': s,
            'canaux': [{
                'libelle': r.get_canal_display(),
                'effectif': r.effectif,
                'attente': r.attente,
                'accord': r.accord,
                'refus': r.refus(),
            } for r in resultats],
            'clients': sum(r.accord for r in resultats),
        })
    return render(request, 'appels/liste_saisies.html', {
        'lignes': lignes,
        'total_clients': sum(l['clients'] for l in lignes),
    })


@login_required
def tableau_general(request):
    # Visible par tous les assistants : toutes les saisies, avec le nom de chacun
    saisies = (SaisieJour.objects
               .select_related('utilisateur')
               .prefetch_related('resultats')
               .order_by('-date'))

    jours = {}     # une entrée par date
    totaux = {}    # total par assistant, toutes dates confondues
    for s in saisies:
        clients = sum(r.accord for r in s.resultats.all())
        u = s.utilisateur
        assistant = {
            'prenom': u.first_name,
            'nom': u.last_name,
            'email': u.email,
            'clients': clients,
        }
        jour = jours.setdefault(s.date, {'date': s.date, 'assistants': [], 'total': 0})
        jour['assistants'].append(assistant)
        jour['total'] += clients

        if u.email not in totaux:
            totaux[u.email] = {**assistant, 'clients': 0}
        totaux[u.email]['clients'] += clients

    return render(request, 'appels/tableau_general.html', {
        'jours': sorted(jours.values(), key=lambda j: j['date'], reverse=True),
        'totaux': sorted(totaux.values(), key=lambda a: a['clients'], reverse=True),
        'total_general': sum(a['clients'] for a in totaux.values()),
    })



@login_required
def exporter_csv(request):
    # 1. Préparation de la réponse HTTP pour le téléchargement du fichier CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    # On force l'encodage UTF-8 avec BOM pour qu'Excel sur Windows ouvre les accents correctement
    response.write(b'\xef\xbb\xbf') 
    response['Content-Disposition'] = 'attachment; filename="mes_saisies_appels.csv"'

    # 2. Utilisation du point-virgule (;) idéal pour Excel en français
    writer = csv.writer(response, delimiter=';')
    
    # En-tête du tableau CSV
    writer.writerow([
        'Date', 
        'Total Appelés', 
        'Total Joignables', 
        'Total Injoignables',
        'Canal', 
        'Effectif (Prospects)', 
        'En attente', 
        'D\'accord (Clients)', 
        'Refus'
    ])

    # 3. Récupération de l'historique de l'utilisateur connecté
    saisies = (SaisieJour.objects
               .filter(utilisateur=request.user)
               .prefetch_related('resultats')
               .order_by('-date'))

    # 4. Écriture des données ligne par ligne
    for s in saisies:
        # On calcule les injoignables grâce à la méthode de votre modèle
        injoignables = s.nb_injoignables() 
        
        # Pour chaque canal lié à cette journée
        for r in s.resultats.all():
            writer.writerow([
                s.date.strftime('%d/%m/%Y'),
                s.nb_appeles,
                s.nb_joignables,
                injoignables,
                r.get_canal_display(),
                r.effectif,
                r.attente,
                r.accord,
                r.refus(), # Utilisation de votre méthode de calcul des refus
            ])

    return response

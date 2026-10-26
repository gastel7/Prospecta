from django.urls import path
from . import views

app_name = 'appels'

urlpatterns = [
    path('', views.saisie_total, name='saisie_total'),
    path('saisie/canal/<str:canal>/', views.saisie_canal, name='saisie_canal'),
    path('saisie/resultat/<str:canal>/', views.saisie_resultat, name='saisie_resultat'),
    path('saisie/bilan/', views.saisie_bilan, name='saisie_bilan'),
    path('saisie/fin/', views.fin_saisie, name='fin_saisie'),
    path('saisie/modifier/', views.modifier_saisie, name='modifier_saisie'),
    path('saisies/', views.liste_saisies, name='liste_saisies'),
    path('tableau/', views.tableau_general, name='tableau_general'),
]
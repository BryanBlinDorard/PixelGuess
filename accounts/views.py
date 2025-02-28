from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import UserProfile, SteamProfile
import requests
import re
import json
import logging

logger = logging.getLogger(__name__)

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Compte créé avec succès !")
            return redirect('accounts:profile')
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Connexion réussie !")
                return redirect('accounts:profile')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect('home')

@login_required
def profile(request):
    user_profile = request.user.userprofile
    try:
        steam_profile = user_profile.steamprofile
    except SteamProfile.DoesNotExist:
        steam_profile = None

    best_session = request.user.gamesession_set.filter(
        is_completed=True
    ).order_by('-score').first()

    context = {
        'user_profile': user_profile,
        'steam_profile': steam_profile,
        'best_session': best_session
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def steam_login(request):
    host = request.get_host()
    scheme = 'https' if request.is_secure() else 'http'
    base_url = f"{scheme}://{host}"
    
    params = {
        'openid.ns': 'http://specs.openid.net/auth/2.0',
        'openid.mode': 'checkid_setup',
        'openid.return_to': f"{base_url}/accounts/steam/callback/",
        'openid.realm': base_url,
        'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
        'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select'
    }
    
    auth_url = 'https://steamcommunity.com/openid/login'
    full_url = f"{auth_url}?{'&'.join(f'{key}={value}' for key, value in params.items())}"
    return redirect(full_url)

@login_required
def steam_auth_callback(request):
    if 'error' in request.GET:
        messages.error(request, f"Erreur Steam: {request.GET['error']}")
        return redirect('accounts:profile')

    params = {
        'openid.assoc_handle': request.GET.get('openid.assoc_handle'),
        'openid.signed': request.GET.get('openid.signed'),
        'openid.sig': request.GET.get('openid.sig'),
        'openid.ns': request.GET.get('openid.ns'),
        'openid.mode': 'check_authentication'
    }

    signed_params = request.GET.get('openid.signed', '').split(',')
    for param in signed_params:
        params[f'openid.{param}'] = request.GET.get(f'openid.{param}')

    validation_url = 'https://steamcommunity.com/openid/login'
    try:
        response = requests.post(validation_url, data=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        messages.error(request, "Erreur lors de la validation Steam")
        return redirect('accounts:profile')

    if 'is_valid:true' not in response.text:
        messages.error(request, "Validation Steam échouée")
        return redirect('accounts:profile')

    steam_id_match = re.search(r'/id/(\d+)$', request.GET.get('openid.claimed_id', ''))
    if not steam_id_match:
        messages.error(request, "Impossible d'extraire l'ID Steam")
        return redirect('accounts:profile')

    steam_id = steam_id_match.group(1)
    steam_user_url = f'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={settings.STEAM_API_KEY}&steamids={steam_id}'
    
    try:
        steam_response = requests.get(steam_user_url)
        steam_response.raise_for_status()
        steam_data = steam_response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        messages.error(request, "Erreur lors de la récupération des données Steam")
        return redirect('accounts:profile')

    if not steam_data.get('response', {}).get('players'):
        messages.error(request, "Aucune donnée utilisateur trouvée")
        return redirect('accounts:profile')

    player_info = steam_data['response']['players'][0]
    
    try:
        # Créer ou mettre à jour le profil Steam
        steam_profile, created = SteamProfile.objects.get_or_create(
            user_profile=request.user.userprofile,
            defaults={
                'steam_id': steam_id,
                'steam_username': player_info.get('personaname'),
                'steam_avatar': player_info.get('avatarfull')
            }
        )

        if not created:
            steam_profile.steam_username = player_info.get('personaname')
            steam_profile.steam_avatar = player_info.get('avatarfull')
            steam_profile.save()

        messages.success(request, "Compte Steam lié avec succès !")
        return redirect('accounts:profile')
    
    except Exception as e:
        messages.error(request, "Erreur lors de la liaison du compte Steam")
        return redirect('accounts:profile')

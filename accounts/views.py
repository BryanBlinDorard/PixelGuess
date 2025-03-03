from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import UserProfile, SteamProfile, AnilistProfile
import requests
import re
import json
import logging
from game.models import AnimeEntry  # Mise à jour de l'import

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

    try:
        anilist_profile = user_profile.anilistprofile
    except AnilistProfile.DoesNotExist:
        anilist_profile = None

    best_session = request.user.gamesession_set.filter(
        is_completed=True
    ).order_by('-score').first()

    context = {
        'user_profile': user_profile,
        'steam_profile': steam_profile,
        'anilist_profile': anilist_profile,
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

@login_required
def anilist_login(request):
    # L'URL d'autorisation Anilist
    auth_url = 'https://anilist.co/api/v2/oauth/authorize'
    
    params = {
        'client_id': settings.ANILIST_CLIENT_ID,
        'redirect_uri': settings.ANILIST_REDIRECT_URI,
        'response_type': 'code'
    }
    
    # Construire l'URL avec les paramètres
    auth_url = f"{auth_url}?{'&'.join(f'{key}={value}' for key, value in params.items())}"
    return redirect(auth_url)

@login_required
def anilist_auth_callback(request):
    if 'error' in request.GET:
        messages.error(request, f"Erreur Anilist: {request.GET['error']}")
        return redirect('accounts:profile')

    code = request.GET.get('code')
    if not code:
        messages.error(request, "Code d'autorisation manquant")
        return redirect('accounts:profile')

    # Échanger le code contre un token
    token_url = 'https://anilist.co/api/v2/oauth/token'
    data = {
        'grant_type': 'authorization_code',
        'client_id': settings.ANILIST_CLIENT_ID,
        'client_secret': settings.ANILIST_CLIENT_SECRET,
        'redirect_uri': settings.ANILIST_REDIRECT_URI,
        'code': code
    }

    try:
        response = requests.post(token_url, json=data)
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data['access_token']

        # Récupérer les informations de l'utilisateur
        query = '''
        query {
            Viewer {
                id
                name
                avatar {
                    large
                }
            }
        }
        '''

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        response = requests.post('https://graphql.anilist.co',
                               json={'query': query},
                               headers=headers)
        response.raise_for_status()
        user_data = response.json()['data']['Viewer']

        # Créer ou mettre à jour le profil Anilist
        anilist_profile, created = AnilistProfile.objects.get_or_create(
            user_profile=request.user.userprofile,
            defaults={
                'anilist_id': str(user_data['id']),
                'anilist_username': user_data['name'],
                'anilist_avatar': user_data['avatar']['large'] if user_data['avatar'] else None,
                'access_token': access_token
            }
        )

        if not created:
            anilist_profile.anilist_username = user_data['name']
            anilist_profile.anilist_avatar = user_data['avatar']['large'] if user_data['avatar'] else None
            anilist_profile.access_token = access_token
            anilist_profile.save()

        messages.success(request, "Compte Anilist lié avec succès !")
        return redirect('accounts:sync_anime_list')

    except requests.exceptions.RequestException as e:
        messages.error(request, "Erreur lors de la connexion à Anilist")
        return redirect('accounts:profile')

@login_required
def sync_anime_list(request):
    try:
        anilist_profile = request.user.userprofile.anilistprofile
    except AnilistProfile.DoesNotExist:
        messages.error(request, "Vous devez d'abord lier votre compte Anilist")
        return redirect('accounts:profile')

    query = '''
    query ($userId: Int) {
        MediaListCollection(userId: $userId, type: ANIME, status_not: PLANNING) {
            lists {
                name
                entries {
                    id
                    status
                    score(format: POINT_10)
                    progress
                    notes
                    repeat
                    media {
                        id
                        title {
                            romaji
                            english
                            native
                        }
                        coverImage {
                            large
                        }
                        bannerImage
                        episodes
                        description
                        genres
                        tags {
                            name
                        }
                        averageScore
                        chapters
                        volumes
                        idMal
                    }
                }
            }
        }
    }
    '''

    variables = {
        'userId': anilist_profile.anilist_id
    }

    headers = {
        'Authorization': f'Bearer {anilist_profile.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    try:
        response = requests.post(
            'https://graphql.anilist.co',
            json={'query': query, 'variables': variables},
            headers=headers
        )

        print("Status Code:", response.status_code)
        print("Response:", response.text)

        response.raise_for_status()

        data = response.json()
        if 'errors' in data:
            error_messages = '; '.join([error.get('message', 'Unknown error') for error in data['errors']])
            messages.error(request, f"Erreur Anilist: {error_messages}")
            return redirect('accounts:profile')

        anime_data = data['data']['MediaListCollection']['lists']

        for list_data in anime_data:
            for entry in list_data['entries']:
                media = entry['media']
                anime, created = AnimeEntry.objects.get_or_create(
                    anilist_id=media['id'],
                    defaults={
                        'title_romaji': media['title']['romaji'],
                        'title_english': media['title']['english'],
                        'title_native': media['title']['native'],
                        'cover_image': media['coverImage']['large'],
                        'banner_image': media['bannerImage'],
                        'episodes': media['episodes'],
                        'description': media['description'],
                        'genres': media['genres'],
                        'tags': [tag['name'] for tag in media['tags']],
                        'average_score': media['averageScore'],
                        'status': entry['status'],
                        'is_synced': True
                    }
                )
                anime.user.add(request.user)

        anilist_profile.last_sync = timezone.now()
        anilist_profile.save()

        messages.success(request, "Liste d'animes synchronisée avec succès !")
        return redirect('accounts:profile')

    except requests.exceptions.RequestException as e:
        print("Erreur de requête:", str(e))
        messages.error(request, f"Erreur lors de la synchronisation avec Anilist: {str(e)}")
        return redirect('accounts:profile')
    except Exception as e:
        print("Erreur inattendue:", str(e))
        messages.error(request, f"Erreur inattendue: {str(e)}")
        return redirect('accounts:profile')

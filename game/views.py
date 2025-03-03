from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.utils import timezone
import requests
import random
import re
import io
from PIL import Image
import base64
from urllib.request import urlopen
from .models import SteamGame, GameSession
from django.db.models import Count, Sum, Avg, F, Case, When, IntegerField, FloatField, ExpressionWrapper, DurationField
from django.db.models.functions import Round
from django.contrib import messages
from accounts.models import SteamProfile

def normalize_text(text):
    # Garde uniquement les lettres et les chiffres, convertit en minuscules
    return re.sub(r'[^a-zA-Z0-9]', '', text.lower())

def pixelate_image(image_url, pixel_size):
    # Télécharger l'image depuis l'URL
    response = urlopen(image_url)
    img = Image.open(io.BytesIO(response.read()))
    
    # Calculer les nouvelles dimensions pour la pixelisation
    width, height = img.size
    small_width = width // pixel_size
    small_height = height // pixel_size
    
    # Réduire l'image puis l'agrandir pour créer l'effet de pixelisation
    # Utiliser BICUBIC pour une meilleure qualité lors de la réduction
    img = img.resize((small_width, small_height), Image.Resampling.BICUBIC)
    # Utiliser NEAREST pour conserver l'effet de pixels nets
    img = img.resize((width, height), Image.Resampling.NEAREST)
    
    # Convertir l'image en base64 pour l'envoyer au navigateur
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=95)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/jpeg;base64,{img_str}"

@login_required
def home(request):
    context = {}
    if request.user.is_authenticated:
        best_session = request.user.gamesession_set.filter(
            is_completed=True
        ).order_by('-score').first()
        context['best_session'] = best_session
    return render(request, 'home.html', context)

@login_required
def sync_games(request):
    try:
        steam_profile = request.user.userprofile.steamprofile
        if not steam_profile:
            messages.error(request, "Vous devez d'abord lier votre compte Steam.")
            return redirect('accounts:profile')

        steam_id = steam_profile.steam_id
        api_url = f'https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/?key={settings.STEAM_API_KEY}&steamid={steam_id}&include_appinfo=1'
        
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()

        if 'response' not in data or 'games' not in data['response']:
            messages.error(request, "Aucun jeu trouvé dans votre bibliothèque Steam.")
            return redirect('accounts:profile')

        games = data['response']['games']
        games_created = 0

        for game in games:
            if game.get('img_icon_url'):
                # Utiliser l'image de la bibliothèque Steam au lieu de l'icône
                image_url = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{game['appid']}/library_600x900.jpg"
                
                # D'abord, on récupère ou crée le jeu sans l'utilisateur
                game_obj, created = SteamGame.objects.get_or_create(
                    app_id=game['appid'],
                    defaults={
                        'name': game['name'],
                        'image_url': image_url,
                    }
                )
                
                if not created:
                    # Mettre à jour le nom et l'image si nécessaire
                    game_obj.name = game['name']
                    game_obj.image_url = image_url
                    game_obj.save()
                
                # Lier le jeu à l'utilisateur
                game_obj.user.add(request.user)
                game_obj.is_synced = True
                game_obj.save()
                
                games_created += 1

        messages.success(request, f"{games_created} jeux synchronisés avec succès ! Utilisez la commande 'python manage.py fetch_game_data' pour récupérer les informations détaillées.")
        return redirect('accounts:profile')

    except SteamProfile.DoesNotExist:
        messages.error(request, "Vous devez d'abord lier votre compte Steam.")
        return redirect('accounts:profile')
    except requests.exceptions.RequestException:
        messages.error(request, "Erreur lors de la communication avec l'API Steam.")
        return redirect('accounts:profile')
    except Exception as e:
        messages.error(request, f"Une erreur est survenue : {str(e)}")
        return redirect('accounts:profile')

@login_required
def start_game(request):
    # Vérifier si l'utilisateur a un profil Steam lié
    try:
        steam_profile = request.user.userprofile.steamprofile
    except SteamProfile.DoesNotExist:
        messages.error(request, "Vous devez d'abord lier votre compte Steam pour jouer.")
        return redirect('accounts:profile')

    # Vérifier si l'utilisateur a des jeux synchronisés
    user_games = SteamGame.objects.filter(user=request.user, is_synced=True)
    if not user_games.exists():
        messages.warning(request, "Vous devez d'abord synchroniser vos jeux Steam.")
        return redirect('game:sync_games')

    # Filtrer les jeux qui ont des screenshots (en utilisant une liste Python)
    games_with_screenshots = [game for game in user_games if game.screenshots]
    if not games_with_screenshots:
        messages.warning(request, "Aucun jeu avec des screenshots n'a été trouvé. Veuillez synchroniser vos jeux à nouveau.")
        return redirect('game:sync_games')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Récupérer la liste des jeux déjà joués
        import json
        played_games = []
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                played_games = data.get('played_games', [])
            except json.JSONDecodeError:
                pass

        # Filtrer les jeux non joués
        available_games = [game for game in games_with_screenshots if game.name not in played_games]
        
        # Si tous les jeux ont été joués, afficher un message
        if not available_games:
            return JsonResponse({
                'error': 'Tous les jeux disponibles ont été joués !'
            })
        
        # Sélectionner un jeu aléatoire parmi les jeux non joués
        game = random.choice(available_games)
        session = GameSession.objects.create(
            user=request.user,
            game=game
        )
        
        # Sélectionner un screenshot aléatoire
        screenshot_url = random.choice(game.screenshots)
        
        return JsonResponse({
            'image_url': screenshot_url,
            'session_id': session.id,
            'game_name': game.name
        })
    else:
        # Requête normale pour démarrer une nouvelle partie
        game = random.choice(games_with_screenshots)
        session = GameSession.objects.create(
            user=request.user,
            game=game
        )
        
        # Sélectionner un screenshot aléatoire
        screenshot_url = random.choice(game.screenshots)
        
        return render(request, 'game/play.html', {
            'session': session,
            'game_name': game.name,
            'image_url': screenshot_url
        })

@login_required
def check_answer(request, session_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    session = get_object_or_404(GameSession, id=session_id, user=request.user)
    if session.is_completed:
        return JsonResponse({'error': 'Game session already completed'}, status=400)

    # Normalise la réponse et la solution
    answer = normalize_text(request.POST.get('answer', ''))
    correct_answer = normalize_text(session.game.name)

    is_correct = answer == correct_answer
    session.attempts += 1
    
    if is_correct:
        session.score = max(100 - ((session.attempts - 1) * 10), 10)
        session.is_completed = True
        session.end_time = timezone.now()
    
    session.save()

    return JsonResponse({
        'correct': is_correct,
        'score': session.score if is_correct else None,
        'attempts': session.attempts
    })

@login_required
def leaderboard(request):
    # Calculer les statistiques globales par utilisateur
    user_stats = GameSession.objects.filter(
        is_completed=True  # On ne prend que les parties terminées
    ).values(
        'user__username',
        'user__userprofile__steamprofile__steam_username',
        'user__userprofile__steamprofile__steam_avatar'
    ).annotate(
        total_score=Sum('score'),
        total_attempts=Sum('attempts'),
        games_played=Count('id'),
        success_rate=Round(
            Count(Case(
                When(is_completed=True, score__gt=0, then=1),
                output_field=IntegerField(),
            )) * 100.0 / Count('id'),
            1
        ),
        avg_attempts=Round(
            Avg('attempts'),
            1
        )
    ).order_by('-total_score')

    return render(request, 'game/leaderboard.html', {'user_stats': user_stats})

@login_required
def get_suggestions(request):
    query = request.GET.get('q', '').lower()
    if len(query) < 2:
        return JsonResponse({'suggestions': []})

    # Recherche les jeux qui contiennent la requête
    suggestions = SteamGame.objects.filter(
        user=request.user,
        is_synced=True,
        name__icontains=query
    ).values_list('name', flat=True)[:5]

    return JsonResponse({'suggestions': list(suggestions)})

@login_required
def games_list(request):
    games = SteamGame.objects.annotate(
        player_count=Count('user', distinct=True)
    ).order_by('name')
    
    # Récupérer tous les tags et genres uniques
    all_tags = set()
    all_genres = set()
    for game in games:
        if game.tags:
            all_tags.update(game.tags)
        if game.genres:
            all_genres.update(game.genres)
    
    context = {
        'games': games,
        'all_tags': sorted(all_tags),  # Trier les tags par ordre alphabétique
        'all_genres': sorted(all_genres)  # Trier les genres par ordre alphabétique
    }
    
    return render(request, 'game/games_list.html', context)

@login_required
def user_stats(request):
    # Statistiques générales
    total_games = GameSession.objects.filter(user=request.user).count()
    completed_games = GameSession.objects.filter(user=request.user, is_completed=True)
    success_rate = (completed_games.count() / total_games * 100) if total_games > 0 else 0
    
    # Temps moyen de réponse pour les parties réussies
    avg_time = completed_games.exclude(end_time=None).annotate(
        duration=ExpressionWrapper(
            F('end_time') - F('start_time'),
            output_field=DurationField()
        )
    ).aggregate(avg_duration=Avg('duration'))
    
    # Jeux les plus difficiles (nombre moyen de tentatives le plus élevé)
    difficult_games = GameSession.objects.filter(
        user=request.user,
        is_completed=True
    ).values(
        'game__name',
        'game__app_id'
    ).annotate(
        avg_attempts=Avg('attempts'),
        play_count=Count('id')
    ).filter(
        play_count__gte=2  # Au moins 2 parties pour être significatif
    ).order_by('-avg_attempts')[:5]
    
    # Progression dans le temps
    recent_sessions = GameSession.objects.filter(
        user=request.user,
        is_completed=True
    ).order_by('start_time').values(
        'start_time',
        'score',
        'attempts'
    )[:50]  # Limiter aux 50 dernières parties
    
    # Meilleurs scores
    best_sessions = GameSession.objects.filter(
        user=request.user,
        is_completed=True
    ).order_by('-score')[:5]
    
    context = {
        'total_games': total_games,
        'completed_games': completed_games.count(),
        'success_rate': round(success_rate, 1),
        'avg_time': avg_time['avg_duration'],
        'difficult_games': difficult_games,
        'recent_sessions': recent_sessions,
        'best_sessions': best_sessions,
    }
    
    return render(request, 'game/user_stats.html', context)

@login_required
def get_pixelated_image(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        image_url = data.get('image_url')
        progress = float(data.get('progress', 0))
        
        # Inverser la logique : au début (progress = 1), les pixels sont très gros (50)
        # À la fin (progress = 0), les pixels sont très petits (1)
        pixel_size = max(1, int(50 * progress))
        
        pixelated_image = pixelate_image(image_url, pixel_size)
        return JsonResponse({'image_data': pixelated_image})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

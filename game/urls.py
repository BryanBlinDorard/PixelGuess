from django.urls import path
from . import views

app_name = 'game'

urlpatterns = [
    path('', views.home, name='home'),
    path('sync/', views.sync_games, name='sync_games'),
    path('start/', views.start_game, name='start_game'),
    path('check/<int:session_id>/', views.check_answer, name='check_answer'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('suggestions/', views.get_suggestions, name='get_suggestions'),
    path('games/', views.games_list, name='games_list'),
    path('stats/', views.user_stats, name='user_stats'),
    path('pixelate/', views.get_pixelated_image, name='get_pixelated_image'),
] 
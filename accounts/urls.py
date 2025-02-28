from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('steam/login/', views.steam_login, name='steam_login'),
    path('steam/callback/', views.steam_auth_callback, name='steam_callback'),
] 
from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class SteamGame(models.Model):
    user = models.ManyToManyField(User, related_name='steam_games')
    app_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    image_url = models.URLField(max_length=500)
    screenshots = models.JSONField(default=list, blank=True)
    local_image = models.ImageField(upload_to='game_images/', null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_synced = models.BooleanField(default=False)
    
    release_date = models.DateField(null=True, blank=True)
    genres = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.name} ({self.app_id})"

class GameSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(SteamGame, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(default=0)
    attempts = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Session de {self.user.username} - {self.game.name}"

class AnimeEntry(models.Model):
    WATCHING = 'WATCHING'
    COMPLETED = 'COMPLETED'
    PLANNING = 'PLANNING'
    DROPPED = 'DROPPED'
    PAUSED = 'PAUSED'

    STATUS_CHOICES = [
        (WATCHING, 'En cours'),
        (COMPLETED, 'Terminé'),
        (PLANNING, 'Prévu'),
        (DROPPED, 'Abandonné'),
        (PAUSED, 'En pause'),
    ]

    user = models.ManyToManyField(User, related_name='anime_entries')
    anilist_id = models.IntegerField(unique=True)
    title_romaji = models.CharField(max_length=255)
    title_english = models.CharField(max_length=255, null=True, blank=True)
    title_native = models.CharField(max_length=255, null=True, blank=True)
    cover_image = models.URLField(max_length=500)
    banner_image = models.URLField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    episodes = models.IntegerField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    genres = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)
    average_score = models.IntegerField(null=True, blank=True)
    is_synced = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title_romaji

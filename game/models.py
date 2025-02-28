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

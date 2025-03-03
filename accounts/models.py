from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.URLField(max_length=300, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

class SteamProfile(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    steam_id = models.CharField(max_length=100)
    steam_username = models.CharField(max_length=100)
    steam_avatar = models.URLField(max_length=300)
    last_sync = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.steam_username}'s Steam Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()

class AnilistProfile(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    anilist_id = models.CharField(max_length=50)
    anilist_username = models.CharField(max_length=255)
    anilist_avatar = models.URLField(max_length=500, null=True, blank=True)
    last_sync = models.DateTimeField(auto_now=True)
    access_token = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Profil Anilist de {self.user_profile.user.username}"

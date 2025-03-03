# Generated by Django 5.1.6 on 2025-02-28 17:54

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0003_auto_20250228_1721'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='steamgame',
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name='steamgame',
            name='app_id',
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.RemoveField(
            model_name='steamgame',
            name='user',
        ),
        migrations.AddField(
            model_name='steamgame',
            name='user',
            field=models.ManyToManyField(related_name='steam_games', to=settings.AUTH_USER_MODEL),
        ),
    ]

from django.core.management.base import BaseCommand
from django.conf import settings
from game.models import SteamGame
import requests
import time
from datetime import datetime
from django.db import models
from django.db.models import Q

class Command(BaseCommand):
    help = 'Récupère les données additionnelles (screenshots, date de sortie, genres, tags) pour les jeux Steam existants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force la mise à jour de tous les jeux, même ceux ayant déjà des données'
        )

    def handle(self, *args, **options):
        # Filtrer les jeux selon l'option --force
        if options['force']:
            games = SteamGame.objects.filter(is_synced=True)
            self.stdout.write(self.style.WARNING('Mode force activé : mise à jour de tous les jeux'))
        else:
            games = SteamGame.objects.filter(
                is_synced=True
            ).filter(
                Q(screenshots__isnull=True) | Q(screenshots=[]) |
                Q(release_date__isnull=True) |
                Q(genres__isnull=True) | Q(genres=[]) |
                Q(tags__isnull=True) | Q(tags=[])
            )
            self.stdout.write(self.style.SUCCESS('Mode normal : mise à jour uniquement des jeux sans données complètes'))

        total_games = games.count()
        if total_games == 0:
            self.stdout.write(self.style.SUCCESS('Aucun jeu à mettre à jour !'))
            return

        updated_games = 0
        failed_games = []

        self.stdout.write(self.style.SUCCESS(f'Début de la mise à jour des données pour {total_games} jeux'))

        for game in games:
            try:
                # Attendre un peu entre chaque requête pour ne pas surcharger l'API
                time.sleep(0.5)

                # Récupérer les détails du jeu depuis l'API Steam
                app_details_url = f'https://store.steampowered.com/api/appdetails?appids={game.app_id}'
                app_response = requests.get(app_details_url)
                
                if app_response.status_code == 200:
                    app_data = app_response.json()
                    
                    if str(game.app_id) in app_data and app_data[str(game.app_id)]['success']:
                        game_details = app_data[str(game.app_id)]['data']
                        updated = False

                        # Récupérer les screenshots
                        if 'screenshots' in game_details:
                            screenshots = [s['path_full'] for s in game_details['screenshots']]
                            game.screenshots = screenshots
                            updated = True

                        # Récupérer la date de sortie
                        if 'release_date' in game_details and 'date' in game_details['release_date']:
                            try:
                                release_date = datetime.strptime(game_details['release_date']['date'], '%d %b, %Y').date()
                                game.release_date = release_date
                                updated = True
                            except (ValueError, TypeError):
                                pass

                        # Récupérer les genres
                        if 'genres' in game_details:
                            genres = [genre['description'] for genre in game_details['genres']]
                            game.genres = genres
                            updated = True

                        # Récupérer les tags
                        if 'categories' in game_details:
                            tags = [category['description'] for category in game_details['categories']]
                            game.tags = tags
                            updated = True

                        if updated:
                            game.save()
                            updated_games += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'[{updated_games}/{total_games}] Mise à jour réussie pour {game.name}'
                                )
                            )
                        else:
                            failed_games.append((game.name, "Aucune nouvelle donnée disponible"))
                    else:
                        failed_games.append((game.name, "Données du jeu non disponibles"))
                else:
                    failed_games.append((game.name, f"Erreur API: {app_response.status_code}"))

            except Exception as e:
                failed_games.append((game.name, str(e)))
                self.stdout.write(
                    self.style.ERROR(f'Erreur lors de la mise à jour de {game.name}: {str(e)}')
                )

        # Afficher le résumé
        self.stdout.write('\nRésumé de la mise à jour :')
        self.stdout.write(self.style.SUCCESS(f'✓ {updated_games} jeux mis à jour avec succès'))
        
        if failed_games:
            self.stdout.write(self.style.ERROR(f'✗ {len(failed_games)} échecs :'))
            for game_name, error in failed_games:
                self.stdout.write(self.style.ERROR(f'  - {game_name}: {error}')) 
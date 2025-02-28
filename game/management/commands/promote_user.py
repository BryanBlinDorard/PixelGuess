from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Q

class Command(BaseCommand):
    help = 'Promeut un utilisateur en superuser'

    def add_arguments(self, parser):
        parser.add_argument(
            'identifier',
            type=str,
            help='Username ou email de l\'utilisateur à promouvoir'
        )

    def handle(self, *args, **options):
        identifier = options['identifier']
        
        try:
            # Chercher l'utilisateur par username ou email
            user = User.objects.get(Q(username=identifier) | Q(email=identifier))
            
            # Promouvoir l'utilisateur
            user.is_superuser = True
            user.is_staff = True
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'L\'utilisateur "{user.username}" a été promu en superuser avec succès !')
            )
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Aucun utilisateur trouvé avec l\'identifiant "{identifier}"')
            )
        except User.MultipleObjectsReturned:
            self.stdout.write(
                self.style.ERROR(f'Plusieurs utilisateurs trouvés avec l\'identifiant "{identifier}". Utilisez le nom d\'utilisateur exact.')
            ) 
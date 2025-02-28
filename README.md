# Pixel Guess

Pixel Guess est un jeu de devinettes d'images de jeux Steam. Les joueurs doivent deviner le nom du jeu à partir d'une image pixelisée qui se dévoile progressivement.

## Fonctionnalités

- 🎮 Connexion via Steam
- 🖼️ Jeu de devinettes avec images progressivement révélées
- 📊 Statistiques détaillées des performances
- 🏆 Classement des joueurs
- 🔍 Liste des jeux filtrables et triables
- 🌓 Mode sombre/clair

## Prérequis

- Python 3.8+
- Django 4.x
- Un compte développeur Steam pour l'API

## Installation

1. Clonez le dépôt :
```bash
git clone https://github.com/BryanBlinDorard/PixelGuess.git
cd PixelGuess
```

2. Créez un environnement virtuel et activez-le :
```bash
python -m venv env
source env/bin/activate  # Linux/Mac
# ou
.\env\Scripts\activate  # Windows
```

3. Installez les dépendances :
```bash
pip install -r requirements.txt
```

4. Créez un fichier `.env` à la racine du projet :
```env
SECRET_KEY=votre_clé_secrète
DEBUG=True
STEAM_API_KEY=votre_clé_api_steam
```

5. Effectuez les migrations :
```bash
python manage.py migrate
```

6. Lancez le serveur de développement :
```bash
python manage.py runserver
```

## Configuration Steam

1. Créez un compte développeur Steam sur [Steam Community](https://steamcommunity.com/dev)
2. Obtenez une clé API Steam
3. Configurez l'URL de retour OAuth dans les paramètres de votre application Steam

## Commandes personnalisées

- `python manage.py fetch_game_data` : Récupère les détails des jeux (images, tags, etc.)

## Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.

## Remerciements

- [Steam API](https://developer.valvesoftware.com/wiki/Steam_Web_API)
- [Bootstrap](https://getbootstrap.com/)
- [Font Awesome](https://fontawesome.com/) 
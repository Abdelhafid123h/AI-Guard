#!/bin/bash
set -e

echo "🚀 Initialisation du conteneur AI-Guards Backend..."

# Attendre que les dépendances soient prêtes (si nécessaire)
echo "📦 Vérification des dépendances..."

# Initialiser la base de données si elle n'existe pas
if [ ! -f "/app/app/database/ai_guards.db" ]; then
    echo "🗄️ Initialisation de la base de données SQLite..."
    cd /app
    python -c "
import sys
sys.path.insert(0, '/app')
from init_database import init_database
init_database()
print('✅ Base de données initialisée avec succès!')
"
else
    echo "✅ Base de données déjà existante, aucune initialisation nécessaire"
fi

# Afficher les informations de démarrage
echo "🌐 Démarrage du serveur AI-Guards sur http://0.0.0.0:8000"
echo "📚 Documentation API disponible sur http://localhost:8000/docs"

# Exécuter la commande principale
exec "$@"

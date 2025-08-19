#!/bin/bash
set -e

echo "🚀 Initialisation du conteneur AI-Guards Backend..."

# Attendre que les dépendances soient prêtes (si nécessaire)
echo "📦 Vérification des dépendances... (DB_ENGINE=${DB_ENGINE})"

if [ "${DB_ENGINE}" = "mysql" ]; then
    echo "🗄️ Mode MySQL détecté: saut de l'initialisation SQLite et attente de MySQL"
    # Attendre MySQL (jusqu'à ~40s)
    /opt/venv/bin/python - <<'PY'
import os, time
import sys
sys.path.insert(0, '/app')
host = os.getenv('DB_HOST','mysql'); port = int(os.getenv('DB_PORT','3306'))
user = os.getenv('DB_USER','root'); pwd = os.getenv('DB_PASSWORD',''); db = os.getenv('DB_NAME','ai_guards')
retries = int(os.getenv('SEED_STARTUP_RETRIES','20')); delay = float(os.getenv('SEED_STARTUP_DELAY','2.0'))
ok = False
for i in range(retries):
    try:
        import pymysql
        conn = pymysql.connect(host=host, port=port, user=user, password=pwd, database=db, charset='utf8mb4')
        with conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
        ok = True
        print('✅ MySQL prêt')
        break
    except Exception as e:
        print(f'MySQL pas prêt (essai {i+1}/{retries}):', e)
        time.sleep(delay)
if not ok:
    print('⚠️  MySQL indisponible, le service pourra réessayer au démarrage de l\'API')
PY
    echo "🌱 Seeding des types/champs par défaut (idempotent) via venv Python"
    /opt/venv/bin/python - <<'PY'
import sys
sys.path.insert(0, '/app')
try:
    from app.init_seed_defaults import seed_defaults
    res = seed_defaults()
    print('Seed defaults:', res)
except Exception as e:
    print('Seed defaults error:', e)
PY
else
    # Initialiser la base de données SQLite si nécessaire
    if [ ! -f "/app/app/database/ai_guards.db" ]; then
        echo "🗄️ Initialisation de la base de données SQLite..."
        cd /app
        /opt/venv/bin/python -c "import sys; sys.path.insert(0, '/app'); from init_database import init_database; init_database(); print('✅ Base de données initialisée avec succès!')"
    else
        echo "✅ Base de données SQLite déjà existante, aucune initialisation nécessaire"
    fi
    # Seed par défaut (idempotent)
    echo "🌱 Seeding des types/champs par défaut (idempotent) via venv Python"
    /opt/venv/bin/python - <<'PY'
import sys
sys.path.insert(0, '/app')
try:
    from app.init_seed_defaults import seed_defaults
    res = seed_defaults()
    print('Seed defaults:', res)
except Exception as e:
    print('Seed defaults error:', e)
PY
fi

# Afficher les informations de démarrage
echo "🌐 Démarrage du serveur AI-Guards sur http://0.0.0.0:8000"
echo "📚 Documentation API disponible sur http://localhost:8000/docs"

# Exécuter la commande principale
exec "$@"

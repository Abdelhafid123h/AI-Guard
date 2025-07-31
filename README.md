# IA_Guards

IA_Guards est une application complète de protection des données personnelles pour l'Intelligence Artificielle. Elle permet de masquer les informations sensibles (PII), d'interroger un LLM (OpenAI), et de consulter les logs du système via une interface web moderne.

## Fonctionnalités principales
- **Masquage PII** : Détection et anonymisation des données personnelles dans un texte.
- **Logs système** : Visualisation des logs du backend depuis le frontend.
- **LLM** : Interaction avec un modèle OpenAI pour traiter des textes masqués.

## Architecture
- **Backend** : FastAPI (Python), gestion du masquage, logs, et communication avec OpenAI.
- **Frontend** : React (JavaScript), interface utilisateur pour soumettre des textes, voir les résultats et les logs.

## Prérequis
- Python 3.9+
- Node.js 16+ et npm
- Clé API OpenAI (à renseigner dans `backend/app/services/llm_service.py`)

## Installation

### 1. Backend
```bash
cd backend
pip install --upgrade pip
pip install -r requirements_exact.txt
```

### 2. Frontend
```bash
cd ../frontend
npm install
```

## Lancement

### 1. Backend
```bash
cd backend
uvicorn app.main:app --reload
```
Le backend sera accessible sur http://127.0.0.1:8000

### 2. Frontend
```bash
cd frontend
npm start
```
Le frontend sera accessible sur http://localhost:3000

## Utilisation
1. Ouvrez http://localhost:3000 dans votre navigateur.
2. Saisissez un texte à protéger, choisissez le type de garde et soumettez.
3. Consultez le résultat masqué et la réponse du LLM.
4. Cliquez sur "Afficher les logs" pour voir les logs système du backend.


import logging
import os
# Correction du chemin pour éviter le double 'backend'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "logs", "app.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .services.guard_service import GuardService
from .utils.config_loader import config_loader
from typing import Dict, List

app = FastAPI()

# Configuration CORS pour permettre les requêtes depuis le frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

from fastapi import Response

@app.get("/logs")
def get_logs():
    try:
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(LOG_PATH, "r", encoding="latin-1") as f:
                content = f.read()
        return Response(content, media_type="text/plain")
    except Exception as e:
        return Response(f"Erreur lecture logs: {e}", media_type="text/plain", status_code=500)

guard_service = GuardService()

class ProcessRequest(BaseModel):
    text: str
    guard_type: str
    llm_provider: str

@app.post("/process")
def process(request: ProcessRequest):
    try:
        result = guard_service.process(request.text, request.guard_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config")
def get_configurations():
    """Retourne toutes les configurations de guards depuis les JSON"""
    try:
        return {
            "configurations": config_loader.get_all_configs(),
            "message": "Configurations chargées depuis les fichiers JSON"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur chargement configuration: {str(e)}")

@app.get("/config/{guard_type}")
def get_guard_config(guard_type: str):
    """Retourne la configuration d'un guard spécifique"""
    try:
        types = config_loader.get_guard_types(guard_type)
        if not types:
            raise HTTPException(status_code=404, detail=f"Configuration pour {guard_type} non trouvée")
        return {
            "guard_type": guard_type,
            "pii_types": types
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config/reload")
def reload_configuration(guard_type: str = None):
    """Recharge la configuration depuis les JSON"""
    try:
        config_loader.reload_config(guard_type)
        return {
            "message": f"Configuration {'de ' + guard_type if guard_type else 'complète'} rechargée avec succès"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur rechargement: {str(e)}")

@app.get("/examples/{guard_type}")
def get_example_text(guard_type: str):
    """Retourne un texte d'exemple basé sur la configuration JSON"""
    try:
        example_text = config_loader.get_example_text(guard_type)
        return {
            "guard_type": guard_type,
            "example_text": example_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
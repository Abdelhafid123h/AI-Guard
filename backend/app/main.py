import logging
import os
import time
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
logging.getLogger().setLevel(logging.DEBUG)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .services.guard_service import GuardService
from .utils.dynamic_config_loader import dynamic_config_loader
from .api.config_api import config_router
from typing import Dict, List
# Import db_manager and try to import DB_MANAGER_VERSION with a safe fallback
try:
    from .database.db_manager import db_manager, DB_MANAGER_VERSION  # type: ignore
except Exception:
    from .database.db_manager import db_manager  # type: ignore
    DB_MANAGER_VERSION = os.getenv("DB_MANAGER_VERSION", "unknown")
from .init_seed_defaults import seed_defaults

app = FastAPI(
    title="AI-Guards API",
    description="API de protection des données personnelles avec configuration dynamique",
    version="2.0.0"
)

# Seed par défaut au démarrage (avec quelques retries pour MySQL)
@app.on_event("startup")
def _startup_seed_defaults():
    retries = int(os.getenv("SEED_STARTUP_RETRIES", "20"))  # ~40s total par défaut
    delay = float(os.getenv("SEED_STARTUP_DELAY", "2.0"))
    for i in range(retries):
        try:
            # Ping DB légère
            try:
                with db_manager.get_connection() as conn:
                    cur = conn.cursor()
                    if db_manager.engine == 'mysql':
                        cur.execute("SELECT 1")
                    else:
                        conn.execute("SELECT 1")
            except Exception as e:
                logging.getLogger(__name__).warning(f"DB pas prête (tentative {i+1}/{retries}): {e}")
                time.sleep(delay)
                continue
            # S'assurer que le schéma est initialisé maintenant que la DB est accessible
            try:
                db_manager.init_database()
            except Exception as e:
                logging.getLogger(__name__).warning(f"Init schéma ignorée/échouée: {e}")
            res = seed_defaults()
            if res.get("success"):
                logging.getLogger(__name__).info(f"Seed défauts OK: {res}")
            else:
                logging.getLogger(__name__).warning(f"Seed défauts échec: {res}")
            break
        except Exception as e:
            logging.getLogger(__name__).warning(f"Seed défauts tentative {i+1}/{retries} échouée: {e}")
            time.sleep(delay)

# Root simple (utile pour tests manuels, renvoie statut de base)
@app.get("/")
def root():
    return {"status": "ok", "service": "ai-guards-backend"}

# Endpoint de santé détaillé (utilisé par Docker healthcheck)
@app.get("/health")
def health():
    status = {"status": "ok"}
    # Vérification DB légère
    try:
        from .database.db_manager import db_manager as _db
        engine = _db.engine
        if engine == 'mysql':
            # simple ping
            with _db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
        else:
            with _db.get_connection() as conn:
                conn.execute("SELECT 1")
        status["database"] = "up"
        status["engine"] = engine
    except Exception as e:
        status["database"] = "down"
        status["error"] = str(e)
    return status

# Configuration CORS pour permettre les requêtes depuis le frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Inclusion des routers API
app.include_router(config_router)

from fastapi import Response  # (plus d'endpoint /logs — historique via /usage/history)

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

class MaskOnlyRequest(BaseModel):
    text: str
    guard_type: str

@app.post("/mask-only")
def mask_only(request: MaskOnlyRequest):
    try:
        return guard_service.mask_only(request.text, request.guard_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class FinalizeRequest(BaseModel):
    masked: str
    tokens: Dict[str, str]
    guard_type: str

@app.post("/finalize")
def finalize(request: FinalizeRequest):
    try:
        return guard_service.finalize_with_mask(request.masked, request.tokens, request.guard_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usage/history")
def list_usage(limit: int = 100):
    try:
        data = db_manager.list_usage_history(limit)
        # Fallback calcul côté backend si masked_token_count absent (ancienne entrées)
        for row in data:
            if not row.get('masked_token_count') and row.get('masked_text'):
                import re
                row['masked_token_count'] = len(re.findall(r"<[^:<>]+:TOKEN_[^>]+>", row['masked_text']))
            # Estimation tokens si 0 et texte présent
            if row.get('prompt_tokens', 0) == 0 and row.get('masked_text'):
                row['prompt_tokens'] = len(row['masked_text'].split())
            if row.get('total_tokens', 0) == 0:
                row['total_tokens'] = row.get('prompt_tokens', 0) + row.get('completion_tokens', 0)
            # llm_mode fallback
            if 'llm_mode' not in row or not row['llm_mode']:
                row['llm_mode'] = 'legacy'
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usage/history/{entry_id}")
def get_usage(entry_id: int):
    try:
        entry = db_manager.get_usage_entry(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Entrée non trouvée")
        return {"success": True, "data": entry}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usage/debug")
def usage_debug():
    try:
        info = {"engine": getattr(db_manager, 'engine', 'unknown')}
        with db_manager.get_connection() as conn:
            cur = conn.cursor()
            engine = info['engine']
            if engine == 'mysql':
                cur.execute("SHOW COLUMNS FROM usage_history")
                cols = [r[0] for r in cur.fetchall()]
            else:
                cur.execute("PRAGMA table_info(usage_history)")
                cols = [r[1] for r in cur.fetchall()]
            info['columns'] = cols
            # Try sample row
            try:
                cursor2 = conn.execute("SELECT * FROM usage_history ORDER BY id DESC LIMIT 1") if db_manager.engine != 'mysql' else conn.cursor()
                if db_manager.engine == 'mysql':
                    cursor2.execute("SELECT * FROM usage_history ORDER BY id DESC LIMIT 1")
                row = cursor2.fetchone()
                info['last_row'] = dict(row) if row else None
            except Exception as inner:
                info['last_row_error'] = str(inner)
        return {"success": True, "data": info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config")
def get_configurations():
    """Retourne toutes les configurations de guards depuis la nouvelle base de données"""
    try:
        return {
            "configurations": dynamic_config_loader.get_all_configs(),
            "message": "Configurations chargées depuis la base de données dynamique"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur chargement configuration: {str(e)}")

@app.get("/config/{guard_type}")
def get_guard_config(guard_type: str):
    """Retourne la configuration d'un guard spécifique"""
    try:
        types = dynamic_config_loader.get_guard_types(guard_type)
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
    """Recharge la configuration depuis la base de données"""
    try:
        dynamic_config_loader.reload_config(guard_type)
        return {
            "message": f"Configuration {'de ' + guard_type if guard_type else 'complète'} rechargée avec succès"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur rechargement: {str(e)}")

@app.get("/examples/{guard_type}")
def get_example_text(guard_type: str):
    """Retourne un texte d'exemple basé sur la configuration de la base de données"""
    try:
        example_text = dynamic_config_loader.get_example_text(guard_type)
        return {
            "guard_type": guard_type,
            "example_text": example_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/usage/backfill")
def backfill_usage(model: str = None, recompute_prompt: bool = True):
    try:
        model_effective = model or os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        result = db_manager.backfill_usage_history(model_effective, recompute_prompt)
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error','unknown'))
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usage/version")
def usage_version():
    has_method = hasattr(db_manager, 'list_usage_history')
    return {"db_manager_version": DB_MANAGER_VERSION, "has_list_usage_history": has_method, "engine_attr": hasattr(db_manager, 'engine')}
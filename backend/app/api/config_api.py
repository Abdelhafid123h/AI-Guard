from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from ..utils.dynamic_config_loader import dynamic_config_loader
from ..database.db_manager import db_manager
from ..utils.entity_mapping import canonicalize_entity, list_supported_entities
import logging
from ..init_seed_defaults import seed_defaults

logger = logging.getLogger(__name__)

# Créer un router pour les endpoints de configuration
config_router = APIRouter(prefix="/api/config", tags=["Configuration"])

# =================== MODÈLES PYDANTIC ===================

class GuardTypeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Nom unique du type")
    display_name: str = Field(..., min_length=1, max_length=100, description="Nom d'affichage")
    description: str = Field("", max_length=500, description="Description du type")
    icon: str = Field("🛡️", max_length=10, description="Icône emoji")
    color: str = Field("#666666", pattern=r"^#[0-9A-Fa-f]{6}$", description="Couleur hex")

class GuardTypeUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=10)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")

class PIIFieldCreate(BaseModel):
    """Modèle officiel (noms courts) utilisé par le frontend récent.
    On garde aussi une route alternative pour l'ancien script de test qui
    envoie detection_type/example_value/regex_pattern.
    """
    field_name: str = Field(..., min_length=1, max_length=50, description="Nom du champ")
    display_name: str = Field(..., min_length=1, max_length=100, description="Nom d'affichage")
    type: str = Field(..., pattern=r"^(regex|ner|hybrid)$", description="Type de détection (regex|ner|hybrid)")
    example: str = Field(..., description="Exemple de valeur")
    pattern: Optional[str] = Field(None, description="Pattern regex ou nom du pattern")
    ner_entity_type: Optional[str] = Field(None, description="Type d'entité NER (ex: EMAIL_ADDRESS, PERSON)")
    # confidence_threshold & priority retirés de l'API publique

class PIIFieldUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    detection_type: Optional[str] = Field(None, pattern=r"^(regex|ner|hybrid)$")
    example_value: Optional[str] = Field(None)
    regex_pattern: Optional[str] = Field(None)
    ner_entity_type: Optional[str] = Field(None)
    # confidence_threshold & priority retirés

class RegexPatternCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Nom unique du pattern")
    display_name: str = Field(..., min_length=1, max_length=100, description="Nom d'affichage")
    pattern: str = Field(..., description="Expression régulière")
    description: str = Field("", max_length=500, description="Description du pattern")
    test_examples: List[str] = Field([], description="Exemples de test")
    flags: str = Field("i", description="Flags regex (i, m, s)")

class RegexPatternUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    pattern: Optional[str] = Field(None)
    description: Optional[str] = Field(None, max_length=500)
    test_examples: Optional[List[str]] = Field(None)
    flags: Optional[str] = Field(None)

# =================== MODÈLE COMPAT ANCIEN SCRIPT ===================

class PIIFieldCreateAlt(BaseModel):
    """Modèle rétro-compatible avec l'ancien script test_dynamic_system.py.
    (detection_type, example_value, regex_pattern)
    """
    guard_type: str = Field(..., min_length=1)
    field_name: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    detection_type: str = Field(..., pattern=r"^(regex|ner|hybrid)$")
    example_value: str = Field(...)
    regex_pattern: Optional[str] = None
    ner_entity_type: Optional[str] = None
    # champs retirés (conservés pour compat mais ignorés)

# =================== ENDPOINTS GUARD TYPES ===================

@config_router.get("/guard-types", summary="Liste des types de protection")
async def get_guard_types():
    """Récupère tous les types de protection disponibles"""
    try:
        guard_types = db_manager.get_guard_types()
        return {
            "success": True,
            "guard_types": guard_types,  # Changé de "data" à "guard_types"
            "count": len(guard_types)
        }
    except Exception as e:
        logger.error(f"Erreur récupération guard types: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.post("/guard-types", summary="Créer un type de protection")
async def create_guard_type(guard_type: GuardTypeCreate):
    """Crée un nouveau type de protection"""
    try:
        guard_id = db_manager.create_guard_type(
            name=guard_type.name,
            display_name=guard_type.display_name,
            description=guard_type.description,
            icon=guard_type.icon,
            color=guard_type.color
        )
        
        return {
            "success": True,
            "message": f"Type '{guard_type.name}' créé avec succès",
            # compat
            "guard_id": guard_id,
            "id": guard_id,
            "name": guard_type.name,
            "display_name": guard_type.display_name
        }
            
    except Exception as e:
        logger.error(f"Erreur création guard type: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.put("/guard-types/{guard_name}", summary="Modifier un type de protection")
async def update_guard_type(guard_name: str, guard_type: GuardTypeUpdate):
    """Met à jour un type de protection existant"""
    try:
        # Convertir le modèle en dict en excluant les valeurs None
        update_data = guard_type.dict(exclude_none=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")
        
        result = dynamic_config_loader.update_guard_type(guard_name, **update_data)
        
        if result['success']:
            return {
                "success": True,
                "message": result['message']
            }
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Erreur mise à jour'))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise à jour guard type: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.delete("/guard-types/{guard_id}", summary="Supprimer un type de protection")
async def delete_guard_type(guard_id: int):
    """Supprime (désactive) un type de protection par ID"""
    try:
        success = db_manager.delete_guard_type(guard_id)
        
        if success:
            return {
                "success": True,
                "message": f"Type ID '{guard_id}' supprimé avec succès"
            }
        else:
            raise HTTPException(status_code=404, detail="Type non trouvé ou erreur lors de la suppression")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression guard type: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Optionnel: suppression par nom (pratique pour nettoyer 'T1')
@config_router.delete("/guard-types/by-name/{guard_name}", summary="Supprimer un type par nom")
async def delete_guard_type_by_name(guard_name: str):
    try:
        gt = db_manager.get_guard_type(guard_name)
        if not gt:
            raise HTTPException(status_code=404, detail="Type non trouvé")
        success = db_manager.delete_guard_type(gt['id'])
        if success:
            return {"success": True, "message": f"Type '{guard_name}' supprimé"}
        raise HTTPException(status_code=400, detail="Suppression échouée")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression par nom: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== ENDPOINTS PII FIELDS ===================

@config_router.get("/guard-types/{guard_name}/fields", summary="Champs PII d'un type")
async def get_pii_fields(guard_name: str):
    """Récupère tous les champs PII d'un type de protection"""
    try:
        fields = db_manager.get_pii_fields(guard_name)
        return {
            "success": True,
            "guard_type": guard_name,
            "data": fields,
            "count": len(fields)
        }
    except Exception as e:
        logger.error(f"Erreur récupération champs PII: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.post("/guard-types/{guard_name}/fields", summary="Créer un champ PII")
async def create_pii_field(guard_name: str, field: PIIFieldCreate):
    """Crée un nouveau champ PII pour un type de protection"""
    try:
        # Validation spécifique
        if field.type in ['regex', 'hybrid'] and not field.pattern:
            raise HTTPException(status_code=400, detail="Pattern requis pour type regex/hybrid")
        
        if field.type in ['ner', 'hybrid']:
            if not field.ner_entity_type:
                raise HTTPException(status_code=400, detail="ner_entity_type requis pour type ner/hybrid")
            canonical, valid = canonicalize_entity(field.ner_entity_type)
            if not valid:
                raise HTTPException(status_code=400, detail=f"ner_entity_type inconnu: {field.ner_entity_type}")
            field.ner_entity_type = canonical
        
        field_data = {
            'field_name': field.field_name,
            'display_name': field.display_name,
            'type': field.type,
            'example': field.example,
            'pattern': field.pattern,
            'ner_entity_type': field.ner_entity_type
        }
        
        result = dynamic_config_loader.create_pii_field(guard_name, field_data)
        
        if result['success']:
            return {
                "success": True,
                "message": result['message'],
                "field_id": result['field_id'],
                # compat
                "id": result['field_id'],
                "guard_type": guard_name,
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur création champ PII: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.put("/pii-fields/{field_id}", summary="Modifier un champ PII")
async def update_pii_field(field_id: int, field: PIIFieldUpdate):
    """Met à jour un champ PII existant"""
    try:
        update_data = field.dict(exclude_none=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")
        
        result = dynamic_config_loader.update_pii_field(field_id, **update_data)
        
        if result['success']:
            return {
                "success": True,
                "message": result['message']
            }
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Erreur mise à jour'))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise à jour champ PII: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.delete("/pii-fields/{field_id}", summary="Supprimer un champ PII")
async def delete_pii_field(field_id: int):
    """Supprime (désactive) un champ PII"""
    try:
        success = db_manager.delete_pii_field(field_id)
        
        if success:
            return {
                "success": True,
                "message": f"Champ ID {field_id} supprimé avec succès"
            }
        else:
            raise HTTPException(status_code=400, detail="Erreur lors de la suppression")
            
    except Exception as e:
        logger.error(f"Erreur suppression champ PII: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== ENDPOINTS REGEX PATTERNS ===================

@config_router.get("/regex-patterns", summary="Liste des patterns regex")
async def get_regex_patterns():
    """Récupère tous les patterns regex disponibles"""
    try:
        patterns = db_manager.get_regex_patterns()
        return {
            "success": True,
            "data": patterns,          # clé existante
            "patterns": patterns,      # alias pour compat frontend
            "count": len(patterns)
        }
    except Exception as e:
        logger.error(f"Erreur récupération patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.post("/regex-patterns", summary="Créer un pattern regex")
async def create_regex_pattern(pattern: RegexPatternCreate):
    """Crée un nouveau pattern regex"""
    try:
        pattern_data = pattern.dict()
        result = dynamic_config_loader.create_regex_pattern(pattern_data)
        
        if result['success']:
            return {
                "success": True,
                "message": result['message'],
                "pattern_id": result['pattern_id']
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur création pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== ROUTE RÉTRO-COMPATIBLE (ANCIEN SCRIPT) ===================

@config_router.post("/pii-fields", summary="(Compat) Créer un champ PII - ancien format")
async def create_pii_field_alt(field: PIIFieldCreateAlt):
    """Permet au script test_dynamic_system.py existant d'ajouter un champ.
    Mapping des clés vers le format moderne.
    """
    try:
        # Validation
        if field.detection_type in ['regex', 'hybrid'] and not field.regex_pattern:
            raise HTTPException(status_code=400, detail="regex_pattern requis pour type regex/hybrid (compat)")
        if field.detection_type in ['ner', 'hybrid']:
            if not field.ner_entity_type:
                raise HTTPException(status_code=400, detail="ner_entity_type requis pour type ner/hybrid (compat)")
            canonical, valid = canonicalize_entity(field.ner_entity_type)
            if not valid:
                raise HTTPException(status_code=400, detail=f"ner_entity_type inconnu: {field.ner_entity_type}")
            field.ner_entity_type = canonical

        field_data = {
            'field_name': field.field_name,
            'display_name': field.display_name,
            'type': field.detection_type,
            'example': field.example_value,
            'pattern': field.regex_pattern,
            'ner_entity_type': field.ner_entity_type
        }

        result = dynamic_config_loader.create_pii_field(field.guard_type, field_data)
        if result['success']:
            return {
                'success': True,
                'message': result['message'],
                'field_id': result['field_id'],
                'id': result['field_id'],
                'guard_type': field.guard_type,
                'field_name': field.field_name
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur création champ PII (compat): {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== ENDPOINTS UTILITAIRES ===================

@config_router.get("/ner-entity-types", summary="Types d'entités NER disponibles")
async def get_ner_entity_types_alias():
    """Types d'entités NER disponibles pour le frontend"""
    try:
        ner_types = db_manager.get_ner_entity_types()
        return {
            "success": True,
            "entity_types": ner_types,  # Nom attendu par le frontend
            "count": len(ner_types)
        }
    except Exception as e:
        logger.error(f"Erreur récupération types NER: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/pii-fields/{guard_type}", summary="Champs PII d'un type")
async def get_pii_fields_by_type(guard_type: str):
    """Récupère tous les champs PII d'un type de protection"""
    try:
        fields = db_manager.get_pii_fields(guard_type)
        return {
            "success": True,
            "fields": fields,
            "count": len(fields)
        }
    except Exception as e:
        logger.error(f"Erreur récupération champs PII: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/ner-types", summary="Types d'entités NER disponibles")
async def get_ner_types():
    """Récupère tous les types d'entités NER disponibles"""
    try:
        ner_types = db_manager.get_ner_entity_types()
        return {
            "success": True,
            "ner_types": ner_types,
            "count": len(ner_types)
        }
    except Exception as e:
        logger.error(f"Erreur récupération types NER: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/ner-supported", summary="Entités NER canoniques supportées")
async def get_supported_ner_entities(include_synonyms: bool = False):
    """Liste des entités NER canoniques (et optionnellement synonymes) supportées.

    Permet d'alimenter un sélecteur frontend et de prévenir les erreurs
    de saisie lors de la création de champs NER.
    """
    try:
        data = list_supported_entities(include_synonyms=include_synonyms)
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Erreur récupération entités supportées: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# (duplicate route removed)

@config_router.post("/reload", summary="Recharger la configuration")
async def reload_configuration():
    """Recharge la configuration depuis la base de données"""
    try:
        dynamic_config_loader.reload_patterns_cache()
        return {
            "success": True,
            "message": "Configuration rechargée avec succès"
        }
    except Exception as e:
        logger.error(f"Erreur rechargement config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/detection-config/{guard_type}", summary="Configuration de détection")
async def get_detection_config(guard_type: str):
    """Récupère la configuration de détection pour un type de protection"""
    try:
        config = dynamic_config_loader.get_detection_config(guard_type)
        return {
            "success": True,
            "guard_type": guard_type,
            "config": config
        }
    except Exception as e:
        logger.error(f"Erreur récupération config détection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== ADMIN: SEED PAR DÉFAUT ===================

@config_router.post("/seed-defaults", summary="Créer les types/champs par défaut si absents")
async def seed_defaults_api():
    try:
        res = seed_defaults()
        if not res.get('success'):
            raise HTTPException(status_code=500, detail=res.get('error','seed échoué'))
        return {"success": True, "data": res}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur seed defaults: {e}")
        raise HTTPException(status_code=500, detail=str(e))

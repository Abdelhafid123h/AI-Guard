from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import logging
from ..models.schemas import (
    GuardType, GuardTypeAttribute, CreateGuardTypeRequest, 
    CreateAttributeRequest, AttributeDefinition, AttributeDetectionType
)
from ..database.db_manager import db_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/guard-types", tags=["Guard Types CRUD"])

# =================== CRUD POUR LES TYPES DE PROTECTION ===================

@router.get("/", response_model=List[GuardType])
async def get_all_guard_types():
    """Récupère tous les types de protection avec leurs attributs"""
    try:
        types_data = db_manager.get_guard_types()
        result = []
        
        for type_data in types_data:
            # Récupérer les attributs (champs PII) pour chaque type
            pii_fields = db_manager.get_pii_fields(type_data['name'])
            
            # Convertir les champs PII en GuardTypeAttribute
            attributes = []
            for field in pii_fields:
                attr_def = AttributeDefinition(
                    type=AttributeDetectionType.REGEX if field['detection_type'] == 'regex' else AttributeDetectionType.NER,
                    exemple=field['example_value'],
                    pattern=field['pattern'],
                    description=field['display_name']
                )
                
                attribute = GuardTypeAttribute(
                    id=field['id'],
                    guard_type_id=type_data['id'],
                    name=field['field_name'],
                    definition=attr_def
                )
                attributes.append(attribute)
            
            guard_type = GuardType(
                id=type_data['id'],
                name=type_data['name'],
                description=type_data['description'],
                is_active=type_data['is_active'],
                attributes=attributes
            )
            result.append(guard_type)
        
        return result
    except Exception as e:
        logger.error(f"Erreur récupération types de protection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{guard_type_name}", response_model=GuardType)
async def get_guard_type(guard_type_name: str):
    """Récupère un type de protection spécifique avec ses attributs"""
    try:
        type_data = db_manager.get_guard_type(guard_type_name)
        if not type_data:
            raise HTTPException(status_code=404, detail=f"Type de protection '{guard_type_name}' non trouvé")
        
        # Récupérer les attributs
        pii_fields = db_manager.get_pii_fields(guard_type_name)
        attributes = []
        
        for field in pii_fields:
            attr_def = AttributeDefinition(
                type=AttributeDetectionType.REGEX if field['detection_type'] == 'regex' else AttributeDetectionType.NER,
                exemple=field['example_value'],
                pattern=field['pattern'],
                description=field['display_name']
            )
            
            attribute = GuardTypeAttribute(
                id=field['id'],
                guard_type_id=type_data['id'],
                name=field['field_name'],
                definition=attr_def
            )
            attributes.append(attribute)
        
        return GuardType(
            id=type_data['id'],
            name=type_data['name'],
            description=type_data['description'],
            is_active=type_data['is_active'],
            attributes=attributes
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération type de protection {guard_type_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=GuardType)
async def create_guard_type(request: CreateGuardTypeRequest):
    """Crée un nouveau type de protection avec ses attributs"""
    try:
        # Créer le type de protection
        guard_type_id = db_manager.create_guard_type(
            name=request.name,
            display_name=request.name,
            description=request.description or ""
        )
        
        # Créer les attributs initiaux
        attributes = []
        for attr_request in request.attributes:
            field_id = db_manager.create_pii_field(
                guard_type_name=request.name,
                field_name=attr_request.name,
                display_name=attr_request.definition.description or attr_request.name,
                detection_type=attr_request.definition.type.value,
                example_value=attr_request.definition.exemple,
                regex_pattern=attr_request.definition.pattern,
                ner_entity_type=None if attr_request.definition.type == AttributeDetectionType.REGEX else "PERSON"  # Default NER type
            )
            
            attribute = GuardTypeAttribute(
                id=field_id,
                guard_type_id=guard_type_id,
                name=attr_request.name,
                definition=attr_request.definition
            )
            attributes.append(attribute)
        
        return GuardType(
            id=guard_type_id,
            name=request.name,
            description=request.description,
            is_active=True,
            attributes=attributes
        )
    except Exception as e:
        logger.error(f"Erreur création type de protection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{guard_type_name}")
async def update_guard_type(guard_type_name: str, updates: Dict[str, Any]):
    """Met à jour un type de protection"""
    try:
        type_data = db_manager.get_guard_type(guard_type_name)
        if not type_data:
            raise HTTPException(status_code=404, detail=f"Type de protection '{guard_type_name}' non trouvé")
        
        success = db_manager.update_guard_type(type_data['id'], **updates)
        if not success:
            raise HTTPException(status_code=500, detail="Échec de la mise à jour")
        
        return {"message": "Type de protection mis à jour avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise à jour type de protection {guard_type_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{guard_type_name}")
async def delete_guard_type(guard_type_name: str):
    """Supprime un type de protection"""
    try:
        type_data = db_manager.get_guard_type(guard_type_name)
        if not type_data:
            raise HTTPException(status_code=404, detail=f"Type de protection '{guard_type_name}' non trouvé")
        
        success = db_manager.delete_guard_type(type_data['id'])
        if not success:
            raise HTTPException(status_code=500, detail="Échec de la suppression")
        
        return {"message": "Type de protection supprimé avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression type de protection {guard_type_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== CRUD POUR LES ATTRIBUTS ===================

@router.post("/{guard_type_name}/attributes", response_model=GuardTypeAttribute)
async def add_attribute_to_guard_type(guard_type_name: str, attribute: CreateAttributeRequest):
    """Ajoute un nouvel attribut à un type de protection existant"""
    try:
        type_data = db_manager.get_guard_type(guard_type_name)
        if not type_data:
            raise HTTPException(status_code=404, detail=f"Type de protection '{guard_type_name}' non trouvé")
        
        # Si c'est un pattern regex, l'ajouter aux patterns disponibles
        if attribute.definition.type == AttributeDetectionType.REGEX and attribute.definition.pattern:
            pattern_name = f"{guard_type_name}_{attribute.name}"
            try:
                db_manager.create_regex_pattern(
                    name=pattern_name,
                    display_name=f"{attribute.name} - {guard_type_name}",
                    pattern=attribute.definition.pattern,
                    description=f"Pattern pour {attribute.name} du type {guard_type_name}",
                    test_examples=[attribute.definition.exemple]
                )
                regex_pattern_ref = pattern_name
            except:
                # Si le pattern existe déjà ou erreur, utiliser directement le pattern
                regex_pattern_ref = attribute.definition.pattern
        else:
            regex_pattern_ref = None
        
        # Créer l'attribut (champ PII)
        field_id = db_manager.create_pii_field(
            guard_type_name=guard_type_name,
            field_name=attribute.name,
            display_name=attribute.definition.description or attribute.name,
            detection_type=attribute.definition.type.value,
            example_value=attribute.definition.exemple,
            regex_pattern=regex_pattern_ref,
            ner_entity_type=None if attribute.definition.type == AttributeDetectionType.REGEX else "PERSON"
        )
        
        return GuardTypeAttribute(
            id=field_id,
            guard_type_id=type_data['id'],
            name=attribute.name,
            definition=attribute.definition
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur ajout attribut au type {guard_type_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{guard_type_name}/attributes/{attribute_id}")
async def update_attribute(guard_type_name: str, attribute_id: int, updates: Dict[str, Any]):
    """Met à jour un attribut d'un type de protection"""
    try:
        success = db_manager.update_pii_field(attribute_id, **updates)
        if not success:
            raise HTTPException(status_code=404, detail="Attribut non trouvé ou échec de la mise à jour")
        
        return {"message": "Attribut mis à jour avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise à jour attribut {attribute_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{guard_type_name}/attributes/{attribute_id}")
async def delete_attribute(guard_type_name: str, attribute_id: int):
    """Supprime un attribut d'un type de protection"""
    try:
        success = db_manager.delete_pii_field(attribute_id)
        if not success:
            raise HTTPException(status_code=404, detail="Attribut non trouvé ou échec de la suppression")
        
        return {"message": "Attribut supprimé avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression attribut {attribute_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== UTILITAIRES ===================

@router.get("/patterns/regex", response_model=List[Dict[str, Any]])
async def get_regex_patterns():
    """Récupère tous les patterns regex disponibles"""
    try:
        return db_manager.get_regex_patterns()
    except Exception as e:
        logger.error(f"Erreur récupération patterns regex: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/patterns/ner", response_model=List[Dict[str, Any]])
async def get_ner_entity_types():
    """Récupère tous les types d'entités NER disponibles"""
    try:
        return db_manager.get_ner_entity_types()
    except Exception as e:
        logger.error(f"Erreur récupération types NER: {e}")
        raise HTTPException(status_code=500, detail=str(e))

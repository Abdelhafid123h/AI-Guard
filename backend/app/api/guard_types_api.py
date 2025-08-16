from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel, Field
from ..database.db_manager import DatabaseManager
from ..models.schemas import GuardType, PIIField, GuardTypeCreate, PIIFieldCreate

guard_types_router = APIRouter(prefix="/api/guard-types", tags=["Guard Types"])

def get_db():
    """Dependency pour obtenir une instance de DatabaseManager"""
    return DatabaseManager()

class GuardTypeResponse(BaseModel):
    id: int
    name: str
    description: str
    is_active: bool
    pii_fields: List[dict] = []

class GuardTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class PIIFieldResponse(BaseModel):
    id: int
    guard_type_id: int
    field_name: str
    field_type: str
    is_sensitive: bool
    anonymization_method: str
    regex_pattern: Optional[str] = None
    example_text: Optional[str] = None

class PIIFieldUpdate(BaseModel):
    field_name: Optional[str] = None
    field_type: Optional[str] = None
    is_sensitive: Optional[bool] = None
    anonymization_method: Optional[str] = None
    regex_pattern: Optional[str] = None
    example_text: Optional[str] = None

# Routes pour les Guard Types
@guard_types_router.get("/", response_model=List[GuardTypeResponse])
def get_all_guard_types(db: DatabaseManager = Depends(get_db)):
    """Récupère tous les types de protection"""
    try:
        guard_types = db.get_all_guard_types()
        result = []
        for gt in guard_types:
            pii_fields = db.get_pii_fields_by_guard_type(gt['id'])
            result.append({
                **gt,
                "pii_fields": pii_fields
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des types: {str(e)}")

@guard_types_router.get("/{guard_type_id}", response_model=GuardTypeResponse)
def get_guard_type(guard_type_id: int, db: DatabaseManager = Depends(get_db)):
    """Récupère un type de protection spécifique"""
    try:
        guard_type = db.get_guard_type_by_id(guard_type_id)
        if not guard_type:
            raise HTTPException(status_code=404, detail="Type de protection non trouvé")
        
        pii_fields = db.get_pii_fields_by_guard_type(guard_type_id)
        return {
            **guard_type,
            "pii_fields": pii_fields
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")

@guard_types_router.post("/", response_model=GuardTypeResponse)
def create_guard_type(guard_type_data: GuardTypeCreate, db: DatabaseManager = Depends(get_db)):
    """Crée un nouveau type de protection"""
    try:
        # Vérifier si le nom existe déjà
        existing = db.get_guard_type_by_name(guard_type_data.name)
        if existing:
            raise HTTPException(status_code=400, detail="Un type avec ce nom existe déjà")
        
        guard_type_id = db.create_guard_type(
            name=guard_type_data.name,
            description=guard_type_data.description,
            is_active=guard_type_data.is_active
        )
        
        # Récupérer le type créé avec ses champs
        return get_guard_type(guard_type_id, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création: {str(e)}")

@guard_types_router.put("/{guard_type_id}", response_model=GuardTypeResponse)
def update_guard_type(guard_type_id: int, guard_type_data: GuardTypeUpdate, db: DatabaseManager = Depends(get_db)):
    """Met à jour un type de protection"""
    try:
        # Vérifier que le type existe
        existing = db.get_guard_type_by_id(guard_type_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Type de protection non trouvé")
        
        # Préparer les données à mettre à jour
        update_data = {}
        if guard_type_data.name is not None:
            # Vérifier l'unicité du nom
            name_check = db.get_guard_type_by_name(guard_type_data.name)
            if name_check and name_check['id'] != guard_type_id:
                raise HTTPException(status_code=400, detail="Un type avec ce nom existe déjà")
            update_data['name'] = guard_type_data.name
        
        if guard_type_data.description is not None:
            update_data['description'] = guard_type_data.description
        
        if guard_type_data.is_active is not None:
            update_data['is_active'] = guard_type_data.is_active
        
        if update_data:
            db.update_guard_type(guard_type_id, **update_data)
        
        return get_guard_type(guard_type_id, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour: {str(e)}")

@guard_types_router.delete("/{guard_type_id}")
def delete_guard_type(guard_type_id: int, db: DatabaseManager = Depends(get_db)):
    """Supprime un type de protection"""
    try:
        # Vérifier que le type existe
        existing = db.get_guard_type_by_id(guard_type_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Type de protection non trouvé")
        
        # Supprimer d'abord tous les champs PII associés
        db.delete_pii_fields_by_guard_type(guard_type_id)
        
        # Puis supprimer le type
        db.delete_guard_type(guard_type_id)
        
        return {"message": "Type de protection supprimé avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression: {str(e)}")

# Routes pour les champs PII
@guard_types_router.get("/{guard_type_id}/fields", response_model=List[PIIFieldResponse])
def get_pii_fields(guard_type_id: int, db: DatabaseManager = Depends(get_db)):
    """Récupère tous les champs PII d'un type de protection"""
    try:
        # Vérifier que le type existe
        guard_type = db.get_guard_type_by_id(guard_type_id)
        if not guard_type:
            raise HTTPException(status_code=404, detail="Type de protection non trouvé")
        
        return db.get_pii_fields_by_guard_type(guard_type_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des champs: {str(e)}")

@guard_types_router.post("/{guard_type_id}/fields", response_model=PIIFieldResponse)
def create_pii_field(guard_type_id: int, field_data: PIIFieldCreate, db: DatabaseManager = Depends(get_db)):
    """Ajoute un nouveau champ PII à un type de protection"""
    try:
        # Vérifier que le type existe
        guard_type = db.get_guard_type_by_id(guard_type_id)
        if not guard_type:
            raise HTTPException(status_code=404, detail="Type de protection non trouvé")
        
        field_id = db.create_pii_field(
            guard_type_id=guard_type_id,
            field_name=field_data.field_name,
            field_type=field_data.field_type,
            is_sensitive=field_data.is_sensitive,
            anonymization_method=field_data.anonymization_method,
            regex_pattern=field_data.regex_pattern,
            example_text=field_data.example_text
        )
        
        # Récupérer le champ créé
        field = db.get_pii_field_by_id(field_id)
        return field
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du champ: {str(e)}")

@guard_types_router.put("/{guard_type_id}/fields/{field_id}", response_model=PIIFieldResponse)
def update_pii_field(guard_type_id: int, field_id: int, field_data: PIIFieldUpdate, db: DatabaseManager = Depends(get_db)):
    """Met à jour un champ PII"""
    try:
        # Vérifier que le champ existe et appartient au bon type
        field = db.get_pii_field_by_id(field_id)
        if not field or field['guard_type_id'] != guard_type_id:
            raise HTTPException(status_code=404, detail="Champ PII non trouvé")
        
        # Préparer les données à mettre à jour
        update_data = {}
        for key, value in field_data.dict(exclude_unset=True).items():
            if value is not None:
                update_data[key] = value
        
        if update_data:
            db.update_pii_field(field_id, **update_data)
        
        # Récupérer le champ mis à jour
        return db.get_pii_field_by_id(field_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour du champ: {str(e)}")

@guard_types_router.delete("/{guard_type_id}/fields/{field_id}")
def delete_pii_field(guard_type_id: int, field_id: int, db: DatabaseManager = Depends(get_db)):
    """Supprime un champ PII"""
    try:
        # Vérifier que le champ existe et appartient au bon type
        field = db.get_pii_field_by_id(field_id)
        if not field or field['guard_type_id'] != guard_type_id:
            raise HTTPException(status_code=404, detail="Champ PII non trouvé")
        
        db.delete_pii_field(field_id)
        return {"message": "Champ PII supprimé avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression du champ: {str(e)}")

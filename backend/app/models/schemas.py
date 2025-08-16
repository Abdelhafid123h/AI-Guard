from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class AttributeDetectionType(str, Enum):
    REGEX = "regex"
    NER = "NER"

class AttributeDefinition(BaseModel):
    type: AttributeDetectionType = Field(..., description="Type de détection (regex ou NER)")
    exemple: str = Field(..., description="Exemple de valeur pour cet attribut")
    pattern: Optional[str] = Field(None, description="Pattern regex (si type=regex)")
    description: Optional[str] = Field(None, description="Description de l'attribut")

class GuardTypeAttribute(BaseModel):
    id: Optional[int] = Field(None, description="ID unique de l'attribut")
    guard_type_id: int = Field(..., description="ID du type de protection")
    name: str = Field(..., description="Nom de l'attribut (ex: phone, email)")
    definition: AttributeDefinition = Field(..., description="Définition de l'attribut")

class CreateAttributeRequest(BaseModel):
    name: str = Field(..., description="Nom de l'attribut")
    definition: AttributeDefinition = Field(..., description="Définition de l'attribut")

class GuardType(BaseModel):
    id: Optional[int] = Field(None, description="ID unique du type de garde")
    name: str = Field(..., description="Nom du type de garde")
    description: Optional[str] = Field(None, description="Description du type de garde")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Configuration du type de garde")
    is_active: bool = Field(True, description="Statut actif/inactif")
    attributes: List[GuardTypeAttribute] = Field(default_factory=list, description="Liste des attributs du type")

class CreateGuardTypeRequest(BaseModel):
    name: str = Field(..., description="Nom du nouveau type de protection")
    description: Optional[str] = Field(None, description="Description du type")
    attributes: List[CreateAttributeRequest] = Field(default_factory=list, description="Attributs initiaux")

class PIIField(BaseModel):
    id: Optional[int] = Field(None, description="ID unique du champ PII")
    name: str = Field(..., description="Nom du champ PII")
    pattern: Optional[str] = Field(None, description="Pattern regex pour détecter ce champ")
    guard_type_id: int = Field(..., description="ID du type de garde associé")
    replacement_template: Optional[str] = Field("[MASKED]", description="Template de remplacement")
    is_active: bool = Field(True, description="Statut actif/inactif")

class GuardRequest(BaseModel):
    text: str = Field(..., description="Texte contenant des données sensibles")
    guard_type: str = Field("TypeA", description="Type de protection (TypeA, TypeB, InfoPerso)")
    llm_provider: Optional[str] = Field("openai", description="Fournisseur LLM (openai, gemini, etc.)")

class GuardResponse(BaseModel):
    original: str = Field(..., description="Texte original")
    masked: str = Field(..., description="Réponse brute du LLM")
    llm_response: str = Field(..., description="Réponse brute du LLM")
    unmasked: str = Field(..., description="Réponse finale avec données restaurées")
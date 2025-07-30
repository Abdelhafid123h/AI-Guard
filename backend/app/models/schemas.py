from pydantic import BaseModel, Field
from typing import Optional

class GuardRequest(BaseModel):
    text: str = Field(..., description="Texte contenant des données sensibles")
    guard_type: str = Field("TypeA", description="Type de protection (TypeA, TypeB, InfoPerso)")
    llm_provider: Optional[str] = Field("openai", description="Fournisseur LLM (openai, gemini, etc.)")

class GuardResponse(BaseModel):
    original: str = Field(..., description="Texte original")
    masked: str = Field(..., description="Texte avec données masquées")
    llm_response: str = Field(..., description="Réponse brute du LLM")
    unmasked: str = Field(..., description="Réponse finale avec données restaurées")
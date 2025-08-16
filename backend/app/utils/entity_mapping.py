"""Centralised entity mapping & canonicalisation utilities.

This module provides a single source of truth for accepted (canonical)
PII entity labels used across the API (creation/validation) and the
runtime detection layer (Presidio + fallback models).

Rationale:
- Avoid duplicating mapping dictionaries (previously hard‑coded inside
  detector + would have to be replicated in API validation).
- Provide a light canonicalisation helper so the frontend / legacy
  scripts can send flexible synonyms (EMAIL, mail, Email_Address, ...)
  while we store & operate only on canonical Presidio-aligned labels.
"""
from typing import Dict, Set, Tuple

# Canonical labels (aligned with Presidio where applicable) – keep UPPERCASE.
CANONICAL_ENTITIES: Set[str] = {
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "US_SSN",
    "DATE_TIME",
    "PERSON",
    "LOCATION",
    "ORGANIZATION",
    "IP_ADDRESS",
    "IBAN",
    "URL",
}

# Synonym → canonical (ALWAYS UPPERCASE KEYS)
_SYNONYM_MAPPING: Dict[str, str] = {
    # Email
    "EMAIL": "EMAIL_ADDRESS",
    "MAIL": "EMAIL_ADDRESS",
    "COURRIEL": "EMAIL_ADDRESS",
    "E_MAIL": "EMAIL_ADDRESS",
    "E_MAIL_ADDRESS": "EMAIL_ADDRESS",
    # Phone
    "PHONE": "PHONE_NUMBER",
    "TELEPHONE": "PHONE_NUMBER",
    "MOBILE": "PHONE_NUMBER",
    "TÉLÉPHONE": "PHONE_NUMBER",
    "NUMERO_TELEPHONE": "PHONE_NUMBER",
    "NUMÉRO_TÉLÉPHONE": "PHONE_NUMBER",
    # Credit card
    "CREDIT_CARD_NUMBER": "CREDIT_CARD",
    "CARD_NUMBER": "CREDIT_CARD",
    "CB": "CREDIT_CARD",
    "NUMERO_CARTE": "CREDIT_CARD",
    "NUMÉRO_CARTE": "CREDIT_CARD",
    "CARTE_BANCAIRE": "CREDIT_CARD",
    # SSN
    "SOCIAL_SECURITY_NUMBER": "US_SSN",
    "SOCIAL_SECURITY": "US_SSN",
    "SSN": "US_SSN",
    "SECURITE_SOCIALE": "US_SSN",
    "NUMERO_SECURITE_SOCIALE": "US_SSN",
    "NUMÉRO_SÉCURITÉ_SOCIALE": "US_SSN",
    # Date
    "DATE_OF_BIRTH": "DATE_TIME",
    "BIRTH_DATE": "DATE_TIME",
    "DOB": "DATE_TIME",
    "DATE": "DATE_TIME",
    # Person
    "PERSON_NAME": "PERSON",
    "FULL_NAME": "PERSON",
    "NAME": "PERSON",
    # spaCy short code
    "PER": "PERSON",
    "PERSONNE": "PERSON",
    "NOM": "PERSON",
    "PRENOM": "PERSON",
    "PRÉNOM": "PERSON",
    # Location / address
    "ADDRESS": "LOCATION",
    "PLACE": "LOCATION",
    "LOC": "LOCATION",
    "GPE": "LOCATION",  # spaCy geopolitical entity
    "ADRESSE": "LOCATION",
    "ADRESSE_POSTALE": "LOCATION",
    "LOCALISATION": "LOCATION",
    "VILLE": "LOCATION",
    "CODE_POSTAL": "LOCATION",
    # Organization
    "ORG": "ORGANIZATION",
    "COMPANY": "ORGANIZATION",
    "ENTREPRISE": "ORGANIZATION",
    "SOCIETE": "ORGANIZATION",
    "SOCIÉTÉ": "ORGANIZATION",
    # Bank / finance
    "BANK_ACCOUNT": "IBAN",
    "IBAN_CODE": "IBAN",
    # URL / web
    "WEBSITE": "URL",
    "LINK": "URL",
    "SITE": "URL",
    "SITE_WEB": "URL",
    "LIEN": "URL",
    # IP
    "IP": "IP_ADDRESS",
    "ADRESSE_IP": "IP_ADDRESS",
}

# Combine canonical self-maps so lookups are always possible.
ENTITY_MAPPING: Dict[str, str] = {
    **{c: c for c in CANONICAL_ENTITIES},
    **_SYNONYM_MAPPING,
}

def canonicalize_entity(label: str) -> Tuple[str, bool]:
    """Return (canonical_label, is_valid).

    The function is permissive with casing & underscores; it strips
    surrounding whitespace and uppercases before lookup.
    """
    if not label:
        return "", False
    key = label.strip().upper()
    # Normalise some accidental variants like EMAIL-ADDRESS, emailAddress
    key = key.replace("-", "_")
    return ENTITY_MAPPING.get(key, key), (key in ENTITY_MAPPING)

def list_supported_entities(include_synonyms: bool = False):
    """List supported canonical entities; optionally include synonyms."""
    if include_synonyms:
        return {
            "canonical": sorted(CANONICAL_ENTITIES),
            "synonyms": sorted(k for k, v in ENTITY_MAPPING.items() if v != k),
        }
    return sorted(CANONICAL_ENTITIES)

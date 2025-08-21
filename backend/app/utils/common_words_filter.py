"""
Filtre pour éliminer les faux positifs des modèles NLP.
"""

# Mots français communs qui ne sont jamais des entités sensibles
COMMON_FRENCH_WORDS = {
    # Salutations et expressions courantes
    "salut", "bonjour", "bonsoir", "au revoir", "à bientôt",
    
    # Pronoms et articles
    "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
    "le", "la", "les", "un", "une", "des", "du", "de", "d'",
    "ce", "cette", "ces", "mon", "ma", "mes", "ton", "ta", "tes",
    "son", "sa", "ses", "notre", "nos", "votre", "vos", "leur", "leurs",
    
    # Verbes auxiliaires et fréquents
    "être", "avoir", "faire", "dire", "aller", "voir", "savoir",
    "pouvoir", "falloir", "vouloir", "venir", "prendre", "donner",
    "est", "sont", "ai", "as", "a", "avons", "avez", "ont",
    "suis", "es", "sommes", "êtes",
    
    # Conjonctions et prépositions
    "et", "ou", "mais", "donc", "or", "ni", "car",
    "dans", "sur", "avec", "sans", "pour", "par", "contre",
    "sous", "vers", "chez", "depuis", "pendant", "avant", "après",
    
    # Expressions courantes
    "c'est", "ce sont", "il y a", "voilà", "voici",
    "oui", "non", "peut-être", "bien", "mal", "très", "plus", "moins",
    
    # Mots temporels
    "hier", "aujourd'hui", "demain", "maintenant", "toujours", "jamais",
    "souvent", "parfois", "quelquefois", "encore", "déjà",
    
    # Nombres en lettres (petits nombres)
    "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix"
}

# Patterns suspects qui ne devraient jamais être des adresses/entreprises
SUSPICIOUS_PATTERNS = {
    "address": [
        r"^(salut|bonjour|bonsoir|hello|hi)$",
        r"^(oui|non|peut-être|ok|d'accord)$",
        r"^(merci|s'il vous plaît|excusez-moi)$"
    ],
    "company": [
        r"^(c'est|ce sont|il y a|voilà|voici)$",
        r"^(je|tu|il|elle|nous|vous|ils|elles)$",
        r"^(le|la|les|un|une|des|du|de)$"
    ],
    "name": [
        r"^(le|la|les|un|une|des)$",
        r"^(et|ou|mais|donc|car)$"
    ]
}

import re

def is_common_word(text: str) -> bool:
    """Vérifie si le texte est un mot commun français."""
    return text.lower().strip() in COMMON_FRENCH_WORDS

def is_suspicious_entity(text: str, entity_type: str) -> bool:
    """Vérifie si l'entité détectée est suspecte selon son type."""
    if entity_type not in SUSPICIOUS_PATTERNS:
        return False
    
    text_clean = text.lower().strip()
    
    for pattern in SUSPICIOUS_PATTERNS[entity_type]:
        if re.match(pattern, text_clean, re.IGNORECASE):
            return True
    
    return False

def filter_false_positives(entities: list) -> list:
    """Filtre les faux positifs d'une liste d'entités."""
    filtered = []
    
    for entity in entities:
        text = entity.get('text', '').strip()
        entity_type = entity.get('type', '')
        
        # Ignorer les entités vides ou trop courtes
        if len(text) < 2:
            continue
            
        # Ignorer les mots communs (sauf si c'est un nom propre plausible)
        if is_common_word(text):
            # Autoriser prénoms très courts capitalisés (ex: "Lu")
            if entity_type in {"name", "person", "PERSON"} and text[:1].isupper() and len(text) >= 2:
                pass
            else:
                print(f"🚫 Filtré mot commun: '{text}' ({entity_type})")
                continue
            
        # Ignorer les patterns suspects
        if is_suspicious_entity(text, entity_type):
            print(f"🚫 Filtré pattern suspect: '{text}' ({entity_type})")
            continue
            
        # Garder l'entité
        filtered.append(entity)
    
    return filtered

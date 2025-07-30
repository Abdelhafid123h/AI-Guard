import re
from typing import List, Dict
from app.utils.regex_patterns import PII_PATTERNS
from app.utils.nlp_utils import NLPModels

class PIIDetector:
    def __init__(self):
        self.models = NLPModels()
        self.spacy_model = self.models.spacy_model
        self.bert_model = self.models.bert_model
    
    def detect(self, text: str) -> List[Dict]:
     """Combine regex, BERT et spaCy pour détecter les entités sensibles."""
     entities = []
    
    # Détection par regex
     entities.extend(self._detect_with_regex(text))
    
    # Détection par BERT
     entities.extend(self._detect_with_bert(text))
    
    # Détection par spaCy
     entities.extend(self._detect_with_spacy(text))
    
    # Valider les entités détectées
     validated_entities = []
     for entity in entities:
        if 'text' in entity and 'type' in entity:  # Vérifiez que les clés existent
            validated_entities.append(entity)
        else:
            print(f"Entité mal formée détectée : {entity}")  # Log pour débogage
    
    # Fusionner les résultats sans doublons
     return self._merge_entities(validated_entities)
    



    
    def _detect_with_regex(self, text: str) -> List[Dict]:
        entities = []
        for pii_type, pattern in PII_PATTERNS.items():
            for match in re.finditer(pattern.regex, text):
                entities.append({
                    "text": match.group(),
                    "type": pii_type,  # Vérifiez que 'type' est défini
                    "start": match.start(),
                    "end": match.end(),
                    "source": "regex"
                })
        return entities

    def _detect_with_bert(self, text: str) -> List[Dict]:
     results = self.bert_model(text)
     print(f"Résultats bruts de BERT : {results}")  # Log pour débogage
     entities = []
     for res in results:
        # Vérifiez que les clés nécessaires existent
        if 'word' in res and 'entity_group' in res and 'start' in res and 'end' in res:
            # Filtrer les entités pertinentes et transformer la structure
            entity_type = res['entity_group']
            if entity_type in ['PER', 'LOC', 'ORG']:  # Filtrer les types pertinents
                entities.append({
                    "text": res['word'],
                    "type": self._map_entity_type(entity_type),  # Mapper les types
                    "start": res['start'],
                    "end": res['end'],
                    "source": "bert"
                })
        else:
            print(f"Résultat mal formé détecté par BERT : {res}")  # Log pour débogage
     return entities

    def _map_entity_type(self, entity_group: str) -> str:
     """Mappe les types d'entités BERT vers les types attendus par l'application."""
     mapping = {
        "PER": "name",
        "LOC": "address", 
        "ORG": "company",
        "MISC": "unknown"
     }
     return mapping.get(entity_group, "unknown")
    



    def _detect_with_spacy(self, text: str) -> List[Dict]:
     """Détecte les entités sensibles avec spaCy."""
     doc = self.spacy_model(text)
     entities = []
     for ent in doc.ents:
        # Mapper les types d'entités spaCy vers les types attendus
        entity_type = self._map_entity_type_spacy(ent.label_)
        if entity_type != "unknown":  # Ignorer les types non pertinents
            entities.append({
                "text": ent.text,
                "type": entity_type,
                "start": ent.start_char,
                "end": ent.end_char,
                "source": "spacy"
            })
     return entities

    def _map_entity_type_spacy(self, spacy_label: str) -> str:
     """Mappe les types d'entités spaCy vers les types attendus par l'application."""
     mapping = {
        "PER": "name",        # Personne
        "LOC": "address",     # Lieu
        "ORG": "company",     # Organisation (company au lieu de organization)
        "MISC": "unknown"     # Divers
    }
     return mapping.get(spacy_label, "unknown")
    


    
    
    
    def _merge_entities(self, entities: List[Dict]) -> List[Dict]:
     """Fusionne les entités qui se chevauchent"""
     if not entities:
        return []
            
     entities.sort(key=lambda x: x['start'])
     merged = [entities[0]]
    
     for entity in entities[1:]:
        last = merged[-1]
        if entity['start'] <= last['end']:
            # Fusionner les entités qui se chevauchent
            if entity['end'] > last['end']:
                last['end'] = entity['end']
                last['text'] = last['text'] + entity['text'][len(last['text']):]
            last['source'] = "combined"
        else:
            merged.append(entity)
    
    # Supprimer les doublons exacts
     unique_entities = []
     seen = set()
     for entity in merged:
        key = (entity['text'], entity['type'], entity['start'], entity['end'])
        if key not in seen:
            unique_entities.append(entity)
            seen.add(key)
    
     return unique_entities
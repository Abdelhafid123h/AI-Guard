import re
from typing import List, Dict
from app.utils.regex_patterns import PII_PATTERNS
from app.utils.nlp_utils import NLPModels

# Nouveau : Ajout de Presidio pour une détection PII spécialisée
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    print("Presidio non installé. Utilisation de BERT et spaCy uniquement.")

class PIIDetector:
    def __init__(self):
        self.models = NLPModels()
        self.spacy_model = self.models.spacy_model
        self.bert_model = self.models.bert_model
        
        # Initialisation de Presidio si disponible
        if PRESIDIO_AVAILABLE:
            try:
                # Configuration pour le français
                configuration = {
                    "nlp_engine_name": "spacy",
                    "models": [{"lang_code": "fr", "model_name": "fr_core_news_sm"}]
                }
                
                provider = NlpEngineProvider(nlp_configuration=configuration)
                nlp_engine = provider.create_engine()
                
                self.presidio_analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
                print("✅ Presidio initialisé avec succès")
            except Exception as e:
                print(f"⚠️ Erreur initialisation Presidio : {e}")
                self.presidio_analyzer = None
        else:
            self.presidio_analyzer = None
    
    def detect(self, text: str) -> List[Dict]:
        """Combine regex, BERT, spaCy et Presidio pour détecter les entités sensibles."""
        entities = []
        
        # Détection par regex
        entities.extend(self._detect_with_regex(text))
        
        # Détection par BERT
        entities.extend(self._detect_with_bert(text))
        
        # Détection par spaCy
        entities.extend(self._detect_with_spacy(text))
        
        # Détection par Presidio (si disponible)
        if self.presidio_analyzer:
            entities.extend(self._detect_with_presidio(text))
        
        # Valider les entités détectées
        validated_entities = []
        for entity in entities:
            if 'text' in entity and 'type' in entity:
                validated_entities.append(entity)
            else:
                print(f"Entité mal formée détectée : {entity}")
        
        # Fusionner les résultats sans doublons
        return self._merge_entities(validated_entities)

    def _detect_with_presidio(self, text: str) -> List[Dict]:
        """Détecte les entités PII avec Microsoft Presidio."""
        if not self.presidio_analyzer:
            return []
            
        try:
            # Analyse avec Presidio
            results = self.presidio_analyzer.analyze(text=text, language="fr")
            
            entities = []
            for result in results:
                # Extraction du texte de l'entité
                entity_text = text[result.start:result.end]
                
                # Mapping des types Presidio vers nos types
                entity_type = self._map_presidio_type(result.entity_type)
                
                if entity_type != "unknown":
                    entities.append({
                        "text": entity_text,
                        "type": entity_type,
                        "start": result.start,
                        "end": result.end,
                        "source": "presidio",
                        "confidence": result.score
                    })
            
            print(f"Presidio détecté {len(entities)} entités")
            return entities
            
        except Exception as e:
            print(f"Erreur Presidio : {e}")
            return []

    def _map_presidio_type(self, presidio_type: str) -> str:
        """Mappe les types Presidio vers nos types d'application."""
        mapping = {
            # Presidio -> Notre système
            "PERSON": "name",
            "EMAIL_ADDRESS": "email",
            "PHONE_NUMBER": "phone",
            "CREDIT_CARD": "credit_card",
            "IBAN_CODE": "iban",
            "DATE_TIME": "birth_date",
            "LOCATION": "address",
            "IP_ADDRESS": "ip_address",
            "SSN": "social_security",
            "MEDICAL_LICENSE": "id_card",
            "PASSPORT": "passport",
            "DRIVER_ID": "driving_license",
            "ORGANIZATION": "company"
        }
        return mapping.get(presidio_type, "unknown")

    def _detect_with_regex(self, text: str) -> List[Dict]:
        entities = []
        for pii_type, pattern in PII_PATTERNS.items():
            for match in re.finditer(pattern.regex, text):
                entities.append({
                    "text": match.group(),
                    "type": pii_type,
                    "start": match.start(),
                    "end": match.end(),
                    "source": "regex"
                })
        return entities

    def _detect_with_bert(self, text: str) -> List[Dict]:
        results = self.bert_model(text)
        print(f"Résultats bruts de BERT : {results}")
        entities = []
        for res in results:
            if 'word' in res and 'entity_group' in res and 'start' in res and 'end' in res:
                entity_type = res['entity_group']
                if entity_type in ['PER', 'LOC', 'ORG']:
                    entities.append({
                        "text": res['word'],
                        "type": self._map_entity_type(entity_type),
                        "start": res['start'],
                        "end": res['end'],
                        "source": "bert"
                    })
            else:
                print(f"Résultat mal formé détecté par BERT : {res}")
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
            entity_type = self._map_entity_type_spacy(ent.label_)
            if entity_type != "unknown":
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
            "PER": "name",
            "LOC": "address",
            "ORG": "company",
            "MISC": "unknown"
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

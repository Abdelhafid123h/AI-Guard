import re
from typing import List, Dict
from app.utils.regex_patterns import PII_PATTERNS
from app.utils.nlp_utils_enhanced import NLPModels
from app.utils.common_words_filter import filter_false_positives

# Nouveau : Ajout de Presidio pour une détection PII spécialisée
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    print("Presidio non installé. Utilisation des modèles français uniquement.")

class PIIDetectorFrench:
    def __init__(self):
        self.models = NLPModels()
        print(f"📋 Modèles disponibles : {', '.join(self.models.get_available_models())}")
        
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
                print("✅ Presidio configuré pour le français")
            except Exception as e:
                print(f"⚠️ Erreur initialisation Presidio : {e}")
                self.presidio_analyzer = None
        else:
            self.presidio_analyzer = None
    
    def detect(self, text: str) -> List[Dict]:
        """Combine tous les modèles français pour détecter les entités sensibles."""
        entities = []
        
        print(f"🔍 DÉBUT DÉTECTION pour: '{text[:100]}...'")
        
        # 1. Détection par regex
        regex_entities = self._detect_with_regex(text)
        entities.extend(regex_entities)
        print(f"📝 REGEX détecté {len(regex_entities)} entités: {[e['text'] for e in regex_entities]}")
        
        # 2. Détection par CamemBERT (spécialisé français)
        if self.models.camembert_model:
            camembert_entities = self._detect_with_camembert(text)
            entities.extend(camembert_entities)
            print(f"🇫🇷 CAMEMBERT détecté {len(camembert_entities)} entités: {[e['text'] for e in camembert_entities]}")
        
        # 3. Détection par modèle français alternatif
        if hasattr(self.models, 'french_model') and self.models.french_model:
            french_entities = self._detect_with_french_model(text)
            entities.extend(french_entities)
            print(f"🏴󠁧󠁢󠁥󠁮󠁧󠁿 FRENCH_MODEL détecté {len(french_entities)} entités: {[e['text'] for e in french_entities]}")
        
        # 4. Détection par BERT multilingue (fallback)
        if self.models.bert_model:
            bert_entities = self._detect_with_bert(text)
            entities.extend(bert_entities)
            print(f"🤖 BERT détecté {len(bert_entities)} entités: {[e['text'] for e in bert_entities]}")
        
        # 5. Détection par spaCy
        if self.models.spacy_model:
            spacy_entities = self._detect_with_spacy(text)
            entities.extend(spacy_entities)
            print(f"🎯 SPACY détecté {len(spacy_entities)} entités: {[e['text'] for e in spacy_entities]}")
        
        # 6. Détection par Presidio (si disponible)
        if self.presidio_analyzer:
            presidio_entities = self._detect_with_presidio(text)
            entities.extend(presidio_entities)
            print(f"🛡️ PRESIDIO détecté {len(presidio_entities)} entités: {[e['text'] for e in presidio_entities]}")
        
        print(f"📊 TOTAL AVANT VALIDATION: {len(entities)} entités")
        
        # Validation et fusion
        validated_entities = self._validate_entities(entities)
        print(f"✅ APRÈS VALIDATION: {len(validated_entities)} entités")

        # NOUVEAU : Filtrage des faux positifs
        filtered_entities = filter_false_positives(validated_entities)
        print(f"🚫 APRÈS FILTRAGE: {len(filtered_entities)} entités")
        
        final_entities = self._merge_entities(filtered_entities)
        print(f"🎯 FINAL APRÈS FUSION: {len(final_entities)} entités: {[(e['text'], e['type']) for e in final_entities]}")
        
        return final_entities

    def _detect_with_camembert(self, text: str) -> List[Dict]:
        """Détecte les entités avec CamemBERT français."""
        try:
            results = self.models.camembert_model(text)
            print(f"CamemBERT détecté : {len(results)} entités")
            
            entities = []
            for res in results:
                if 'word' in res and 'entity_group' in res and 'start' in res and 'end' in res:
                    entity_type = self._map_camembert_type(res['entity_group'])
                    if entity_type != "unknown":
                        entities.append({
                            "text": res['word'],
                            "type": entity_type,
                            "start": res['start'],
                            "end": res['end'],
                            "source": "camembert",
                            "confidence": res.get('score', 0.0)
                        })
            return entities
        except Exception as e:
            print(f"Erreur CamemBERT : {e}")
            return []

    def _detect_with_french_model(self, text: str) -> List[Dict]:
        """Détecte les entités avec le modèle français alternatif."""
        try:
            results = self.models.french_model(text)
            print(f"Modèle français alternatif détecté : {len(results)} entités")
            
            entities = []
            for res in results:
                if 'word' in res and 'entity_group' in res and 'start' in res and 'end' in res:
                    entity_type = self._map_french_type(res['entity_group'])
                    if entity_type != "unknown":
                        entities.append({
                            "text": res['word'],
                            "type": entity_type,
                            "start": res['start'],
                            "end": res['end'],
                            "source": "french_model",
                            "confidence": res.get('score', 0.0)
                        })
            return entities
        except Exception as e:
            print(f"Erreur modèle français : {e}")
            return []

    def _map_camembert_type(self, entity_group: str) -> str:
        """Mappe les types CamemBERT vers nos types d'application."""
        mapping = {
            "PER": "name",        # Personne
            "PERS": "name",       # Variante personne
            "LOC": "address",     # Lieu
            "ORG": "company",     # Organisation
            "MISC": "unknown"     # Divers
        }
        return mapping.get(entity_group, "unknown")

    def _map_french_type(self, entity_group: str) -> str:
        """Mappe les types du modèle français vers nos types d'application."""
        mapping = {
            "PER": "name",
            "LOC": "address",
            "ORG": "company",
            "MISC": "unknown"
        }
        return mapping.get(entity_group, "unknown")

    def _detect_with_presidio(self, text: str) -> List[Dict]:
        """Détecte les entités PII avec Microsoft Presidio."""
        if not self.presidio_analyzer:
            return []
            
        try:
            # Analyse avec Presidio en français
            results = self.presidio_analyzer.analyze(text=text, language="fr")
            
            entities = []
            for result in results:
                entity_text = text[result.start:result.end]
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
            "PERSON": "name",
            "EMAIL_ADDRESS": "email",
            "PHONE_NUMBER": "phone",
            "CREDIT_CARD": "credit_card",
            "IBAN_CODE": "iban",
            "DATE_TIME": "birth_date",
            "LOCATION": "address",
            "IP_ADDRESS": "ip_address",
            "SSN": "social_security",
            "PASSPORT": "passport",
            "ORGANIZATION": "company"
        }
        return mapping.get(presidio_type, "unknown")

    def _detect_with_regex(self, text: str) -> List[Dict]:
        """Détection par patterns regex."""
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
        """Détection avec BERT multilingue (fallback)."""
        try:
            results = self.models.bert_model(text)
            entities = []
            for res in results:
                if 'word' in res and 'entity_group' in res and 'start' in res and 'end' in res:
                    entity_type = res['entity_group']
                    if entity_type in ['PER', 'LOC', 'ORG', 'MISC']:
                        mapped_type = self._map_bert_type(entity_type)
                        entities.append({
                            "text": res['word'],
                            "type": mapped_type,
                            "start": res['start'],
                            "end": res['end'],
                            "source": "bert"
                        })
            return entities
        except Exception as e:
            print(f"Erreur BERT : {e}")
            return []

    def _map_bert_type(self, entity_group: str) -> str:
        """Mappe les types BERT."""
        mapping = {
            "PER": "name",     # Personne → nom
            "PERSON": "name",  # Alternative
            "LOC": "address",  # Lieu → adresse
            "ORG": "company",  # Organisation → entreprise
            "MISC": "name"     # Divers → nom (au cas où)
        }
        mapped = mapping.get(entity_group, "unknown")
        print(f"🔄 Mapping BERT: '{entity_group}' → '{mapped}'")
        return mapped

    def _detect_with_spacy(self, text: str) -> List[Dict]:
        """Détection avec spaCy français."""
        try:
            doc = self.models.spacy_model(text)
            entities = []
            for ent in doc.ents:
                entity_type = self._map_spacy_type(ent.label_)
                if entity_type != "unknown":
                    entities.append({
                        "text": ent.text,
                        "type": entity_type,
                        "start": ent.start_char,
                        "end": ent.end_char,
                        "source": "spacy"
                    })
            return entities
        except Exception as e:
            print(f"Erreur spaCy : {e}")
            return []

    def _map_spacy_type(self, spacy_label: str) -> str:
        """Mappe les types spaCy."""
        mapping = {
            "PER": "name",
            "LOC": "address",
            "ORG": "company"
        }
        return mapping.get(spacy_label, "unknown")

    def _validate_entities(self, entities: List[Dict]) -> List[Dict]:
        """Valide les entités détectées."""
        validated = []
        for entity in entities:
            if 'text' in entity and 'type' in entity and entity['text'].strip():
                validated.append(entity)
            else:
                print(f"Entité mal formée : {entity}")
        return validated

    def _merge_entities(self, entities: List[Dict]) -> List[Dict]:
        """Fusionne les entités qui se chevauchent avec une logique améliorée pour les noms composés."""
        if not entities:
            return []
                
        # Trier par position
        entities.sort(key=lambda x: (x['start'], -x['end']))
        merged = []
        
        for entity in entities:
            # Vérifier les chevauchements et proximités
            overlap = False
            for i, merged_entity in enumerate(merged):
                # Chevauchement classique
                if (entity['start'] < merged_entity['end'] and 
                    entity['end'] > merged_entity['start']):
                    # Garder l'entité avec le meilleur score ou la plus longue
                    if (entity.get('confidence', 0) > merged_entity.get('confidence', 0) or
                        (entity['end'] - entity['start']) > (merged_entity['end'] - merged_entity['start'])):
                        merged[i] = entity
                    overlap = True
                    break
                    
                # NOUVEAU: Fusion des noms adjacents (ex: "Marie-Claire" + "Dubois")
                elif (entity['type'] in ['name', 'full_name', 'firstname'] and 
                      merged_entity['type'] in ['name', 'full_name', 'firstname']):
                    # Si les entités sont proches (moins de 5 caractères d'écart)
                    gap = entity['start'] - merged_entity['end']
                    if 0 <= gap <= 5:
                        # Fusionner en une seule entité
                        full_text = merged_entity['text'] + ' ' + entity['text']
                        merged[i] = {
                            'text': full_text,
                            'type': 'name',  # Normaliser vers 'name'
                            'start': merged_entity['start'],
                            'end': entity['end'],
                            'source': 'merged_names',
                            'confidence': max(entity.get('confidence', 0), merged_entity.get('confidence', 0))
                        }
                        overlap = True
                        print(f"🔗 Fusion de noms : '{merged_entity['text']}' + '{entity['text']}' = '{full_text}'")
                        break
            
            if not overlap:
                merged.append(entity)
        
        # Supprimer les doublons exacts
        unique_entities = []
        seen = set()
        for entity in merged:
            key = (entity['text'].lower(), entity['type'], entity['start'], entity['end'])
            if key not in seen:
                unique_entities.append(entity)
                seen.add(key)
        
        print(f"🎯 Fusion terminée : {len(unique_entities)} entités finales")
        return unique_entities

import re
import logging
import os
from typing import List, Dict
from app.utils.regex_patterns import PII_PATTERNS
from app.utils.nlp_utils_enhanced import NLPModels
from app.utils.common_words_filter import filter_false_positives
from app.utils.dynamic_config_loader import dynamic_config_loader

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
        # Initialisation des modèles internes
        self.models = NLPModels()
        self.config_loader = dynamic_config_loader  # Configuration dynamique
        self.presidio_init_error = None

        # Mapping centralisé (synonymes -> canoniques)
        from app.utils.entity_mapping import ENTITY_MAPPING
        self.entity_mapping = ENTITY_MAPPING

        print(f"📋 Modèles disponibles : {', '.join(self.models.get_available_models())}")
        print("🔧 Configuration dynamique activée")
        print(f"🔄 Mapping d'entités configuré: {len(self.entity_mapping)} entrées (canoniques + synonymes)")

        # Initialisation de Presidio (multi-lang si possible)
        self.presidio_analyzer = None
        if PRESIDIO_AVAILABLE:
            self._init_presidio()
        else:
            print("ℹ️ Presidio non disponible (package non installé).")

    def _init_presidio(self):
        """Initialise Presidio avec fr + fallback en si disponible."""
        try:
            # Essayer de charger les modèles spaCy nécessaires
            import spacy
            available_models = []
            # Langues souhaitées via variable d'environnement (ex: PII_PRESIDIO_LANGS=fr ou fr,en)
            langs_env = os.getenv("PII_PRESIDIO_LANGS", "fr,en")
            wanted_langs = [l.strip() for l in langs_env.split(',') if l.strip()]
            # Mapping code -> modèle spaCy
            model_map = {"fr": "fr_core_news_sm", "en": "en_core_web_sm"}
            for code in wanted_langs:
                model_name = model_map.get(code)
                if not model_name:
                    continue
                try:
                    spacy.load(model_name)
                    available_models.append({"lang_code": code, "model_name": model_name})
                except Exception:
                    # Tentative de téléchargement automatique (utile en dev / container frais)
                    try:
                        from spacy.cli import download as spacy_download
                        print(f"⬇️ Téléchargement modèle spaCy manquant: {model_name}")
                        spacy_download(model_name)
                        spacy.load(model_name)
                        available_models.append({"lang_code": code, "model_name": model_name})
                    except Exception:
                        print(f"⚠️ Modèle spaCy {model_name} indisponible (lang {code}), ignoré.")
            if not available_models:
                raise RuntimeError("Aucun modèle spaCy fr/en disponible pour Presidio")
            configuration = {"nlp_engine_name": "spacy", "models": available_models}
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()
            self.presidio_analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
            supported = []
            try:
                supported = self.presidio_analyzer.get_supported_entities()
            except Exception:
                pass
            print(f"✅ Presidio initialisé. Langues: {[m['lang_code'] for m in available_models]} | Entités supportées: {supported}")
        except Exception as e:
            self.presidio_init_error = str(e)
            self.presidio_analyzer = None
            print(f"⚠️ Échec initialisation Presidio: {e}")
    
    def detect(self, text: str, guard_type: str = None) -> List[Dict]:
        """Détection intelligente : privilégie les patterns regex personnalisés."""
        entities = []
        regex_covered_text = set()
        logging.info(f"🔍 DÉBUT DÉTECTION pour: '{text[:100]}...' (guard_type: {guard_type})")

        # 1. Regex DB
        regex_entities = self._detect_with_regex(text, guard_type)
        entities.extend(regex_entities)
        regex_covered_text.update(e['text'] for e in regex_entities)

        # 2. NER configuré
        ner_entities = self._detect_with_ner_for_configured_fields(text, regex_covered_text, guard_type)
        entities.extend(ner_entities)

        # 3. Fallback models
        fallback_added = self._augment_with_fallback_models(text, ner_entities, guard_type)
        if fallback_added:
            entities.extend(fallback_added)

        # 3bis. Heuristique supplémentaire pour noms simples non capitalisés ("je m'appelle josh")
        try:
            heuristic_new = self._heuristic_name_entities(text, guard_type, existing=entities)
            if heuristic_new:
                entities.extend(heuristic_new)
        except Exception as e:
            logging.debug(f"Heuristique nom erreur: {e}")

        # Validation
        validated = self._validate_entities(entities)
        filtered = filter_false_positives(validated)

        regex_part = [e for e in filtered if e.get('source') == 'regex_db']
        other_part = [e for e in filtered if e.get('source') != 'regex_db']
        merged_other = self._merge_entities(other_part)
        final_entities = regex_part + merged_other
        # Unification (optionnelle via env PII_UNIFY_DOCS=0 pour désactiver)
        if os.getenv('PII_UNIFY_DOCS', '1') != '0':
            final_entities = self._unify_equivalent_types(final_entities)
        # Post-traitement incohérences & filtrages contextuels
        final_entities = self._post_process_incoherences(final_entities, text)
        return final_entities

    def _augment_with_fallback_models(self, text: str, existing_ner: List[Dict], guard_type: str = None) -> List[Dict]:
        """Ajoute des entités NER issues des modèles internes (Camembert / BERT) UNIQUEMENT
        si elles correspondent à des champs configurés en NER non encore détectés par Presidio.
        """
        try:
            # Champs NER configurés
            if guard_type:
                guard_types = [{'name': guard_type}]
            else:
                guard_types = self.config_loader.db.get_guard_types()
            configured = {}
            for gt in guard_types:
                for f in self.config_loader.db.get_pii_fields(gt['name']):
                    if f['detection_type'] == 'ner' and f['ner_entity_type']:
                        configured[f['ner_entity_type'].upper()] = f

            if not configured:
                return []

            already_texts = {(e['text'], e['type']) for e in existing_ner}

            additions = []

            # Utiliser Camembert
            try:
                cam_results = self._detect_with_camembert(text)
            except Exception:
                cam_results = []
            # Utiliser BERT
            try:
                bert_results = self._detect_with_bert(text)
            except Exception:
                bert_results = []

            combined = cam_results + bert_results
            if not combined:
                return []

            # Mapping simplifié: on mappe les types application (name, company, address...) vers entités configurées sémantiquement proches
            semantic_map = {
                'name': 'PERSON', 'company': 'ORGANIZATION', 'address': 'LOCATION', 'birth_date': 'DATE_TIME'
            }

            for res in combined:
                app_type = res.get('type')
                canonical = semantic_map.get(app_type)
                if not canonical:
                    continue
                if canonical not in configured:
                    continue
                field_conf = configured[canonical]
                key = (res['text'], field_conf['field_name'])
                if key in already_texts:
                    continue
                additions.append({
                    'text': res['text'],
                    'type': field_conf['field_name'],
                    'start': res['start'],
                    'end': res['end'],
                    'source': 'ner_fallback_model',
                    'confidence': res.get('confidence', 0.5),
                    'presidio_type': canonical,
                    'guard_type': guard_type or field_conf.get('guard_type')
                })
            return additions
        except Exception as e:
            logging.warning(f"⚠️ Fallback NER erreur: {e}")
            return []

    def _detect_with_ner_for_configured_fields(self, text: str, regex_covered_text: set, target_guard_type: str = None) -> List[Dict]:
        """Détecte uniquement les champs configurés avec detection_type='ner'."""
        entities = []
        
        try:
            if target_guard_type:
                # Récupérer les champs NER pour un guard_type spécifique
                guard_types = [{'name': target_guard_type}]
                logging.info(f"🎯 Détection NER pour guard_type spécifique: {target_guard_type}")
            else:
                # Récupérer les champs NER pour tous les guard_types
                guard_types = self.config_loader.db.get_guard_types()
                logging.info(f"🌍 Détection NER pour tous les guard_types: {len(guard_types)}")
            
            ner_fields = []
            
            for guard_type in guard_types:
                pii_fields = self.config_loader.db.get_pii_fields(guard_type['name'])
                for field in pii_fields:
                    if field['detection_type'] == 'ner' and field['ner_entity_type']:
                        ner_fields.append({
                            'field_name': field['field_name'],
                            'ner_entity_type': field['ner_entity_type'],
                            'guard_type': guard_type['name'],
                            'confidence_threshold': field.get('confidence_threshold', 0.7)
                        })
            
            if not ner_fields:
                print("🤖 Aucun champ NER configuré, pas de détection NER")
                return entities
            
            print(f"🤖 Champs NER configurés: {[f['field_name'] + ':' + f['ner_entity_type'] for f in ner_fields]}")
            
            # Utiliser Presidio pour détecter chaque entité configurée (multi-lang fallback)
            if self.presidio_analyzer:
                # Déterminer les langues chargées dans l'engine spaCy
                try:
                    loaded_langs = list(getattr(self.presidio_analyzer.nlp_engine, 'nlp', {}).keys())
                    if not loaded_langs:
                        loaded_langs = ['fr']
                except Exception:
                    loaded_langs = ['fr']
                # Ajouter 'en' comme fallback si absent (souvent utile pour EMAIL_ADDRESS / CREDIT_CARD)
                if 'en' not in loaded_langs:
                    loaded_langs.append('en')
                logging.info(f"🌐 Langues NER disponibles/fallback: {loaded_langs}")

                for field in ner_fields:
                    raw_type = field['ner_entity_type'] or ''
                    presidio_type = self.entity_mapping.get(raw_type.upper(), raw_type.upper())
                    logging.info(f"🔄 Champ '{field['field_name']}' type interface '{raw_type}' → canonique '{presidio_type}'")
                    found = False
                    for lang in loaded_langs:
                        try:
                            # Analyse ciblée
                            results = self.presidio_analyzer.analyze(text=text, language=lang, entities=[presidio_type])
                            logging.info(f"🧪 Résultats {presidio_type} ({lang}): {[(r.entity_type, text[r.start:r.end], round(r.score,3)) for r in results]}")
                            for result in results:
                                if result.entity_type != presidio_type:
                                    continue
                                detected_text = text[result.start:result.end]
                                if detected_text in regex_covered_text:
                                    logging.info(f"⏭️ Ignoré regex: {detected_text}")
                                    continue
                                # Seuil de confiance supprimé : on accepte tous les résultats retournés par l'analyseur
                                # Ancien filtre basé sur field['confidence_threshold'] retiré.
                                entities.append({
                                    'text': detected_text,
                                    'type': field['field_name'],
                                    'start': result.start,
                                    'end': result.end,
                                    'source': f'ner_configured_{lang}',
                                    'confidence': result.score,
                                    'presidio_type': result.entity_type,
                                    'guard_type': field['guard_type']
                                })
                                print(f"🎯 NER trouvé ({lang}): '{detected_text}' → {field['field_name']} [{presidio_type}] score={result.score:.2f}")
                                found = True
                            if found:
                                break
                        except Exception as e:
                            logging.warning(f"❌ Erreur analyse {presidio_type} ({lang}): {e}")
                    if not found:
                        logging.warning(f"⚠️ Aucune détection pour '{presidio_type}' (champ '{field['field_name']}') sur langues {loaded_langs}")
            else:
                logging.warning("⚠️ Presidio inactif – fallback partiel regex pour certains types NER (EMAIL_ADDRESS, PHONE_NUMBER)")
                # Fallback minimal pour EMAIL_ADDRESS si utilisateur a créé un champ NER mais Presidio absent
                email_like = [f for f in ner_fields if (f['ner_entity_type'] or '').upper() in ('EMAIL_ADDRESS','EMAIL')]
                if email_like:
                    # Simple regex email standard
                    email_pattern = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
                    for match in email_pattern.finditer(text):
                        val = match.group(0)
                        if val in regex_covered_text:
                            continue
                        for field in email_like:
                            entities.append({
                                'text': val,
                                'type': field['field_name'],
                                'start': match.start(),
                                'end': match.end(),
                                'source': 'ner_fallback_regex',
                                'confidence': 0.50,
                                'presidio_type': 'EMAIL_ADDRESS',
                                'guard_type': field['guard_type']
                            })
                            print(f"🔁 Fallback EMAIL_ADDRESS regex → {val}")
        
        except Exception as e:
            print(f"⚠️ Erreur détection NER configurée: {e}")
        
        return entities

    def _detect_with_camembert(self, text: str) -> List[Dict]:
        """Détecte les entités avec CamemBERT français."""
        try:
            if not getattr(self.models, 'camembert_model', None):
                return []
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

    def _detect_with_regex(self, text: str, target_guard_type: str = None) -> List[Dict]:
        """Détection par patterns regex dynamiques depuis la base de données."""
        entities = []
        
        try:
            if target_guard_type:
                # Détecter seulement pour un guard_type spécifique
                guard_types = [{'name': target_guard_type}]
                logging.info(f"🎯 Détection regex pour guard_type spécifique: {target_guard_type}")
            else:
                # Détecter pour tous les guard_types (comportement par défaut)
                guard_types = self.config_loader.db.get_guard_types()
                logging.info(f"🌍 Détection regex pour tous les guard_types: {len(guard_types)}")
            
            for guard_type in guard_types:
                pii_fields = self.config_loader.db.get_pii_fields(guard_type['name'])
                
                for field in pii_fields:
                    if field['detection_type'] == 'regex' and field['pattern']:
                        try:
                            # Utiliser directement le pattern du champ
                            pattern_text = field['pattern']
                            
                            if not pattern_text:
                                logging.info(f"⚠️ Pattern vide pour {field['field_name']}")
                                continue
                                
                            logging.info(f"🔍 Test pattern '{pattern_text}' pour champ '{field['field_name']}' sur texte: '{text}'")
                            
                            # Compiler le pattern
                            compiled_pattern = re.compile(pattern_text, re.IGNORECASE)
                            
                            # Chercher les correspondances
                            for match in compiled_pattern.finditer(text):
                                val = match.group()
                                s, e = match.start(), match.end()
                                # Filtrage spécifique CVV pour éviter années / segments de grands nombres
                                if field['field_name'] == 'cvv':
                                    # Exclure si entouré par d'autres chiffres (fait partie d'une plus longue séquence)
                                    if (s > 0 and text[s-1].isdigit()) or (e < len(text) and text[e].isdigit()):
                                        continue
                                    # Exclure années plausibles 19xx / 20xx
                                    if re.fullmatch(r'19\d\d|20\d\d', val):
                                        continue
                                    # Exiger contexte lexical (cvv, cvc, code de securite) si pattern très générique
                                    # Étendre la fenêtre de contexte pour couvrir 'code de sécurité'
                                    window_start = max(0, s-40)
                                    context = text[window_start:s].lower()
                                    # Accepter contextes: cvv, cvc, code de sécurité, sécurité seule
                                    if not re.search(r'(cvv|cvc|code\s+de\s+s[eé]curit[ée]|s[eé]curit[ée])', context):
                                        # Si pas de contexte explicite et pattern est juste \d{3,4}, ignorer
                                        if field['pattern'] == r'\d{3,4}':
                                            continue
                                entities.append({
                                    "text": val,
                                    "type": field['field_name'],
                                    "start": s,
                                    "end": e,
                                    "source": "regex_db",
                                    "confidence": 0.9,
                                    "guard_type": guard_type['name'],
                                    "field_info": field
                                })
                                logging.info(f"🎯 REGEX DB trouvé: '{val}' type: {field['field_name']} dans {guard_type['name']}")
                                
                        except re.error as e:
                            print(f"⚠️ Pattern regex invalide '{field['field_name']}': {e}")
                            continue
                    
        except Exception as e:
            print(f"⚠️ Erreur accès champs PII DB: {e}")
            # Fallback vers les patterns statiques
            for pii_type, pattern in PII_PATTERNS.items():
                for match in re.finditer(pattern.regex, text):
                    entities.append({
                        "text": match.group(),
                        "type": pii_type,
                        "start": match.start(),
                        "end": match.end(),
                        "source": "regex_static"
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

    # =================== UNIFICATION TYPES ÉQUIVALENTS ===================
    def _unify_equivalent_types(self, entities: List[Dict]) -> List[Dict]:
        """Si plusieurs types représentent le même concept (ex: id_card & passport avec même regex)
        on peut les projeter vers un type canonique commun (identity_document).

        Critères d'unification:
        - Types membres présents (ex: id_card, passport)
        - Même segment texte détecté OU patterns identiques (source regex_db) sur la même plage
        """
        GROUPS = [
            {"canonical": "identity_document", "members": {"id_card", "passport"}},
        ]
        by_span = {}
        for ent in entities:
            key = (ent.get('start'), ent.get('end'))
            by_span.setdefault(key, []).append(ent)
        updated = []
        for key, ents in by_span.items():
            replaced = False
            for grp in GROUPS:
                member_types = {e['type'] for e in ents}
                intersect = member_types & grp['members']
                if len(intersect) >= 2:  # au moins deux types concurrents détectés même span
                    # Garder la première (priorité regex_db puis ordre) mais renommer canonical
                    chosen = sorted(ents, key=lambda e: 0 if e.get('source') == 'regex_db' else 1)[0]
                    chosen = dict(chosen)
                    chosen['original_type'] = chosen['type']
                    chosen['type'] = grp['canonical']
                    updated.append(chosen)
                    replaced = True
                    break
            if not replaced:
                updated.extend(ents)
        return updated

    # =================== POST TRAITEMENT INCOHERENCES ===================
    def _post_process_incoherences(self, entities: List[Dict], text: str) -> List[Dict]:
        """Nettoie incohérences courantes:
        - Retire PERSON/PER/NOM détecté uniquement comme sous-partie d'un email
        - Filtre petits nombres (3-4 digits) hors contexte CVV explicite
        - Dé-duplique fragments numériques inclus dans une entité plus longue (carte, iban, phone)
        - (Optionnel) filtrage strict activé via PII_STRICT_NUMERIC=1
        """
        if not entities:
            return entities
        strict_numeric = os.getenv('PII_STRICT_NUMERIC', '1') == '1'

        # Préparer index d'entités par span & type
        cleaned = []
        spans = []  # (start,end,type)
        # Construire liste des emails pour exclusion
        email_spans = [(e['start'], e['end']) for e in entities if e['type'] in ('email','EMAIL','email_address')]

        for ent in entities:
            t = ent['type'].lower()
            s, e = ent['start'], ent['end']
            val = ent['text']
            # 1. Supprimer noms inclus dans email
            if t in {'name','full_name','firstname','person'}:
                inside_email = False
                for es, ee in email_spans:
                    if s >= es and e <= ee:
                        inside_email = True
                        break
                if inside_email:
                    logging.info(f"🧹 SUPPR nom dans email: {val}")
                    continue
            # 2. Filtrage petits nombres hors contexte si strict_numeric
            if strict_numeric and t not in {'cvv','credit_card','iban','phone','social_security'}:
                if re.fullmatch(r'\d{3,4}', val):
                    # Vérifier présence d'un mot clé autour sinon ignorer
                    window_start = max(0, s-40)
                    context = text[window_start:s].lower()
                    if not re.search(r'(cvv|cvc|code\s+de\s+s[eé]curit[ée]|s[eé]curit[ée])', context):
                        logging.info(f"🧹 SUPPR nombre isolé {val}")
                        continue
            spans.append((s,e,t))
            cleaned.append(ent)

        # 3. Supprimer fragments numériques inclus dans plus long segment du même type ou type carte/iban
        final_list = []
        for ent in cleaned:
            s,e = ent['start'], ent['end']
            val = ent['text']
            t = ent['type'].lower()
            if t in {'cvv'}:
                # si inclus dans un credit_card span plus large, ignorer
                included = False
                for other in cleaned:
                    if other is ent:
                        continue
                    ot = other['type'].lower()
                    if ot in {'credit_card','card_number'} and other['start'] <= s and other['end'] >= e:
                        included = True
                        break
                if included:
                    logging.info(f"🧹 SUPPR cvv fragment dans carte: {val}")
                    continue
            final_list.append(ent)
        return final_list

    # =================== HEURISTIQUE NOMS ===================
    def _heuristic_name_entities(self, text: str, guard_type: str | None, existing: List[Dict]) -> List[Dict]:
        """Détection déterministe de noms simples en minuscules lorsque les modèles NER hésitent.

        Cas ciblé : phrases comme:
          - "je m'appelle josh" / "je m appele josh" (fautes courantes)
          - "mon ami s'appelle doua" / "mon amie s appel Doua"

        Conditions d'ajout:
          - Champ NER configuré avec ner_entity_type=PERSON (ex: mon_nom)
          - Le token candidat n'est pas déjà détecté
          - Longueur >= 2 et lettres uniquement (avec accents, tirets autorisés)
        """
        # Récupération des champs NER PERSON configurés
        try:
            if guard_type:
                guard_types = [{'name': guard_type}]
            else:
                guard_types = self.config_loader.db.get_guard_types()
        except Exception:
            return []

        person_fields = []
        for gt in guard_types:
            try:
                for f in self.config_loader.db.get_pii_fields(gt['name']):
                    if f['detection_type'] == 'ner' and (f.get('ner_entity_type') or '').upper() in {'PERSON','PER'}:
                        person_fields.append({'field_name': f['field_name'], 'guard_type': gt['name']})
            except Exception:
                continue
        if not person_fields:
            return []

        existing_lower_spans = {(e['text'].lower(), e['type']) for e in existing}

        # Regex variantes "je m'appelle" + "mon ami(e) s'appelle" + prénom seul en tête
        patterns = [
            r"\bje\s+m['’ ]?app(?:e|a)l(?:e|le)\s+([a-zA-ZÀ-ÖØ-öø-ÿ'’\-]{2,40})",
            r"\bmon\s+ami[e]?\s+s['’ ]?app(?:e|a)l(?:e|le)\s+([a-zA-ZÀ-ÖØ-öø-ÿ'’\-]{2,40})",
            r"^\s*([a-zà-öø-ÿ]{2,30})(?=\s*[,:])"  # début de texte: josh, doua,
        ]
        found = []
        for pat in patterns:
            for m in re.finditer(pat, text, flags=re.IGNORECASE):
                name_raw = m.group(1).strip(" -'’")
                if len(name_raw) < 2:
                    continue
                # Normaliser capitalisation: Josh, Doua
                norm = name_raw[0].upper() + name_raw[1:]
                # Choisir premier champ person (ou celui matching guard_type)
                target_field = person_fields[0]
                key = (norm.lower(), target_field['field_name'])
                if key in existing_lower_spans:
                    continue
                # Filtrer tokens bruit
                if norm.lower() in {"mon","ami","amie","appelle","appel","je"}:
                    continue
                found.append({
                    'text': norm,
                    'type': target_field['field_name'],
                    'start': m.start(1),
                    'end': m.end(1),
                    'source': 'heuristic_name',
                    'confidence': 0.6,
                    'guard_type': target_field['guard_type'],
                    'presidio_type': 'PERSON'
                })
        return found

import re
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from ..database.db_manager import db_manager

logger = logging.getLogger(__name__)

class DynamicConfigLoader:
    """
    Gestionnaire de configuration dynamique utilisant la base de données
    pour permettre la gestion CRUD des types de protection et leurs champs
    """
    
    def __init__(self):
        self.db = db_manager
        self._compiled_patterns_cache = {}
        self._load_patterns_cache()
    
    def _load_patterns_cache(self):
        """Charge et compile les patterns regex en cache"""
        try:
            patterns = self.db.get_regex_patterns()
            self._compiled_patterns_cache = {}
            
            for pattern in patterns:
                try:
                    flags = 0
                    if 'i' in pattern.get('flags', ''):
                        flags |= re.IGNORECASE
                    if 'm' in pattern.get('flags', ''):
                        flags |= re.MULTILINE
                    if 's' in pattern.get('flags', ''):
                        flags |= re.DOTALL
                    
                    compiled_pattern = re.compile(pattern['pattern'], flags)
                    self._compiled_patterns_cache[pattern['name']] = {
                        'pattern': compiled_pattern,
                        'display_name': pattern['display_name'],
                        'test_examples': pattern['test_examples']
                    }
                    
                except re.error as e:
                    logger.error(f"Pattern regex invalide '{pattern['name']}': {e}")
                    
        except Exception as e:
            logger.error(f"Erreur chargement patterns: {e}")
    
    def reload_patterns_cache(self):
        """Recharge le cache des patterns"""
        self._load_patterns_cache()
        logger.info("Cache des patterns rechargé")
    
    # =================== MÉTHODES COMPATIBLES ANCIEN SYSTÈME ===================
    
    def get_guard_types(self, guard_type: str) -> List[str]:
        """
        Retourne les types PII autorisés pour un guard_type donné
        (Compatible avec l'ancien système)
        """
        try:
            pii_fields = self.db.get_pii_fields(guard_type)
            return [field['field_name'] for field in pii_fields if field['is_active']]
        except Exception as e:
            logger.error(f"Erreur récupération types pour {guard_type}: {e}")
            return []
    
    def get_all_configs(self) -> Dict[str, Any]:
        """
        Retourne toutes les configurations (compatible ancien système)
        """
        try:
            guard_types = self.db.get_guard_types()
            configs = {}
            
            for guard_type in guard_types:
                guard_name = guard_type['name']
                pii_fields = self.db.get_pii_fields(guard_name)
                
                configs[guard_name] = {
                    'info': {
                        'display_name': guard_type['display_name'],
                        'description': guard_type['description'],
                        'icon': guard_type['icon'],
                        'color': guard_type['color']
                    },
                    'fields': {}
                }
                
                for field in pii_fields:
                    field_config = {
                        'type': field['detection_type'],
                        'example': field['example_value']
                    }
                    
                    # Ajouter pattern si c'est du regex
                    if field['detection_type'] in ['regex', 'hybrid'] and field['pattern']:
                        field_config['pattern'] = field['pattern']
                    
                    # Ajouter type NER si applicable
                    if field['detection_type'] in ['ner', 'hybrid'] and field['ner_entity_type']:
                        field_config['ner_entity_type'] = field['ner_entity_type']
                    
                    configs[guard_name]['fields'][field['field_name']] = field_config
            
            return configs
            
        except Exception as e:
            logger.error(f"Erreur récupération configurations: {e}")
            return {}
    
    def get_example_text(self, guard_type: str) -> str:
        """
        Génère un texte d'exemple basé sur les champs configurés
        """
        try:
            pii_fields = self.db.get_pii_fields(guard_type)
            
            # Templates de phrases par type de guard
            templates = {
                'TypeA': "Bonjour, je suis {name}, né le {birth_date}. Mon numéro de sécurité sociale est {social_security}.",
                'TypeB': "Ma carte bancaire {credit_card} avec le code {cvv} et mon IBAN {iban}.",
                'InfoPerso': "Contactez-moi à {email} ou au {phone}. J'habite à {address}."
            }
            
            template = templates.get(guard_type, "Exemple avec {field_name}")
            
            # Remplacer les champs par leurs exemples
            example_text = template
            for field in pii_fields:
                placeholder = "{" + field['field_name'] + "}"
                if placeholder in example_text and field['example_value']:
                    example_text = example_text.replace(placeholder, field['example_value'])
            
            return example_text
            
        except Exception as e:
            logger.error(f"Erreur génération exemple pour {guard_type}: {e}")
            return f"Exemple pour {guard_type} non disponible"
    
    def reload_config(self, guard_type: str = None):
        """
        Recharge la configuration (compatible ancien système)
        """
        self.reload_patterns_cache()
        logger.info(f"Configuration rechargée pour {guard_type or 'tous les types'}")
    
    # =================== NOUVELLES MÉTHODES CRUD ===================
    
    def create_guard_type(self, name: str, display_name: str, description: str = "",
                         icon: str = "🛡️", color: str = "#666666") -> Dict[str, Any]:
        """Crée un nouveau type de protection"""
        try:
            guard_id = self.db.create_guard_type(name, display_name, description, icon, color)
            return {
                'success': True,
                'guard_id': guard_id,
                'message': f"Type de protection '{name}' créé avec succès"
            }
        except Exception as e:
            logger.error(f"Erreur création guard type: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_guard_type(self, guard_name: str, **kwargs) -> Dict[str, Any]:
        """Met à jour un type de protection"""
        try:
            guard_type = self.db.get_guard_type(guard_name)
            if not guard_type:
                return {'success': False, 'error': f"Type '{guard_name}' non trouvé"}
            
            success = self.db.update_guard_type(guard_type['id'], **kwargs)
            return {
                'success': success,
                'message': f"Type '{guard_name}' mis à jour" if success else "Aucune modification"
            }
        except Exception as e:
            logger.error(f"Erreur mise à jour guard type: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_pii_field(self, guard_type_name: str, field_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée un nouveau champ PII
        
        field_data format:
        {
            "field_name": "phone",
            "display_name": "Téléphone",
            "type": "regex",  # ou "ner" ou "hybrid"
            "example": "+33 6 45 67 89 12",
            "pattern": "french_phone",  # nom du pattern ou pattern inline
            "ner_entity_type": "PHONE_NUMBER",  # si type="ner"
            "confidence_threshold": 0.7,
            "priority": 1
        }
        """
        try:
            # Validation des données
            required_fields = ['field_name', 'display_name', 'type', 'example']
            for field in required_fields:
                if field not in field_data:
                    return {'success': False, 'error': f"Champ requis manquant: {field}"}
            
            detection_type = field_data['type']
            if detection_type not in ['regex', 'ner', 'hybrid']:
                return {'success': False, 'error': "Type doit être 'regex', 'ner' ou 'hybrid'"}
            
            # Validation spécifique au type
            if detection_type in ['regex', 'hybrid']:
                if 'pattern' not in field_data:
                    return {'success': False, 'error': "Pattern requis pour type regex/hybrid"}
            
            if detection_type in ['ner', 'hybrid']:
                if 'ner_entity_type' not in field_data:
                    return {'success': False, 'error': "ner_entity_type requis pour type ner/hybrid"}
            
            # Créer le champ
            field_id = self.db.create_pii_field(
                guard_type_name=guard_type_name,
                field_name=field_data['field_name'],
                display_name=field_data['display_name'],
                detection_type=detection_type,
                example_value=field_data['example'],
                regex_pattern=field_data.get('pattern'),
                ner_entity_type=field_data.get('ner_entity_type')
            )
            
            return {
                'success': True,
                'field_id': field_id,
                'message': f"Champ '{field_data['field_name']}' créé avec succès"
            }
            
        except Exception as e:
            logger.error(f"Erreur création champ PII: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_pii_field(self, field_id: int, **kwargs) -> Dict[str, Any]:
        """Met à jour un champ PII"""
        try:
            success = self.db.update_pii_field(field_id, **kwargs)
            return {
                'success': success,
                'message': f"Champ ID {field_id} mis à jour" if success else "Aucune modification"
            }
        except Exception as e:
            logger.error(f"Erreur mise à jour champ PII: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_regex_pattern(self, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée un nouveau pattern regex
        
        pattern_data format:
        {
            "name": "custom_phone",
            "display_name": "Téléphone Personnalisé",
            "pattern": "\\d{2}\\.\\d{2}\\.\\d{2}\\.\\d{2}\\.\\d{2}",
            "description": "Format téléphone avec points",
            "test_examples": ["01.23.45.67.89", "06.12.34.56.78"],
            "flags": "i"
        }
        """
        try:
            # Validation
            required_fields = ['name', 'display_name', 'pattern']
            for field in required_fields:
                if field not in pattern_data:
                    return {'success': False, 'error': f"Champ requis manquant: {field}"}
            
            # Test de compilation du pattern
            try:
                re.compile(pattern_data['pattern'])
            except re.error as e:
                return {'success': False, 'error': f"Pattern regex invalide: {e}"}
            
            pattern_id = self.db.create_regex_pattern(
                name=pattern_data['name'],
                display_name=pattern_data['display_name'],
                pattern=pattern_data['pattern'],
                description=pattern_data.get('description', ''),
                test_examples=pattern_data.get('test_examples', []),
                flags=pattern_data.get('flags', 'i')
            )
            
            # Recharger le cache
            self.reload_patterns_cache()
            
            return {
                'success': True,
                'pattern_id': pattern_id,
                'message': f"Pattern '{pattern_data['name']}' créé avec succès"
            }
            
        except Exception as e:
            logger.error(f"Erreur création pattern: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_compiled_pattern(self, pattern_name: str):
        """Retourne un pattern compilé depuis le cache"""
        return self._compiled_patterns_cache.get(pattern_name, {}).get('pattern')
    
    def get_detection_config(self, guard_type: str) -> Dict[str, Any]:
        """
        Retourne la configuration de détection pour un guard_type
        Format optimisé pour le détecteur PII
        """
        try:
            pii_fields = self.db.get_pii_fields(guard_type)
            
            config = {
                'regex_fields': {},
                'ner_fields': {},
                'hybrid_fields': {}
            }
            
            for field in pii_fields:
                field_name = field['field_name']
                detection_type = field['detection_type']
                
                field_config = {
                    'display_name': field['display_name'],
                    'example': field['example_value']
                }
                
                if detection_type == 'regex':
                    if field['pattern']:
                        compiled_pattern = self.get_compiled_pattern(field['regex_pattern'])
                        if compiled_pattern:
                            field_config['compiled_pattern'] = compiled_pattern
                    config['regex_fields'][field_name] = field_config
                
                elif detection_type == 'ner':
                    field_config['entity_type'] = field['ner_entity_type']
                    config['ner_fields'][field_name] = field_config
                
                elif detection_type == 'hybrid':
                    if field['pattern']:
                        compiled_pattern = self.get_compiled_pattern(field['regex_pattern'])
                        if compiled_pattern:
                            field_config['compiled_pattern'] = compiled_pattern
                    
                    field_config['entity_type'] = field['ner_entity_type']
                    config['hybrid_fields'][field_name] = field_config
            
            return config
            
        except Exception as e:
            logger.error(f"Erreur récupération config détection: {e}")
            return {'regex_fields': {}, 'ner_fields': {}, 'hybrid_fields': {}}

# Instance globale (compatible avec l'ancien système)
dynamic_config_loader = DynamicConfigLoader()

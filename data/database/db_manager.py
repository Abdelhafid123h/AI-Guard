import sqlite3
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Chemin vers la base de données dans le projet
            current_dir = Path(__file__).parent
            self.db_path = current_dir / "ai_guards.db"
        else:
            self.db_path = Path(db_path)
        
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données avec le schéma"""
        try:
            # Lire le fichier schema.sql
            schema_path = Path(__file__).parent / "schema.sql"
            
            if not schema_path.exists():
                logger.error(f"Fichier schema.sql non trouvé: {schema_path}")
                return
            
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(schema_sql)
                logger.info(f"Base de données initialisée: {self.db_path}")
                
        except Exception as e:
            logger.error(f"Erreur initialisation base de données: {e}")
    
    def get_connection(self):
        """Retourne une connexion à la base de données"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Permet l'accès par nom de colonne
        return conn

    # =================== GESTION DES TYPES DE PROTECTION ===================
    
    def get_guard_types(self) -> List[Dict]:
        """Récupère tous les types de protection"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, name, display_name, description, icon, color, is_active
                FROM guard_types 
                WHERE is_active = 1
                ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_guard_type(self, guard_type_name: str) -> Optional[Dict]:
        """Récupère un type de protection spécifique"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, name, display_name, description, icon, color, is_active
                FROM guard_types 
                WHERE name = ? AND is_active = 1
            """, (guard_type_name,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def create_guard_type(self, name: str, display_name: str, description: str = "", 
                         icon: str = "🛡️", color: str = "#666666") -> int:
        """Crée un nouveau type de protection"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO guard_types (name, display_name, description, icon, color)
                VALUES (?, ?, ?, ?, ?)
            """, (name, display_name, description, icon, color))
            return cursor.lastrowid
    
    def update_guard_type(self, guard_id: int, **kwargs) -> bool:
        """Met à jour un type de protection"""
        if not kwargs:
            return False
        
        # Construction dynamique de la requête UPDATE
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [guard_id]
        
        with self.get_connection() as conn:
            cursor = conn.execute(f"""
                UPDATE guard_types 
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)
            return cursor.rowcount > 0
    
    def delete_guard_type(self, guard_id: int) -> bool:
        """Supprime (désactive) un type de protection"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE guard_types 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (guard_id,))
            return cursor.rowcount > 0

    # =================== GESTION DES CHAMPS PII ===================
    
    def get_pii_fields(self, guard_type_name: str) -> List[Dict]:
        """Récupère tous les champs PII d'un type de protection"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT pf.id, pf.field_name, pf.display_name, pf.detection_type,
                       pf.example_value, pf.regex_pattern, pf.ner_entity_type,
                       pf.confidence_threshold, pf.priority, pf.is_active,
                       rp.pattern as regex_pattern_value
                FROM pii_fields pf
                JOIN guard_types gt ON pf.guard_type_id = gt.id
                LEFT JOIN regex_patterns rp ON pf.regex_pattern = rp.name
                WHERE gt.name = ? AND pf.is_active = 1
                ORDER BY pf.priority, pf.field_name
            """, (guard_type_name,))
            
            fields = []
            for row in cursor.fetchall():
                field = dict(row)
                # Si c'est une référence à un pattern, utiliser le pattern de la table
                if field['regex_pattern'] and field['regex_pattern_value']:
                    field['pattern'] = field['regex_pattern_value']
                elif field['regex_pattern'] and not field['regex_pattern_value']:
                    # Pattern inline (directement dans le champ)
                    field['pattern'] = field['regex_pattern']
                else:
                    field['pattern'] = None
                
                del field['regex_pattern_value']  # Nettoyer le champ temporaire
                fields.append(field)
            
            return fields
    
    def create_pii_field(self, guard_type_name: str, field_name: str, 
                        display_name: str, detection_type: str, 
                        example_value: str = "", regex_pattern: str = None,
                        ner_entity_type: str = None, confidence_threshold: float = 0.7,
                        priority: int = 1) -> int:
        """Crée un nouveau champ PII"""
        
        # Récupérer l'ID du guard_type
        guard_type = self.get_guard_type(guard_type_name)
        if not guard_type:
            raise ValueError(f"Type de protection '{guard_type_name}' non trouvé")
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO pii_fields 
                (guard_type_id, field_name, display_name, detection_type, 
                 example_value, regex_pattern, ner_entity_type, 
                 confidence_threshold, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (guard_type['id'], field_name, display_name, detection_type,
                  example_value, regex_pattern, ner_entity_type,
                  confidence_threshold, priority))
            return cursor.lastrowid
    
    def update_pii_field(self, field_id: int, **kwargs) -> bool:
        """Met à jour un champ PII"""
        if not kwargs:
            return False
        
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [field_id]
        
        with self.get_connection() as conn:
            cursor = conn.execute(f"""
                UPDATE pii_fields 
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)
            return cursor.rowcount > 0
    
    def delete_pii_field(self, field_id: int) -> bool:
        """Supprime (désactive) un champ PII"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE pii_fields 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (field_id,))
            return cursor.rowcount > 0

    # =================== GESTION DES PATTERNS REGEX ===================
    
    def get_regex_patterns(self) -> List[Dict]:
        """Récupère tous les patterns regex"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, name, display_name, pattern, description, 
                       test_examples, flags, is_active
                FROM regex_patterns 
                WHERE is_active = 1
                ORDER BY name
            """)
            
            patterns = []
            for row in cursor.fetchall():
                pattern = dict(row)
                # Parser les exemples JSON
                try:
                    pattern['test_examples'] = json.loads(pattern['test_examples'] or '[]')
                except json.JSONDecodeError:
                    pattern['test_examples'] = []
                patterns.append(pattern)
            
            return patterns
    
    def get_regex_pattern(self, pattern_name: str) -> Optional[Dict]:
        """Récupère un pattern regex spécifique"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, name, display_name, pattern, description, 
                       test_examples, flags, is_active
                FROM regex_patterns 
                WHERE name = ? AND is_active = 1
            """, (pattern_name,))
            row = cursor.fetchone()
            
            if row:
                pattern = dict(row)
                try:
                    pattern['test_examples'] = json.loads(pattern['test_examples'] or '[]')
                except json.JSONDecodeError:
                    pattern['test_examples'] = []
                return pattern
            return None
    
    def create_regex_pattern(self, name: str, display_name: str, pattern: str,
                           description: str = "", test_examples: List[str] = None,
                           flags: str = "i") -> int:
        """Crée un nouveau pattern regex"""
        test_examples_json = json.dumps(test_examples or [])
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO regex_patterns 
                (name, display_name, pattern, description, test_examples, flags)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, display_name, pattern, description, test_examples_json, flags))
            return cursor.lastrowid
    
    def update_regex_pattern(self, pattern_id: int, **kwargs) -> bool:
        """Met à jour un pattern regex"""
        if not kwargs:
            return False
        
        # Convertir test_examples en JSON si présent
        if 'test_examples' in kwargs:
            kwargs['test_examples'] = json.dumps(kwargs['test_examples'])
        
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [pattern_id]
        
        with self.get_connection() as conn:
            cursor = conn.execute(f"""
                UPDATE regex_patterns 
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)
            return cursor.rowcount > 0
    
    def delete_regex_pattern(self, pattern_id: int) -> bool:
        """Supprime (désactive) un pattern regex"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE regex_patterns 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (pattern_id,))
            return cursor.rowcount > 0

    # =================== GESTION DES TYPES NER ===================
    
    def get_ner_entity_types(self, model_name: str = None) -> List[Dict]:
        """Récupère les types d'entités NER disponibles"""
        query = """
            SELECT id, model_name, entity_type, display_name, description, is_active
            FROM ner_entity_types 
            WHERE is_active = 1
        """
        params = []
        
        if model_name:
            query += " AND model_name = ?"
            params.append(model_name)
        
        query += " ORDER BY model_name, entity_type"
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

# Instance globale
db_manager = DatabaseManager()

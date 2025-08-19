import sqlite3
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

# Support MySQL optionnel (piloté par variables d'environnement)
try:
    import pymysql  # type: ignore
    from pymysql.cursors import DictCursor  # type: ignore
except Exception:  # pymysql pas requis si on reste sur sqlite
    pymysql = None

logger = logging.getLogger(__name__)
DB_MANAGER_VERSION = "history-debug-1"

class DatabaseManager:
    def __init__(self, db_path: str = None):
        # Déterminer moteur (sqlite par défaut)
        self.engine = os.getenv("DB_ENGINE", "sqlite").lower()

        # Préparer chemin SQLite par défaut, même si MySQL ciblé (pour fallback)
        current_dir = Path(__file__).parent
        self.db_path = Path(db_path) if db_path else (current_dir / "ai_guards.db")

        if self.engine == 'mysql':
            # Paramètres MySQL via env (valeurs par défaut raisonnables)
            self.mysql_host = os.getenv('DB_HOST', '127.0.0.1')
            self.mysql_port = int(os.getenv('DB_PORT', '3306'))
            self.mysql_user = os.getenv('DB_USER', 'root')
            self.mysql_password = os.getenv('DB_PASSWORD', '0000')
            self.mysql_name = os.getenv('DB_NAME', 'ai_guards')
            if pymysql is None:
                logger.error("PyMySQL non installé – bascule sur SQLite")
                self.engine = 'sqlite'

        self.init_database()

    # Permet de récupérer si l'objet a été gardé en mémoire sans attributs après un reload
    def ensure_initialized(self):
        if not hasattr(self, 'engine'):
            self.engine = os.getenv("DB_ENGINE", "sqlite").lower()
            try:
                self.init_database()
            except Exception as e:
                logger.error(f"ensure_initialized: init_database échec: {e}")
        return self.engine

    # ---------------- Internal helper for cross-engine SQL -----------------
    def _query(self, conn, sql: str, params: tuple = ()):  # returns a cursor
        """Unified query executor.
        - For SQLite: direct conn.execute
        - For MySQL (PyMySQL): create cursor, adapt '?' placeholders to '%s'
        NOTE: We assume '?' only appears as a placeholder in our queries.
        """
        if self.engine == 'mysql':
            cur = conn.cursor()
            if params:
                adapted = sql.replace('?', '%s')
                cur.execute(adapted, params)
            else:
                cur.execute(sql)
            return cur
        # sqlite
        return conn.execute(sql, params) if params else conn.execute(sql)
    
    def init_database(self):
        """Initialise la base selon moteur (idempotent)."""
        try:
            if self.engine == 'mysql':
                # Création conditionnelle (si tables absentes)
                with self.get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("SHOW TABLES LIKE 'guard_types'")
                    exists = cur.fetchone() is not None
                    if exists:
                        # S'assurer que la table usage_history existe même si schéma non ré-exécuté
                        self._ensure_usage_history_mysql(cur)
                        self._ensure_usage_history_columns_mysql(cur)
                        conn.commit()
                        return
                    schema_path = Path(__file__).parent / 'schema_mysql.sql'
                    if not schema_path.exists():
                        logger.error(f"Fichier schema_mysql.sql manquant: {schema_path}")
                        return
                    sql = schema_path.read_text(encoding='utf-8')
                    for statement in [s.strip() for s in sql.split(';') if s.strip()]:
                        cur.execute(statement)
                    conn.commit()
                    logger.info("Base MySQL initialisée (schéma appliqué)")
            else:  # SQLite
                schema_path = Path(__file__).parent / "schema.sql"
                if not schema_path.exists():
                    logger.error(f"Fichier schema.sql non trouvé: {schema_path}")
                    return
                # Pour éviter erreurs si tables existent déjà, vérifier guard_types
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guard_types'")
                    exists = cursor.fetchone() is not None
                    if not exists:
                        with open(schema_path, 'r', encoding='utf-8') as f:
                            schema_sql = f.read()
                        conn.executescript(schema_sql)
                        logger.info(f"Base de données SQLite initialisée: {self.db_path}")
                    # Assurer création table usage_history si absente
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usage_history'")
                    if cursor.fetchone() is None:
                        cursor.execute("""
                            CREATE TABLE usage_history (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                guard_type VARCHAR(50),
                                masked_text TEXT,
                                prompt_tokens INTEGER DEFAULT 0,
                                completion_tokens INTEGER DEFAULT 0,
                                total_tokens INTEGER DEFAULT 0
                            )
                        """)
                        conn.commit()
                        logger.info("Table usage_history créée (migration)")
                    else:
                        # Migration colonnes manquantes
                        self._ensure_usage_history_columns_sqlite(conn)
        except Exception as e:
            logger.error(f"Erreur initialisation base de données: {e}")

    def _ensure_usage_history_mysql(self, cursor):
        try:
            cursor.execute("SHOW TABLES LIKE 'usage_history'")
            if cursor.fetchone() is None:
                cursor.execute("""
                                        CREATE TABLE IF NOT EXISTS usage_history (
                                            id INT AUTO_INCREMENT PRIMARY KEY,
                                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                            guard_type VARCHAR(50),
                                            masked_text TEXT,
                                            prompt_tokens INT DEFAULT 0,
                                            completion_tokens INT DEFAULT 0,
                                            total_tokens INT DEFAULT 0,
                                            masked_token_count INT DEFAULT 0,
                                            model VARCHAR(50) DEFAULT NULL,
                                            llm_mode VARCHAR(20) DEFAULT NULL
                                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)
                logger.info("Table usage_history créée (migration MySQL)")
            else:
                # table exists: ensure columns
                cursor.execute("SHOW COLUMNS FROM usage_history")
                fetched = cursor.fetchall()
                existing = { (row['Field'] if isinstance(row, dict) and 'Field' in row else row[0]) for row in fetched }
                alters = []
                if 'masked_token_count' not in existing:
                    alters.append("ADD COLUMN masked_token_count INT DEFAULT 0")
                if 'model' not in existing:
                    alters.append("ADD COLUMN model VARCHAR(50) DEFAULT NULL")
                if 'llm_mode' not in existing:
                    alters.append("ADD COLUMN llm_mode VARCHAR(20) DEFAULT NULL")
                for stmt in alters:
                    cursor.execute(f"ALTER TABLE usage_history {stmt}")
                if alters:
                    logger.info(f"Colonnes ajoutées à usage_history MySQL: {alters}")
        except Exception as e:
            logger.error(f"Migration usage_history MySQL échouée: {e}")

    def _ensure_usage_history_columns_mysql(self, cursor):
        try:
            cursor.execute("SHOW COLUMNS FROM usage_history")
            fetched = cursor.fetchall()
            existing = { (row['Field'] if isinstance(row, dict) and 'Field' in row else row[0]) for row in fetched }
            alters = []
            if 'masked_text' not in existing:
                alters.append("ADD COLUMN masked_text TEXT")
            if 'masked_token_count' not in existing:
                alters.append("ADD COLUMN masked_token_count INT DEFAULT 0")
            if 'model' not in existing:
                alters.append("ADD COLUMN model VARCHAR(50) DEFAULT NULL")
            if 'llm_mode' not in existing:
                alters.append("ADD COLUMN llm_mode VARCHAR(20) DEFAULT NULL")
            if alters:
                for stmt in alters:
                    cursor.execute(f"ALTER TABLE usage_history {stmt}")
                logger.info(f"Migration colonnes usage_history MySQL ajoutées: {alters}")
        except Exception as e:
            logger.error(f"Migration colonnes usage_history MySQL échouée: {e}")

    def _ensure_usage_history_columns_sqlite(self, conn):
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(usage_history)")
            cols = {row[1] for row in cur.fetchall()}
            if 'masked_text' not in cols:
                cur.execute("ALTER TABLE usage_history ADD COLUMN masked_text TEXT")
            if 'masked_token_count' not in cols:
                cur.execute("ALTER TABLE usage_history ADD COLUMN masked_token_count INTEGER DEFAULT 0")
            if 'model' not in cols:
                cur.execute("ALTER TABLE usage_history ADD COLUMN model VARCHAR(50)")
            if 'llm_mode' not in cols:
                cur.execute("ALTER TABLE usage_history ADD COLUMN llm_mode VARCHAR(20)")
            conn.commit()
        except Exception as e:
            logger.error(f"Migration colonnes usage_history SQLite échouée: {e}")
    
    def get_connection(self):
        """Retourne une connexion (sqlite ou mysql). Bascule sur SQLite si MySQL indisponible."""
        self.ensure_initialized()
        if self.engine == 'mysql':
            try:
                return pymysql.connect(
                    host=self.mysql_host,
                    port=self.mysql_port,
                    user=self.mysql_user,
                    password=self.mysql_password,
                    database=self.mysql_name,
                    charset='utf8mb4',
                    cursorclass=DictCursor,
                    autocommit=True
                )
            except Exception as e:
                # Fallback contrôlé par variable d'environnement (désactivé par défaut)
                allow_fallback = os.getenv('DB_SQLITE_FALLBACK', 'false').lower() in ('1','true','yes')
                logger.error(f"Connexion MySQL échouée ({e}) – fallbackSQLite={allow_fallback}")
                if not allow_fallback:
                    # Ne pas changer de moteur, laisser l'appelant réessayer
                    raise
                # Sinon, activer la bascule vers SQLite
                self.engine = 'sqlite'
                # S'assurer que la base SQLite est prête
                self.init_database()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =================== GESTION DES TYPES DE PROTECTION ===================
    
    def get_guard_types(self) -> List[Dict]:
        """Récupère tous les types de protection"""
        with self.get_connection() as conn:
            cursor = self._query(conn, """
                SELECT id, name, display_name, description, icon, color, is_active, created_at, updated_at
                FROM guard_types 
                WHERE is_active = 1
                ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_guard_type(self, guard_type_name: str) -> Optional[Dict]:
        """Récupère un type de protection spécifique"""
        with self.get_connection() as conn:
            cursor = self._query(conn, """
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
            # Idempotent: retourner l'ID si déjà existant
            try:
                cur_check = self._query(conn, "SELECT id FROM guard_types WHERE name = ? AND is_active = 1", (name,))
                row = cur_check.fetchone()
                if row:
                    return (row['id'] if isinstance(row, dict) else row[0])
            except Exception as e:
                logger.debug(f"create_guard_type: check exist failed (continuing to insert): {e}")

            logger.debug(f"create_guard_type: engine={self.engine} inserting name={name}")
            cursor = self._query(conn, """
                INSERT INTO guard_types (name, display_name, description, icon, color)
                VALUES (?, ?, ?, ?, ?)
            """, (name, display_name, description, icon, color))
            # Commit explicit pour MySQL si autocommit désactivé, no-op sinon
            try:
                conn.commit()
            except Exception as e:
                logger.debug(f"create_guard_type: commit hint (ignored) {e}")
            rid = cursor.lastrowid
            logger.debug(f"create_guard_type: inserted id={rid}")
            return rid
    
    def update_guard_type(self, guard_id: int, **kwargs) -> bool:
        """Met à jour un type de protection"""
        if not kwargs:
            return False
        
        # Construction dynamique de la requête UPDATE
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [guard_id]
        
        with self.get_connection() as conn:
            cursor = self._query(conn, f"""
                UPDATE guard_types 
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, tuple(values))
            try:
                conn.commit()
            except Exception:
                pass
            return cursor.rowcount > 0
    
    def delete_guard_type(self, guard_id: int) -> bool:
        """Supprime (désactive) un type de protection"""
        with self.get_connection() as conn:
            cursor = self._query(conn, """
                UPDATE guard_types 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (guard_id,))
            try:
                conn.commit()
            except Exception:
                pass
            return cursor.rowcount > 0

    # =================== GESTION DES CHAMPS PII ===================
    
    def get_pii_fields(self, guard_type_name: str) -> List[Dict]:
        """Récupère tous les champs PII d'un type de protection"""
        with self.get_connection() as conn:
            cursor = self._query(conn, """
                SELECT pf.id, pf.field_name, pf.display_name, pf.detection_type,
                       pf.example_value, pf.regex_pattern, pf.ner_entity_type,
                       pf.is_active,
                       rp.pattern as regex_pattern_value
                FROM pii_fields pf
                JOIN guard_types gt ON pf.guard_type_id = gt.id
                LEFT JOIN regex_patterns rp ON pf.regex_pattern = rp.name
                WHERE gt.name = ? AND pf.is_active = 1
                ORDER BY pf.field_name
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
                # Nettoyer anciennes clés si présentes
                field.pop('confidence_threshold', None)
                field.pop('priority', None)
                fields.append(field)
            
            return fields
    
    def create_pii_field(self, guard_type_name: str, field_name: str, 
                        display_name: str, detection_type: str, 
                        example_value: str = "", regex_pattern: str = None,
                        ner_entity_type: str = None) -> int:
        """Crée un nouveau champ PII"""
        
        # Récupérer l'ID du guard_type
        guard_type = self.get_guard_type(guard_type_name)
        if not guard_type:
            raise ValueError(f"Type de protection '{guard_type_name}' non trouvé")
        
        with self.get_connection() as conn:
            # Idempotent: si le champ existe déjà sur ce guard_type, retourner son ID
            try:
                cur_check = self._query(conn, "SELECT id FROM pii_fields WHERE guard_type_id = ? AND field_name = ? AND is_active = 1", (guard_type['id'], field_name))
                row = cur_check.fetchone()
                if row:
                    return (row['id'] if isinstance(row, dict) else row[0])
            except Exception as e:
                logger.debug(f"create_pii_field: check exist failed (continuing to insert): {e}")
            # Insérer sans colonnes confidence_threshold / priority (laisser valeurs par défaut si elles existent)
            try:
                cursor = self._query(conn, """
                    INSERT INTO pii_fields 
                    (guard_type_id, field_name, display_name, detection_type, 
                     example_value, regex_pattern, ner_entity_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (guard_type['id'], field_name, display_name, detection_type,
                      example_value, regex_pattern, ner_entity_type))
            except Exception:
                # Fallback si schéma exige encore les colonnes (legacy)
                cursor = self._query(conn, """
                    INSERT INTO pii_fields 
                    (guard_type_id, field_name, display_name, detection_type, 
                     example_value, regex_pattern, ner_entity_type, confidence_threshold, priority)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0.7, 1)
                """, (guard_type['id'], field_name, display_name, detection_type,
                      example_value, regex_pattern, ner_entity_type))
            try:
                conn.commit()
            except Exception as e:
                logger.debug(f"create_pii_field: commit hint (ignored) {e}")
            return cursor.lastrowid
    
    def update_pii_field(self, field_id: int, **kwargs) -> bool:
        """Met à jour un champ PII"""
        if not kwargs:
            return False
        
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [field_id]
        
        with self.get_connection() as conn:
            cursor = self._query(conn, f"""
                UPDATE pii_fields 
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, tuple(values))
            try:
                conn.commit()
            except Exception:
                pass
            return cursor.rowcount > 0
    
    def delete_pii_field(self, field_id: int) -> bool:
        """Supprime (désactive) un champ PII"""
        with self.get_connection() as conn:
            cursor = self._query(conn, """
                UPDATE pii_fields 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (field_id,))
            try:
                conn.commit()
            except Exception:
                pass
            return cursor.rowcount > 0

    # =================== GESTION DES PATTERNS REGEX ===================
    
    def get_regex_patterns(self) -> List[Dict]:
        """Récupère tous les patterns regex"""
        with self.get_connection() as conn:
            cursor = self._query(conn, """
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
            cursor = self._query(conn, """
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
            cursor = self._query(conn, """
                INSERT INTO regex_patterns 
                (name, display_name, pattern, description, test_examples, flags)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, display_name, pattern, description, test_examples_json, flags))
            try:
                conn.commit()
            except Exception:
                pass
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
            cursor = self._query(conn, f"""
                UPDATE regex_patterns 
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, tuple(values))
            try:
                conn.commit()
            except Exception:
                pass
            return cursor.rowcount > 0
    
    def delete_regex_pattern(self, pattern_id: int) -> bool:
        """Supprime (désactive) un pattern regex"""
        with self.get_connection() as conn:
            cursor = self._query(conn, """
                UPDATE regex_patterns 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (pattern_id,))
            try:
                conn.commit()
            except Exception:
                pass
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
            cursor = self._query(conn, query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    # =================== HISTORIQUE UTILISATION ===================
    def add_usage_history(self, guard_type: str, masked_text: str,
                          prompt_tokens: int, completion_tokens: int, masked_token_count: int = 0,
                          model: str | None = None, llm_mode: str | None = None) -> int:
        total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)
        try:
            with self.get_connection() as conn:
                try:
                    cursor = self._query(conn,
                        """INSERT INTO usage_history (guard_type, masked_text, prompt_tokens, completion_tokens, total_tokens, masked_token_count, model, llm_mode)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (guard_type, masked_text, prompt_tokens, completion_tokens, total_tokens, masked_token_count, model, llm_mode)
                    )
                except Exception as inner:
                    logger.debug(f"Insertion avec colonnes étendues échouée ({inner}), tentative version legacy")
                    cursor = self._query(conn,
                        """INSERT INTO usage_history (guard_type, masked_text, prompt_tokens, completion_tokens, total_tokens, masked_token_count)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                        (guard_type, masked_text, prompt_tokens, completion_tokens, total_tokens, masked_token_count)
                    )
                try:
                    conn.commit()
                except Exception:
                    pass
                return cursor.lastrowid
        except Exception as e:
            # Tentative migration à chaud puis retry une fois
            logger.warning(f"add_usage_history: tentative création table suite erreur: {e}")
            self.init_database()
            with self.get_connection() as conn:
                cursor = self._query(conn,
                    """INSERT INTO usage_history (guard_type, masked_text, prompt_tokens, completion_tokens, total_tokens, masked_token_count, model, llm_mode)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (guard_type, masked_text, prompt_tokens, completion_tokens, total_tokens, masked_token_count, model, llm_mode)
                )
                return cursor.lastrowid

    def list_usage_history(self, limit: int = 100) -> List[Dict]:
        try:
            logger.debug(f"list_usage_history(start) version={DB_MANAGER_VERSION} limit={limit}")
            self.ensure_initialized()
            with self.get_connection() as conn:
                # Determine existing columns
                cur = conn.cursor()
                if self.engine == 'mysql':
                    cur.execute("SHOW COLUMNS FROM usage_history")
                    fetched = cur.fetchall()
                    existing = { (row['Field'] if isinstance(row, dict) and 'Field' in row else row[0]) for row in fetched }
                else:
                    cur.execute("PRAGMA table_info(usage_history)")
                    fetched = cur.fetchall()
                    existing = { (row['name'] if isinstance(row, dict) and 'name' in row else row[1]) for row in fetched }
                logger.debug(f"usage_history existing columns={existing}")

                desired = ['id','created_at','guard_type','masked_text','prompt_tokens','completion_tokens','total_tokens','masked_token_count','model','llm_mode']
                present = [c for c in desired if c in existing]
                select_parts: List[str] = []
                for c in present:
                    if c in ('model','llm_mode'):
                        select_parts.append(f"COALESCE({c},'') as {c}")
                    else:
                        select_parts.append(c)
                if 'id' not in present:
                    raise RuntimeError("usage_history table missing 'id' column")
                select_sql = ", ".join(select_parts)
                sql = f"SELECT {select_sql} FROM usage_history ORDER BY id DESC LIMIT ?"
                logger.debug(f"usage_history select_sql={select_sql}")
                cursor = self._query(conn, sql, (limit,))
                raw_rows = cursor.fetchall()
                logger.debug(f"usage_history fetched_rows_count={len(raw_rows)}")
                rows: List[Dict[str, Any]] = []
                for row in raw_rows:
                    if isinstance(row, dict):
                        rows.append(row)
                    else:  # sqlite3.Row
                        rows.append(dict(row))
                for r in rows:
                    if 'total_tokens' in r and (r.get('total_tokens') in (None,0)):
                        pt = r.get('prompt_tokens') or 0
                        ct = r.get('completion_tokens') or 0
                        r['total_tokens'] = pt + ct
                    if 'masked_token_count' not in r:
                        import re
                        mt = r.get('masked_text') or ''
                        r['masked_token_count'] = len(re.findall(r"<[^:<>]+:TOKEN_[^>]+>", mt)) if mt else 0
                logger.debug("list_usage_history(success)")
                return rows
        except Exception as e:
            logger.exception(f"list_usage_history: erreur {e} (tentative migration & debug)")
            self.init_database()
            with self.get_connection() as conn:
                # Retry once with dynamic columns
                cur = conn.cursor()
                if self.engine == 'mysql':
                    cur.execute("SHOW COLUMNS FROM usage_history")
                    existing = {r[0] for r in cur.fetchall()}
                else:
                    cur.execute("PRAGMA table_info(usage_history)")
                    existing = {r[1] for r in cur.fetchall()}
                base_cols = ['id','created_at','guard_type','masked_text','prompt_tokens','completion_tokens','total_tokens']
                present = [c for c in base_cols if c in existing]
                select_sql = ", ".join(present)
                sql = f"SELECT {select_sql} FROM usage_history ORDER BY id DESC LIMIT ?"
                cursor = self._query(conn, sql, (limit,))
                rows = [dict(row) for row in cursor.fetchall()]
                for r in rows:
                    if 'total_tokens' in r and (r.get('total_tokens') in (None,0)):
                        pt = r.get('prompt_tokens') or 0
                        ct = r.get('completion_tokens') or 0
                        r['total_tokens'] = pt + ct
                return rows

    def debug_usage_history_columns(self) -> Dict[str, any]:
        """Return current columns of usage_history and sample row for debugging."""
        info: Dict[str, any] = {"engine": self.engine}
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                if self.engine == 'mysql':
                    cur.execute("SHOW COLUMNS FROM usage_history")
                    fetched = cur.fetchall()
                    cols = [ (r['Field'] if isinstance(r, dict) and 'Field' in r else r[0]) for r in fetched ]
                else:
                    cur.execute("PRAGMA table_info(usage_history)")
                    cols = [r[1] for r in cur.fetchall()]
                info['columns'] = cols
                cur2 = self._query(conn, "SELECT * FROM usage_history ORDER BY id DESC LIMIT 1")
                row = cur2.fetchone()
                info['last_row'] = dict(row) if row else None
        except Exception as e:
            info['error'] = str(e)
        return info

    # =================== BACKFILL / MIGRATION DONNÉES ===================
    def backfill_usage_history(self, model: str, recompute_prompt: bool = True) -> Dict[str, Any]:
        """Met à jour les anciennes lignes sans model/llm_mode.
        - Assigne model
        - Définit llm_mode='legacy_filled' si absent
        - Recalcule prompt_tokens (approx) à partir de masked_text si demandé et valeur existante <= 0
        Retourne stats: updated_rows, recomputed_prompt_tokens.
        """
        updated = 0
        recomputed = 0
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                # Récupérer lignes à mettre à jour
                cur.execute("SELECT id, masked_text, prompt_tokens FROM usage_history WHERE (model IS NULL OR model='')")
                rows = cur.fetchall()
                for row in rows:
                    rid = row[0] if not isinstance(row, sqlite3.Row) else row['id']
                    masked_text = row[1] if not isinstance(row, sqlite3.Row) else row['masked_text']
                    prompt_tokens = row[2] if not isinstance(row, sqlite3.Row) else row['prompt_tokens']
                    new_prompt = prompt_tokens
                    if recompute_prompt and (prompt_tokens is None or prompt_tokens <= 0) and masked_text:
                        # Approximation simple: mots * 1.1
                        words = len(masked_text.split())
                        new_prompt = max(1, int(words * 1.1))
                        recomputed += 1
                    cur.execute("UPDATE usage_history SET model = ?, llm_mode = COALESCE(llm_mode,'legacy_filled'), prompt_tokens = ? WHERE id = ?", (model, new_prompt, rid))
                    updated += 1
                conn.commit()
        except Exception as e:
            logger.error(f"backfill_usage_history échec: {e}")
            return {"success": False, "error": str(e), "updated_rows": updated, "recomputed_prompt_tokens": recomputed}
        return {"success": True, "updated_rows": updated, "recomputed_prompt_tokens": recomputed}

    def get_usage_entry(self, entry_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = self._query(conn, """
                SELECT * FROM usage_history WHERE id = ?
            """, (entry_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

# Instance globale
db_manager = DatabaseManager()

from typing import List, Dict
import json
import logging
from .database.db_manager import db_manager
import os
try:
    import pymysql  # type: ignore
except Exception:  # safe import guard
    pymysql = None

logger = logging.getLogger(__name__)

DEFAULT_GUARDS = [
    {
        "name": "InfoPerso",
        "display_name": "Données de Contact",
        "description": "Informations de contact et localisation",
        "icon": "📍",
        "color": "#3498db",
        "fields": [
            {"field_name": "email", "display_name": "Adresse e-mail", "type": "regex", "pattern": "email"},
            {"field_name": "phone", "display_name": "Téléphone", "type": "regex", "pattern": "french_phone"},
            {"field_name": "address", "display_name": "Adresse postale", "type": "ner", "ner_entity_type": "LOCATION"},
            {"field_name": "company", "display_name": "Entreprise", "type": "ner", "ner_entity_type": "ORGANIZATION"},
            {"field_name": "ip_address", "display_name": "Adresse IP", "type": "regex", "pattern": "ip_address"},
        ]
    },
    {
        "name": "TypeA",
        "display_name": "Données Personnelles Identifiantes",
        "description": "Identité personnelle",
        "icon": "🆔",
        "color": "#e74c3c",
        "fields": [
            {"field_name": "name", "display_name": "Nom & Prénom", "type": "ner", "ner_entity_type": "PERSON"},
            {"field_name": "birth_date", "display_name": "Date de naissance", "type": "regex", "pattern": "date_generic"},
            {"field_name": "social_security", "display_name": "N° Sécurité Sociale (FR)", "type": "regex", "pattern": "fr_nir"},
            {"field_name": "passport", "display_name": "Passeport", "type": "regex", "pattern": "passport_generic"},
            {"field_name": "driver_license", "display_name": "Permis de conduire", "type": "regex", "pattern": "driver_license_generic"},
        ]
    },
    {
        "name": "TypeB",
        "display_name": "Données Financières",
        "description": "Informations bancaires et paiement",
        "icon": "💳",
        "color": "#f39c12",
        "fields": [
            {"field_name": "credit_card", "display_name": "Carte bancaire", "type": "regex", "pattern": "credit_card"},
            {"field_name": "expiry_date", "display_name": "Date d'expiration", "type": "regex", "pattern": "expiry_mm_yy"},
            {"field_name": "cvv", "display_name": "Code de sécurité (CVV)", "type": "regex", "pattern": "cvv_3_4"},
            {"field_name": "iban", "display_name": "IBAN", "type": "regex", "pattern": "iban"},
            {"field_name": "account_number", "display_name": "N° de compte", "type": "regex", "pattern": "account_number_generic"},
        ]
    }
]

# Minimal patterns to seed if absent
DEFAULT_PATTERNS = [
    ("email", "E-mail", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "Adresse e-mail standard", ["john.doe@mail.com"], "i"),
    ("french_phone", "Téléphone FR", r"(?:\+33\s?|0)[1-9](?:[ .-]?\d{2}){4}", "Numéro FR divers formats", ["+33 6 12 34 56 78"], ""),
    ("ip_address", "Adresse IP", r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b", "IPv4", ["192.168.1.10"], ""),
    ("date_generic", "Date (générique)", r"\b(?:\d{4}[-/]\d{2}[-/]\d{2}|\d{2}/\d{2}/\d{4})\b", "aaaa-mm-jj ou jj/mm/aaaa", ["1990-07-12"], ""),
    ("fr_nir", "NIR France", r"\b[12]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b", "Sécurité sociale FR", ["1 94 02 75 123 456 19"], ""),
    ("passport_generic", "Passeport (générique)", r"\b[A-Z]{2}\d{7}\b", "Passeport simplifié", ["FR1234567"], ""),
    ("driver_license_generic", "Permis (générique)", r"\b[0-9A-Z]{12,16}\b", "Permis format large", ["AB123456789012"], "i"),
    ("credit_card", "Carte bancaire", r"\b(?:\d[ -]*?){13,19}\b", "Numéro carte (brut)", ["4532 9876 1122 4456"], ""),
    ("expiry_mm_yy", "Expiration MM/YY", r"\b(0[1-9]|1[0-2])\/(\d{2})\b", "Date expiration carte", ["08/27"], ""),
    ("cvv_3_4", "CVV 3-4", r"\b\d{3,4}\b", "Code sécurité carte", ["381"], ""),
    ("iban", "IBAN (UE)", r"\b[A-Z]{2}[0-9A-Z]{13,30}\b", "IBAN compact", ["FR7630006000011234567890189"], ""),
    ("account_number_generic", "Compte (générique)", r"\b\d{8,16}\b", "Numéro de compte simple", ["0123456789"], ""),
]

# Minimal NER entity types to seed if absent (aligned with entity_mapping canonical labels)
DEFAULT_NER_TYPES = [
    # model_name, entity_type, display_name, description
    ("presidio", "EMAIL_ADDRESS", "Email", "Adresse e-mail"),
    ("presidio", "PHONE_NUMBER", "Téléphone", "Numéro de téléphone"),
    ("presidio", "CREDIT_CARD", "Carte bancaire", "Numéro de carte de paiement"),
    ("presidio", "PERSON", "Personne", "Nom de personne"),
    ("presidio", "LOCATION", "Localisation", "Adresse / lieu"),
    ("presidio", "ORGANIZATION", "Organisation", "Entreprise / organisme"),
    ("presidio", "IP_ADDRESS", "Adresse IP", "Adresse IPv4/IPv6"),
    ("presidio", "IBAN", "IBAN", "Identifiant bancaire international"),
    ("presidio", "URL", "URL", "Adresse de site web"),
    ("presidio", "DATE_TIME", "Date/Heure", "Dates et expressions temporelles"),
]


def seed_defaults() -> dict:
    try:
        added_patterns: list[str] = []
        created_guards: list[str] = []
        created_fields = 0

        # Prefer direct MySQL seeding when requested and PyMySQL is available
        if os.getenv('DB_ENGINE', 'sqlite').lower() == 'mysql' and pymysql is not None:
            host = os.getenv('DB_HOST', 'mysql')
            port = int(os.getenv('DB_PORT', '3306'))
            user = os.getenv('DB_USER', 'root')
            pwd = os.getenv('DB_PASSWORD', '')
            db = os.getenv('DB_NAME', 'ai_guards')
            try:
                conn = pymysql.connect(host=host, port=port, user=user, password=pwd, database=db, charset='utf8mb4')
                with conn:
                    with conn.cursor() as cur:
                        # Seed guard_types idempotently
                        for g in DEFAULT_GUARDS:
                            cur.execute(
                                "INSERT IGNORE INTO guard_types (name, display_name, description, icon, color) VALUES (%s,%s,%s,%s,%s)",
                                (g['name'], g['display_name'], g['description'], g['icon'], g['color'])
                            )
                        conn.commit()
                        cur.execute(
                            "SELECT name FROM guard_types WHERE name IN (%s,%s,%s)",
                            (DEFAULT_GUARDS[0]['name'], DEFAULT_GUARDS[1]['name'], DEFAULT_GUARDS[2]['name'])
                        )
                        present = {row[0] for row in cur.fetchall()}
                        for g in DEFAULT_GUARDS:
                            if g['name'] in present:
                                created_guards.append(g['name'])
                        # Seed regex_patterns (idempotent)
                        for name, display, patt, desc, examples, flags in DEFAULT_PATTERNS:
                            cur.execute(
                                "INSERT IGNORE INTO regex_patterns (name, display_name, pattern, description, test_examples, flags) VALUES (%s,%s,%s,%s,%s,%s)",
                                (name, display, patt, desc, json.dumps(examples or []), flags)
                            )
                        conn.commit()
                        # Report which patterns are present now
                        placeholders = ",".join(["%s"] * len(DEFAULT_PATTERNS))
                        cur.execute(
                            f"SELECT name FROM regex_patterns WHERE name IN ({placeholders})",
                            tuple(n for (n, *_rest) in DEFAULT_PATTERNS)
                        )
                        added_patterns = [row[0] for row in cur.fetchall()]
                        # Seed default PII fields for each guard
                        name_to_id = {}
                        cur.execute(
                            "SELECT id,name FROM guard_types WHERE name IN (%s,%s,%s)",
                            (DEFAULT_GUARDS[0]['name'], DEFAULT_GUARDS[1]['name'], DEFAULT_GUARDS[2]['name'])
                        )
                        for rid, nm in cur.fetchall():
                            name_to_id[nm] = rid
                        for g in DEFAULT_GUARDS:
                            gid = name_to_id.get(g['name'])
                            if not gid:
                                continue
                            for f in g['fields']:
                                cur.execute(
                                    "INSERT IGNORE INTO pii_fields (guard_type_id, field_name, display_name, detection_type, example_value, regex_pattern, ner_entity_type) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                                    (gid, f['field_name'], f['display_name'], f['type'], f.get('example', ''), f.get('pattern'), f.get('ner_entity_type'))
                                )
                        conn.commit()
                        # Seed NER entity types (idempotent)
                        try:
                            for model_name, entity_type, display_name, description in DEFAULT_NER_TYPES:
                                cur.execute(
                                    "INSERT IGNORE INTO ner_entity_types (model_name, entity_type, display_name, description, is_active) VALUES (%s, %s, %s, %s, 1)",
                                    (model_name, entity_type, display_name, description)
                                )
                            conn.commit()
                        except Exception as ner_e:
                            logger.warning(f"Seed NER MySQL ignoré: {ner_e}")
            except Exception as e:
                logger.warning(f"Seed MySQL direct a échoué ({e}), bascule via db_manager")
                # Fallback to db_manager flow below
            else:
                # If we seeded via MySQL directly and db_manager is not on MySQL in this process, skip fields to avoid writing to SQLite
                if getattr(db_manager, 'engine', 'sqlite') != 'mysql':
                    return {"success": True, "patterns_added": added_patterns, "guards_created": sorted(set(created_guards)), "fields_created": 0}

        # Generic path via db_manager (SQLite or MySQL if available in-process)
        existing_patterns = {p['name'] for p in db_manager.get_regex_patterns()}
        for name, display, patt, desc, examples, flags in DEFAULT_PATTERNS:
            if name not in existing_patterns:
                db_manager.create_regex_pattern(name, display, patt, desc, examples, flags)
                added_patterns.append(name)

        existing_guards = {g['name'] for g in db_manager.get_guard_types()}
        for g in DEFAULT_GUARDS:
            if g['name'] not in existing_guards:
                db_manager.create_guard_type(g['name'], g['display_name'], g['description'], g['icon'], g['color'])
                created_guards.append(g['name'])
            # Ensure fields
            for f in g['fields']:
                try:
                    db_manager.create_pii_field(
                        guard_type_name=g['name'],
                        field_name=f['field_name'],
                        display_name=f['display_name'],
                        detection_type=f['type'],
                        example_value=f.get('example', ''),
                        regex_pattern=f.get('pattern'),
                        ner_entity_type=f.get('ner_entity_type')
                    )
                    created_fields += 1
                except Exception:
                    continue

        # Seed NER entity types via a direct connection if table exists
        try:
            with db_manager.get_connection() as conn:
                cur = conn.cursor()
                # Detect table presence
                has_table = False
                try:
                    if getattr(db_manager, 'engine', 'sqlite') == 'mysql':
                        cur.execute("SHOW TABLES LIKE 'ner_entity_types'")
                        has_table = (cur.fetchone() is not None)
                    else:
                        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ner_entity_types'")
                        has_table = (cur.fetchone() is not None)
                except Exception:
                    has_table = False
                if has_table:
                    for model_name, entity_type, display_name, description in DEFAULT_NER_TYPES:
                        try:
                            if getattr(db_manager, 'engine', 'sqlite') == 'mysql':
                                cur.execute(
                                    "INSERT IGNORE INTO ner_entity_types (model_name, entity_type, display_name, description, is_active) VALUES (%s,%s,%s,%s,1)",
                                    (model_name, entity_type, display_name, description)
                                )
                            else:
                                # SQLite doesn't support INSERT IGNORE; emulate idempotency
                                cur.execute(
                                    "SELECT 1 FROM ner_entity_types WHERE model_name = ? AND entity_type = ?",
                                    (model_name, entity_type)
                                )
                                if cur.fetchone() is None:
                                    cur.execute(
                                        "INSERT INTO ner_entity_types (model_name, entity_type, display_name, description, is_active) VALUES (?,?,?,?,1)",
                                        (model_name, entity_type, display_name, description)
                                    )
                        except Exception:
                            # Continue with others
                            pass
                    try:
                        conn.commit()
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Seeding NER types (fallback) ignoré: {e}")

        return {"success": True, "patterns_added": added_patterns, "guards_created": created_guards, "fields_created": created_fields}
    except Exception as e:
        logger.error(f"Seeding défauts échoué: {e}")
        return {"success": False, "error": str(e)}

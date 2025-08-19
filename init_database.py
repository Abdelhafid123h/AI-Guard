import sqlite3
import json
import os
from pathlib import Path
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialise la base de données AI-Guards avec le schéma complet"""
    
    # Chemin vers la base de données
    db_path = Path("backend/app/database/ai_guards.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Connexion à la base de données
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Création des tables
        cursor.executescript('''
        -- Table des types de protection (Guards)
        CREATE TABLE IF NOT EXISTS guard_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) UNIQUE NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            description TEXT,
            icon VARCHAR(10),
            color VARCHAR(7),
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Table des champs PII configurables
        CREATE TABLE IF NOT EXISTS pii_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guard_type_id INTEGER NOT NULL,
            field_name VARCHAR(50) NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            detection_type VARCHAR(20) NOT NULL CHECK (detection_type IN ('regex', 'ner', 'hybrid')),
            example_value TEXT,
            regex_pattern TEXT,
            ner_entity_type VARCHAR(50),
            confidence_threshold FLOAT DEFAULT 0.7,
            is_active BOOLEAN DEFAULT 1,
            priority INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (guard_type_id) REFERENCES guard_types (id) ON DELETE CASCADE,
            UNIQUE(guard_type_id, field_name)
        );

        -- Table des patterns regex réutilisables
        CREATE TABLE IF NOT EXISTS regex_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) UNIQUE NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            pattern TEXT NOT NULL,
            description TEXT,
            test_examples TEXT,
            flags VARCHAR(20) DEFAULT 'i',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Table des types d'entités NER disponibles
        CREATE TABLE IF NOT EXISTS ner_entity_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name VARCHAR(50) NOT NULL,
            entity_type VARCHAR(50) NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT 1,
            UNIQUE(model_name, entity_type)
        );
        ''')
        
        # Insertion des données initiales
        logger.info("Insertion des types de protection initiaux...")
        
        # Types de protection par défaut
        guard_types_data = [
            ('TypeA', '🆔 Données Personnelles Identifiantes', 'Protection des informations d\'identité personnelle', '🆔', '#e74c3c'),
            ('TypeB', '💳 Données Financières', 'Protection des informations bancaires et financières', '💳', '#f39c12'),
            ('InfoPerso', '📍 Données de Contact', 'Protection des informations de contact et localisation', '📍', '#3498db')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO guard_types (name, display_name, description, icon, color)
            VALUES (?, ?, ?, ?, ?)
        ''', guard_types_data)
        
        # Patterns regex par défaut
        logger.info("Insertion des patterns regex...")
        
        regex_patterns_data = [
            ('french_phone', 'Téléphone Français', r'(\+33|0)[1-9](?:[0-9]{8})', 
             'Numéros de téléphone français', '["06 12 34 56 78", "+33 6 12 34 56 78", "01.23.45.67.89"]', 'i'),
            ('email_standard', 'Email Standard', r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', 
             'Adresses email standard', '["test@example.com", "user.name@domain.fr"]', 'i'),
            ('french_social_security', 'Numéro Sécurité Sociale', r'\d{1}\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}', 
             'Numéro de sécurité sociale français', '["1 85 03 75 123 456 78", "185037512345678"]', ''),
            ('credit_card', 'Carte Bancaire', r'\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}', 
             'Numéros de carte bancaire', '["1234 5678 9012 3456", "1234-5678-9012-3456"]', ''),
            ('french_iban', 'IBAN Français', r'FR\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{3}', 
             'IBAN français', '["FR14 2004 1010 0505 0001 3M02 606"]', 'i'),
            ('french_date', 'Date Française', r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4}', 
             'Dates au format français', '["15/03/1985", "15-03-1985", "15.03.1985"]', ''),
            ('french_postal_code', 'Code Postal', r'\d{5}', 
             'Code postal français', '["75001", "69000", "13000"]', '')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO regex_patterns (name, display_name, pattern, description, test_examples, flags)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', regex_patterns_data)
        
        # Types d'entités NER
        logger.info("Insertion des types d'entités NER...")
        
        ner_types_data = [
            ('spacy', 'PERSON', 'Personne', 'Noms de personnes détectés par spaCy'),
            ('spacy', 'GPE', 'Entité Géopolitique', 'Pays, villes, régions'),
            ('spacy', 'ORG', 'Organisation', 'Entreprises, institutions'),
            ('spacy', 'DATE', 'Date', 'Dates et expressions temporelles'),
            ('spacy', 'MONEY', 'Montant', 'Montants monétaires'),
            ('bert', 'PER', 'Personne', 'Noms de personnes détectés par BERT'),
            ('bert', 'LOC', 'Lieu', 'Lieux géographiques'),
            ('bert', 'ORG', 'Organisation', 'Organisations et entreprises'),
            ('camembert', 'PER', 'Personne', 'Noms de personnes détectés par CamemBERT'),
            ('camembert', 'LOC', 'Lieu', 'Lieux géographiques'),
            ('camembert', 'ORG', 'Organisation', 'Organisations et entreprises'),
            ('presidio', 'PERSON', 'Personne', 'Noms de personnes détectés par Presidio'),
            ('presidio', 'EMAIL_ADDRESS', 'Email', 'Adresses email'),
            ('presidio', 'PHONE_NUMBER', 'Téléphone', 'Numéros de téléphone'),
            ('presidio', 'CREDIT_CARD', 'Carte Bancaire', 'Numéros de carte bancaire')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO ner_entity_types (model_name, entity_type, display_name, description)
            VALUES (?, ?, ?, ?)
        ''', ner_types_data)
        
        # Configuration des champs PII par défaut
        logger.info("Configuration des champs PII...")
        
        # Récupération des IDs des guard_types
        cursor.execute("SELECT id, name FROM guard_types")
        guard_type_ids = {name: id for id, name in cursor.fetchall()}
        
        # Champs TypeA - Données Personnelles Identifiantes
        typea_fields = [
            (guard_type_ids['TypeA'], 'name', 'Nom Complet', 'hybrid', 'Jean Dupont', None, 'PERSON', 0.7, 1),
            (guard_type_ids['TypeA'], 'firstname', 'Prénom', 'ner', 'Jean', None, 'PERSON', 0.7, 2),
            (guard_type_ids['TypeA'], 'birth_date', 'Date de Naissance', 'regex', '15/03/1985', 'french_date', None, 0.8, 3),
            (guard_type_ids['TypeA'], 'social_security', 'Numéro Sécurité Sociale', 'regex', '1 85 03 75 123 456 78', 'french_social_security', None, 0.9, 4),
            (guard_type_ids['TypeA'], 'id_card', 'Carte d\'Identité', 'regex', 'CNI 123456789', '[A-Z]{2,3}\\s?\\d{6,9}', None, 0.8, 5),
            (guard_type_ids['TypeA'], 'passport', 'Passeport', 'regex', '18FR12345', '\\d{2}[A-Z]{2}\\d{5}', None, 0.8, 6),
            (guard_type_ids['TypeA'], 'driving_license', 'Permis de Conduire', 'regex', '123456789ABC', '\\d{9,12}[A-Z]*', None, 0.8, 7)
        ]
        
        # Champs TypeB - Données Financières
        typeb_fields = [
            (guard_type_ids['TypeB'], 'credit_card', 'Carte Bancaire', 'regex', '5555 5555 5555 4444', 'credit_card', None, 0.9, 1),
            (guard_type_ids['TypeB'], 'iban', 'IBAN', 'regex', 'FR14 2004 1010 0505 0001 3M02 606', 'french_iban', None, 0.9, 2),
            (guard_type_ids['TypeB'], 'bank_account', 'Compte Bancaire', 'regex', '20041 01005 05000013M02 60', '\\d{5}\\s?\\d{5}\\s?\\d{11}\\s?\\d{2,3}', None, 0.8, 3),
            (guard_type_ids['TypeB'], 'cvv', 'Code Sécurité', 'regex', '123', '\\d{3,4}', None, 0.9, 4)
        ]
        
        # Champs InfoPerso - Données de Contact
        infoperso_fields = [
            (guard_type_ids['InfoPerso'], 'email', 'Email', 'regex', 'contact@example.com', 'email_standard', None, 0.9, 1),
            (guard_type_ids['InfoPerso'], 'phone', 'Téléphone', 'regex', '+33 6 12 34 56 78', 'french_phone', None, 0.8, 2),
            (guard_type_ids['InfoPerso'], 'address', 'Adresse', 'ner', '123 Rue de la République', None, 'LOC', 0.7, 3),
            (guard_type_ids['InfoPerso'], 'postal_code', 'Code Postal', 'regex', '75001', 'french_postal_code', None, 0.8, 4),
            (guard_type_ids['InfoPerso'], 'company', 'Entreprise', 'ner', 'TechCorp SARL', None, 'ORG', 0.7, 5),
            (guard_type_ids['InfoPerso'], 'ip_address', 'Adresse IP', 'regex', '192.168.1.1', '\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}', None, 0.8, 6)
        ]
        
        all_fields = typea_fields + typeb_fields + infoperso_fields
        
        cursor.executemany('''
            INSERT OR IGNORE INTO pii_fields 
            (guard_type_id, field_name, display_name, detection_type, example_value, regex_pattern, ner_entity_type, confidence_threshold, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', all_fields)
        
        # Valider les changements
        conn.commit()
        logger.info(f"✅ Base de données initialisée avec succès : {db_path}")
        
        # Afficher un résumé
        cursor.execute("SELECT COUNT(*) FROM guard_types")
        guard_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM pii_fields")
        field_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM regex_patterns")
        pattern_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ner_entity_types")
        ner_count = cursor.fetchone()[0]
        
        logger.info(f"📊 Résumé de la base de données:")
        logger.info(f"   - {guard_count} types de protection")
        logger.info(f"   - {field_count} champs PII configurés")
        logger.info(f"   - {pattern_count} patterns regex")
        logger.info(f"   - {ner_count} types d'entités NER")
        
        # Affichage détaillé des configurations
        logger.info("\n📋 Configuration des types de protection:")
        for guard_name in ['TypeA', 'TypeB', 'InfoPerso']:
            cursor.execute('''
                SELECT COUNT(*) FROM pii_fields pf
                JOIN guard_types gt ON pf.guard_type_id = gt.id
                WHERE gt.name = ?
            ''', (guard_name,))
            field_count = cursor.fetchone()[0]
            cursor.execute('SELECT display_name FROM guard_types WHERE name = ?', (guard_name,))
            display_name = cursor.fetchone()[0]
            logger.info(f"   • {guard_name} ({display_name}): {field_count} champs")
        
        logger.info("\n🎯 Le système est maintenant configuré avec:")
        logger.info("   • Configuration dynamique complète")
        logger.info("   • Support du format: \"phone\":{\"type\":\"regex\",\"exemple\":\"+33 6 45 67 89 12\",\"pattern\":...}")
        logger.info("   • API CRUD pour gérer les types et champs")
        logger.info("   • Interface utilisateur pour ajouter/modifier des attributs")
        
        logger.info("\n🚀 Pour démarrer le système:")
        logger.info("   1. Backend: cd backend && uvicorn app.main:app --reload")
        logger.info("   2. Frontend: cd frontend && npm start")
        logger.info("   3. Configuration: http://localhost:8000/docs (API) ou http://localhost:3000")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation : {e}")
        raise
    
    finally:
        if conn:
            conn.close()

def show_database_content():
    """Affiche le contenu de la base de données pour vérification"""
    db_path = Path("backend/app/database/ai_guards.db")
    
    if not db_path.exists():
        logger.error("❌ Base de données non trouvée. Exécutez d'abord init_database()")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n" + "="*60)
        print("📋 CONTENU DE LA BASE DE DONNÉES AI-GUARDS")
        print("="*60)
        
        # Guard Types
        cursor.execute("SELECT * FROM guard_types")
        guard_types = cursor.fetchall()
        print(f"\n🔰 TYPES DE PROTECTION ({len(guard_types)}):")
        for gt in guard_types:
            print(f"   {gt[1]} - {gt[2]} {gt[4]}")
        
        # PII Fields par type
        for guard_type in ['TypeA', 'TypeB', 'InfoPerso']:
            cursor.execute('''
                SELECT pf.field_name, pf.display_name, pf.detection_type, pf.example_value, 
                       pf.regex_pattern, pf.ner_entity_type, pf.confidence_threshold
                FROM pii_fields pf
                JOIN guard_types gt ON pf.guard_type_id = gt.id
                WHERE gt.name = ?
                ORDER BY pf.priority
            ''', (guard_type,))
            fields = cursor.fetchall()
            
            cursor.execute('SELECT display_name, icon FROM guard_types WHERE name = ?', (guard_type,))
            display_info = cursor.fetchone()
            
            print(f"\n{display_info[1]} {guard_type.upper()} - {display_info[0]} ({len(fields)} champs):")
            for field in fields:
                field_name, display_name, det_type, example, regex_pattern, ner_type, confidence = field
                print(f"   • {field_name}:")
                print(f"     - Nom: {display_name}")
                print(f"     - Type: {det_type}")
                print(f"     - Exemple: {example}")
                if regex_pattern:
                    print(f"     - Pattern: {regex_pattern}")
                if ner_type:
                    print(f"     - Entité NER: {ner_type}")
                print(f"     - Confiance: {confidence}")
        
        # Patterns Regex
        cursor.execute("SELECT name, display_name, pattern, description FROM regex_patterns")
        patterns = cursor.fetchall()
        print(f"\n🔤 PATTERNS REGEX ({len(patterns)}):")
        for pattern in patterns:
            print(f"   • {pattern[0]} ({pattern[1]})")
            print(f"     Pattern: {pattern[2]}")
            print(f"     Description: {pattern[3]}")
        
        print("\n" + "="*60)
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la lecture : {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Initialisation de la base de données AI-Guards...")
    
    # Initialiser la base de données
    success = init_database()
    
    if success:
        print("\n✅ Initialisation réussie!")
        
        # Afficher le contenu pour vérification
        show_database_content()
        
        # Instructions finales
        print("\n" + "="*60)
        print("🎯 SYSTÈME DYNAMIQUE CONFIGURÉ")
        print("="*60)
        print("\nVotre système AI-Guards est maintenant entièrement dynamique!")
        print("\n📌 Fonctionnalités disponibles:")
        print("   • Ajouter des attributs dans des types existants")
        print("   • Créer de nouveaux types de protection")
        print("   • Modifier les patterns et configurations")
        print("   • Format exact supporté: \"phone\":{\"type\":\"regex\",\"exemple\":\"+33 6 12 34 56 78\",\"pattern\":...}")
        
        print("\n🔧 API disponibles:")
        print("   • GET /api/config/guard-types - Liste tous les types")
        print("   • POST /api/config/guard-types - Créer nouveau type")
        print("   • POST /api/config/pii-fields - Ajouter nouveau champ")
        print("   • GET /api/config/pii-fields/{guard_type} - Champs d'un type")
        
        print("\n🌐 Pour démarrer:")
        print("   1. cd backend && uvicorn app.main:app --reload")
        print("   2. cd frontend && npm start")
        print("   3. Ouvrir http://localhost:3000 pour l'interface")
        print("   4. API documentation: http://localhost:8000/docs")

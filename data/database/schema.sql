-- Schéma de base de données pour AI-Guards
-- Configuration dynamique des types de protection

-- Table des types de protection (Guards)
CREATE TABLE guard_types (
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
CREATE TABLE pii_fields (
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
CREATE TABLE regex_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    pattern TEXT NOT NULL,
    description TEXT,
    test_examples TEXT, -- JSON array d'exemples de test
    flags VARCHAR(20) DEFAULT 'i', -- Flags regex (i=ignorecase, m=multiline, etc.)
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des types d'entités NER disponibles
CREATE TABLE ner_entity_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name VARCHAR(50) NOT NULL, -- spacy, bert, camembert, presidio
    entity_type VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    UNIQUE(model_name, entity_type)
);

-- Données initiales
INSERT INTO guard_types (name, display_name, description, icon, color) VALUES
('TypeA', '🆔 Données Personnelles Identifiantes', 'Protection des informations d''identité personnelle', '🆔', '#e74c3c'),
('TypeB', '💳 Données Financières', 'Protection des informations bancaires et financières', '💳', '#f39c12'),
('InfoPerso', '📍 Données de Contact', 'Protection des informations de contact et localisation', '📍', '#3498db');

-- Patterns regex initiaux
INSERT INTO regex_patterns (name, display_name, pattern, description, test_examples) VALUES
('french_phone', 'Téléphone Français', '(\+33|0)[1-9](?:[0-9]{8})', 'Numéros de téléphone français', '["06 12 34 56 78", "+33 6 12 34 56 78", "01.23.45.67.89"]'),
('email_standard', 'Email Standard', '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', 'Adresses email standard', '["test@example.com", "user.name@domain.fr"]'),
('french_social_security', 'Numéro Sécurité Sociale', '\d{1}\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}', 'Numéro de sécurité sociale français', '["1 85 03 75 123 456 78", "185037512345678"]'),
('credit_card', 'Carte Bancaire', '\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}', 'Numéros de carte bancaire', '["1234 5678 9012 3456", "1234-5678-9012-3456"]'),
('french_iban', 'IBAN Français', 'FR\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{3}', 'IBAN français', '["FR14 2004 1010 0505 0001 3M02 606"]'),
('french_date', 'Date Française', '\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4}', 'Dates au format français', '["15/03/1985", "15-03-1985", "15.03.1985"]'),
('french_postal_code', 'Code Postal', '\d{5}', 'Code postal français', '["75001", "69000", "13000"]');

-- Types d'entités NER
INSERT INTO ner_entity_types (model_name, entity_type, display_name, description) VALUES
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
('presidio', 'CREDIT_CARD', 'Carte Bancaire', 'Numéros de carte bancaire');

-- Configuration initiale TypeA
INSERT INTO pii_fields (guard_type_id, field_name, display_name, detection_type, example_value, regex_pattern, ner_entity_type, priority) VALUES
(1, 'name', 'Nom Complet', 'hybrid', 'Jean Dupont', NULL, 'PERSON', 1),
(1, 'firstname', 'Prénom', 'ner', 'Jean', NULL, 'PERSON', 2),
(1, 'birth_date', 'Date de Naissance', 'regex', '15/03/1985', 'french_date', NULL, 3),
(1, 'social_security', 'Numéro Sécurité Sociale', 'regex', '1 85 03 75 123 456 78', 'french_social_security', NULL, 4),
(1, 'id_card', 'Carte d''Identité', 'regex', 'CNI 123456789', '[A-Z]{2,3}\s?\d{6,9}', NULL, 5),
(1, 'passport', 'Passeport', 'regex', '18FR12345', '\d{2}[A-Z]{2}\d{5}', NULL, 6),
(1, 'driving_license', 'Permis de Conduire', 'regex', '123456789ABC', '\d{9,12}[A-Z]*', NULL, 7);

-- Configuration initiale TypeB
INSERT INTO pii_fields (guard_type_id, field_name, display_name, detection_type, example_value, regex_pattern, ner_entity_type, priority) VALUES
(2, 'credit_card', 'Carte Bancaire', 'regex', '5555 5555 5555 4444', 'credit_card', NULL, 1),
(2, 'iban', 'IBAN', 'regex', 'FR14 2004 1010 0505 0001 3M02 606', 'french_iban', NULL, 2),
(2, 'bank_account', 'Compte Bancaire', 'regex', '20041 01005 05000013M02 60', '\d{5}\s?\d{5}\s?\d{11}\s?\d{2,3}', NULL, 3),
(2, 'cvv', 'Code Sécurité', 'regex', '123', '\d{3,4}', NULL, 4);

-- Configuration initiale InfoPerso
INSERT INTO pii_fields (guard_type_id, field_name, display_name, detection_type, example_value, regex_pattern, ner_entity_type, priority) VALUES
(3, 'email', 'Email', 'regex', 'contact@example.com', 'email_standard', NULL, 1),
(3, 'phone', 'Téléphone', 'regex', '+33 6 12 34 56 78', 'french_phone', NULL, 2),
(3, 'address', 'Adresse', 'ner', '123 Rue de la République', NULL, 'LOC', 3),
(3, 'postal_code', 'Code Postal', 'regex', '75001', 'french_postal_code', NULL, 4),
(3, 'company', 'Entreprise', 'ner', 'TechCorp SARL', NULL, 'ORG', 5),
(3, 'ip_address', 'Adresse IP', 'regex', '192.168.1.1', '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', NULL, 6);

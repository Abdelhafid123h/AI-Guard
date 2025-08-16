-- Schéma MySQL équivalent à schema.sql (simplifié)
CREATE TABLE IF NOT EXISTS guard_types (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) UNIQUE NOT NULL,
  display_name VARCHAR(100) NOT NULL,
  description TEXT,
  icon VARCHAR(10),
  color VARCHAR(7),
  is_active TINYINT(1) DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS pii_fields (
  id INT AUTO_INCREMENT PRIMARY KEY,
  guard_type_id INT NOT NULL,
  field_name VARCHAR(50) NOT NULL,
  display_name VARCHAR(100) NOT NULL,
  detection_type VARCHAR(20) NOT NULL,
  example_value TEXT,
  regex_pattern TEXT,
  ner_entity_type VARCHAR(50),
  confidence_threshold FLOAT DEFAULT 0.7,
  is_active TINYINT(1) DEFAULT 1,
  priority INT DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_guard_field (guard_type_id, field_name),
  CONSTRAINT fk_pii_guard FOREIGN KEY (guard_type_id) REFERENCES guard_types(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS regex_patterns (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) UNIQUE NOT NULL,
  display_name VARCHAR(100) NOT NULL,
  pattern TEXT NOT NULL,
  description TEXT,
  test_examples TEXT,
  flags VARCHAR(20) DEFAULT 'i',
  is_active TINYINT(1) DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ner_entity_types (
  id INT AUTO_INCREMENT PRIMARY KEY,
  model_name VARCHAR(50) NOT NULL,
  entity_type VARCHAR(50) NOT NULL,
  display_name VARCHAR(100) NOT NULL,
  description TEXT,
  is_active TINYINT(1) DEFAULT 1,
  UNIQUE KEY uniq_model_entity (model_name, entity_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Historique d'utilisation des traitements
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

import json
import os
from typing import Dict, List
from pathlib import Path

class ConfigLoader:
    def __init__(self, data_path: str = None):
        if data_path is None:
            # 🆕 CORRECTION: Chemin absolu vers le dossier data du projet
            current_file = Path(__file__)  # config_loader.py
            backend_dir = current_file.parent.parent.parent  # remonte à /backend/
            project_root = backend_dir.parent  # remonte à /IA_Guards/
            self.data_path = project_root / "data"
            print(f"📁 Chemin data calculé automatiquement: {self.data_path}")
        else:
            self.data_path = Path(data_path)
            print(f"📁 Chemin data personnalisé: {self.data_path}")
        
        # Vérifier que le dossier data existe
        if not self.data_path.exists():
            print(f"⚠️ Dossier data non trouvé à {self.data_path}")
            print(f"📍 Répertoire de travail actuel: {Path.cwd()}")
            # Créer le dossier s'il n'existe pas
            self.data_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Dossier data créé: {self.data_path}")
        
        self._guard_configs = {}
        self.load_all_configs()
    
    def load_all_configs(self):
        """Charge toutes les configurations JSON"""
        json_files = ["TypeA.json", "TypeB.json", "InfoPerso.json"]
        
        print(f"🔍 Recherche des fichiers JSON dans: {self.data_path}")
        print(f"📂 Contenu du dossier data:")
        
        # Lister le contenu du dossier pour debug
        try:
            if self.data_path.exists():
                for item in self.data_path.iterdir():
                    print(f"   📄 {item.name}")
            else:
                print(f"   ❌ Dossier {self.data_path} n'existe pas")
        except Exception as e:
            print(f"   ❌ Erreur lecture dossier: {e}")
        
        for json_file in json_files:
            file_path = self.data_path / json_file
            guard_type = json_file.replace(".json", "")
            
            print(f"🔎 Recherche de {json_file} à {file_path}")
            
            try:
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        self._guard_configs[guard_type] = self._extract_pii_types(config)
                        print(f"✅ Configuration {guard_type} chargée : {self._guard_configs[guard_type]}")
                else:
                    print(f"⚠️ Fichier {json_file} non trouvé à {file_path}")
                    print(f"📍 Utilisation configuration par défaut pour {guard_type}")
                    self._guard_configs[guard_type] = self._get_default_config(guard_type)
            except Exception as e:
                print(f"❌ Erreur lors du chargement de {json_file}: {e}")
                self._guard_configs[guard_type] = self._get_default_config(guard_type)
    
    def _extract_pii_types(self, config: Dict) -> List[str]:
        """Extrait les types PII depuis la configuration JSON"""
        pii_types = []
        
        # Parcourir les exemples dans le JSON
        if "examples" in config:
            for example in config["examples"]:
                for key, value in example.items():
                    if key != "id" and value:  # Ignorer l'ID et valeurs nulles
                        mapped_type = self._map_json_key_to_pii_type(key)
                        if mapped_type not in pii_types:
                            pii_types.append(mapped_type)
        
        return pii_types
    
    def _map_json_key_to_pii_type(self, json_key: str) -> str:
        """Mappe les clés JSON vers les types PII du système"""
        mapping = {
            # TypeA - Données Personnelles
            "name": "name",
            "firstname": "firstname", 
            "birth_date": "birth_date",
            "birth_place": "birth_place",
            "social_security": "social_security",
            "id_card": "id_card",
            "passport": "passport",
            "driving_license": "driving_license",
            
            # TypeA - Nouvelles clés françaises
            "date_naissance": "birth_date",
            "lieu_naissance": "birth_place", 
            "numero_securite_sociale": "social_security",
            "carte_identite": "id_card",
            "permis_conduire": "driving_license",
            
            # TypeB - Données Financières
            "credit_card": "credit_card",
            "numero_carte_bancaire": "credit_card",
            "iban": "iban", 
            "rib": "iban",
            "bank_account": "bank_account",
            "numero_compte_bancaire": "bank_account",
            "codes_securite": "security_code",
            "cvv": "security_code",
            "informations_paiement": "payment_info",
            
            # InfoPerso - Données Contact
            "address": "address",
            "adresse_postale_complete": "address",
            "postal_code": "postal_code",
            "code_postal": "postal_code",
            "email": "email",
            "adresse_email": "email",
            "phone": "phone",
            "numero_telephone": "phone",
            "company": "company",
            "nom_entreprise": "company",
            "ip_address": "ip_address",
            "adresse_ip": "ip_address"
        }
        
        # 🆕 NOUVEAU : Permettre des types personnalisés
        mapped_type = mapping.get(json_key, json_key)
        if mapped_type != json_key:
            print(f"🔄 Mapping: '{json_key}' → '{mapped_type}'")
        else:
            print(f"🆕 Nouveau type PII détecté: '{json_key}'")
        
        return mapped_type
    
    def _get_default_config(self, guard_type: str) -> List[str]:
        """Configuration par défaut si JSON non disponible"""
        defaults = {
            "TypeA": ['name', 'full_name', 'firstname', 'birth_date', 'birth_place', 
                     'social_security', 'id_card', 'passport', 'driving_license'],
            "TypeB": ['credit_card', 'iban', 'bank_account', 'security_code', 'payment_info'],
            "InfoPerso": ['address', 'postal_code', 'email', 'phone', 'company', 'ip_address']
        }
        return defaults.get(guard_type, [])
    
    def get_guard_types(self, guard_type: str) -> List[str]:
        """Retourne les types PII pour un guard donné"""
        return self._guard_configs.get(guard_type, [])
    
    def get_all_configs(self) -> Dict[str, List[str]]:
        """Retourne toutes les configurations"""
        return self._guard_configs.copy()
    
    def reload_config(self, guard_type: str = None):
        """Recharge une configuration spécifique ou toutes"""
        if guard_type:
            json_file = f"{guard_type}.json"
            file_path = self.data_path / json_file
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self._guard_configs[guard_type] = self._extract_pii_types(config)
                    print(f"🔄 Configuration {guard_type} rechargée")
            except Exception as e:
                print(f"❌ Erreur rechargement {guard_type}: {e}")
        else:
            self.load_all_configs()
    
    def get_example_text(self, guard_type: str) -> str:
        """Génère un texte d'exemple basé sur la configuration JSON"""
        json_file = f"{guard_type}.json"
        file_path = self.data_path / json_file
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if "examples" in config and config["examples"]:
                    example = config["examples"][0]
                    return self._generate_text_from_example(example)
        except Exception as e:
            print(f"❌ Erreur génération exemple {guard_type}: {e}")
        
        return self._get_default_example_text(guard_type)
    
    def _generate_text_from_example(self, example: Dict) -> str:
        """Génère un texte naturel depuis un exemple JSON"""
        text_parts = []
        
        if "name" in example:
            text_parts.append(f"Bonjour, je suis {example['name']}")
        
        # Dates et lieux de naissance
        birth_date_key = next((k for k in ["birth_date", "date_naissance"] if k in example), None)
        birth_place_key = next((k for k in ["birth_place", "lieu_naissance"] if k in example), None)
        
        if birth_date_key and birth_place_key:
            text_parts.append(f"né le {example[birth_date_key]} à {example[birth_place_key]}")
        elif birth_date_key:
            text_parts.append(f"né le {example[birth_date_key]}")
        
        # Sécurité sociale
        ssn_key = next((k for k in ["social_security", "numero_securite_sociale"] if k in example), None)
        if ssn_key:
            text_parts.append(f"Mon numéro de sécurité sociale est {example[ssn_key]}")
        
        # Cartes et documents
        card_key = next((k for k in ["credit_card", "numero_carte_bancaire"] if k in example), None)
        if card_key:
            text_parts.append(f"Ma carte bancaire est {example[card_key]}")
        
        iban_key = next((k for k in ["iban", "rib"] if k in example), None)
        if iban_key:
            text_parts.append(f"mon IBAN est {example[iban_key]}")
        
        # Contact
        email_key = next((k for k in ["email", "adresse_email"] if k in example), None)
        if email_key:
            text_parts.append(f"Contactez-moi à {example[email_key]}")
        
        phone_key = next((k for k in ["phone", "numero_telephone"] if k in example), None)
        if phone_key:
            text_parts.append(f"ou au {example[phone_key]}")
        
        # Adresse
        address_key = next((k for k in ["address", "adresse_postale_complete"] if k in example), None)
        if address_key:
            text_parts.append(f"J'habite au {example[address_key]}")
        
        # Entreprise
        company_key = next((k for k in ["company", "nom_entreprise"] if k in example), None)
        if company_key:
            text_parts.append(f"Je travaille chez {example[company_key]}")
        
        return ". ".join(text_parts) + "."
    
    def _get_default_example_text(self, guard_type: str) -> str:
        """Texte d'exemple par défaut"""
        defaults = {
            "TypeA": "Bonjour, je suis Jean Dupont, né le 15/03/1980 à Lyon. Mon numéro de sécurité sociale est 1 80 03 69 123 456 78.",
            "TypeB": "Ma carte bancaire est 4111 1111 1111 1111 et mon IBAN est FR76 3000 6000 0112 3456 7890 189.",
            "InfoPerso": "Contactez-moi à jean.dupont@example.com ou au +33 6 12 34 56 78. J'habite au 123 Rue de la République, 75001 Paris."
        }
        return defaults.get(guard_type, "Exemple non disponible.")

# Instance globale
config_loader = ConfigLoader()

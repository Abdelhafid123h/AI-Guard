import logging
from ..services.pii_detector_french import PIIDetectorFrench
from ..utils.token_manager import TokenManager
from ..services.llm_service import LLMService
from ..utils.config_loader import config_loader

class GuardService:
    def __init__(self, key: str = "ia_guards_secret_2025"):
        self.token_manager = TokenManager(key)
        self.llm_service = LLMService()
        self.pii_detector = PIIDetectorFrench()  # Nouveau détecteur français
        self.config_loader = config_loader  # Gestionnaire de configuration JSON

    def process(self, text: str, guard_type: str) -> dict:
        """Traite le texte pour détecter, masquer, envoyer au LLM et restaurer les entités sensibles."""
        logging.info(f"Début du traitement du texte (guard_type={guard_type})")
        all_entities = self.pii_detector.detect(text)
        logging.info(f"Entités détectées : {[(e['text'], e['type']) for e in all_entities]}")

        allowed_types = self.config_loader.get_guard_types(guard_type)
        if not allowed_types:
            logging.error(f"Guard type non supporté ou configuration manquante : {guard_type}")
            raise ValueError(f"Guard type non supporté ou configuration manquante : {guard_type}")

        entities = [e for e in all_entities if e['type'] in allowed_types]
        logging.info(f"Entités filtrées pour {guard_type} : {[(e['text'], e['type']) for e in entities]}")
        logging.info(f"Types autorisés (depuis JSON) : {allowed_types}")

        masked_text, tokens = self.generate_tokens(text, entities)
        logging.info(f"Texte masqué généré : {masked_text}")

        try:
            llm_response = self.llm_service.send_to_llm(masked_text)
            logging.info(f"Réponse LLM reçue : {llm_response}")
        except Exception as e:
            logging.error(f"Erreur lors de l'appel au LLM : {e}")
            llm_response = "[Erreur LLM]"

        unmasked_response = self.unmask(llm_response, tokens)
        logging.info(f"Texte démasqué généré : {unmasked_response}")

        return {
            "original": text,
            "masked": masked_text,
            "llm_response": llm_response,
        "unmasked": unmasked_response
    }

    def generate_tokens(self, text: str, entities: list) -> tuple[str, dict]:
     """Génère des tokens pour les entités détectées et masque le texte."""
     tokens = {}
     masked_text = text
     print(f"Entités reçues pour masquage : {entities}")  # Log pour débogage
     
     # Trier les entités par position (de la fin vers le début pour éviter les décalages)
     sorted_entities = sorted(entities, key=lambda x: x.get('start', 0), reverse=True)
     
     for entity in sorted_entities:
        if 'text' in entity and 'type' in entity:  # Vérifiez que les clés existent
            token = f"<{entity['type']}:{self.token_manager.generate_token(entity['text'])}>"
            tokens[token] = entity['text']
            
            # NOUVEAU: Utiliser la position exacte si disponible
            if 'start' in entity and 'end' in entity:
                # Remplacer par position exacte
                original_text = masked_text[entity['start']:entity['end']]
                print(f"🔄 Remplacement positionnel: '{original_text}' → '{token}'")
                masked_text = masked_text[:entity['start']] + token + masked_text[entity['end']:]
            else:
                # Fallback: remplacement par texte (méthode originale)
                print(f"🔄 Remplacement textuel: '{entity['text']}' → '{token}'")
                if entity['text'] in masked_text:
                    masked_text = masked_text.replace(entity['text'], token, 1)  # Une seule occurrence
                else:
                    print(f"⚠️ ATTENTION: Texte '{entity['text']}' non trouvé pour remplacement")
        else:
            raise ValueError(f"Entité mal formée : {entity}")
     return masked_text, tokens

    def unmask(self, text: str, tokens: dict) -> str:
     """Restaure les entités sensibles dans le texte."""
     for token, original in tokens.items():
        # Remplacez chaque token par sa valeur originale
        text = text.replace(token, original)
     return text
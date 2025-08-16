import logging
from ..services.pii_detector_french import PIIDetectorFrench
from ..utils.token_manager import TokenManager
from ..services.llm_service import LLMService
from ..database.db_manager import db_manager
from ..utils.dynamic_config_loader import dynamic_config_loader

class GuardService:
    def __init__(self, key: str = "ia_guards_secret_2025"):
        self.token_manager = TokenManager(key)
        self.llm_service = LLMService()
        self.pii_detector = PIIDetectorFrench()  # Nouveau détecteur français
        self.config_loader = dynamic_config_loader  # Gestionnaire de configuration dynamique

    def process(self, text: str, guard_type: str) -> dict:
        """Traite le texte pour détecter, masquer, envoyer au LLM et restaurer les entités sensibles."""
        logging.info(f"Début du traitement du texte (guard_type={guard_type})")
        all_entities = self.pii_detector.detect(text, guard_type)  # 🆕 Passer guard_type
        logging.info(f"Entités détectées : {[(e['text'], e['type']) for e in all_entities]}")

        allowed_types = self.config_loader.get_guard_types(guard_type)
        if not allowed_types:
            logging.error(f"Guard type non supporté ou configuration manquante : {guard_type}")
            raise ValueError(f"Guard type non supporté ou configuration manquante : {guard_type}")

        entities = [e for e in all_entities if e['type'] in allowed_types]
        logging.info(f"Entités filtrées pour {guard_type} : {[(e['text'], e['type']) for e in entities]}")
        logging.info(f"Types autorisés (depuis DB) : {allowed_types}")

        masked_text, tokens = self.generate_tokens(text, entities)
        logging.info(f"Texte masqué généré : {masked_text}")

        try:
            llm_payload = self.llm_service.send_to_llm(masked_text)
            llm_content = llm_payload.get('content') if isinstance(llm_payload, dict) else str(llm_payload)
            prompt_tokens = llm_payload.get('prompt_tokens', 0) if isinstance(llm_payload, dict) else 0
            completion_tokens = llm_payload.get('completion_tokens', 0) if isinstance(llm_payload, dict) else 0
            logging.info(f"Réponse LLM reçue : {llm_content} (prompt={prompt_tokens} completion={completion_tokens})")
        except Exception as e:
            logging.error(f"Erreur lors de l'appel au LLM : {e}")
            llm_content = "[Erreur LLM]"
            prompt_tokens = completion_tokens = 0

        # Historique
        try:
            masked_token_count = len(tokens)
            llm_mode = 'disabled' if completion_tokens == 0 and prompt_tokens > 0 and llm_content.startswith('[LLM') else 'enabled'
            db_manager.add_usage_history(
                guard_type, masked_text, prompt_tokens, completion_tokens, masked_token_count,
                model=getattr(self.llm_service, 'model', None), llm_mode=llm_mode
            )
        except Exception as e:
            logging.warning(f"Impossible d'enregistrer l'historique: {e}")

        unmasked_response = self.unmask(llm_content, tokens)
        logging.info(f"Texte démasqué généré : {unmasked_response}")

        return {
            "original": text,
            "masked": masked_text,
            "llm_response": llm_content,
            "unmasked": unmasked_response,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "masked_token_count": len(tokens),
            "model": getattr(self.llm_service, 'model', None),
            "client_version": getattr(self.llm_service, 'client_version', None)
        }

    def generate_tokens(self, text: str, entities: list) -> tuple[str, dict]:
        """Génère des tokens en évitant les corruptions dues aux décalages d'index.

        Stratégie:
        1. Filtrer les entités invalides / vides
        2. Normaliser et supprimer les chevauchements (priorité regex_db > confiance > longueur)
        3. Reconstruire la chaîne en une passe (pas de remplacements successifs sur la même string)
        """
        # 1. Filtrer entités valides
        cleaned = [e for e in entities if all(k in e for k in ('start','end','text','type')) and e['start'] < e['end']]
        if not cleaned:
            return text, {}

        # 2. Suppression des chevauchements
        def score(ent):
            # Regex ayant priorité maximale
            base = 1000 if ent.get('source') == 'regex_db' else 0
            conf = ent.get('confidence', 0.0)
            length = ent['end'] - ent['start']
            return (base, conf, length)

        # Trier par score desc puis start
        cleaned.sort(key=lambda e: (-score(e)[0], -score(e)[1], -score(e)[2], e['start']))
        selected = []
        occupied = []  # list of (start,end)
        for ent in cleaned:
            overlap = False
            for (s,e) in occupied:
                if not (ent['end'] <= s or ent['start'] >= e):
                    overlap = True
                    break
            if not overlap:
                occupied.append((ent['start'], ent['end']))
                selected.append(ent)

        # Ordonner sélection pour reconstruction
        selected.sort(key=lambda e: e['start'])

        tokens = {}
        out_parts = []
        cursor = 0
        for ent in selected:
            if ent['start'] > cursor:
                out_parts.append(text[cursor:ent['start']])
            original_segment = text[ent['start']:ent['end']]
            token = f"<{ent['type']}:{self.token_manager.generate_token(original_segment)} >".replace(' >','>')
            tokens[token] = original_segment
            out_parts.append(token)
            cursor = ent['end']
        if cursor < len(text):
            out_parts.append(text[cursor:])
        masked_text = ''.join(out_parts)
        return masked_text, tokens

    def unmask(self, text: str, tokens: dict) -> str:
        """Restaure les entités sensibles dans le texte."""
        for token, original in tokens.items():
            text = text.replace(token, original)
        return text
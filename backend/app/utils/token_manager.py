
import hashlib

class TokenManager:
    def __init__(self, key: str = None):
        # Clé par défaut robuste et unique pour IA_Guards
        self.key = key or "IA_GUARDS_PII_PROTECTION_2025_SECURE_KEY_Fr@nce"

    def generate_token(self, data: str) -> str:
        """Génère un token déterministe qui reste le même après redémarrage"""
        # Utilise SHA-256 qui est déterministe (pas de randomization)
        hash_input = f"{self.key}_{data}".encode('utf-8')
        stable_hash = hashlib.sha256(hash_input).hexdigest()[:16]
        return f"TOKEN_{stable_hash}"
import openai
import os
import json
import time
from typing import Dict, Optional
import logging
import requests

logger = logging.getLogger(__name__)
try:
    from dotenv import load_dotenv, find_dotenv  # python-dotenv already in requirements
    _found_env = find_dotenv()
    if _found_env:
        load_dotenv(_found_env)
        print(f"🔍 .env chargé depuis: {_found_env}")
    else:
        # Tentative chargement manuel parent (utile si lancé depuis backend/)
        parent_env = os.path.abspath(os.path.join(os.getcwd(), '..', '.env'))
        if os.path.isfile(parent_env):
            load_dotenv(parent_env)
            print(f"🔍 .env parent chargé depuis: {parent_env}")
        else:
            print("⚠️ Aucun fichier .env trouvé (find_dotenv) – vérifier répertoire de lancement.")
except Exception as _e:
    print(f"⚠️ Chargement .env échoué: {_e}")

try:
    import tiktoken  # type: ignore
except Exception:  # tiktoken optionnel
    tiktoken = None

def _approx_token_count(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text.split()) * 1.1))

def _count_tokens(model: str, text: str) -> int:
    if not text:
        return 0
    if tiktoken:
        try:
            enc = tiktoken.encoding_for_model(model)
        except Exception:
            try:
                enc = tiktoken.get_encoding("cl100k_base")
            except Exception:
                return _approx_token_count(text)
        try:
            return len(enc.encode(text))
        except Exception:
            return _approx_token_count(text)
    return _approx_token_count(text)

class LLMService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            openai.api_key = api_key.strip().strip('"').strip("'")  # nettoyer guillemets éventuels
            print(f"✅ OPENAI_API_KEY chargé (longueur={len(openai.api_key)}).")
        else:
            print("⚠️ OPENAI_API_KEY non défini - appels LLM désactivés")
        requested_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.model = requested_model
        # Détection version client & compatibilité modèles
        try:
            import pkg_resources  # type: ignore
            version = pkg_resources.get_distribution('openai').version
        except Exception:
            version = '0.0'
        self.client_version = version
        if version.startswith('0.') and requested_model.startswith('gpt-4-turbo'):
            # Ancien client ne gère probablement pas ce label marketing -> fallback
            fallback = os.getenv('OPENAI_MODEL_FALLBACK', 'gpt-3.5-turbo')
            print(f"⚠️ Client OpenAI {version} incompatible avec {requested_model}. Fallback vers {fallback} (mettre à jour la lib pour utiliser les modèles turbo).")
            self.model = fallback
        print(f"🧪 LLMService initialisé (client={version}, model_effectif={self.model})")

        # Support nouveau client 1.x
        self._client = None
        if not version.startswith('0.'):
            try:
                from openai import OpenAI  # type: ignore
                self._client = OpenAI(api_key=openai.api_key or os.getenv("OPENAI_API_KEY"))
                print("🧩 Client OpenAI 1.x initialisé")
            except Exception as cli_e:
                print(f"⚠️ Impossible d'initialiser client OpenAI 1.x: {cli_e}")
                logger.exception("Init client OpenAI 1.x échouée")

    def send_to_llm(self, text: str) -> Dict[str, int | str]:
        # Ajoute une consigne explicite pour le LLM
        instruction = (
            "ATTENTION : Les entités sensibles dans ce texte ont été remplacées par des tokens de la forme <type:TOKEN_xxx>. "
            "Quand vous répondez à une question sur une entité masquée, répondez uniquement en réutilisant le token correspondant, sans inventer ni deviner la donnée réelle. "
            "Exemple : Si on demande le numéro de sécurité sociale, répondez : <social_security:TOKEN_xxx>. "
            "Ne dites jamais que vous ne pouvez pas répondre, ne donnez pas de conseils de sécurité, ne reformulez pas la question. "
            "Répondez uniquement avec le token haché approprié."
        )
        prompt = instruction + "\n\n" + text
        print(f"Envoi au LLM : {prompt}")  # Log pour débogage
        try:
            if not getattr(openai, 'api_key', None):
                approx = _approx_token_count(prompt)
                return {"content": "[LLM désactivé]", "prompt_tokens": approx, "completion_tokens": 0}
            content = ''
            usage = {}
            error_chain: list[str] = []

            # 1. Essai client officiel 1.x
            if self._client:
                try:
                    response = self._client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=100,
                        temperature=0
                    )
                    choice0 = response.choices[0] if response.choices else None
                    content = (choice0.message.content if choice0 and choice0.message else '') or ''
                    usage_obj = getattr(response, 'usage', None)
                    usage = {
                        'prompt_tokens': getattr(usage_obj, 'prompt_tokens', None) if usage_obj else None,
                        'completion_tokens': getattr(usage_obj, 'completion_tokens', None) if usage_obj else None
                    }
                except Exception as e1:
                    err1 = f"client1x:{e1}"[:160]
                    error_chain.append(err1)
                    logger.warning(f"Chat client1x échec: {err1}")

            # 2. Fallback HTTP brut si content vide
            if not content:
                try:
                    http_payload = {
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 100,
                        "temperature": 0
                    }
                    headers = {
                        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                        "Content-Type": "application/json"
                    }
                    t0 = time.time()
                    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=json.dumps(http_payload), timeout=30)
                    if r.status_code == 200:
                        data = r.json()
                        choices = data.get('choices') or []
                        if choices:
                            content = (choices[0].get('message', {}) or {}).get('content', '') or ''
                        usage = data.get('usage') or usage
                        logger.info(f"HTTP fallback réussi en {round((time.time()-t0)*1000)} ms")
                    else:
                        error_chain.append(f"http:{r.status_code}:{r.text[:120]}")
                except Exception as e2:
                    error_chain.append(f"http_exc:{e2}"[:120])

            prompt_tokens = usage.get('prompt_tokens') if isinstance(usage, dict) else None
            completion_tokens = usage.get('completion_tokens') if isinstance(usage, dict) else None
            if prompt_tokens is None:
                prompt_tokens = _count_tokens(self.model, prompt)
            if completion_tokens is None:
                completion_tokens = _count_tokens(self.model, content)
            if not content:
                content = f"[Erreur LLM] {' | '.join(error_chain) or 'inconnue'}"
                completion_tokens = 0
            return {"content": content, "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}
        except Exception as e:
            # Ne pas lever pour éviter tokens = 0 côté appelant; fournir estimation
            err = str(e)
            print(f"❌ Erreur OpenAI: {err}")
            approx_prompt = _count_tokens(self.model, prompt)
            return {"content": f"[Erreur LLM] {err[:160]}", "prompt_tokens": approx_prompt, "completion_tokens": 0}
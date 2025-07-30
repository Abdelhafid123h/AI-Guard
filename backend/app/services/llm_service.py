import openai

class LLMService:
    def __init__(self):
        # Utilisez votre clé API OpenAI ici
        openai.api_key = "OPENAI_API_KEY"
    def send_to_llm(self, text: str) -> str:
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
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100
            )
            return response['choices'][0]['message']['content'].strip()
        except Exception as e:
            raise RuntimeError(f"Erreur lors de l'appel à OpenAI : {e}")
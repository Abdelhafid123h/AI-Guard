

class Settings():
    # Configuration LLM
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4-turbo"
    
    # Sécurité
    SECRET_KEY: str = "change-me-in-production"
    
    # Configuration des guards
    GUARD_CONFIG_PATH: str = "./data"
    
    class Config:
        env_file = ".env"

settings = Settings()
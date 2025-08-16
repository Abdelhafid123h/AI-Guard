
import os
from typing import Optional

class Settings():
    # Configuration Base de données
    DATABASE_TYPE: str = os.getenv("DATABASE_TYPE", "sqlite")
    DATABASE_HOST: str = os.getenv("DATABASE_HOST", "localhost")
    DATABASE_PORT: int = int(os.getenv("DATABASE_PORT", "3306"))
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "ai_guards")
    DATABASE_USER: str = os.getenv("DATABASE_USER", "root")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD", "")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./app/database/ai_guards.db")
    
    # Configuration LLM
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
    
    # Configuration API
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # Sécurité
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    
    # Configuration des guards
    GUARD_CONFIG_PATH: str = os.getenv("GUARD_CONFIG_PATH", "./data")
    
    @property
    def database_url(self) -> str:
        if self.DATABASE_TYPE == "mysql":
            return f"mysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        else:
            return f"sqlite:///{self.DATABASE_PATH}"
    
    class Config:
        env_file = ".env"

settings = Settings()
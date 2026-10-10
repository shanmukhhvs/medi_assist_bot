import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "MediBot RAG API"
    VERSION: str = "1.0.0"
    SECRET_KEY: str = "medibot_secret_key_super_secure_2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    RAW_DOCS_DIR: str = os.path.join(DATA_DIR, "raw_documents")
    DB_PATH: str = os.path.join(DATA_DIR, "mediassist.db")
    QDRANT_PATH: str = os.path.join(BASE_DIR, "backend", "qdrant_storage")
    
    COLLECTION_NAME: str = "medibot_chunks"
    
    # LLM API configuration
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ONEMIN_API_KEY: str = ""
    ONEMIN_MODEL: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"

settings = Settings()

import os
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(BACKEND_DIR)

# backend/.env is read regardless of the working directory; MEDIBOT_ENV_FILE overrides it (used by tests).
ENV_FILE = os.environ.get("MEDIBOT_ENV_FILE", os.path.join(BACKEND_DIR, ".env"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    PROJECT_NAME: str = "MediBot RAG API"
    VERSION: str = "1.1.0"

    # Required. No default: app.auth refuses to import (so the API refuses to start) without a valid value.
    JWT_SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    BASE_DIR: str = BASE_DIR
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    RAW_DOCS_DIR: str = os.path.join(DATA_DIR, "raw_documents")
    DB_PATH: str = os.path.join(DATA_DIR, "mediassist.db")
    QDRANT_PATH: str = os.path.join(BACKEND_DIR, "qdrant_storage")

    COLLECTION_NAME: str = "medibot_chunks"

    # LLM API configuration (cloud-hosted inference; at least one key is required to answer questions)
    ONEMIN_API_KEY: str = ""
    ONEMIN_MODEL: str = "gpt-4o-mini"
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"


settings = Settings()

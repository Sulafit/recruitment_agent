from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Email Configuration
    email_address: str = "sultan.mukhtar1404@gmail.com"
    email_password: str
    imap_server: str = "imap.gmail.com"
    imap_port: int = 993

    # API Keys
    mistral_api_key: str
    mistral_model: str = "mistral-small-2506"

    # Embedding Model
    qwen_model: str = "BAAI/bge-m3"  # BGE-M3 model for embeddings (runs locally via sentence-transformers)

    # Paths
    resumes_dir: str = "backend/data/resumes"
    jobs_dir: str = "backend/data/jobs"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

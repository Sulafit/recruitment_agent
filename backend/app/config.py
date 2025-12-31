from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Email Configuration
    email_address: str = "sultan.mukhtar1404@gmail.com"
    email_password: str
    imap_server: str = "imap.gmail.com"
    imap_port: int = 993

    # API Keys
    hf_token: str  # Required for Qwen embeddings via HuggingFace Inference API
    mistral_api_key: str
    mistral_model: str = "mistral-large-2512"

    # Embedding Model
    qwen_model: str = "Qwen/Qwen3-Embedding-0.6B"  # HuggingFace model for embeddings

    # Paths
    resumes_dir: str = "data/resumes"
    jobs_dir: str = "data/jobs"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

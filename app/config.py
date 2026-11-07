"""Configuration management for SafeExec AI."""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Base directory for the SafeExec AI project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


class Settings(BaseModel):
    # Service settings
    app_name: str = "SafeExec AI"
    version: str = "0.1.0"
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8080")))
    host: str = Field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "*").split(",")
            if origin.strip()
        ]
    )

    # Celesto Cloud API
    celesto_api_key: str = Field(default_factory=lambda: os.getenv("CELESTO_API_KEY", ""))

    # Database configuration
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql://safeexec:safeexec_secret@localhost:5432/safeexec_ledger"
        )
    )

    # Gemini API (OpenAI-compatible endpoint)
    llm_base_url: str = Field(
        default_factory=lambda: os.getenv("LLM_BASE_URL")
        or "https://generativelanguage.googleapis.com/v1beta/openai"
    )

    llm_api_key: str = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY")
        or os.getenv("LLM_API_KEY", "")
    )

    llm_model: str = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL")
        or os.getenv("LLM_MODEL")
        or "gemini-3.8-flash"
    )

    # Paths
    base_dir: Path = BASE_DIR
    logs_dir: Path = BASE_DIR / "logs"
    reports_dir: Path = BASE_DIR / "reports"
    evidence_dir: Path = BASE_DIR / "reports" / "evidence"


settings = Settings()

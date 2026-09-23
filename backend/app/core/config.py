"""
Application Settings and Configuration Loader
Supports loading settings from environment variables with safe defaults.
"""

import os
from pathlib import Path
from typing import List

# Determine base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR.parent


class Settings:
    # Project Info
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "NagarSetu Civic Complaint Triage Engine")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")

    # Host & Port
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if origin.strip()
    ]

    # Database (Future Phase)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://nagarsetu_user:nagarsetu_password@localhost:5432/nagarsetu_db"
    )

    # Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Paths
    DATA_RAW_DIR: Path = Path(os.getenv("DATA_RAW_DIR", str(ROOT_DIR / "data" / "raw")))
    DATA_PROCESSED_DIR: Path = Path(os.getenv("DATA_PROCESSED_DIR", str(ROOT_DIR / "data" / "processed")))
    DATA_TEST_DIR: Path = Path(os.getenv("DATA_TEST_DIR", str(ROOT_DIR / "data" / "test")))
    GAZETTEER_PATH: Path = Path(os.getenv("GAZETTEER_PATH", str(ROOT_DIR / "data" / "gazetteer" / "sample_wards_gazetteer.json")))
    CONFIG_DIR: Path = Path(os.getenv("CONFIG_DIR", str(ROOT_DIR / "config")))
    PROMPTS_DIR: Path = Path(os.getenv("PROMPTS_DIR", str(ROOT_DIR / "prompts")))

    # Thresholds
    CONFIDENCE_THRESHOLD_ROUTING: float = float(os.getenv("CONFIDENCE_THRESHOLD_ROUTING", "0.75"))
    CONFIDENCE_THRESHOLD_DUPLICATE: float = float(os.getenv("CONFIDENCE_THRESHOLD_DUPLICATE", "0.85"))
    CONFIDENCE_THRESHOLD_NORMAL: float = float(os.getenv("CONFIDENCE_THRESHOLD_NORMAL", "0.80"))
    CONFIDENCE_THRESHOLD_ATTENTION: float = float(os.getenv("CONFIDENCE_THRESHOLD_ATTENTION", "0.50"))
    ENABLE_STRICT_DETERMINISTIC_VALIDATION: bool = (
        os.getenv("ENABLE_STRICT_DETERMINISTIC_VALIDATION", "True").lower() in ("true", "1", "yes")
    )

    # Prompt & Model Versions
    MODEL_VERSION: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    PROMPT_VERSION: str = os.getenv("PROMPT_VERSION", "classification_v1.0")
    URGENCY_PROMPT_VERSION: str = os.getenv("URGENCY_PROMPT_VERSION", "urgency_v1.0")


settings = Settings()

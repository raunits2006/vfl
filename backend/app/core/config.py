import os
import logging
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()  # Loads variables from .env file into environment

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"
    VLR_API_UPCOMING_MATCHES_URL: str = "https://vlrggapi.vercel.app/match?q=upcoming"
    # Optional endpoint to fetch recent or live results to backfill matches
    VLR_API_RECENT_MATCHES_URL: str | None = None
    VLR_API_LIVE_SCORE_URL: str = "https://vlrggapi.vercel.app/match?q=live_score"
    # SECURITY: No default - must be provided via environment variable
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
    SECRET_KEY: str
    # Optional separate admin secret key - if not provided, derived from SECRET_KEY
    ADMIN_SECRET_KEY: str | None = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Comma-separated list of allowed origins for CORS in production
    ALLOWED_ORIGINS: str | None = None
    # Environment mode: development or production
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

settings = Settings()

# --- Production security validation ---
# Refuse to start with known default/placeholder secret keys in production.
_KNOWN_WEAK_SECRETS = {
    "CHANGE_THIS_TO_A_SECURE_RANDOM_STRING",
    "change_this_to_a_secure_random_string",
    "your-secret-key-change-me",
    "supersecretkey",
}
if settings.ENVIRONMENT == "production":
    if settings.SECRET_KEY in _KNOWN_WEAK_SECRETS or len(settings.SECRET_KEY) < 32:
        raise SystemExit(
            "FATAL: SECRET_KEY is a known placeholder or too short (< 32 chars). "
            "Generate a secure key in production."
        )
    if settings.ADMIN_SECRET_KEY is None:
        raise SystemExit(
            "FATAL: ADMIN_SECRET_KEY is not set. In production, the admin key must be "
            "set independently of SECRET_KEY for proper security isolation."
        )

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    logging.warning("DATABASE_URL environment variable not set.")
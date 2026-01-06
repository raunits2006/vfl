import os
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

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    print("Warning: DATABASE_URL environment variable not set.")
    # For local development without Docker, you might want to set a default here
    # e.g., DATABASE_URL = "postgresql://user:pass@localhost:5432/dbname"
    # However, for Dockerized setup, it should always come from docker-compose

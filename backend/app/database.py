
import logging
from sqlmodel import create_engine, SQLModel, Session
# Ensure the path to config is correct based on your project structure
from app.core.config import DATABASE_URL, settings

# The connect_args is specific to SQLite. For PostgreSQL, it's not needed.
# For PostgreSQL, ensure your DATABASE_URL is correctly formatted:
# e.g., postgresql://user:password@host:port/dbname
# The DATABASE_URL should be coming from your config.py which loads it from .env

# SQL echo exposes all query parameters in logs — enabled only in development
_sql_echo = settings.ENVIRONMENT != "production"
engine = create_engine(str(DATABASE_URL), echo=_sql_echo)

if _sql_echo:
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

def create_db_and_tables_on_startup():
    # This function should be called during application startup
    # For example, in main.py using FastAPI's @app.on_event("startup")
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

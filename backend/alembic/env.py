from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Standard library imports
import os
import sys
from pathlib import Path

# --- BEGIN APP PATH SETUP ---
# Determine the root directory of the application (e.g., /app in the container)
# This assumes env.py is in alembic/ and the app root is its parent.
APP_ROOT_DIR = Path(__file__).resolve().parents[1]

# Add the application's root directory to sys.path for module imports
# Using insert(0, ...) to prioritize this path
if str(APP_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(APP_ROOT_DIR))

# Load .env file from the APP_ROOT_DIR
# Ensure .env is in the same directory as your alembic.ini or adjust path accordingly
dotenv_path = APP_ROOT_DIR / '.env'
if dotenv_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path)
else:
    print(f"CRITICAL [env.py]: .env file not found at {dotenv_path}")
    # Optionally, you could raise an error or sys.exit() here
    # For now, we'll let it proceed and likely fail if DATABASE_URL isn't otherwise set

# --- END APP PATH SETUP ---

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# --- BEGIN DATABASE URL CONFIGURATION ---
# Get DATABASE_URL from environment
db_url = os.getenv("DATABASE_URL")

if not db_url:
    print("CRITICAL [env.py]: DATABASE_URL not found in environment variables after attempting to load .env.")
    # Attempt to fall back to alembic.ini setting if needed, though explicit is better.
    # If alembic.ini also uses ${DATABASE_URL}, this will still fail if not substituted.
    # It's best to ensure .env is loaded correctly and DATABASE_URL is set.
    # Forcing a failure if not found can be safer:
    # raise ValueError("DATABASE_URL not set in environment, cannot proceed with migrations.")
else:
    # Set the sqlalchemy.url in the Alembic config object.
    # This ensures Alembic uses the URL from the environment.
    config.set_main_option("sqlalchemy.url", db_url)
    print(f"INFO [env.py]: DATABASE_URL successfully loaded and set for Alembic: {db_url[:30]}...") # Log a truncated URL for confirmation

# --- END DATABASE URL CONFIGURATION ---

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from app.models.match_model import Match # Import your models
from app.models.live_data_models import LiveScore, MapRound, PlayerStat # Import new models
from app.models.player_pool_model import Players # Import new models
from app.database import SQLModel # Use SQLModel.metadata

target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired: 
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

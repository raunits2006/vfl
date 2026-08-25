import time
import logging
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from sqlmodel import Session, select # Added select
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Assuming your project structure is backend/app/...
# Adjust imports if your structure is different or if main.py is inside app
from app.database import get_session, create_db_and_tables_on_startup, engine # Corrected import
from app.models.match_model import Match, MatchCreate # Corrected import
from app.celery_app import celery_app # Import your celery app instance
from app.models.player_pool_model import Players
from app.add_players import add_players
from app.models.agent_model import Agent
from app.utils.agents import FALLBACK_AGENT_TO_CLASS
from app.workers.match_updater import update_upcoming_matches_task, maybe_trigger_scrape_live_matches # Import the tasks
from app.core.config import settings
from app.utils.rate_limit import limiter
from app.utils.admin_auth import require_match_management
from app.utils.security_headers import SecurityHeadersMiddleware

# Import routers
from app.routers import league, team, user, draft, fantasy_scores, free_agents, auth, trade, websocket, admin_auth, admin

app = FastAPI(title="Valorant Fantasy League API", version="1.0.0")

# Configure rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware (env-configurable)
_default_allowed_origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://frontend:3000",
]
_env_allowed_origins = [o.strip() for o in (getattr(settings, 'ALLOWED_ORIGINS', None) or "").split(',') if o.strip()]
_allowed_origins = _env_allowed_origins if _env_allowed_origins else _default_allowed_origins

# Explicit allowed methods and headers for security
_allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
_allowed_headers = [
    "Authorization",
    "Content-Type",
    "Accept",
    "Origin",
    "X-Requested-With",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=_allowed_methods,
    allow_headers=_allowed_headers,
)

# Add security headers middleware (after CORS to ensure headers are added)
app.add_middleware(SecurityHeadersMiddleware)

# Include routers
app.include_router(auth.router)
app.include_router(league.router)
app.include_router(team.router)
app.include_router(user.router)
app.include_router(draft.router)
app.include_router(fantasy_scores.router)
app.include_router(free_agents.router)
app.include_router(trade.router)
app.include_router(websocket.router)
app.include_router(admin_auth.router)
app.include_router(admin.router)

@app.on_event("startup")
def on_startup():
    create_db_and_tables_on_startup()
    # Seed players if none exist
    try:
        with Session(engine) as session:
            existing = session.exec(select(Players)).all()
            if not existing:
                add_players()
    except Exception:
        # Non-fatal if seeding fails; app can still start
        pass

    # Seed agents if none exist
    try:
        with Session(engine) as session:
            has_agent = session.exec(select(Agent)).first()
            if not has_agent:
                for name, agent_class in FALLBACK_AGENT_TO_CLASS.items():
                    session.add(Agent(name=name, agent_class=agent_class))
                session.commit()
    except Exception:
        # Non-fatal
        pass

    # Kick off background tasks so scraping resumes after restarts
    try:
        update_upcoming_matches_task.delay()
    except Exception:
        pass
    try:
        maybe_trigger_scrape_live_matches.delay()
    except Exception:
        pass


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/healthz")
async def healthz():
    """Basic liveness probe — always returns 200 if the server is running."""
    return {"status": "ok"}

@app.get("/readyz")
async def readyz():
    """Readiness probe — checks DB and Redis connectivity."""
    from sqlmodel import Session, text
    import redis as _redis
    from app.database import engine
    from app.core.config import settings

    # Check DB
    try:
        with Session(engine) as s:
            s.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unreachable: {e}")

    # Check Redis
    try:
        r = _redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        if not r.ping():
            raise HTTPException(status_code=503, detail="Redis ping failed")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis unreachable: {e}")

    return {"status": "ready"}

@app.get("/matches")
async def get_matches(session: Session = Depends(get_session)): # Add session dependency
    try:
        current_unix_timestamp = int(time.time())
        statement = select(Match).where(Match.unix_timestamp > current_unix_timestamp).order_by(Match.unix_timestamp)
        upcoming_matches = session.exec(statement).all()
        
        if not upcoming_matches:
            return {"message": "No upcoming matches found in the database."}
            
        return upcoming_matches

    except Exception as e:
        # Log the exception with proper logging
        logger.error(f"Error retrieving matches from database: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred while retrieving matches.")


@app.post("/trigger-match-update", status_code=202)
async def trigger_match_update_task(
    current_admin = Depends(require_match_management)
):
    """
    Manually triggers the Celery task to update upcoming matches.
    Requires admin authentication with match management permissions.
    """
    task = update_upcoming_matches_task.delay()
    return {"message": "Match update task triggered successfully.", "task_id": task.id}


import time
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import httpx
from sqlmodel import Session, select # Added select

# Assuming your project structure is backend/app/...
# Adjust imports if your structure is different or if main.py is inside app
from app.database import get_session, create_db_and_tables_on_startup # Corrected import
from app.models.match_model import Match, MatchCreate # Corrected import
from app.celery_app import celery_app # Import your celery app instance
from app.workers.match_updater import update_upcoming_matches_task # Import the task

# Import routers
from app.routers import league, team, user, draft, fantasy_scores, free_agents, auth, trade, websocket, admin_auth, admin

app = FastAPI(title="Valorant Fantasy League API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://localhost:3001",  # Alternative React port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# @app.on_event("startup")
# def on_startup():
#     create_db_and_tables_on_startup()

@app.get("/")
async def root():
    return {"message": "Hello World"}

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
        # Log the exception e
        print(f"An unexpected error occurred while retrieving matches from the database: {str(e)}")
        raise HTTPException(status_code=500, detail="An internal server error occurred while retrieving matches.")


@app.post("/trigger-match-update", status_code=202)
async def trigger_match_update_task():
    """
    Manually triggers the Celery task to update upcoming matches.
    """
    task = update_upcoming_matches_task.delay()
    return {"message": "Match update task triggered successfully.", "task_id": task.id}

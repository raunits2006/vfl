"""
WebSocket endpoints for real-time updates during drafts and league events.
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import Optional

from app.database import get_session
from app.models.league_models import DraftSession, LeagueMember
from app.models.user_model import User
from app.utils.websocket_manager import manager
from app.utils.auth import verify_token

router = APIRouter(tags=["websockets"])

# Note: previously had a helper to parse websocket token into a user-like dict,
# but it is unused. If needed in the future, prefer verifying the token inline
# within each websocket endpoint for clarity and to avoid dead code.

@router.websocket("/ws/draft/{draft_id}")
async def websocket_draft_endpoint(
    websocket: WebSocket,
    draft_id: int,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time draft updates.
    
    Provides live updates for:
    - Draft picks
    - Timer updates
    - Turn changes
    - User connections/disconnections
    - Autopick notifications
    """
    # Basic token validation (simplified)
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return
    
    username = verify_token(token)
    if not username:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    # Get session to validate draft and user
    session_gen = get_session()
    try:
        session = next(session_gen)
        # Verify draft exists
        draft = session.exec(select(DraftSession).where(DraftSession.id == draft_id)).first()
        if not draft:
            await websocket.close(code=1008, reason="Draft not found")
            return
        
        # Get user
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            await websocket.close(code=1008, reason="User not found")
            return
        
        # Verify user is in the league
        league_member = session.exec(
            select(LeagueMember).where(
                LeagueMember.league_id == draft.league_id,
                LeagueMember.user_id == user.id
            )
        ).first()
        
        if not league_member:
            await websocket.close(code=1008, reason="User not in league")
            return
        
        # Connect to draft room
        await manager.connect_to_draft(websocket, draft_id, user.id)
        
        # Send initial draft state
        await manager.send_personal_message({
            "type": "draft_state",
            "draft_id": draft_id,
            "status": draft.status.value if draft.status else None,
            "current_pick": draft.current_pick,
            "current_user_id": draft.current_user_id,
            "pick_deadline": draft.pick_deadline.isoformat() if draft.pick_deadline else None,
            "connected_users": manager.get_connected_users_in_draft(draft_id)
        }, websocket)
        
        try:
            while True:
                # Listen for messages from client
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    await handle_draft_message(message, websocket, draft_id, user.id, session)
                except json.JSONDecodeError:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }, websocket)
                
        except WebSocketDisconnect:
            manager.disconnect(websocket)
            # Notify others that user left
            await manager.broadcast_to_draft({
                "type": "user_left",
                "user_id": user.id,
                "draft_id": draft_id,
                "connected_users": manager.get_connected_users_in_draft(draft_id)
            }, draft_id)
            
    finally:
        try:
            # Properly advance dependency generator to trigger cleanup
            next(session_gen)
        except StopIteration:
            pass


async def handle_draft_message(message: dict, websocket: WebSocket, draft_id: int, user_id: int, session: Session):
    """Handle messages received in draft WebSocket."""
    message_type = message.get("type")
    
    if message_type == "ping":
        await manager.send_personal_message({"type": "pong"}, websocket)
    
    elif message_type == "get_draft_state":
        # Send current draft state
        draft = session.exec(select(DraftSession).where(DraftSession.id == draft_id)).first()
        if draft:
            await manager.send_personal_message({
                "type": "draft_state",
                "draft_id": draft_id,
                "status": draft.status.value if draft.status else None,
                "current_pick": draft.current_pick,
                "current_user_id": draft.current_user_id,
                "pick_deadline": draft.pick_deadline.isoformat() if draft.pick_deadline else None,
                "connected_users": manager.get_connected_users_in_draft(draft_id)
            }, websocket)
    
    # Note: chat messages are not supported in the draft at this time.

# Helper functions to broadcast events from other routers are now integrated directly
# into the WebSocket manager to avoid circular imports

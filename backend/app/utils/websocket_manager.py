"""
WebSocket connection manager for handling real-time updates.
Manages connections for draft rooms and league-wide updates.
"""
import json
import logging
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        # Draft connections: draft_id -> set of websockets
        self.draft_connections: Dict[int, Set[WebSocket]] = {}
        
        # League connections: league_id -> set of websockets  
        self.league_connections: Dict[int, Set[WebSocket]] = {}
        
        # User connections: user_id -> set of websockets (for personal notifications)
        self.user_connections: Dict[int, Set[WebSocket]] = {}
        
        # Connection metadata: websocket -> user info
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect_to_draft(self, websocket: WebSocket, draft_id: int, user_id: int):
        """Connect user to a draft room."""
        await websocket.accept()
        
        if draft_id not in self.draft_connections:
            self.draft_connections[draft_id] = set()
        
        self.draft_connections[draft_id].add(websocket)
        
        # Also register in user connections for personal notifications
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "draft_id": draft_id,
            "connected_at": datetime.utcnow(),
            "type": "draft"
        }
        
        logger.info(f"User {user_id} connected to draft {draft_id}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connected",
            "message": f"Connected to draft {draft_id}",
            "draft_id": draft_id,
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
        
        # Notify others in the draft room
        await self.broadcast_to_draft({
            "type": "user_joined",
            "user_id": user_id,
            "draft_id": draft_id,
            "timestamp": datetime.utcnow().isoformat()
        }, draft_id, exclude=websocket)

    async def connect_to_league(self, websocket: WebSocket, league_id: int, user_id: int):
        """Connect user to a league for general updates."""
        await websocket.accept()
        
        if league_id not in self.league_connections:
            self.league_connections[league_id] = set()
        
        self.league_connections[league_id].add(websocket)
        
        # Also register in user connections for personal notifications
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "league_id": league_id,
            "connected_at": datetime.utcnow(),
            "type": "league"
        }
        
        logger.info(f"User {user_id} connected to league {league_id}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connected",
            "message": f"Connected to league {league_id}",
            "league_id": league_id,
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)

    async def connect_user(self, websocket: WebSocket, user_id: int):
        """Connect user for personal notifications."""
        await websocket.accept()
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        
        self.user_connections[user_id].add(websocket)
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            "type": "user"
        }
        
        logger.info(f"User {user_id} connected for personal notifications")

    def disconnect(self, websocket: WebSocket):
        """Disconnect a websocket and clean up."""
        if websocket not in self.connection_metadata:
            return
        
        metadata = self.connection_metadata[websocket]
        user_id = metadata["user_id"]
        connection_type = metadata["type"]
        
        # Always remove from user connections if present
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from appropriate connection pools
        if connection_type == "draft" and "draft_id" in metadata:
            draft_id = metadata["draft_id"]
            if draft_id in self.draft_connections:
                self.draft_connections[draft_id].discard(websocket)
                if not self.draft_connections[draft_id]:
                    del self.draft_connections[draft_id]
                    
        elif connection_type == "league" and "league_id" in metadata:
            league_id = metadata["league_id"]
            if league_id in self.league_connections:
                self.league_connections[league_id].discard(websocket)
                if not self.league_connections[league_id]:
                    del self.league_connections[league_id]
        
        # Clean up metadata
        del self.connection_metadata[websocket]
        
        logger.info(f"User {user_id} disconnected from {connection_type}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific websocket."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def send_to_user(self, message: dict, user_id: int):
        """Send message to all connections for a specific user."""
        if user_id not in self.user_connections:
            return
        
        disconnected = []
        for websocket in self.user_connections[user_id].copy():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)

    async def broadcast_to_draft(self, message: dict, draft_id: int, exclude: Optional[WebSocket] = None):
        """Broadcast message to all users in a draft room."""
        if draft_id not in self.draft_connections:
            return
        
        disconnected = []
        for websocket in self.draft_connections[draft_id].copy():
            if exclude and websocket == exclude:
                continue
                
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to draft {draft_id}: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)

    async def broadcast_to_league(self, message: dict, league_id: int, exclude: Optional[WebSocket] = None):
        """Broadcast message to all users in a league."""
        if league_id not in self.league_connections:
            return
        
        disconnected = []
        for websocket in self.league_connections[league_id].copy():
            if exclude and websocket == exclude:
                continue
                
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to league {league_id}: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)

    def get_draft_connections_count(self, draft_id: int) -> int:
        """Get number of active connections for a draft."""
        return len(self.draft_connections.get(draft_id, set()))

    def get_league_connections_count(self, league_id: int) -> int:
        """Get number of active connections for a league."""
        return len(self.league_connections.get(league_id, set()))

    def get_connected_users_in_draft(self, draft_id: int) -> List[int]:
        """Get list of user IDs connected to a draft."""
        if draft_id not in self.draft_connections:
            return []
        
        user_ids = []
        for websocket in self.draft_connections[draft_id]:
            if websocket in self.connection_metadata:
                user_ids.append(self.connection_metadata[websocket]["user_id"])
        
        return list(set(user_ids))  # Remove duplicates

    def get_connected_users_in_league(self, league_id: int) -> List[int]:
        """Get list of user IDs connected to a league."""
        if league_id not in self.league_connections:
            return []
        
        user_ids = []
        for websocket in self.league_connections[league_id]:
            if websocket in self.connection_metadata:
                user_ids.append(self.connection_metadata[websocket]["user_id"])
        
        return list(set(user_ids))  # Remove duplicates

# Global connection manager instance
manager = ConnectionManager()

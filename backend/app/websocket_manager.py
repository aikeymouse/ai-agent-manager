from fastapi import WebSocket
from typing import Dict, Set
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # session_id -> set of websockets
        self.active_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: int):
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        
        self.active_connections[session_id].add(websocket)
        logger.info(f"WebSocket connected for session {session_id}")
    
    def disconnect(self, websocket: WebSocket, session_id: int):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        
        logger.info(f"WebSocket disconnected for session {session_id}")
    
    async def send_message(self, session_id: int, message: dict):
        """Send message to all connections for a session"""
        if session_id not in self.active_connections:
            return
        
        disconnected = set()
        
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection, session_id)
    
    async def broadcast_log(self, session_id: int, log_line: str):
        """Broadcast container log to all connections"""
        await self.send_message(session_id, {
            "type": "log",
            "content": log_line
        })
    
    async def broadcast_status(self, session_id: int, status: str):
        """Broadcast status update to all connections"""
        logger.info(f"Broadcasting status '{status}' to session {session_id}")
        await self.send_message(session_id, {
            "type": "status",
            "status": status
        })


# Global instance
connection_manager = ConnectionManager()

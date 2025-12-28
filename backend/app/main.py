from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
import logging

from app.database import init_db, get_db, AgentSession, ChatMessage
from app.venv_manager import container_manager
from app.websocket_manager import connection_manager
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Agent Manager API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Database initialized")
    
    # Start background task to monitor session health
    asyncio.create_task(monitor_session_health())


@app.on_event("shutdown")
async def shutdown_event():
    container_manager.cleanup_all()
    logger.info("Cleaned up all containers")


async def monitor_session_health():
    """Background task to check for unresponsive sessions and broadcast status updates"""
    while True:
        try:
            await asyncio.sleep(10)  # Check every 10 seconds
            
            # Get database session
            db = next(get_db())
            try:
                sessions = db.query(AgentSession).filter(AgentSession.status == "running").all()
                
                for session in sessions:
                    if session.last_heartbeat:
                        time_since_heartbeat = (datetime.now() - session.last_heartbeat).total_seconds()
                        
                        # If no heartbeat for 45 seconds, mark as unresponsive
                        if time_since_heartbeat > 45:
                            logger.warning(f"Session {session.id} is unresponsive (no heartbeat for {time_since_heartbeat:.0f}s)")
                            session.status = "unresponsive"
                            db.commit()
                            
                            # Broadcast status update to all connected clients
                            await connection_manager.broadcast_status(session.id, "unresponsive")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in session health monitor: {e}")


@app.get("/")
async def root():
    return {"message": "AI Agent Manager API"}


@app.get("/agents")
async def list_agents():
    """List available agents from the agents directory"""
    agents = container_manager.get_available_agents()
    return {"agents": agents}


@app.get("/sessions")
async def list_sessions(db: Session = Depends(get_db)):
    """List all agent sessions"""
    sessions = db.query(AgentSession).order_by(AgentSession.created_at.desc()).all()
    
    result = []
    for session in sessions:
        # Update status from running process
        if session.status == "running":
            # First check process status
            process_status = container_manager.get_container_status(session.id)
            
            # Check heartbeat timeout (45 seconds = 3 missed heartbeats)
            if session.last_heartbeat:
                time_since_heartbeat = (datetime.now() - session.last_heartbeat).total_seconds()
                if time_since_heartbeat > 45:
                    session.status = "unresponsive"
                    db.commit()
            # If heartbeat is OK but process exited, mark as exited
            elif process_status == "exited":
                session.status = "exited"
                db.commit()
        
        result.append({
            "session_id": session.id,
            "agent_name": session.agent_name,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "stopped_at": session.stopped_at.isoformat() if session.stopped_at else None
        })
    
    return {"sessions": result}


@app.post("/sessions")
async def create_session(agent_name: str, db: Session = Depends(get_db)):
    """Create a new agent session and spawn process in sandbox"""
    
    # Verify agent exists
    available_agents = container_manager.get_available_agents()
    if not any(a["name"] == agent_name for a in available_agents):
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create session in database
    session = AgentSession(agent_name=agent_name)
    db.add(session)
    db.commit()
    db.refresh(session)
    
    try:
        # Spawn agent process
        process_id, session_id_returned = container_manager.spawn_agent(agent_name, session.id)
        
        # Update session status
        session.status = "running"
        db.commit()
        
        # Start log streaming in background
        asyncio.create_task(stream_container_logs(session.id, session.id))
        
        return {
            "session_id": session.id,
            "agent_name": agent_name,
            "status": "running"
        }
    
    except Exception as e:
        session.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}")
async def get_session(session_id: int, db: Session = Depends(get_db)):
    """Get session details"""
    session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update status from process
    process_status = container_manager.get_container_status(session.id)
    if process_status:
        session.status = process_status
        db.commit()
    
    return {
        "session_id": session.id,
        "agent_name": session.agent_name,
        "status": session.status,
        "created_at": session.created_at.isoformat()
    }


@app.post("/sessions/{session_id}/stop")
async def stop_session(session_id: int, db: Session = Depends(get_db)):
    """Stop agent session and terminate process"""
    session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Stop agent process if running
        if session.status == "running":
            container_manager.stop_agent(session.id)
        
        # Update session status and timestamp instead of deleting
        session.status = "stopped"
        session.stopped_at = datetime.now()
        db.commit()
        
        # Notify connected clients
        await connection_manager.broadcast_status(session_id, "stopped")
        
        return {"message": "Session stopped successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sessions/{session_id}/restart")
async def restart_session(session_id: int, db: Session = Depends(get_db)):
    """Restart a stopped session"""
    session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Stop if currently running
        if session.status == "running":
            container_manager.stop_agent(session.id)
        
        # Spawn agent process
        process_id, session_id_returned = container_manager.spawn_agent(session.agent_name, session.id)
        
        # Update session status
        session.status = "running"
        session.stopped_at = None
        db.commit()
        
        # Start log streaming in background
        asyncio.create_task(stream_container_logs(session.id, session.id))
        
        # Notify connected clients
        await connection_manager.broadcast_status(session_id, "running")
        
        return {
            "session_id": session.id,
            "agent_name": session.agent_name,
            "status": "running"
        }
    
    except Exception as e:
        session.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: int, db: Session = Depends(get_db)):
    """Permanently delete a session and all its messages"""
    session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Stop agent process if running
        if session.status == "running":
            container_manager.stop_agent(session.id)
        
        # Delete all messages for this session
        db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
        
        # Delete session from database
        db.delete(session)
        db.commit()
        
        # Notify connected clients
        await connection_manager.broadcast_status(session_id, "deleted")
        
        return {"message": "Session deleted successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}/messages")
async def get_messages(session_id: int, db: Session = Depends(get_db)):
    """Get chat messages for a session"""
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.timestamp).all()
    
    return {
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ]
    }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: int, db: Session = Depends(get_db)):
    """WebSocket endpoint for real-time communication"""
    
    # Verify session exists
    session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    if not session:
        await websocket.close(code=1008, reason="Session not found")
        return
    
    await connection_manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            message_type = data.get("type")
            content = data.get("content", "")
            
            if message_type == "user_message":
                # Save user message
                msg = ChatMessage(
                    session_id=session_id,
                    role="user",
                    content=content
                )
                db.add(msg)
                db.commit()
                
                # Broadcast user message to all connections (including the agent)
                await connection_manager.send_message(session_id, {
                    "type": "user_message",
                    "content": content
                })
                
                # Also send formatted message back to UI for display
                await connection_manager.send_message(session_id, {
                    "type": "message",
                    "role": "user",
                    "content": content,
                    "timestamp": msg.timestamp.isoformat()
                })
            
            elif message_type == "agent_message":
                # Save agent message
                msg = ChatMessage(
                    session_id=session_id,
                    role="agent",
                    content=content
                )
                db.add(msg)
                db.commit()
                
                # Broadcast to all connections
                await connection_manager.send_message(session_id, {
                    "type": "message",
                    "role": "agent",
                    "content": content,
                    "timestamp": msg.timestamp.isoformat()
                })
            
            elif message_type == "agent_message_stream":
                # Stream partial response without saving (for real-time updates)
                await connection_manager.send_message(session_id, {
                    "type": "message_stream",
                    "role": "agent",
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                })
            
            elif message_type == "agent_log":
                # Forward log message to UI without saving to database
                await connection_manager.send_message(session_id, {
                    "type": "log",
                    "role": "log",
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                })
            
            elif message_type == "typing":
                # Forward typing indicator to UI
                await connection_manager.send_message(session_id, {
                    "type": "typing",
                    "is_typing": data.get("is_typing", True)
                })
            
            elif message_type == "heartbeat":
                # Update last heartbeat timestamp
                session.last_heartbeat = datetime.now()
                db.commit()
                logger.info(f"Heartbeat received for session {session_id}")
                
                # Optionally forward heartbeat to UI for debugging
                await connection_manager.send_message(session_id, {
                    "type": "heartbeat",
                    "timestamp": session.last_heartbeat.isoformat()
                })
    
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connection_manager.disconnect(websocket, session_id)


async def stream_container_logs(session_id: int, process_id: int):
    """Background task to stream agent logs to WebSocket"""
    try:
        async for log_line in container_manager.stream_logs(session_id):
            await connection_manager.broadcast_log(session_id, log_line)
    except Exception as e:
        logger.error(f"Error streaming logs for session {session_id}: {e}")

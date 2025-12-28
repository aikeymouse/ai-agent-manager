import os
import sys
import json
import asyncio
import websockets
from io import StringIO


class LogCapture:
    """Capture print statements and send them as log messages"""
    def __init__(self, agent):
        self.agent = agent
        self.original_stdout = sys.stdout
        
    def write(self, text):
        # Write to original stdout
        self.original_stdout.write(text)
        self.original_stdout.flush()
        
        # Send as log message if it's not empty and agent is connected
        if text.strip() and self.agent.websocket:
            try:
                # Run async send in the event loop
                asyncio.create_task(self.agent.send_log(text.strip()))
            except:
                pass
    
    def flush(self):
        self.original_stdout.flush()


class BaseAgent:
    """Base class for all agents with WebSocket communication to backend"""
    
    def __init__(self):
        self.agent_name = os.getenv("AGENT_NAME", "unknown")
        self.session_id = int(os.getenv("SESSION_ID", "0"))
        self.backend_host = os.getenv("BACKEND_HOST", "localhost")
        self.backend_port = os.getenv("BACKEND_PORT", "8000")
        self.websocket = None
        self.message_queue = asyncio.Queue()
        
    async def connect(self):
        """Connect to backend WebSocket"""
        ws_url = f"ws://{self.backend_host}:{self.backend_port}/ws/{self.session_id}"
        
        print(f"[{self.agent_name}] Attempting to connect to {ws_url}", flush=True)
        try:
            self.websocket = await websockets.connect(ws_url, open_timeout=10)
            print(f"[{self.agent_name}] Connected to backend", flush=True)
            
            # Enable log capture after connection
            sys.stdout = LogCapture(self)
        except Exception as e:
            print(f"[{self.agent_name}] Failed to connect: {e}", file=sys.stderr, flush=True)
            raise
    
    async def send_log(self, content: str):
        """Send log message to UI via WebSocket"""
        if not self.websocket:
            return
        
        try:
            await self.websocket.send(json.dumps({
                "type": "agent_log",
                "content": content
            }))
        except Exception as e:
            pass  # Don't log errors from logging to avoid recursion
    
    async def send_message(self, content: str):
        """Send message to user via WebSocket"""
        if not self.websocket:
            print(f"[{self.agent_name}] WebSocket not connected", file=sys.stderr, flush=True)
            return
        
        try:
            await self.websocket.send(json.dumps({
                "type": "agent_message",
                "content": content
            }))
            print(f"[{self.agent_name}] Sent: {content}", flush=True)
        except Exception as e:
            print(f"[{self.agent_name}] Error sending message: {e}", file=sys.stderr, flush=True)
    
    async def send_message_stream(self, content: str):
        """Send streaming message update (doesn't save to database)"""
        if not self.websocket:
            return
        
        try:
            await self.websocket.send(json.dumps({
                "type": "agent_message_stream",
                "content": content
            }))
        except Exception as e:
            pass  # Silently fail for streaming updates
    
    async def save_message(self, content: str):
        """Save message to database without broadcasting"""
        if not self.websocket:
            return
        
        try:
            await self.websocket.send(json.dumps({
                "type": "agent_message_save",
                "content": content
            }))
        except Exception as e:
            pass  # Silently fail
    
    async def send_typing(self, is_typing: bool = True):
        """Send typing indicator status"""
        if not self.websocket:
            return
        
        try:
            await self.websocket.send(json.dumps({
                "type": "typing",
                "is_typing": is_typing
            }))
        except Exception as e:
            pass  # Don't log typing errors
    
    async def send_heartbeat(self):
        """Send heartbeat to keep connection alive"""
        if not self.websocket:
            return
        
        try:
            await self.websocket.send(json.dumps({
                "type": "heartbeat"
            }))
        except Exception as e:
            pass  # Don't log heartbeat errors
    
    async def receive_message(self):
        """Receive message from user via WebSocket (non-blocking)"""
        try:
            # Try to get a message from the queue without blocking
            message = await asyncio.wait_for(self.message_queue.get(), timeout=0.1)
            return message
        except asyncio.TimeoutError:
            return None
    
    async def _message_receiver_loop(self):
        """Background task to receive messages and put them in queue"""
        try:
            while True:
                if not self.websocket:
                    await asyncio.sleep(0.1)
                    continue
                
                try:
                    message = await self.websocket.recv()
                    data = json.loads(message)
                    
                    if data.get("type") == "user_message":
                        content = data.get("content", "")
                        print(f"[{self.agent_name}] Received: {content}", flush=True)
                        await self.message_queue.put(content)
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"[{self.agent_name}] WebSocket connection closed: {e}", file=sys.stderr, flush=True)
                    break
                except Exception as e:
                    print(f"[{self.agent_name}] Error receiving message: {e}", file=sys.stderr, flush=True)
        except asyncio.CancelledError:
            pass  # Normal cancellation
    
    async def initialize(self):
        """Override this method to initialize your agent"""
        pass
    
    async def process_message(self, message: str) -> str:
        """Override this method to process incoming messages"""
        return f"Echo: {message}"
    
    async def run(self):
        """Main agent loop"""
        print(f"[{self.agent_name}] Starting agent for session {self.session_id}", flush=True)
        
        try:
            # Connect to backend
            await self.connect()
            
            # Initialize agent
            await self.initialize()
            
            # Send welcome message
            await self.send_message(f"Hello! I'm {self.agent_name} agent. How can I help you?")
            
            # Start background tasks
            heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            receiver_task = asyncio.create_task(self._message_receiver_loop())
            
            # Main message loop
            try:
                while True:
                    # Receive user message (non-blocking)
                    user_message = await self.receive_message()
                    
                    if user_message:
                        # Process message
                        response = await self.process_message(user_message)
                        
                        # Send response
                        if response:
                            await self.send_message(response)
                    
                    # Small delay to prevent tight loop
                    await asyncio.sleep(0.1)
            finally:
                # Cancel background tasks
                heartbeat_task.cancel()
                receiver_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
                try:
                    await receiver_task
                except asyncio.CancelledError:
                    pass
        
        except KeyboardInterrupt:
            print(f"[{self.agent_name}] Shutting down", flush=True)
        except Exception as e:
            print(f"[{self.agent_name}] Error: {e}", file=sys.stderr, flush=True)
            raise
        finally:
            if self.websocket:
                await self.websocket.close()
                print(f"[{self.agent_name}] Disconnected", flush=True)
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages"""
        try:
            while True:
                await asyncio.sleep(15)  # Send heartbeat every 15 seconds
                await self.send_heartbeat()
        except asyncio.CancelledError:
            pass  # Normal cancellation

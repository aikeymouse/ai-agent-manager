import sys
import asyncio
import httpx
import json
import os

# Add parent directory to path to import base_agent
sys.path.insert(0, '/workspace/agents')

from base_agent import BaseAgent


class OllamaAgent(BaseAgent):
    """Agent that uses local Ollama with configurable model"""
    
    def __init__(self):
        super().__init__()
        config = self._load_config()
        self.base_url = config.get("base_url", "http://host.docker.internal:11434")
        self.model_endpoint = config.get("model_endpoint", "/api/chat")
        self.test_endpoint = config.get("test_endpoint", "/api/show")
        self.model = config.get("model", "llama3.1:8b")
        self.timeout = config.get("timeout", 60)
        self.stream = config.get("stream", False)
        self.conversation_history = []
    
    def _load_config(self):
        """Load configuration from agent_metadata.json"""
        try:
            config_path = "/workspace/agents/ollama/agent_metadata.json"
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    model = config.get("model", "llama3.1:8b")
                    timeout = config.get("timeout", 60)
                    print(f"[{self.agent_name}] Loaded config - model: {model}, timeout: {timeout}s")
                    return config
        except Exception as e:
            print(f"[{self.agent_name}] Error loading config: {e}, using defaults")
        
        # Default config
        return {
            "model": "llama3.1:8b", 
            "timeout": 60, 
            "base_url": "http://host.docker.internal:11434",
            "model_endpoint": "/api/chat",
            "test_endpoint": "/api/show"
        }
        
    async def initialize(self):
        """Initialize the agent"""
        print(f"[{self.agent_name}] Initializing Ollama agent with model {self.model}")
        
        # Test Ollama connection
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.base_url}{self.test_endpoint}",
                    json={"name": self.model}
                )
                if response.status_code == 200:
                    model_info = response.json()
                    print(f"[{self.agent_name}] Successfully connected to Ollama - Model: {model_info.get('details', {}).get('family', 'unknown')}")
                else:
                    print(f"[{self.agent_name}] Warning: Ollama connection issue (status {response.status_code})")
        except Exception as e:
            print(f"[{self.agent_name}] Warning: Could not connect to Ollama: {e}")
    
    async def process_message(self, message: str) -> str:
        """Process incoming messages using Ollama chat API"""
        print(f"[{self.agent_name}] Processing message with Ollama chat API...")
        
        # Show typing indicator
        await self.send_typing(True)
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=10.0)) as client:
                if self.stream:
                    # Streaming response
                    print(f"[{self.agent_name}] Starting streaming response...", flush=True)
                    full_response = ""
                    try:
                        async with client.stream(
                            "POST",
                            f"{self.base_url}{self.model_endpoint}",
                            json={
                                "model": self.model,
                                "messages": self.conversation_history,
                                "stream": True
                            }
                        ) as response:
                            if response.status_code == 200:
                                async for line in response.aiter_lines():
                                    if line:
                                        try:
                                            chunk = json.loads(line)
                                            if not chunk.get("done"):
                                                content = chunk.get("message", {}).get("content", "")
                                                if content:
                                                    full_response += content
                                                    # Send partial response to update UI
                                                    try:
                                                        await self.send_message_stream(full_response)
                                                    except Exception as e:
                                                        print(f"[{self.agent_name}] Error sending stream: {e}", flush=True)
                                                        raise
                                        except json.JSONDecodeError:
                                            continue
                                
                                # Add complete response to history
                                print(f"[{self.agent_name}] Streaming complete, received {len(full_response)} characters", flush=True)
                                self.conversation_history.append({
                                    "role": "assistant",
                                    "content": full_response
                                })
                                
                                # Hide typing indicator (signals end of stream)
                                await self.send_typing(False)
                                
                                # Save to database without broadcasting (already streamed)
                                await self.save_message(full_response)
                                
                                # Return None to prevent base agent from sending again
                                return None
                            else:
                                await self.send_typing(False)
                                return f"Error: Ollama returned status {response.status_code}"
                    except httpx.ReadTimeout:
                        await self.send_typing(False)
                        return f"Error: Request timed out after {self.timeout} seconds"
                else:
                    # Non-streaming response
                    response = await client.post(
                        f"{self.base_url}{self.model_endpoint}",
                        json={
                            "model": self.model,
                            "messages": self.conversation_history,
                            "stream": False
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        assistant_message = result["message"]["content"]
                        
                        # Add assistant response to history
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": assistant_message
                        })
                        
                        # Hide typing indicator
                        await self.send_typing(False)
                        
                        return assistant_message
                    else:
                        # Hide typing indicator
                        await self.send_typing(False)
                        return f"Error: Ollama returned status {response.status_code}"
                
        except Exception as e:
            # Hide typing indicator on error
            await self.send_typing(False)
            
            error_msg = f"Error communicating with Ollama: {str(e)}"
            print(f"[{self.agent_name}] {error_msg}")
            return error_msg


if __name__ == "__main__":
    agent = OllamaAgent()
    asyncio.run(agent.run())

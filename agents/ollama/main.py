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
        self.base_url = self.config.get("base_url")
        self.model_endpoint = self.config.get("model_endpoint")
        self.test_endpoint = self.config.get("test_endpoint")
        self.model = self.config.get("model")
        self.timeout = self.config.get("timeout")
        self.stream = self.config.get("stream")
        print(f"[{self.agent_name}] Config - model: {self.model}, timeout: {self.timeout}s")
        
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
        
        try:
            if self.stream:
                # Use streaming with base agent helper (handles history automatically)
                response = await self.stream_response(self._ollama_stream_generator())
                return response
            else:
                # Non-streaming response
                return await self._ollama_non_streaming()
                
        except Exception as e:
            error_msg = f"Error communicating with Ollama: {str(e)}"
            print(f"[{self.agent_name}] {error_msg}")
            return error_msg
    
    async def _ollama_stream_generator(self):
        """Generator that yields streaming chunks from Ollama"""
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=10.0)) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}{self.model_endpoint}",
                json={
                    "model": self.model,
                    "messages": self.get_history(),
                    "stream": True
                }
            ) as response:
                if response.status_code != 200:
                    raise Exception(f"Ollama returned status {response.status_code}")
                
                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if not chunk.get("done"):
                                content = chunk.get("message", {}).get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
    
    async def _ollama_non_streaming(self):
        """Handle non-streaming Ollama response"""
        await self.send_typing(True)
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=10.0)) as client:
            response = await client.post(
                f"{self.base_url}{self.model_endpoint}",
                json={
                    "model": self.model,
                    "messages": self.get_history(),
                    "stream": False
                }
            )
            
            await self.send_typing(False)
            
            if response.status_code == 200:
                result = response.json()
                assistant_message = result["message"]["content"]
                return assistant_message
            else:
                raise Exception(f"Ollama returned status {response.status_code}")


if __name__ == "__main__":
    agent = OllamaAgent()
    asyncio.run(agent.run())

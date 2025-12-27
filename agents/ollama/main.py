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
        self.ollama_url = "http://host.docker.internal:11434/api/generate"
        config = self._load_config()
        self.model = config.get("model", "llama3.1:8b")
        self.timeout = config.get("timeout", 60)
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
        return {"model": "llama3.1:8b", "timeout": 60}
        
    async def initialize(self):
        """Initialize the agent"""
        print(f"[{self.agent_name}] Initializing Ollama agent with model {self.model}")
        
        # Test Ollama connection
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    "http://host.docker.internal:11434/api/tags"
                )
                if response.status_code == 200:
                    print(f"[{self.agent_name}] Successfully connected to Ollama")
                else:
                    print(f"[{self.agent_name}] Warning: Ollama connection issue (status {response.status_code})")
        except Exception as e:
            print(f"[{self.agent_name}] Warning: Could not connect to Ollama: {e}")
    
    async def process_message(self, message: str) -> str:
        """Process incoming messages using Ollama"""
        print(f"[{self.agent_name}] Processing message with Ollama...")
        
        # Show typing indicator
        await self.send_typing(True)
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        
        # Build prompt with conversation history
        prompt = self._build_prompt()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Stream the response from Ollama
                full_response = ""
                
                async with client.stream(
                    "POST",
                    self.ollama_url,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    }
                ) as response:
                    if response.status_code == 200:
                        data = await response.aread()
                        import json
                        result = json.loads(data)
                        full_response = result.get("response", "")
                    else:
                        full_response = f"Error: Ollama returned status {response.status_code}"
                
                # Hide typing indicator
                await self.send_typing(False)
                
                # Add assistant response to history
                if full_response:
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": full_response
                    })
                
                # Keep conversation history manageable (last 10 exchanges)
                if len(self.conversation_history) > 20:
                    self.conversation_history = self.conversation_history[-20:]
                
                return full_response
                
        except Exception as e:
            # Hide typing indicator on error
            await self.send_typing(False)
            
            error_msg = f"Error communicating with Ollama: {str(e)}"
            print(f"[{self.agent_name}] {error_msg}")
            return error_msg
    
    def _build_prompt(self) -> str:
        """Build prompt from conversation history"""
        prompt_parts = []
        
        for msg in self.conversation_history:
            role = msg["role"]
            content = msg["content"]
            
            if role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        return "\n\n".join(prompt_parts)


if __name__ == "__main__":
    agent = OllamaAgent()
    asyncio.run(agent.run())

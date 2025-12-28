import sys
import asyncio
import httpx
import json
import os

# Add parent directory to path to import base_agent
sys.path.insert(0, '/workspace/agents')

from base_agent import BaseAgent


class OllamaGenerateAgent(BaseAgent):
    """Agent that uses Ollama /api/generate endpoint for completions"""
    
    def __init__(self):
        super().__init__()
        self.base_url = self.config.get("base_url")
        self.model_endpoint = self.config.get("model_endpoint")
        self.test_endpoint = self.config.get("test_endpoint")
        self.model = self.config.get("model")
        self.timeout = self.config.get("timeout")
        self.stream = self.config.get("stream")
        self.system_prompt = self.config.get("system_prompt")
        print(f"[{self.agent_name}] Config - model: {self.model}, timeout: {self.timeout}s")
        
    async def initialize(self):
        """Initialize the agent"""
        print(f"[{self.agent_name}] Initializing Ollama Generate agent with model {self.model}")
        
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
    
    def _build_prompt(self) -> str:
        """Build prompt from conversation history"""
        prompt_parts = []
        
        # Add system prompt if configured
        if self.system_prompt:
            prompt_parts.append(f"System: {self.system_prompt}\n")
        
        # Add conversation history
        for msg in self.get_history():
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"System: {content}\n")
            elif role == "user":
                prompt_parts.append(f"User: {content}\n")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}\n")
        
        prompt_parts.append("Assistant: ")
        return "\n".join(prompt_parts)
    
    async def process_message(self, message: str) -> str:
        """Process incoming messages using Ollama /api/generate"""
        print(f"[{self.agent_name}] Processing message with Ollama /api/generate...")
        
        try:
            if self.stream:
                # Use streaming
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
        """Generator that yields streaming chunks from Ollama /api/generate"""
        prompt = self._build_prompt()
        
        request_body = {
            "model": self.model,
            "prompt": prompt,
            "stream": True
        }
        
        # Add options from config if present
        if "options" in self.config:
            request_body["options"] = self.config["options"]
        
        self.log_request_body(request_body)
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=10.0)) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}{self.model_endpoint}",
                json=request_body
            ) as response:
                if response.status_code != 200:
                    raise Exception(f"Ollama returned status {response.status_code}")
                
                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if not chunk.get("done"):
                                content = chunk.get("response", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
    
    async def _ollama_non_streaming(self):
        """Handle non-streaming Ollama /api/generate response"""
        await self.send_typing(True)
        
        prompt = self._build_prompt()
        
        request_body = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        # Add options from config if present
        if "options" in self.config:
            request_body["options"] = self.config["options"]
        
        self.log_request_body(request_body)
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=10.0)) as client:
            response = await client.post(
                f"{self.base_url}{self.model_endpoint}",
                json=request_body
            )
            
            await self.send_typing(False)
            
            if response.status_code == 200:
                result = response.json()
                assistant_message = result["response"]
                return assistant_message
            else:
                raise Exception(f"Ollama returned status {response.status_code}")


if __name__ == "__main__":
    agent = OllamaGenerateAgent()
    asyncio.run(agent.run())

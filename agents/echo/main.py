import sys
import asyncio

# Add parent directory to path to import base_agent
sys.path.insert(0, '/workspace/agents')

from base_agent import BaseAgent


class EchoAgent(BaseAgent):
    """Simple echo agent that repeats user messages"""
    
    async def initialize(self):
        """Initialize the echo agent"""
        print("[EchoAgent] Initialized", flush=True)
    
    async def process_message(self, message: str) -> str:
        """Echo the user's message back"""
        return f"You said: {message}"


if __name__ == "__main__":
    agent = EchoAgent()
    asyncio.run(agent.run())

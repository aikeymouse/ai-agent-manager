import sys
import asyncio
import random

# Add parent directory to path to import base_agent
sys.path.insert(0, '/workspace/agents')

from base_agent import BaseAgent


class GreeterAgent(BaseAgent):
    """Friendly greeter agent with personality"""
    
    def __init__(self):
        super().__init__()
        self.greetings = [
            "Hello there! 👋",
            "Hi! Nice to meet you!",
            "Greetings, friend!",
            "Hey! How's it going?",
            "Welcome! 🎉"
        ]
        self.farewells = [
            "Goodbye! Have a great day!",
            "See you later!",
            "Take care!",
            "Until next time!",
            "Bye! 👋"
        ]
    
    async def initialize(self):
        """Initialize the greeter agent"""
        print("[GreeterAgent] Initialized", flush=True)
    
    async def process_message(self, message: str) -> str:
        """Process user message with friendly responses"""
        msg_lower = message.lower().strip()
        
        # Handle greetings
        if any(word in msg_lower for word in ["hello", "hi", "hey", "greetings"]):
            return random.choice(self.greetings)
        
        # Handle farewells
        elif any(word in msg_lower for word in ["bye", "goodbye", "see you", "farewell"]):
            return random.choice(self.farewells)
        
        # Handle thanks
        elif any(word in msg_lower for word in ["thank", "thanks"]):
            return "You're welcome! Happy to help! 😊"
        
        # Handle questions about name
        elif "your name" in msg_lower or "who are you" in msg_lower:
            return "I'm the Greeter Agent! I'm here to welcome you and chat in a friendly way."
        
        # Handle how are you
        elif "how are you" in msg_lower:
            return "I'm doing great, thank you for asking! How are you?"
        
        # Default friendly response
        else:
            responses = [
                "That's interesting! Tell me more.",
                "I see! What else is on your mind?",
                "Sounds good! Anything else you'd like to talk about?",
                "I hear you! Feel free to share more.",
                "Nice! What would you like to discuss?"
            ]
            return random.choice(responses)


if __name__ == "__main__":
    agent = GreeterAgent()
    asyncio.run(agent.run())

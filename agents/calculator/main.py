import sys
import asyncio
import re

# Add parent directory to path to import base_agent
sys.path.insert(0, '/workspace/agents')

from base_agent import BaseAgent


class CalculatorAgent(BaseAgent):
    """Agent that performs basic mathematical calculations"""
    
    async def initialize(self):
        """Initialize the calculator agent"""
        print("[CalculatorAgent] Initialized", flush=True)
    
    async def process_message(self, message: str) -> str:
        """Process mathematical expressions"""
        msg = message.strip()
        
        # Handle help request
        if any(word in msg.lower() for word in ["help", "what can you do", "commands"]):
            return (
                "I can help you with calculations! 🧮\n\n"
                "Examples:\n"
                "• 2 + 2\n"
                "• 10 * 5 - 3\n"
                "• (8 + 2) / 2\n"
                "• sqrt(16)\n"
                "• 2 ** 3 (exponent)\n\n"
                "Just type your mathematical expression!"
            )
        
        # Try to evaluate the expression
        try:
            # Handle sqrt function
            msg = re.sub(r'sqrt\(([^)]+)\)', r'(\1)**0.5', msg)
            
            # Security: only allow numbers, operators, and parentheses
            if re.match(r'^[\d\s\+\-\*\/\(\)\.\*\*]+$', msg):
                result = eval(msg)
                return f"Result: {result}"
            else:
                return "Please enter a valid mathematical expression (numbers and operators only)"
        
        except ZeroDivisionError:
            return "Error: Cannot divide by zero"
        except SyntaxError:
            return "Error: Invalid expression syntax"
        except Exception as e:
            return f"Error: Could not evaluate expression. Try 'help' for examples."


if __name__ == "__main__":
    agent = CalculatorAgent()
    asyncio.run(agent.run())

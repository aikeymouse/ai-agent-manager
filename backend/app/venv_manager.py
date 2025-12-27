import os
import asyncio
import subprocess
from typing import Dict, Optional, AsyncIterator
from app.config import settings
import logging
import signal

logger = logging.getLogger(__name__)


class VenvManager:
    """Manages agent processes in isolated virtual environments within the sandbox container"""
    
    def __init__(self):
        self.sandbox_container = os.getenv('SANDBOX_CONTAINER', 'ai-agent-sandbox')
        self.active_processes: Dict[int, subprocess.Popen] = {}
        logger.info(f"VenvManager initialized for sandbox container: {self.sandbox_container}")
        
    def get_available_agents(self):
        """Scan agents directory for available agents"""
        agents = []
        agents_path = settings.agents_path
        
        if not os.path.exists(agents_path):
            logger.warning(f"Agents path {agents_path} does not exist")
            return agents
        
        for item in os.listdir(agents_path):
            agent_dir = os.path.join(agents_path, item)
            main_file = os.path.join(agent_dir, "main.py")
            
            if os.path.isdir(agent_dir) and os.path.exists(main_file):
                # Read agent metadata if available
                metadata_file = os.path.join(agent_dir, "agent_metadata.json")
                description = ""
                
                if os.path.exists(metadata_file):
                    import json
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            description = metadata.get("description", "")
                    except:
                        pass
                
                agents.append({
                    "name": item,
                    "description": description
                })
        
        return agents
    
    def _setup_venv(self, agent_name: str, session_id: int) -> str:
        """Create virtual environment for the agent in the sandbox container"""
        venv_name = f"agent-{session_id}-{agent_name}"
        venv_path = f"/workspace/venvs/{venv_name}"
        
        try:
            # Create venv in sandbox container
            create_cmd = [
                "docker", "exec", self.sandbox_container,
                "python", "-m", "venv", venv_path
            ]
            
            logger.info(f"Creating venv: {venv_path}")
            subprocess.run(create_cmd, check=True, capture_output=True, text=True)
            
            # Install base dependencies (websockets)
            install_cmd = [
                "docker", "exec", self.sandbox_container,
                f"{venv_path}/bin/pip", "install", "-q", "websockets"
            ]
            
            logger.info(f"Installing base dependencies in {venv_name}")
            subprocess.run(install_cmd, check=True, capture_output=True, text=True)
            
            # Install agent-specific requirements if they exist
            requirements_path = f"/workspace/agents/{agent_name}/requirements.txt"
            check_req_cmd = [
                "docker", "exec", self.sandbox_container,
                "test", "-f", requirements_path
            ]
            
            if subprocess.run(check_req_cmd, capture_output=True).returncode == 0:
                logger.info(f"Installing agent-specific requirements for {agent_name}")
                install_agent_req_cmd = [
                    "docker", "exec", self.sandbox_container,
                    f"{venv_path}/bin/pip", "install", "-q", "-r", requirements_path
                ]
                subprocess.run(install_agent_req_cmd, check=True, capture_output=True, text=True)
            
            return venv_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to setup venv: {e.stderr}")
            raise
    
    def spawn_agent(self, agent_name: str, session_id: int) -> tuple[str, int]:
        """Spawn a new agent process in the sandbox container"""
        
        try:
            # Setup virtual environment
            venv_path = self._setup_venv(agent_name, session_id)
            
            # Prepare environment variables
            env_vars = [
                "-e", f"AGENT_NAME={agent_name}",
                "-e", f"SESSION_ID={session_id}",
                "-e", f"BACKEND_HOST={settings.backend_host}",
                "-e", f"BACKEND_PORT={settings.backend_port}"
            ]
            
            # Start agent process in sandbox container
            cmd = [
                "docker", "exec", "-d"
            ] + env_vars + [
                self.sandbox_container,
                f"{venv_path}/bin/python",
                f"/workspace/agents/{agent_name}/main.py"
            ]
            
            logger.info(f"Starting agent {agent_name} in session {session_id}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # The process ID from docker exec -d isn't directly useful
            # We'll use session_id as the identifier
            process_id = session_id
            
            logger.info(f"Spawned agent {agent_name} for session {session_id}")
            
            return f"venv-{session_id}", process_id
            
        except Exception as e:
            logger.error(f"Failed to spawn agent: {e}")
            raise
    
    async def stream_logs(self, session_id: int) -> AsyncIterator[str]:
        """Stream agent logs from the sandbox container"""
        log_file = f"/workspace/logs/agent-{session_id}.log"
        
        try:
            # Use docker exec to tail the log file
            cmd = [
                "docker", "exec", self.sandbox_container,
                "tail", "-f", log_file
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            for line in iter(process.stdout.readline, ''):
                if line:
                    yield line.strip()
                    await asyncio.sleep(0)
                    
        except Exception as e:
            logger.error(f"Error streaming logs: {e}")
    
    def stop_agent(self, session_id: int):
        """Stop agent process in sandbox container"""
        try:
            # Find and kill the process using the venv path pattern
            cmd = [
                "docker", "exec", self.sandbox_container,
                "sh", "-c", f"pkill -f 'agent-{session_id}-'"
            ]
            
            logger.info(f"Stopping agent for session {session_id}")
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully killed process for session {session_id}")
            else:
                logger.warning(f"No process found for session {session_id} (may already be stopped)")
            
            # Clean up venv
            cleanup_cmd = [
                "docker", "exec", self.sandbox_container,
                "sh", "-c", f"rm -rf /workspace/venvs/agent-{session_id}-*"
            ]
            
            subprocess.run(cleanup_cmd, check=False, capture_output=True)
            
            if session_id in self.active_processes:
                del self.active_processes[session_id]
            
            logger.info(f"Stopped agent for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error stopping agent: {e}")
            raise
    
    def get_container_status(self, session_id: int) -> Optional[str]:
        """Get agent process status"""
        try:
            # Check if process is running by looking for the venv path
            cmd = [
                "docker", "exec", self.sandbox_container,
                "sh", "-c", f"ps aux | grep 'agent-{session_id}-' | grep -v grep"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                return "running"
            else:
                return "exited"
                
        except Exception as e:
            logger.error(f"Error getting process status: {e}")
            return None
    
    def cleanup_all(self):
        """Clean up all agent processes and venvs"""
        try:
            # Kill all agent processes
            kill_cmd = [
                "docker", "exec", self.sandbox_container,
                "pkill", "-f", "agents/.*/main.py"
            ]
            subprocess.run(kill_cmd, check=False, capture_output=True)
            
            # Clean up all venvs
            cleanup_cmd = [
                "docker", "exec", self.sandbox_container,
                "sh", "-c", "rm -rf /workspace/venvs/*"
            ]
            subprocess.run(cleanup_cmd, check=False, capture_output=True)
            
            self.active_processes.clear()
            logger.info("Cleaned up all agents")
            
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")


# Global instance
container_manager = VenvManager()

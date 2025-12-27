# AI Agent Manager

Web UI to create, manage, and communicate with AI agents running in isolated virtual environments.

## Features

- **Dynamic Process Management**: Each agent runs in its own Python virtual environment
- **Shared Agent Code**: Python agent code mounted from shared volumes
- **Streaming Chat**: Real-time WebSocket communication with agents
- **Agent Selection**: Create and select from available agents
- **Sandbox Isolation**: All agents run in a dedicated sandbox container

## Architecture

```
├── backend/          # FastAPI server with venv management
├── frontend/         # React + Vite web UI
├── agents/           # Shared Python agent code (mounted to sandbox)
├── agents-sandbox/   # Dedicated container for running agent processes
└── docker-compose.yml
```

**Sandbox Architecture:**
- **agents-sandbox**: Dedicated container hosting all agent processes
- **backend**: FastAPI server manages venvs and spawns processes via `docker exec`
- **Agent processes**: Each runs in isolated Python venv within sandbox
- **Security**: Lightweight isolation via virtual environments, read-only agent code

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)

### Run with Docker Compose

```bash
docker-compose up --build
```

- Frontend: http://localhost:8500
- Backend API: http://localhost:5500
- API Docs: http://localhost:5500/docs

### Development Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Usage

1. Open the web UI at http://localhost:8500
2. Select an agent from the dropdown
3. Click "Run Agent" to spawn the agent process
4. Chat with the agent in real-time
5. Agent process stops when session is terminated

## Security

- Agents run in isolated Python virtual environments
- Agent code mounted as read-only
- Custom bridge network for container isolation
- Sandbox container runs without privileged mode

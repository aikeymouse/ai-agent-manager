# Ollama Agent

AI assistant powered by Ollama with configurable model support.

## Requirements

- Ollama must be running on the host machine
- The configured model must be pulled (e.g., `ollama pull llama3.1:8b`)

## Configuration

Edit `agent_metadata.json` to configure the model and timeout:

```json
{
  "name": "ollama",
  "description": "AI assistant powered by Ollama",
  "model": "llama3.1:8b",
  "timeout": 120
}
```

**Configuration options:**
- `model`: The Ollama model to use (default: `llama3.1:8b`)
- `timeout`: Request timeout in seconds (default: 60, recommended: 120 for larger models)

Available models (if you have them pulled):
- `llama3.1:8b` - Default, balanced performance
- `mistral:7b` - Fast and efficient
- Any other Ollama model you have installed

## Features

- Natural language conversations
- Maintains conversation history
- Connects to Ollama via host.docker.internal
- Configurable model selection

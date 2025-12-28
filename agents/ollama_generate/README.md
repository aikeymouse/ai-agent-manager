# Ollama Generate Agent

AI assistant powered by Ollama's `/api/generate` endpoint for raw text completions.

## Differences from Ollama Chat Agent

This agent uses the lower-level `/api/generate` endpoint instead of `/api/chat`:

- **More control**: Direct prompt construction, custom formatting
- **Raw completions**: No enforced conversation structure
- **Simpler**: Single prompt in, response out
- **Use case**: When you need custom prompt templates or don't want OpenAI-style message format

## Requirements

- Ollama must be running on the host machine
- The configured model must be pulled (e.g., `ollama pull llama3.1:8b`)

## Configuration

Edit `agent_metadata.json`:

```json
{
  "name": "ollama-generate",
  "description": "AI assistant powered by Ollama /api/generate endpoint",
  "model": "llama3.1:8b",
  "timeout": 120,
  "base_url": "http://host.docker.internal:11434",
  "model_endpoint": "/api/generate",
  "stream": true,
  "system_prompt": "You are a helpful AI assistant.",
  "options": {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "num_predict": 512,
    "num_ctx": 8192,
    "repeat_penalty": 1.1
  }
}
```

### Configuration Options

#### Basic Settings

- **`model`**: The Ollama model to use (default: `llama3.1:8b`)
- **`timeout`**: Request timeout in seconds (default: 120)
- **`stream`**: Enable streaming responses (default: `true`)
- **`base_url`**: Ollama server URL (default: `http://host.docker.internal:11434`)
- **`model_endpoint`**: API endpoint (must be `/api/generate` for this agent)
- **`system_prompt`**: System instructions prepended to every prompt (default: `"You are a helpful AI assistant."`)

#### LLM Options

Same as the Ollama Chat agent. See the main Ollama agent README for detailed explanations of:
- `temperature` - Controls randomness (0.0-2.0)
- `top_p` - Nucleus sampling (0.0-1.0)
- `top_k` - Top-k sampling (int)
- `num_predict` - Max tokens to generate
- `num_ctx` - Context window size
- `repeat_penalty` - Prevent repetition (1.0+)
- `seed` - For reproducible outputs (optional)

### Recommended Presets

Same presets as Ollama Chat agent work here. Examples:

#### Precise/Factual
```json
"options": {
  "temperature": 0.1,
  "top_p": 0.1,
  "top_k": 10,
  "repeat_penalty": 1.1
}
```

#### Creative
```json
"options": {
  "temperature": 1.2,
  "top_p": 0.95,
  "top_k": 100,
  "repeat_penalty": 1.2
}
```

## How It Works

### Prompt Construction

The agent builds prompts from conversation history:

```
System: You are a helpful AI assistant.

User: Hello
Assistant: Hi there! How can I help you?
User: What's 2+2?
Assistant: 
```

This gives you more control over the exact prompt format compared to `/api/chat`.

### API Differences

**`/api/generate`** (this agent):
```json
{
  "model": "llama3.1:8b",
  "prompt": "User: Hello\nAssistant: ",
  "stream": true
}
```

**`/api/chat`** (standard Ollama agent):
```json
{
  "model": "llama3.1:8b",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "stream": true
}
```

### Response Format

Streaming responses yield chunks with `"response"` field (not `"message"`):

```json
{"response": "Hi", "done": false}
{"response": " there", "done": false}
{"response": "!", "done": true}
```

## When to Use This Agent

✅ **Use `/api/generate` (this agent) when:**
- You need custom prompt formatting
- Working with models that don't follow chat format well
- Implementing custom conversation logic
- Need raw text completions
- Want full control over prompt construction

❌ **Use `/api/chat` (standard Ollama agent) when:**
- Building standard chatbots
- Want automatic conversation formatting
- Using models trained on chat templates
- Prefer OpenAI-compatible API structure

## Features

- Raw text generation using `/api/generate`
- Custom system prompts
- Manual conversation history management
- Configurable response generation
- Streaming support
- Full control over prompt format

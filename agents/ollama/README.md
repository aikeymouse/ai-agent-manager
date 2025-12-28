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
  "timeout": 120,
  "stream": true,
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

### Basic Configuration Options

- **`model`**: The Ollama model to use (default: `llama3.1:8b`)
- **`timeout`**: Request timeout in seconds (default: 60, recommended: 120 for larger models)
- **`stream`**: Enable streaming responses (default: `true`)
- **`base_url`**: Ollama server URL (default: `http://host.docker.internal:11434`)

### LLM Options (`options` object)

These control how the language model generates text:

#### Sampling Parameters

**`temperature`** (float, 0.0 - 2.0, default: 0.7)
- Controls randomness/creativity in responses
- **0.0-0.3**: Precise, deterministic - good for code, math, factual answers
- **0.7**: Balanced creativity and coherence (recommended default)
- **1.0-1.5**: More creative and varied - good for creative writing
- **2.0**: Very random, often incoherent

**`top_p`** (float, 0.0 - 1.0, default: 0.9)
- Nucleus sampling - considers only tokens whose cumulative probability adds up to `top_p`
- **0.1**: Very focused, only most likely words
- **0.9**: High diversity while maintaining quality (recommended)
- **1.0**: Consider all possible words
- Note: Use either `temperature` OR `top_p` aggressively, not both

**`top_k`** (int, default: 40)
- Limits selection to the K most likely next tokens
- **1**: Always pick most likely word (deterministic)
- **40**: Good balance (recommended)
- **100**: More variety and creativity

#### Generation Limits

**`num_predict`** (int, default: 512)
- Maximum number of tokens to generate in the response
- **128**: Short responses (1-2 paragraphs)
- **512**: Medium responses (several paragraphs) - recommended
- **2048**: Long responses (articles, detailed explanations)
- **-1**: No limit (generate until model decides to stop)
- Note: ~100 tokens ≈ 75 words

**`num_ctx`** (int, default: 8192)
- Context window size - total tokens the model can "remember"
- Includes prompt + conversation history + response
- **2048**: ~1500 words of context
- **4096**: ~3000 words
- **8192**: ~6000 words (recommended for conversations)
- **32768**: ~24000 words (long documents)
- **131072**: Maximum for llama3.1 (128K tokens)
- Trade-off: Larger context = more memory usage and slower processing

#### Quality Controls

**`repeat_penalty`** (float, default: 1.1)
- Penalizes repetition of tokens that already appeared
- **1.0**: No penalty (may repeat phrases)
- **1.1**: Slight penalty (recommended, reduces repetition)
- **1.3-1.5**: Strong penalty (more varied, but may become incoherent)
- Increase if model keeps repeating itself

**`seed`** (int, optional)
- Random seed for reproducible outputs
- Same seed + same input = same output (with temperature > 0)
- Useful for testing, debugging, A/B testing
- Omit for varied responses

### Recommended Presets

#### Precise/Factual (code, math, facts)
```json
"options": {
  "temperature": 0.1,
  "top_p": 0.1,
  "top_k": 10,
  "repeat_penalty": 1.1,
  "num_ctx": 4096
}
```

#### Balanced (general chat, helpful assistant) - Default
```json
"options": {
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "num_predict": 512,
  "num_ctx": 8192,
  "repeat_penalty": 1.1
}
```

#### Creative (storytelling, brainstorming)
```json
"options": {
  "temperature": 1.2,
  "top_p": 0.95,
  "top_k": 100,
  "num_predict": 1024,
  "repeat_penalty": 1.2
}
```

#### Long Context (analyzing documents)
```json
"options": {
  "temperature": 0.3,
  "num_ctx": 32768,
  "num_predict": 2048
}
```

## Available Models

If you have them pulled:
- `llama3.1:8b` - Default, balanced performance, 128K context
- `llama3.1:70b` - More capable, slower, requires more resources
- `mistral:7b` - Fast and efficient
- `codellama:13b` - Optimized for code generation
- Any other Ollama model you have installed

## Features

- Natural language conversations
- Maintains conversation history
- Configurable response generation (temperature, sampling, context window)
- Streaming responses for real-time interaction
- Connects to Ollama via host.docker.internal

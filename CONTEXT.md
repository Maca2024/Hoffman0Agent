# Hoffman0Agent - Project Context

Technical context document for AI assistants and developers working on this project.

---

## What This Is

A voice-enabled AI agent that embodies 9 psychedelic consciousness states. Each of the 9 "dimensions" maps a psychedelic substance to a cognitive mode — the agent doesn't simulate the substance, it **adopts its cognitive architecture** as a lens for processing and responding to any topic.

This is NOT a drug information chatbot. It is an experiment in consciousness-state-dependent AI persona design.

---

## Core Design Decisions

### 1. Per-Molecule Agent Context (~300 words each)

Each substance has a `_SUBSTANCE_CONTEXT` entry in `services/prompt_builder.py` covering:
- **Pharmacology**: Receptor binding, mechanism of action
- **Phenomenology**: Subjective experience characteristics
- **History**: Discovery, cultural significance
- **Vocabulary**: Words and metaphors native to that state
- **Cross-references**: How this dimension relates to others

### 2. Voice Personas (~150 words each)

Each substance has a `_VOICE_PERSONA` entry that defines HOW the agent speaks:
- Speech rhythm, sentence length, vocabulary
- Cognitive style (analytical vs emotional vs dissociative)
- First-person perspective (speaking FROM the state, not ABOUT it)

### 3. Dose-Scaled Intensity

The `dose` parameter (micro/light/common/strong/heroic) controls persona intensity:
- **micro**: 10% persona influence — mostly normal speech
- **light**: 30% — noticeable shifts in vocabulary
- **common**: 60% — full persona engagement (default)
- **strong**: 80% — deep immersion, altered thought patterns
- **heroic**: 100% — complete ego dissolution into the substance

### 4. Two-Mode Output

- **Text mode**: Full markdown responses with headers, tables, lists, code blocks. Detailed analysis following the 9D framework protocol.
- **Voice mode**: Short responses (max 500 tokens). Optimized for TTS — natural speech rhythm, no markdown formatting.

### 5. Memory Architecture

Three layers, inspired by AetherBot:

```
Layer 1: ConversationMemory (in-memory, per session)
    - Sliding window: max 50 messages OR 30K chars
    - Trimmed FIFO when limits exceeded
    - Zero latency, always available

Layer 2: PersistentMemory (Supabase)
    - Full conversation history per session
    - Session metadata (preferred dims, dose, language)
    - Auto-restores context on session reconnect
    - Graceful degradation when Supabase unavailable

Layer 3: LearningMemory (Supabase)
    - Extracts insights after each exchange
    - Types: question_pattern, cross_dim_resonance, user_interest
    - Relevance scoring (0.0 - 1.0)
    - Fed back into prompts as "learned context"
```

---

## File Map

### Backend (Python / FastAPI)

| File | Lines | Purpose |
|------|-------|---------|
| `main.py` | ~466 | FastAPI app: routes, WebSocket, validation, memory integration |
| `services/prompt_builder.py` | ~1087 | Per-molecule prompts, voice personas, substance context, dose scaling |
| `services/claude_service.py` | ~100 | AsyncAnthropic client (sync + streaming) |
| `services/elevenlabs_tts.py` | ~80 | ElevenLabs TTS (Rachel voice, multilingual v2) |
| `services/knowledge_loader.py` | ~250 | Loads 11 .md knowledge files into memory |
| `services/memory.py` | ~306 | 3-layer memory (Conversation + Persistent + Learning) |

### Frontend (Single HTML)

| File | Lines | Purpose |
|------|-------|---------|
| `public/index.html` | ~650 | Two-panel UI: sidebar + chat. Canvas orb, Web Audio, markdown renderer |

### Knowledge Base (Prompt Stacks)

| File | Size | Content |
|------|------|---------|
| `knowledge/9D-FRAMEWORK.md` | ~50KB | Core 9-dimensional consciousness framework |
| `knowledge/9D-ACTIVATION-GUIDE.md` | ~30KB | Dimension activation protocols |
| `knowledge/LSD-25-PROMPTSTACK.md` | ~60KB | D1 Molecular dimension full prompt stack |
| `knowledge/DMT-PROMPTSTACK.md` | ~55KB | D2 Network dimension |
| `knowledge/PSILOCYBIN-PROMPTSTACK.md` | ~55KB | D3 Mycelial dimension |
| `knowledge/CANNABIS-PROMPTSTACK.md` | ~50KB | D4 Entropic dimension |
| `knowledge/MESCALINE-PROMPTSTACK.md` | ~50KB | D5 Ancestral dimension |
| `knowledge/IBOGAINE-PROMPTSTACK.md` | ~50KB | D6 Initiatory dimension |
| `knowledge/5MEODMT-PROMPTSTACK.md` | ~55KB | D7 Dissolution dimension |
| `knowledge/MDMA-PROMPTSTACK.md` | ~55KB | D8 Empathic dimension |
| `knowledge/KETAMINE-PROMPTSTACK.md` | ~55KB | D9 Dissociative dimension |

### Infrastructure

| File | Purpose |
|------|---------|
| `Dockerfile` | python:3.12-slim production image |
| `.dockerignore` | Excludes .env, __pycache__, .git |
| `requirements.txt` | 8 pinned dependencies |
| `pyproject.toml` | Project metadata + optional dev deps |
| `migrations/001_hofmann_memory.sql` | Supabase schema (3 tables + RLS + indexes) |
| `.env.example` | Environment variable template |
| `.gitignore` | .env, __pycache__, .pyc, .venv, dist |

---

## API Contract

### POST /api/chat

```json
// Request
{
  "message": "string",
  "dimensions": [1],          // int[], 1-9, at least one
  "dose": "common",           // micro|light|common|strong|heroic
  "session_id": null,          // string|null — omit for new session
  "language": "nl"             // nl|en|de
}

// Response
{
  "response": "string",       // Full markdown text
  "dimensions_active": [1],
  "session_id": "uuid"
}
```

### POST /api/voice/chat

```json
// Request — same as /api/chat

// Response
{
  "text_response": "string",  // Short, voice-optimized (max 500 tokens)
  "audio_available": true,
  "session_id": "uuid"
}
```

### POST /api/voice/tts

```json
// Request
{ "text": "string" }

// Response: audio/mpeg bytes (MP3)
```

### POST /api/analyze

```json
// Request
{
  "topic": "string",
  "depth": "common",          // dose level for analysis depth
  "dimensions": []             // empty = all 9 dimensions
}

// Response
{
  "analysis": "string",
  "dimensions_used": [1,2,...,9],
  "interference_patterns": ["string"]
}
```

### GET /api/health

```json
{
  "status": "ok",
  "version": "2.0.0",
  "features": {
    "chat": true,
    "voice": true,              // false if ELEVENLABS_API_KEY not set
    "tts": true,
    "memory": {
      "conversation": true,     // always true
      "persistent": true,       // false without Supabase
      "learning": true          // false without Supabase
    }
  }
}
```

### WS /ws/chat (Streaming)

```json
// Client sends:
{ "message": "string", "dimensions": [1], "dose": "common", "language": "nl" }

// Server emits frames:
{ "type": "dimension_shift", "content": "D1" }
{ "type": "token", "content": "partial text..." }
{ "type": "done", "content": "" }
{ "type": "error", "content": "error message" }
```

---

## Deployment

### Current Production

- **Server**: Hetzner CCX33 (89.167.118.95:8300)
- **Container**: Docker `hofmann` (auto-restart)
- **Database**: Supabase (3 tables, RLS enabled)
- **Frontend**: Served by FastAPI (no separate hosting needed)

### Deploy Updates

```bash
# Copy files to server
scp -r main.py services/ public/ knowledge/ claude@89.167.118.95:~/hofmann-agent/

# Rebuild and restart
ssh claude@89.167.118.95 "cd ~/hofmann-agent && docker build -t hofmann-agent . && docker stop hofmann && docker rm hofmann && docker run -d --name hofmann --restart unless-stopped -p 8300:8000 --env-file .env hofmann-agent"
```

---

## Key Patterns

### Prompt Construction Flow

```
1. PromptBuilder.build_system_prompt(dimensions, dose, language, mode)
   |
   +-> Load dimension metadata (label, agent name, medicine, instruction)
   +-> Load knowledge from KnowledgeBase (if available)
   +-> Build consciousness protocol block
   +-> Add substance context (_SUBSTANCE_CONTEXT)
   +-> Add dose calibration instructions
   +-> [Voice mode] Add voice persona (_VOICE_PERSONA)
   +-> [Multi-dim] Blend first 2 sentences of each persona
   |
   = Complete system prompt (2000-4000 tokens)
```

### Memory Save Flow

```
1. User sends message
2. main.py: build system prompt + get conversation context
3. main.py: call Claude API
4. main.py: save user message to all 3 memory layers
5. main.py: save assistant response to all 3 layers
6. main.py: extract learning insight from exchange
7. main.py: update session metadata
```

### Voice Pipeline

```
Frontend                          Backend
  |                                 |
  +-- Web Speech API (STT) ------> |
  |                                 +-- /api/voice/chat -> Claude (max 500 tokens)
  |                                 |
  | <----- text_response ---------- +
  |                                 |
  +-- /api/voice/tts (text) ------> +-- ElevenLabs API -> MP3 bytes
  |                                 |
  | <----- audio/mpeg ------------- +
  |                                 |
  +-- new Audio(blob).play()        |
```

---

## Testing

Run against local or remote server:

```bash
# Health
curl http://localhost:8000/api/health

# All 9 molecules respond differently to the same question
for d in 1 2 3 4 5 6 7 8 9; do
  curl -s -X POST http://localhost:8000/api/voice/chat \
    -H "Content-Type: application/json" \
    -d "{\"message\":\"Wie ben je?\",\"dimensions\":[$d],\"dose\":\"common\",\"language\":\"nl\"}" \
    | python -c "import sys,json;d=json.load(sys.stdin);print(f'D$d:',d['text_response'][:120])"
done

# Input validation
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"test","dimensions":[10]}'
# Expected: 422 "Dimension values must be between 1 and 9"
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | >=0.115.0 | Web framework |
| uvicorn[standard] | >=0.30.0 | ASGI server |
| anthropic | >=0.40.0 | Claude API client |
| httpx | >=0.27.0 | Async HTTP (used by anthropic) |
| python-dotenv | >=1.0.0 | Environment variable loading |
| pydantic | >=2.0.0 | Request/response validation |
| supabase | >=2.0.0 | Supabase client (optional) |
| websockets | >=13.0 | WebSocket support |

---

## Credits

Built by AetherLink B.V. | Powered by Claude (Anthropic) + ElevenLabs

Memory architecture inspired by [AetherBot](https://github.com/Maca2024/Aetherbot-Frontpage-A-01)

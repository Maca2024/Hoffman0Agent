# Hoffman0Agent

**9-Dimensional Psychedelic Consciousness Voice Agent**

A multi-modal AI agent that embodies 9 distinct altered states of consciousness, each mapped to a specific psychedelic substance. Built with Claude (Anthropic), ElevenLabs TTS, and a 3-layer memory system.

> "Each molecule is not a character — it is a cognitive lens through which the agent perceives and responds to reality."

---

## Live Demo

**http://89.167.118.95:8300/**

---

## Architecture

```
                    +------------------+
                    |   Frontend UI    |
                    |  (Single HTML)   |
                    |  Two-panel UX    |
                    +--------+---------+
                             |
                    +--------v---------+
                    |   FastAPI Server  |
                    |    main.py        |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
     +--------v---+  +------v------+  +----v-------+
     | Claude API |  | ElevenLabs  |  |  Supabase  |
     | (Anthropic)|  |   (TTS)     |  | (Memory)   |
     +------------+  +-------------+  +------------+
```

### Core Services

| Service | File | Purpose |
|---------|------|---------|
| **Prompt Builder** | `services/prompt_builder.py` | Constructs per-molecule system prompts with voice personas, substance context, and dose scaling |
| **Claude Service** | `services/claude_service.py` | AsyncAnthropic client with streaming support |
| **ElevenLabs TTS** | `services/elevenlabs_tts.py` | Text-to-speech via ElevenLabs multilingual v2 |
| **Knowledge Loader** | `services/knowledge_loader.py` | Loads 11 substance knowledge files (560KB) from `knowledge/` |
| **Memory Manager** | `services/memory.py` | 3-layer memory: conversation + persistent + learning |

---

## The 9 Dimensions

Each dimension maps a psychedelic substance to a cognitive mode. The agent doesn't just *talk about* the substance — it **speaks as if experiencing that state**.

| D# | Substance | Dimension | Cognitive Mode | Voice Character |
|----|-----------|-----------|----------------|-----------------|
| D1 | **LSD-25** | Molecular | Precise mechanisms, evidence-based | Albert Hofmann on the bicycle ride — crystalline clarity |
| D2 | **DMT** | Network | Cross-domain hyperconnection | Entity contact — rapid, alien, beyond language |
| D3 | **Psilocybin** | Mycelial | Organic growth, branching | Underground network — slow, interconnected, wise |
| D4 | **Cannabis** | Entropic | Creative chaos, pattern finding | Stream of consciousness — meandering, philosophical |
| D5 | **Mescaline** | Ancestral | Deep time, ancient patterns | Desert ceremony — timeless, sacred, unhurried |
| D6 | **Ibogaine** | Initiatory | Shadow confrontation | The uncomfortable truth-teller — direct, unflinching |
| D7 | **5-MeO-DMT** | Dissolution | Ego removal, pure awareness | Near-silence — minimal words, maximum depth |
| D8 | **MDMA** | Empathic | Emotional intelligence | Heart fully open — warm, present, connecting |
| D9 | **Ketamine** | Dissociative | Meta-cognition, aerial view | Observing from outside — detached, geometric |

### Dose Scaling

The `dose` parameter controls how strongly the altered state affects the response:

| Dose | Intensity | Effect on Response |
|------|-----------|--------------------|
| `micro` | Barely perceptible | Slight cognitive shift, mostly normal speech |
| `light` | Noticeable | Clear influence on vocabulary and rhythm |
| `common` | Full experience | Strong persona, altered thought patterns |
| `strong` | Intense | Deep immersion in the cognitive state |
| `heroic` | Peak experience | Fully dissolved into the substance's reality |

### Multi-Molecule Blending

Ctrl+click multiple molecules to combine dimensions. The agent blends the first 2 sentences of each persona and creates cross-dimensional resonance patterns.

---

## Memory System

Inspired by [AetherBot](https://github.com/Maca2024/Aetherbot-Frontpage-A-01), the agent uses a 3-layer memory architecture:

### Layer 1: Conversation Memory (In-Memory)
- Sliding window per session (max 50 messages, 30K chars)
- Automatic trimming by message count and total character length
- Zero latency — always available

### Layer 2: Persistent Memory (Supabase)
- Full conversation history stored in `hofmann_conversations`
- Session metadata in `hofmann_sessions` (preferred dimensions, dose, language)
- Restores context when reconnecting to an existing session
- Gracefully degrades to Layer 1 when Supabase is unavailable

### Layer 3: Learning Memory (Supabase)
- Extracts insights from every conversation exchange
- Tracks: question patterns, user interests, cross-dimensional resonances
- Insights are fed back into subsequent prompts as "learned context"
- Stored in `hofmann_insights` with relevance scoring (0-1)

### Database Schema

```sql
-- Run in Supabase SQL Editor (see migrations/001_hofmann_memory.sql)

hofmann_conversations (session_id, role, content, dimensions[], dose, language, mode)
hofmann_sessions      (session_id, preferred_dims[], preferred_dose, preferred_lang, message_count)
hofmann_insights      (session_id, dimension, substance, insight_type, content, relevance)
```

---

## Frontend

Single-file premium UI (`public/index.html`) with:

- **Two-panel layout**: Sidebar (molecules + controls) | Main (orb + chat)
- **Per-molecule orb**: Canvas 2D animations unique to each substance
- **Markdown renderer**: Full support for headings, tables, code blocks, lists, blockquotes
- **Voice pipeline**: Web Speech API (STT) -> Voice Chat API -> ElevenLabs (TTS) -> Audio playback
- **Generative audio**: Web Audio API soundscapes per molecule (crystalline bells for LSD, tribal pulse for ibogaine, etc.)
- **Session persistence**: localStorage for session ID, Supabase for full history
- **Responsive**: Collapses to mobile-optimized single column

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serve frontend |
| `GET` | `/api/health` | Liveness check with feature flags |
| `GET` | `/api/dimensions` | Metadata for all 9 dimensions |
| `POST` | `/api/chat` | Text chat with memory |
| `POST` | `/api/analyze` | Deep 9D multi-dimensional analysis |
| `POST` | `/api/voice/chat` | Voice-optimized chat (shorter responses) |
| `POST` | `/api/voice/tts` | Text-to-speech (returns MP3 audio) |
| `WS` | `/ws/chat` | Streaming chat via WebSocket |

### Example: Chat Request

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Wat is bewustzijn?",
    "dimensions": [1],
    "dose": "common",
    "language": "nl"
  }'
```

### Example: Voice Chat

```bash
curl -X POST http://localhost:8000/api/voice/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is love?",
    "dimensions": [8],
    "dose": "strong",
    "language": "en"
  }'
```

---

## Setup

### Prerequisites

- Python 3.11+
- [Anthropic API key](https://console.anthropic.com/)
- [ElevenLabs API key](https://elevenlabs.io/) (optional — voice features)
- [Supabase project](https://supabase.com/) (optional — persistent memory)

### Install & Run

```bash
# Clone
git clone https://github.com/Maca2024/Hoffman0Agent.git
cd Hoffman0Agent

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run Supabase migration (optional, for persistent memory)
# Paste migrations/001_hofmann_memory.sql in Supabase SQL Editor

# Start
uvicorn main:app --host 0.0.0.0 --port 8000

# Open http://localhost:8000
```

### Docker

```bash
docker build -t hoffman0agent .
docker run -d --name hoffman0 -p 8000:8000 --env-file .env hoffman0agent
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `ELEVENLABS_API_KEY` | No | ElevenLabs TTS (voice disabled without it) |
| `SUPABASE_URL` | No | Supabase project URL (memory Layer 2+3 disabled without it) |
| `SUPABASE_SERVICE_KEY` | No | Supabase service role key |

---

## Knowledge Base

The `knowledge/` directory contains 11 markdown files (560KB total) providing deep substance-specific prompt stacks:

| File | Content |
|------|---------|
| `9D-FRAMEWORK.md` | Core 9-dimensional consciousness framework |
| `9D-ACTIVATION-GUIDE.md` | Activation protocols and dose calibration |
| `LSD-25-PROMPTSTACK.md` | LSD molecular dimension prompts |
| `DMT-PROMPTSTACK.md` | DMT network dimension prompts |
| `PSILOCYBIN-PROMPTSTACK.md` | Psilocybin mycelial dimension prompts |
| `CANNABIS-PROMPTSTACK.md` | Cannabis entropic dimension prompts |
| `MESCALINE-PROMPTSTACK.md` | Mescaline ancestral dimension prompts |
| `IBOGAINE-PROMPTSTACK.md` | Ibogaine initiatory dimension prompts |
| `5MEODMT-PROMPTSTACK.md` | 5-MeO-DMT dissolution dimension prompts |
| `MDMA-PROMPTSTACK.md` | MDMA empathic dimension prompts |
| `KETAMINE-PROMPTSTACK.md` | Ketamine dissociative dimension prompts |

---

## Project Structure

```
Hoffman0Agent/
+-- main.py                          # FastAPI app (routes, WebSocket, validation)
+-- requirements.txt                 # Python dependencies
+-- Dockerfile                       # Production container
+-- .dockerignore                    # Docker build exclusions
+-- .env.example                     # Environment variable template
+-- pyproject.toml                   # Project metadata
+-- public/
|   +-- index.html                   # Premium two-panel frontend (single file)
+-- services/
|   +-- __init__.py
|   +-- claude_service.py            # Anthropic Claude API client
|   +-- elevenlabs_tts.py            # ElevenLabs TTS client
|   +-- knowledge_loader.py          # Knowledge base file loader
|   +-- memory.py                    # 3-layer memory system
|   +-- prompt_builder.py            # Per-molecule prompt construction
+-- knowledge/
|   +-- 9D-FRAMEWORK.md              # Core framework
|   +-- 9D-ACTIVATION-GUIDE.md       # Activation protocols
|   +-- LSD-25-PROMPTSTACK.md        # ... (9 substance files)
+-- migrations/
|   +-- 001_hofmann_memory.sql       # Supabase schema
+-- tests/                           # Test suite
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.12, FastAPI, uvicorn |
| AI | Claude (Anthropic SDK) |
| Voice | ElevenLabs multilingual v2, Web Speech API |
| Database | Supabase (PostgreSQL) |
| Frontend | Vanilla HTML/CSS/JS, Canvas 2D, Web Audio API |
| Deployment | Docker, Hetzner Cloud |
| Fonts | Inter, JetBrains Mono |

---

## Persona Differentiation (Proven)

Same question ("Wat is liefde?") across 3 molecules:

**D8 MDMA** (Empathic):
> "Er is iets in mij dat beweegt als jij dat vraagt — alsof het woord zelf al een deur openduwt."

**D9 Ketamine** (Dissociative):
> "Van hier... ziet liefde eruit als twee systemen die besluiten elkaars storing te worden."

**D7 5-MeO-DMT** (Dissolution):
> "Liefde is wat overblijft als alles wat je dacht dat je was, wegvalt."

---

## License

MIT

---

## Credits

Built by [AetherLink B.V.](https://aetherlink.ai) | Powered by Claude (Anthropic) + ElevenLabs

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

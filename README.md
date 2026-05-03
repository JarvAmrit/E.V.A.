# E.V.A. — Enhanced Voice Assistant

> A Jarvis-like, voice-commanded, autonomous AI assistant for macOS.  
> Speak to activate · Browse the web · Perform system tasks · Rendered in an Iron Man–style HUD.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  macOS                                                              │
│  ┌─────────────────────────────┐   WebSocket    ┌────────────────┐ │
│  │  Python Backend             │◄──────────────►│ Electron HUD   │ │
│  │  ─────────────────────────  │                │ ─────────────  │ │
│  │  Wake word (Porcupine)      │                │ Chat panel     │ │
│  │  STT (Whisper)              │                │ Browser iframe │ │
│  │  TTS (pyttsx3 / ElevenLabs) │                │ Activity feed  │ │
│  │  Agent (OpenAI + tools)     │                │ Waveform HUD   │ │
│  │    ├ web_search             │                └────────────────┘ │
│  │    ├ browse_url (Playwright)│                                   │
│  │    ├ system (AppleScript)   │                                   │
│  │    └ memory (ChromaDB)      │                                   │
│  └─────────────────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1 — Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10+ |
| Node.js | 18+ |
| macOS | 12+ (Monterey or later recommended) |

### 2 — Clone & configure

```bash
git clone https://github.com/JarvAmrit/E.V.A.
cd E.V.A.
cp .env.example .env
# Edit .env and fill in your API keys
```

### 3 — Install Python backend

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4 — Install Electron frontend

```bash
cd frontend
npm install
cd ..
```

### 5 — Run

**Terminal 1 – Backend:**
```bash
python -m backend.main
```

**Terminal 2 – Frontend:**
```bash
cd frontend
npm start
```

The HUD window opens automatically and connects to the backend.  
Say **"Hey Eva"** (or the configured keyword) to start a voice interaction.

---

## Configuration (`.env`)

Copy `.env.example` and fill in your values:

```ini
# Required
OPENAI_API_KEY=sk-...

# Optional — better TTS
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...

# Optional — wake word (get a free key at https://picovoice.ai)
PICOVOICE_ACCESS_KEY=...

# Optional — Bing Search (falls back to DuckDuckGo if not set)
BING_SEARCH_API_KEY=...

# Tunables
OPENAI_MODEL=gpt-4o
WHISPER_MODEL=base.en
TTS_BACKEND=pyttsx3        # or "elevenlabs"
WS_PORT=8765
SILENCE_THRESHOLD=0.01
SILENCE_DURATION=1.5
```

---

## Directory Structure

```
E.V.A./
├── backend/
│   ├── main.py              # Entry point & WebSocket server
│   ├── config.py            # Settings loaded from .env
│   ├── voice/
│   │   ├── wake_word.py     # Porcupine wake-word detector
│   │   ├── stt.py           # Whisper speech-to-text
│   │   └── tts.py           # pyttsx3 / ElevenLabs TTS
│   └── agent/
│       ├── orchestrator.py  # OpenAI function-calling agent loop
│       ├── prompts.py       # System prompt & persona
│       └── tools/
│           ├── web_search.py  # Bing / DuckDuckGo search
│           ├── browser.py     # Playwright headless browsing
│           ├── system.py      # macOS AppleScript integration
│           └── memory.py      # ChromaDB long-term memory
├── frontend/
│   ├── main.js              # Electron main process
│   ├── preload.js           # Secure IPC bridge
│   ├── package.json
│   └── renderer/
│       ├── index.html       # HUD layout
│       ├── style.css        # Iron Man dark glass-morphism UI
│       └── app.js           # WebSocket client & UI logic
├── data/
│   └── chroma/              # ChromaDB persistence (auto-created)
├── requirements.txt
└── README.md
```

---

## Features

| Feature | Status |
|---------|--------|
| Voice wake word ("Hey Eva") | ✅ Porcupine (offline) |
| Speech-to-text | ✅ OpenAI Whisper (local) |
| Text-to-speech | ✅ pyttsx3 (local) / ElevenLabs (cloud) |
| Conversational AI | ✅ GPT-4o with full tool use |
| Web search | ✅ Bing / DuckDuckGo |
| Web browsing | ✅ Playwright headless Chrome |
| In-HUD browser panel | ✅ Electron webview |
| Long-term memory | ✅ ChromaDB vector store |
| macOS Calendar/Reminders | ✅ AppleScript |
| iMessage sending | ✅ AppleScript |
| Battery level / screenshot | ✅ shell + screencapture |
| Iron Man HUD UI | ✅ Electron glass-morphism |
| Animated waveform | ✅ Canvas animation |

---

## macOS Permissions

On first run, macOS will prompt for:

- **Microphone** — required for voice input
- **Accessibility** — required for AppleScript to control Calendar, Messages, etc.
- **Screen Recording** — required for `take_screenshot`

Grant these in **System Settings → Privacy & Security**.

---

## Development Notes

- The backend falls back to an energy-based wake trigger (fires once on start) when `PICOVOICE_ACCESS_KEY` is not set, so you can test the full pipeline by typing in the HUD.
- The Whisper `base.en` model (~150 MB) is downloaded automatically on first use.
- ChromaDB persists to `data/chroma/` across sessions.

---

## License

MIT
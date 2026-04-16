# 🤖 Stewie — Voice-Controlled AI Assistant for Windows

> *"At your service, sir."*

Stewie is a JARVIS-inspired AI assistant that runs on your Windows laptop. Control it with your voice or remotely via Telegram.

## ✨ Features

- 🎙️ **Voice Control** — Wake word detection ("Hey Stewie") + natural language commands
- 🧠 **LLM-Powered NLU** — GPT-4o function-calling for intent parsing
- 💻 **System Control** — Brightness, volume, shutdown, restart, lock
- 📱 **App Management** — Open/close any Windows application by name
- 📖 **Screen Reading** — OCR + AI summarization of screen content
- ✍️ **Dictation** — Voice-to-typing in any application
- 🔍 **Web Research** — Search, scrape, and synthesize information
- 📄 **Document Creation** — Auto-generate Word documents from research
- 📱 **Telegram Integration** — Remote control from your phone
- 🎭 **JARVIS Personality** — Polished, witty, and helpful responses

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Windows 10/11
- Microphone
- Internet connection (for LLM API)

### Installation

```bash
# 1. Navigate to the project
cd stewie

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Edit .env with your API keys

# 5. Run Stewie
python main.py
```

### System Dependencies (Optional)

```bash
# For screen reading (OCR)
choco install tesseract

# For audio processing (Whisper)
choco install ffmpeg
```

## 🎤 Voice Commands

| Command | What it does |
|---|---|
| "Hey Stewie, open Chrome" | Launches Chrome |
| "Set brightness to 50" | Sets brightness to 50% |
| "Increase the volume" | Raises system volume |
| "Search for Python tutorials" | Web search |
| "Read the screen" | OCR + read aloud |
| "Summarize the screen" | AI summary of visible content |
| "Research Jenkins architecture and create a Word document" | Full research pipeline |
| "Shut down in 60 seconds" | Scheduled shutdown |
| "Lock the screen" | Locks workstation |

## 📱 Telegram Commands

| Command | Description |
|---|---|
| `/status` | Check if Stewie is online |
| `/order <details>` | Place an order |
| `/run <command>` | Execute a voice-style command |
| `/screen` | Get a screenshot |
| `/say <text>` | Make Stewie speak |
| `/brightness <0-100>` | Set brightness |
| `/volume <0-100>` | Set volume |

## 📁 Project Structure

```
stewie/
├── config/          # Settings, app registry, persona templates
├── core/            # Orchestrator, event bus, context, exceptions
├── input/           # Wake word, speech recognition, Telegram bot
├── nlu/             # Intent parser, function schemas, fallback
├── execution/       # System control, apps, screen, research, docs
├── output/          # TTS engine, response formatter
├── utils/           # Audio, Windows API, text processing
├── tests/           # Test suite
├── assets/          # Sound effects, wake word models
├── logs/            # Daily rotating log files
└── main.py          # Entry point
```

## ⚙️ Configuration

All settings are managed via environment variables in `.env`:

| Variable | Description | Default |
|---|---|---|
| `STEWIE_OPENAI_API_KEY` | OpenAI API key | Required |
| `STEWIE_OPENAI_MODEL` | LLM model | `gpt-4o` |
| `STEWIE_TG_BOT_TOKEN` | Telegram bot token | Optional |
| `STEWIE_TG_ALLOWED_USER_IDS` | Authorized user IDs | `[]` |
| `STEWIE_WAKE_PHRASE` | Wake word | `hey stewie` |
| `STEWIE_WHISPER_MODEL` | Whisper size | `base` |
| `STEWIE_TTS_VOICE` | TTS voice name | `en-US-GuyNeural` |

## 📝 License

MIT

---

*"The Stewie protocol is ready for deployment, sir."*
 if you want yo support me , mail me on 
 shyamjisingh9999@gmail.com

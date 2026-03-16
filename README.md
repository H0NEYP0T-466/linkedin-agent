# LinkedIn Agent

An autonomous LinkedIn content agent that monitors your GitHub profile, clones your repositories, drafts posts, and sends them for your approval via Telegram.

**LLM**: LongCat (OpenAI-format API) • **Frontend**: React + TypeScript • **Backend**: Python FastAPI (port 8006)

---

## Features

- 🤖 **Autonomous agent** – runs continuously, no manual intervention needed
- 📦 **First-run setup** – clones all your GitHub repos, builds `repos.md` and a todo list
- 📝 **Post drafting** – one (or 2–3 for larger repos) LinkedIn post per repo
- 📱 **Telegram approval flow** – approve, reject, improve, or regenerate each post
- 🔍 **GitHub monitoring** – detects new repos and noteworthy commits
- 🌐 **Tech news scraping** – HuggingFace, ArXiv, Google AI Blog, Papers With Code, and more
- 💾 **Memory** – `memory.md` tracks all approved posts; `repos.md` tracks all repos
- 🖥️ **Terminal UI** – full-screen black terminal with green agent logs

---

## Quick Start

### 1. Backend

```bash
cd backend
cp .env.example .env
# Fill in LONGCAT_API_KEY and TELEGRAM_CHAT_ID in .env
pip install -r requirements.txt
python main.py
```

### 2. Frontend

```bash
# In the repo root
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Configuration (`.env`)

| Variable | Description | Default |
|---|---|---|
| `LONGCAT_API_KEY` | LongCat API key | *required* |
| `OPENAI_API_KEY` | Optional fallback key name | — |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | pre-filled |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | *required* |
| `GITHUB_USERNAME` | GitHub profile to monitor | `H0NEYP0T-466` |
| `LLM_MODEL` | LongCat model name | `longcat-flash-lite` |
| `LONGCAT_BASE_URL` | LongCat OpenAI-compatible base URL | `https://api.longcat.chat/openai` |
| `LLM_TIMEOUT_SECONDS` | LLM request timeout in seconds | `60` |
| `CLOUDFLARE_API_TOKEN` | Cloudflare Browser Rendering (optional) | — |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account ID (optional) | — |

> **Get your Telegram chat ID**: Start the bot and send `/start` — it will reply with your chat ID.

> **LongCat endpoint**: OpenAI format is `https://api.longcat.chat/openai`.

---

## Telegram Commands

| Command | Description |
|---|---|
| `/start` | Shows bot info and your chat ID |
| `/status` | Agent status, repo count, task queue |
| `/todo` | List pending tasks |
| `/repos` | List all tracked repositories |
| `/post <topic>` | Draft a custom post on any topic |
| `/skip` | Skip the current pending task |
| `approve` | ✅ Approve a drafted post |
| `reject` | ❌ Reject / skip a drafted post |
| `improve: <feedback>` | ✏️ Request changes with feedback |
| `regenerate` | 🔁 Generate a fresh version |

---

## Agent Flow

```
First start
  └─► Fetch all GitHub repos
  └─► Clone each repo (one by one)
  └─► Generate descriptions with LLM
  └─► Write repos.md + todo.json + memory.md
  └─► Notify via Telegram

Daily loop
  └─► Next pending repo post? → draft → Telegram review
  └─► All repos done? → Check GitHub for new commits/repos
  └─► Nothing interesting? → Scrape HuggingFace / ArXiv / Google AI Blog
  └─► Draft post → Telegram review → approved posts go to memory.md
```

---

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI app + WebSocket
│   ├── agent.py             # Core agent loop
│   ├── github_service.py    # GitHub API + git clone
│   ├── telegram_service.py  # Telegram bot
│   ├── scraper_service.py   # RSS feed scraper
│   ├── llm_service.py       # LongCat OpenAI-format client
│   ├── storage.py           # memory.md / repos.md / todo.json
│   ├── requirements.txt
│   └── .env.example
├── src/
│   ├── App.tsx              # Terminal UI
│   ├── index.css            # Minimal global styles
│   └── main.tsx
└── index.html
```


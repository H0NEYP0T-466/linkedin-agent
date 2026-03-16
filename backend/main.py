"""FastAPI backend for LinkedIn Agent."""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Load environment variables from .env if present
load_dotenv(Path(__file__).parent / ".env")

import agent
import storage
import telegram_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_agent_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent_task
    storage.ensure_data_dir()
    _agent_task = asyncio.create_task(agent.run_agent())
    yield
    if _agent_task:
        _agent_task.cancel()
        try:
            await _agent_task
        except asyncio.CancelledError:
            pass
    await telegram_service.stop_bot()


app = FastAPI(title="LinkedIn Agent", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── WebSocket for real-time log streaming ────────────────────────────────────

@app.websocket("/ws")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    log_queue = agent.subscribe_logs()
    try:
        # Send buffered welcome message
        await websocket.send_text(json.dumps({
            "type": "log",
            "message": "[system] WebSocket connected. Streaming agent logs..."
        }))
        while True:
            try:
                msg = await asyncio.wait_for(log_queue.get(), timeout=30.0)
                await websocket.send_text(json.dumps({"type": "log", "message": msg}))
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    finally:
        agent.unsubscribe_logs(log_queue)


# ── REST API ─────────────────────────────────────────────────────────────────

@app.get("/status")
async def get_status():
    state = storage.get_state()
    repos = storage.get_repos_data()
    todo = storage.load_todo()
    pending = [t for t in todo if t.get("status") == "pending"]
    done = [t for t in todo if t.get("status") == "done"]
    return {
        "initialized": state.get("initialized", False),
        "initialized_at": state.get("initialized_at"),
        "repos_count": len(repos),
        "pending_tasks": len(pending),
        "done_tasks": len(done),
        "agent_running": _agent_task is not None and not _agent_task.done(),
    }


@app.get("/todo")
async def get_todo():
    return storage.load_todo()


@app.get("/repos")
async def get_repos():
    return storage.get_repos_data()


@app.get("/repos/md")
async def get_repos_md():
    return {"content": storage.read_repos_md()}


@app.get("/memory")
async def get_memory():
    return {"content": storage.read_memory()}


@app.post("/restart")
async def restart_agent():
    global _agent_task
    if _agent_task and not _agent_task.done():
        _agent_task.cancel()
        try:
            await _agent_task
        except asyncio.CancelledError:
            pass
    _agent_task = asyncio.create_task(agent.run_agent())
    return {"status": "restarted"}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    _reload = bool(os.getenv("RELOAD", ""))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8006")),
        reload=_reload,
        # Exclude the data directory so cloning repos doesn't trigger a reload
        reload_excludes=["data", "data/**","data/repos/"],
        log_level="info",
    )

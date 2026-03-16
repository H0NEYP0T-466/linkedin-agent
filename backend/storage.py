"""Storage service for managing memory.md, repos.md, and todo.json."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
MEMORY_FILE = DATA_DIR / "memory.md"
REPOS_FILE = DATA_DIR / "repos.md"
TODO_FILE = DATA_DIR / "todo.json"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# ── memory.md ────────────────────────────────────────────────────────────────

def init_memory() -> None:
    ensure_data_dir()
    if not MEMORY_FILE.exists():
        MEMORY_FILE.write_text(
            "# Memory\n\nThis file tracks all approved LinkedIn posts.\n\n"
        )


def append_to_memory(post_content: str, repo_name: str | None = None) -> None:
    ensure_data_dir()
    init_memory()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    source = f" (repo: {repo_name})" if repo_name else ""
    entry = f"\n---\n### {timestamp}{source}\n\n{post_content}\n"
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def read_memory() -> str:
    if not MEMORY_FILE.exists():
        return ""
    return MEMORY_FILE.read_text(encoding="utf-8")


# ── repos.md ─────────────────────────────────────────────────────────────────

def init_repos() -> None:
    ensure_data_dir()
    if not REPOS_FILE.exists():
        REPOS_FILE.write_text(
            "# Repositories\n\nThis file tracks all GitHub repositories.\n\n"
        )


def write_repos_md(repos: list[dict[str, Any]]) -> None:
    ensure_data_dir()
    lines = ["# Repositories\n\n"]
    for repo in repos:
        name = repo.get("name", "")
        description = repo.get("description") or "No description"
        language = repo.get("language") or "Unknown"
        url = repo.get("html_url", "")
        topics = ", ".join(repo.get("topics", []))
        stars = repo.get("stargazers_count", 0)
        posted = "✅" if repo.get("posted") else "⏳"
        lines.append(f"## {name} {posted}\n")
        lines.append(f"- **URL**: {url}\n")
        lines.append(f"- **Language**: {language}\n")
        lines.append(f"- **Stars**: {stars}\n")
        lines.append(f"- **Description**: {description}\n")
        if topics:
            lines.append(f"- **Topics**: {topics}\n")
        lines.append("\n")
    REPOS_FILE.write_text("".join(lines), encoding="utf-8")


def read_repos_md() -> str:
    if not REPOS_FILE.exists():
        return ""
    return REPOS_FILE.read_text(encoding="utf-8")


def get_repos_data() -> list[dict[str, Any]]:
    """Load repos from the stored JSON side-file."""
    repos_json = DATA_DIR / "repos.json"
    if not repos_json.exists():
        return []
    return json.loads(repos_json.read_text(encoding="utf-8"))


def save_repos_data(repos: list[dict[str, Any]]) -> None:
    ensure_data_dir()
    repos_json = DATA_DIR / "repos.json"
    repos_json.write_text(json.dumps(repos, indent=2, ensure_ascii=False), encoding="utf-8")


def mark_repo_posted(repo_name: str) -> None:
    repos = get_repos_data()
    for repo in repos:
        if repo.get("name") == repo_name:
            repo["posted"] = True
            break
    save_repos_data(repos)
    write_repos_md(repos)


# ── todo.json ────────────────────────────────────────────────────────────────

def load_todo() -> list[dict[str, Any]]:
    if not TODO_FILE.exists():
        return []
    return json.loads(TODO_FILE.read_text(encoding="utf-8"))


def save_todo(todo: list[dict[str, Any]]) -> None:
    ensure_data_dir()
    TODO_FILE.write_text(json.dumps(todo, indent=2, ensure_ascii=False), encoding="utf-8")


def add_todo(task: str, task_type: str = "repo_post", meta: dict | None = None) -> None:
    todo = load_todo()
    next_id = max((item["id"] for item in todo), default=0) + 1
    todo.append({
        "id": next_id,
        "task": task,
        "type": task_type,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "meta": meta or {},
    })
    save_todo(todo)


def complete_todo(task_id: int) -> None:
    todo = load_todo()
    for item in todo:
        if item["id"] == task_id:
            item["status"] = "done"
            item["completed_at"] = datetime.now().isoformat()
            break
    save_todo(todo)


def get_next_pending_repo_task() -> dict[str, Any] | None:
    todo = load_todo()
    for item in todo:
        if item.get("status") == "pending" and item.get("type") == "repo_post":
            return item
    return None


def build_initial_todo(repos: list[dict[str, Any]]) -> None:
    todo: list[dict[str, Any]] = []
    task_id = 1
    for repo in repos:
        name = repo.get("name", "")
        description = repo.get("description") or ""
        # Larger or complex repos get 2-3 posts
        stars = repo.get("stargazers_count", 0)
        num_posts = 2 if stars > 5 else 1
        for i in range(1, num_posts + 1):
            label = f"Post {i}/{num_posts}" if num_posts > 1 else "Post"
            todo.append({
                "id": task_id,
                "task": f"{label} about repo: {name} - {description}",
                "type": "repo_post",
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "meta": {"repo_name": name, "post_index": i, "total_posts": num_posts},
            })
            task_id += 1
    save_todo(todo)


# ── first-run state ──────────────────────────────────────────────────────────

def is_first_run() -> bool:
    state_file = DATA_DIR / "state.json"
    if not state_file.exists():
        return True
    state = json.loads(state_file.read_text(encoding="utf-8"))
    return not state.get("initialized", False)


def mark_initialized() -> None:
    ensure_data_dir()
    state_file = DATA_DIR / "state.json"
    state: dict[str, Any] = {}
    if state_file.exists():
        state = json.loads(state_file.read_text(encoding="utf-8"))
    state["initialized"] = True
    state["initialized_at"] = datetime.now().isoformat()
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")


def get_state() -> dict[str, Any]:
    ensure_data_dir()
    state_file = DATA_DIR / "state.json"
    if not state_file.exists():
        return {}
    return json.loads(state_file.read_text(encoding="utf-8"))


def update_state(updates: dict[str, Any]) -> None:
    state = get_state()
    state.update(updates)
    state_file = DATA_DIR / "state.json"
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

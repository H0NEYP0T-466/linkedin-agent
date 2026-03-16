"""GitHub service - fetch repos, commits, and clone repositories."""

import asyncio
import os
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any

import httpx

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "H0NEYP0T-466")
GITHUB_API = "https://api.github.com"
REPOS_DIR = Path(os.getenv("REPOS_DIR", "./data/repos"))
CLONE_DEPTH = 100


def _fix_permissions(path: Path) -> None:
    """Ensure all files/dirs under path are user-writable so they can be deleted."""
    try:
        for root, dirs, files in os.walk(str(path)):
            for d in dirs:
                dp = Path(root) / d
                dp.chmod(dp.stat().st_mode | stat.S_IRWXU)
            for f in files:
                fp = Path(root) / f
                fp.chmod(fp.stat().st_mode | stat.S_IRUSR | stat.S_IWUSR)
        path.chmod(path.stat().st_mode | stat.S_IRWXU)
    except Exception:
        pass  # best-effort


def _rmtree_force(path: Path) -> None:
    """Remove a directory tree, fixing permissions first."""

    def _on_error(func, fpath, exc_info):  # noqa: ANN001
        try:
            Path(fpath).chmod(stat.S_IRWXU)
            func(fpath)
        except Exception:
            pass

    shutil.rmtree(str(path), onerror=_on_error)


async def fetch_all_repos() -> list[dict[str, Any]]:
    """Fetch all public repos for the configured GitHub user."""
    repos: list[dict[str, Any]] = []
    page = 1
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            response = await client.get(
                f"{GITHUB_API}/users/{GITHUB_USERNAME}/repos",
                params={"per_page": 100, "page": page, "type": "owner", "sort": "updated"},
                headers={"Accept": "application/vnd.github+json"},
            )
            response.raise_for_status()
            batch = response.json()
            if not batch:
                break
            repos.extend(batch)
            if len(batch) < 100:
                break
            page += 1
    return repos


async def fetch_latest_commits(repo_name: str, limit: int = 5) -> list[dict[str, Any]]:
    """Fetch the latest commits for a repo."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{GITHUB_API}/repos/{GITHUB_USERNAME}/{repo_name}/commits",
            params={"per_page": limit},
            headers={"Accept": "application/vnd.github+json"},
        )
        if response.status_code != 200:
            return []
        return response.json()


async def fetch_recent_activity() -> list[dict[str, Any]]:
    """Fetch recent public events (pushes, new repos) for the user."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{GITHUB_API}/users/{GITHUB_USERNAME}/events/public",
            params={"per_page": 30},
            headers={"Accept": "application/vnd.github+json"},
        )
        if response.status_code != 200:
            return []
        return response.json()


def clone_repo(repo: dict[str, Any], log_callback=None) -> bool:
    """Clone a single repo to REPOS_DIR. Returns True on success."""
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    repo_name = repo["name"]
    clone_url = repo.get("clone_url") or repo.get("html_url")
    target_dir = REPOS_DIR / repo_name

    if target_dir.exists():
        if log_callback:
            log_callback(f"[github] Repo already cloned: {repo_name}, pulling latest...")
        try:
            result = subprocess.run(
                ["git", "-C", str(target_dir), "pull", "--ff-only"],
                capture_output=True, text=True, timeout=120,
            )
            _fix_permissions(target_dir)
            return result.returncode == 0
        except Exception as exc:
            if log_callback:
                log_callback(f"[github] Pull failed for {repo_name}: {exc}")
            return False

    if log_callback:
        log_callback(f"[github] Cloning {repo_name}...")
    try:
        result = subprocess.run(
            ["git", "clone", f"--depth={CLONE_DEPTH}", clone_url, str(target_dir)],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            _fix_permissions(target_dir)
            if log_callback:
                log_callback(f"[github] ✓ Cloned {repo_name}")
            return True
        else:
            if log_callback:
                log_callback(f"[github] ✗ Failed to clone {repo_name}: {result.stderr.strip()}")
            return False
    except Exception as exc:
        if log_callback:
            log_callback(f"[github] ✗ Exception cloning {repo_name}: {exc}")
        return False


def get_repo_readme(repo_name: str) -> str:
    """Read the README from a cloned repo."""
    for name in ["README.md", "readme.md", "README.rst", "README.txt", "README"]:
        readme_path = REPOS_DIR / repo_name / name
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8", errors="ignore")
            return content[:3000]
    return ""


def get_repo_file_tree(repo_name: str) -> str:
    """Get a brief file listing from a cloned repo."""
    repo_path = REPOS_DIR / repo_name
    if not repo_path.exists():
        return ""
    try:
        result = subprocess.run(
            ["find", str(repo_path), "-maxdepth", "2", "-type", "f",
             "-not", "-path", "*/.*", "-not", "-path", "*/node_modules/*",
             "-not", "-path", "*/__pycache__/*"],
            capture_output=True, text=True, timeout=10,
        )
        lines = result.stdout.strip().split("\n")[:40]
        return "\n".join(lines)
    except Exception:
        return ""


async def sync_repos(
    stored_repos: list[dict[str, Any]],
    log_callback=None,
) -> list[dict[str, Any]]:
    """Compare stored repos against GitHub, clone any new ones, pull existing.

    Returns the updated full list of repos (existing + newly discovered).
    """
    log = log_callback or (lambda m: None)
    log("🔄 Syncing repos with GitHub...")

    try:
        remote_repos = await fetch_all_repos()
    except Exception as exc:
        log(f"⚠️  Could not fetch remote repos for sync: {exc}")
        return stored_repos

    stored_names = {r.get("name", "") for r in stored_repos}
    remote_names = {r.get("name", "") for r in remote_repos}

    new_names = remote_names - stored_names
    if new_names:
        log(f"🆕 Found {len(new_names)} new remote repo(s): {', '.join(sorted(new_names))}")
    else:
        log("✅ No new repos detected on GitHub.")

    updated = list(stored_repos)

    # Single loop: pull existing repos, clone and record new ones
    for repo in remote_repos:
        repo_name = repo["name"]
        if repo_name in new_names:
            log(f"[sync] Cloning new repo: {repo_name}...")
            ok = clone_repo(repo, log_callback=log)
            entry = dict(repo)
            entry["generated_description"] = repo.get("description") or ""
            entry["posted"] = False
            entry["cloned"] = ok
            updated.append(entry)
        else:
            clone_repo(repo, log_callback=log)  # pulls latest for existing repos

    return updated


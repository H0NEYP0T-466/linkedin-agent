"""GitHub service - fetch repos, README files, and commit activity."""

import base64
import os
from pathlib import Path
from typing import Any

import httpx

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "H0NEYP0T-466")
GITHUB_API = "https://api.github.com"
REPOS_DIR = Path(os.getenv("REPOS_DIR", "./data/repos"))

README_MAX_CHARS = 5000    # Characters to keep from a fetched README
FILE_MAX_CHARS = 4000      # Characters to keep from a fetched source file


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


async def fetch_readme_from_api(repo_name: str) -> str:
    """Fetch README content for a repo via the GitHub Contents API (no git clone)."""
    candidates = ["README.md", "readme.md", "README.rst", "README.txt", "README"]
    async with httpx.AsyncClient(timeout=30) as client:
        for filename in candidates:
            response = await client.get(
                f"{GITHUB_API}/repos/{GITHUB_USERNAME}/{repo_name}/contents/{filename}",
                headers={"Accept": "application/vnd.github+json"},
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and data.get("encoding") == "base64":
                    raw = base64.b64decode(
                        data["content"].replace("\n", "")
                    ).decode("utf-8", errors="ignore")
                    return raw[:README_MAX_CHARS]
    return ""


def save_readme(repo_name: str, content: str) -> None:
    """Persist README content under REPOS_DIR/{repo_name}/README.md."""
    readme_dir = REPOS_DIR / repo_name
    readme_dir.mkdir(parents=True, exist_ok=True)
    (readme_dir / "README.md").write_text(content, encoding="utf-8")


async def fetch_and_save_readme(repo_name: str, log_callback=None) -> str:
    """Fetch README from GitHub API, save locally, and return content."""
    _log = log_callback or (lambda m: None)
    _log(f"[github] Fetching README for {repo_name}...")
    content = await fetch_readme_from_api(repo_name)
    if content:
        save_readme(repo_name, content)
        _log(f"[github] ✓ README saved for {repo_name}")
    else:
        _log(f"[github] ⚠ No README found for {repo_name}")
    return content


def get_repo_readme(repo_name: str) -> str:
    """Read the locally saved README for a repo."""
    for name in ["README.md", "readme.md", "README.rst", "README.txt", "README"]:
        readme_path = REPOS_DIR / repo_name / name
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8", errors="ignore")
            return content[:README_MAX_CHARS]
    return ""


async def fetch_commit_details(repo_name: str, commit_sha: str) -> dict[str, Any]:
    """Fetch a single commit with the list of changed files."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{GITHUB_API}/repos/{GITHUB_USERNAME}/{repo_name}/commits/{commit_sha}",
            headers={"Accept": "application/vnd.github+json"},
        )
        if response.status_code != 200:
            return {}
        return response.json()


async def fetch_file_content(repo_name: str, file_path: str, ref: str = "") -> str:
    """Fetch the raw content of a single file from a repo at a given ref."""
    params: dict[str, str] = {}
    if ref:
        params["ref"] = ref
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{GITHUB_API}/repos/{GITHUB_USERNAME}/{repo_name}/contents/{file_path}",
            params=params,
            headers={"Accept": "application/vnd.github+json"},
        )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and data.get("encoding") == "base64":
                raw = base64.b64decode(
                    data["content"].replace("\n", "")
                ).decode("utf-8", errors="ignore")
                return raw[:FILE_MAX_CHARS]
    return ""


async def sync_readmes(
    stored_repos: list[dict[str, Any]],
    log_callback=None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Compare local README files with remote repos and fetch any that are new/changed.

    Returns (updated_repo_list, new_repo_names).
    New repos are repos present on GitHub but not yet in stored_repos.
    """
    _log = log_callback or (lambda m: None)
    _log("🔄 Syncing READMEs with GitHub...")

    try:
        remote_repos = await fetch_all_repos()
    except Exception as exc:
        _log(f"⚠️  Could not fetch remote repos: {exc}")
        return stored_repos, []

    stored_names = {r.get("name", "") for r in stored_repos}
    new_repo_names: list[str] = []
    updated = list(stored_repos)

    for repo in remote_repos:
        repo_name = repo["name"]
        local_readme = get_repo_readme(repo_name)
        remote_readme = await fetch_readme_from_api(repo_name)

        if repo_name not in stored_names:
            _log(f"🆕 New repo detected: {repo_name}")
            if remote_readme:
                save_readme(repo_name, remote_readme)
            entry = dict(repo)
            entry["generated_description"] = repo.get("description") or ""
            entry["posted"] = False
            entry["readme_synced"] = True
            updated.append(entry)
            new_repo_names.append(repo_name)
        else:
            # Update local README if it changed
            if remote_readme and remote_readme != local_readme:
                _log(f"[sync] README updated for {repo_name}")
                save_readme(repo_name, remote_readme)

    if new_repo_names:
        _log(f"🆕 {len(new_repo_names)} new repo(s): {', '.join(sorted(new_repo_names))}")
    else:
        _log("✅ No new repos detected on GitHub.")

    return updated, new_repo_names


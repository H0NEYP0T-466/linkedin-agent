"""Core LinkedIn Agent - orchestrates all services."""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any

import github_service
import llm_service
import scraper_service
import storage
import telegram_service

logger = logging.getLogger(__name__)

RETRY_DELAY_SECONDS = 5
AGENT_CYCLE_INTERVAL_SECONDS = 3600

# File extensions that are generally not interesting for a LinkedIn post
_UNINTERESTING_EXTENSIONS = (
    ".lock", ".txt", ".md", ".json", ".yaml", ".yml", ".toml",
)

# Broadcast log lines to all connected WebSocket clients
_log_listeners: list[asyncio.Queue] = []


def subscribe_logs() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=500)
    _log_listeners.append(q)
    return q


def unsubscribe_logs(q: asyncio.Queue) -> None:
    try:
        _log_listeners.remove(q)
    except ValueError:
        pass


def log(msg: str) -> None:
    """Log a message to the terminal, logger, and all WebSocket listeners."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    logger.info(msg)
    for q in list(_log_listeners):
        try:
            q.put_nowait(line)
        except asyncio.QueueFull:
            pass


# ── Startup config check ──────────────────────────────────────────────────────

def check_config() -> None:
    """Log warnings for any missing critical environment variables."""
    missing = []
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        missing.append("TELEGRAM_BOT_TOKEN")
    if not os.getenv("TELEGRAM_CHAT_ID"):
        missing.append("TELEGRAM_CHAT_ID")
    if not (os.getenv("LONGCAT_API_KEY") or os.getenv("OPENAI_API_KEY")):
        missing.append("LONGCAT_API_KEY / OPENAI_API_KEY")
    if not os.getenv("GITHUB_USERNAME"):
        log("⚠️  GITHUB_USERNAME not set; defaulting to H0NEYP0T-466")
    if missing:
        log(
            f"❌ MISSING CONFIG: {', '.join(missing)}. "
            "These features will be broken until you set them in backend/.env"
        )
        logger.error("Missing environment variables: %s", ", ".join(missing))
    else:
        log("✅ All required environment variables are configured.")


# ── Initialization ────────────────────────────────────────────────────────────

async def sync_repos_on_startup() -> None:
    """On every server start: sync local READMEs with GitHub, update repos.md."""
    log("🔄 Checking local READMEs vs GitHub...")
    stored = storage.get_repos_data()
    updated, new_repo_names = await github_service.sync_readmes(stored, log_callback=log)

    if new_repo_names:
        # New repos discovered — enrich them with descriptions and queue posts
        new_repos = [r for r in updated if r.get("name") in set(new_repo_names)]
        log(f"📦 Enriching {len(new_repos)} new repo(s) with descriptions...")
        for repo in new_repos:
            repo_name = repo.get("name", "")
            readme = github_service.get_repo_readme(repo_name)
            try:
                desc = await llm_service.generate_repo_description(repo, readme)
            except Exception as exc:
                log(f"⚠️  LLM description failed for {repo_name}: {exc}")
                desc = repo.get("description") or "No description available."
            repo["generated_description"] = desc
            await asyncio.sleep(1)

        # Add todo tasks for new repos
        for repo in new_repos:
            name = repo.get("name", "")
            desc = repo.get("generated_description", "")
            storage.add_todo(
                f"Post about new repo: {name} - {desc[:80]}",
                task_type="repo_post",
                meta={"repo_name": name, "post_index": 1, "total_posts": 1},
            )
    else:
        log("✅ No new repos detected on GitHub.")

    storage.save_repos_data(updated)
    storage.write_repos_md(updated)
    log(f"✅ repos.md updated ({len(updated)} repos).")


async def first_run_setup() -> None:
    """Perform first-run initialization: fetch READMEs and build files."""
    log("🚀 First run detected. Starting initialization...")

    storage.ensure_data_dir()
    storage.init_memory()
    storage.init_repos()

    log("📡 Fetching repository list from GitHub...")
    try:
        repos = await github_service.fetch_all_repos()
    except Exception as exc:
        log(f"❌ Failed to fetch repos from GitHub: {exc}")
        repos = []

    if not repos:
        log("⚠️  No repositories found. Check your GitHub username.")
        storage.mark_initialized()
        return

    log(f"📦 Found {len(repos)} repositories. Initializing repos.md...")

    # Enrich each repo with a generated description (fetch README via API only)
    enriched_repos: list[dict[str, Any]] = []
    for i, repo in enumerate(repos, 1):
        repo_name = repo.get("name", "")
        log(f"[{i}/{len(repos)}] Fetching README for {repo_name}...")
        await github_service.fetch_and_save_readme(repo_name, log_callback=log)

        readme = github_service.get_repo_readme(repo_name)

        log(f"[{i}/{len(repos)}] Generating description for {repo_name}...")
        try:
            description = await llm_service.generate_repo_description(repo, readme)
        except Exception as exc:
            log(f"⚠️  LLM error for {repo_name}: {exc}")
            description = repo.get("description") or "No description available."

        enriched = dict(repo)
        enriched["generated_description"] = description
        enriched["posted"] = False
        enriched["readme_synced"] = True
        enriched_repos.append(enriched)

        # Small delay to avoid rate limits
        await asyncio.sleep(1)

    storage.save_repos_data(enriched_repos)
    storage.write_repos_md(enriched_repos)
    log(f"✅ repos.md created with {len(enriched_repos)} repos.")

    log("📋 Building initial todo list...")
    storage.build_initial_todo(enriched_repos)
    todo = storage.load_todo()
    log(f"✅ Todo list created with {len(todo)} tasks.")

    storage.mark_initialized()
    log("🎉 Initialization complete! Agent is ready.")

    await telegram_service.send_message(
        f"🤖 LinkedIn Agent initialized!\n\n"
        f"📦 Found {len(enriched_repos)} repos\n"
        f"📋 {len(todo)} posts queued\n\n"
        f"I'll start drafting posts for your review. First one coming up!"
    )


# ── Main agent loop ────────────────────────────────────────────────────────────

def _post_label(name: str) -> str:
    """Sanitise a name for use as a post file-name label."""
    return name.replace("/", "-").replace(" ", "-").lower()[:30]


async def process_next_repo_post() -> bool:
    """Process the next pending repo post from the todo list. Returns True if processed."""
    task = storage.get_next_pending_repo_task()
    if not task:
        return False

    # Enforce one-post-per-day limit
    if not storage.can_post_today():
        log("📅 Already posted today. Waiting until tomorrow...")
        return False

    repo_name = task["meta"].get("repo_name", "")
    post_index = task["meta"].get("post_index", 1)
    total_posts = task["meta"].get("total_posts", 1)

    log(f"📝 Processing post {post_index}/{total_posts} for repo: {repo_name}")

    repos = storage.get_repos_data()
    repo = next((r for r in repos if r.get("name") == repo_name), None)
    if not repo:
        log(f"⚠️  Repo {repo_name} not found in data. Skipping task.")
        storage.complete_todo(task["id"])
        return True

    readme = github_service.get_repo_readme(repo_name)
    description = repo.get("generated_description") or repo.get("description") or ""
    memory_ctx = storage.read_memory()

    log(f"🤖 Generating LinkedIn post for {repo_name}...")
    max_attempts = 3
    post = ""
    for attempt in range(1, max_attempts + 1):
        try:
            post = await llm_service.generate_linkedin_post(
                repo, description, readme, memory_ctx, post_index, total_posts
            )
            break
        except Exception as exc:
            log(f"⚠️  LLM attempt {attempt} failed: {exc}")
            if attempt == max_attempts:
                log("❌ Failed to generate post after 3 attempts. Skipping.")
                storage.complete_todo(task["id"])
                return True
            await asyncio.sleep(RETRY_DELAY_SECONDS)

    # Save draft to posts folder
    label = _post_label(repo_name)
    draft_path = storage.save_post_draft(post, label=label)
    log(f"💾 Draft saved: {draft_path.name}")

    log("📤 Sending post to Telegram for review...")
    context_str = f"Repo: {repo_name} | Post {post_index}/{total_posts}"
    await telegram_service.send_post_for_review(post, context_str)

    # Wait for user decision
    decision = await telegram_service.get_user_decision(timeout=86400)
    action = decision.get("action", "timeout")
    log(f"👤 User decision: {action}")

    if action == "approve":
        approved_path = storage.save_approved_post(post, label=label)
        log(f"💾 Approved post saved: {approved_path.name}")
        storage.append_to_memory(post, repo_name)
        if post_index == total_posts:
            storage.mark_repo_posted(repo_name)
        storage.complete_todo(task["id"])
        await telegram_service.send_message("✅ Post approved and saved!")
        log(f"✅ Post approved for {repo_name}")

    elif action == "reject":
        storage.complete_todo(task["id"])
        await telegram_service.send_message("⏭️ Post skipped.")
        log(f"⏭️ Post rejected for {repo_name}")

    elif action == "regenerate":
        log(f"🔄 Regenerating post for {repo_name}...")
        # Re-queue: don't mark done, just return True to retry on next loop
        await telegram_service.send_message("🔄 Regenerating post...")
        return await process_next_repo_post()

    elif action == "improve":
        feedback = decision.get("feedback", "")
        log(f"✏️  Improving post based on feedback: {feedback}")
        await telegram_service.send_message("✏️ Applying feedback and regenerating...")
        try:
            improved = await llm_service.generate_text(
                f"Improve this LinkedIn post based on feedback.\n\nOriginal post:\n{post}\n\n"
                f"Feedback: {feedback}\n\nRewrite the post:"
            )
        except Exception as exc:
            log(f"⚠️  Improve failed: {exc}")
            improved = post

        improved_draft = storage.save_post_draft(improved, label=f"{label}-improved")
        log(f"💾 Improved draft saved: {improved_draft.name}")
        await telegram_service.send_post_for_review(improved, f"{context_str} [IMPROVED]")
        decision2 = await telegram_service.get_user_decision(timeout=86400)
        if decision2.get("action") == "approve":
            approved_path = storage.save_approved_post(improved, label=label)
            log(f"💾 Approved improved post saved: {approved_path.name}")
            storage.append_to_memory(improved, repo_name)
            if post_index == total_posts:
                storage.mark_repo_posted(repo_name)
            storage.complete_todo(task["id"])
            await telegram_service.send_message("✅ Improved post approved!")
        else:
            storage.complete_todo(task["id"])
            await telegram_service.send_message("⏭️ Post skipped.")

    elif action == "timeout":
        log("⏰ No response from user. Skipping post for now.")

    return True


async def check_github_updates() -> bool:
    """Check for new GitHub activity and post if interesting. Returns True if found."""
    log("🔍 Checking GitHub for recent activity...")
    try:
        events = await github_service.fetch_recent_activity()
    except Exception as exc:
        log(f"⚠️  Failed to fetch GitHub activity: {exc}")
        return False

    if not events:
        log("ℹ️  No recent GitHub activity found.")
        return False

    # Collect push events keyed by repo, preserving latest commit SHAs
    push_repos: dict[str, list[dict]] = {}

    for event in events[:20]:
        etype = event.get("type", "")
        repo_info = event.get("repo", {})
        repo_name = repo_info.get("name", "").split("/")[-1]
        if etype == "PushEvent":
            payload = event.get("payload", {})
            commits = payload.get("commits", [])
            if repo_name not in push_repos:
                push_repos[repo_name] = []
            push_repos[repo_name].extend(commits)

    # Check each active repo
    found_interesting = False
    for repo_name, event_commits in push_repos.items():
        log(f"🔍 Analyzing activity for {repo_name}...")
        try:
            commits = await github_service.fetch_latest_commits(repo_name, limit=10)
            summary = await llm_service.summarize_commit_activity(repo_name, commits)
            interesting = await llm_service.is_activity_worth_posting(summary)
        except Exception as exc:
            log(f"⚠️  Analysis failed for {repo_name}: {exc}")
            continue

        if not interesting:
            continue

        log(f"💡 Interesting activity found in {repo_name}: {summary}")

        # Find the most relevant changed file from the latest commit
        latest_sha = (event_commits[0].get("sha") or "") if event_commits else ""
        file_path = ""
        file_content = ""
        if latest_sha:
            try:
                commit_details = await github_service.fetch_commit_details(repo_name, latest_sha)
                changed_files = [
                    f["filename"] for f in commit_details.get("files", [])
                    if not f["filename"].endswith(_UNINTERESTING_EXTENSIONS)
                ]
                if not changed_files:
                    # Fall back to any changed file
                    changed_files = [f["filename"] for f in commit_details.get("files", [])]
                if changed_files:
                    file_path = changed_files[0]
                    file_content = await github_service.fetch_file_content(
                        repo_name, file_path, ref=latest_sha
                    )
                    log(f"[github] Fetched changed file: {file_path} ({len(file_content)} chars)")
            except Exception as exc:
                log(f"⚠️  Could not fetch commit file for {repo_name}: {exc}")

        await telegram_service.send_message(
            f"🔍 *New Activity Detected*\n\nRepo: `{repo_name}`\n{summary}\n\n"
            f"Reply 'yes' to draft a post or 'no' to skip."
        )
        decision = await telegram_service.get_user_decision(timeout=3600)
        if (decision.get("action") in ("approve", "message")
                and decision.get("text", "").lower().startswith("y")):
            repos = storage.get_repos_data()
            repo = next((r for r in repos if r.get("name") == repo_name), {})
            memory_ctx = storage.read_memory()
            repos_md = storage.read_repos_md()
            try:
                if file_content:
                    post = await llm_service.generate_commit_activity_post(
                        repo_name, repo, file_path, file_content, summary,
                        memory_ctx, repos_md
                    )
                else:
                    # No file content available — fall back to readme-based post
                    readme = github_service.get_repo_readme(repo_name)
                    description = repo.get("generated_description") or summary
                    post = await llm_service.generate_linkedin_post(
                        repo, description, readme, memory_ctx
                    )
            except Exception as exc:
                log(f"⚠️  Post generation failed: {exc}")
                found_interesting = True
                break

            label = _post_label(repo_name)
            draft_path = storage.save_post_draft(post, label=f"{label}-activity")
            log(f"💾 Activity draft saved: {draft_path.name}")
            await telegram_service.send_post_for_review(
                post, f"Recent activity: {repo_name}"
            )
            decision2 = await telegram_service.get_user_decision(timeout=86400)
            if decision2.get("action") == "approve":
                approved_path = storage.save_approved_post(post, label=label)
                log(f"💾 Approved activity post saved: {approved_path.name}")
                storage.append_to_memory(post, repo_name)
                await telegram_service.send_message("✅ Post approved!")
            else:
                await telegram_service.send_message("⏭️ Post skipped.")
        found_interesting = True
        break  # One post per cycle

    return found_interesting


async def post_from_news() -> None:
    """Scrape tech news and generate a post."""
    log("🌐 Fetching latest AI/ML/tech news...")
    try:
        articles = await scraper_service.fetch_latest_tech_news()
    except Exception as exc:
        log(f"⚠️  Scraping failed: {exc}")
        return

    if not articles:
        log("ℹ️  No new articles found.")
        return

    log(f"📰 Found {len(articles)} articles. Selecting most relevant...")

    # Let the LLM pick the best one
    article_list = "\n".join(
        f"{i+1}. [{a['source']}] {a['title']} - {a.get('summary', '')[:100]}"
        for i, a in enumerate(articles[:10])
    )
    try:
        choice_text = await llm_service.generate_text(
            f"You are selecting the most LinkedIn-worthy AI/ML/tech article. "
            f"Pick the number (1-{min(10, len(articles))}) of the most interesting article:\n"
            f"{article_list}\n\nReply with ONLY the number.",
            temperature=0.2,
        )
        choice = int(choice_text.strip().split()[0]) - 1
        if not (0 <= choice < len(articles)):
            choice = 0
    except Exception:
        choice = 0

    article = articles[choice]
    log(f"📰 Selected: [{article['source']}] {article['title']}")

    # Enforce one-post-per-day limit
    if not storage.can_post_today():
        log("📅 Already posted today. Skipping news post.")
        return

    memory_ctx = storage.read_memory()
    post = await llm_service.generate_news_post(article, memory_ctx)

    # Save draft
    news_label = "news-" + _post_label(article.get("source", "unknown"))
    draft_path = storage.save_post_draft(post, label=news_label)
    log(f"💾 News draft saved: {draft_path.name}")

    await telegram_service.send_post_for_review(
        post, f"Source: {article['source']} | {article['title'][:60]}"
    )
    decision = await telegram_service.get_user_decision(timeout=86400)

    if decision.get("action") == "approve":
        approved_path = storage.save_approved_post(post, label=news_label)
        log(f"💾 Approved news post saved: {approved_path.name}")
        storage.append_to_memory(post)
        await telegram_service.send_message("✅ News post approved and saved!")
        log("✅ News post approved.")
    elif decision.get("action") == "improve":
        feedback = decision.get("feedback", "")
        improved = await llm_service.generate_text(
            f"Improve this LinkedIn post:\n{post}\n\nFeedback: {feedback}\n\nRewrite:"
        )
        improved_draft = storage.save_post_draft(improved, label="news-improved")
        log(f"💾 Improved news draft saved: {improved_draft.name}")
        await telegram_service.send_post_for_review(improved, "[IMPROVED NEWS POST]")
        decision2 = await telegram_service.get_user_decision(timeout=86400)
        if decision2.get("action") == "approve":
            approved_path = storage.save_approved_post(improved, label="news")
            log(f"💾 Approved news post saved: {approved_path.name}")
            storage.append_to_memory(improved)
            await telegram_service.send_message("✅ Improved news post approved!")


def _find_repo_in_text(text: str, repos: list[dict]) -> dict | None:
    """Try to find a repo mentioned by name in free-form text."""
    lower = text.lower()
    # Sort by length descending so longer/more-specific names match first
    for repo in sorted(repos, key=lambda r: len(r.get("name", "")), reverse=True):
        name = repo.get("name", "")
        if name and name.lower() in lower:
            return repo
    return None


async def _run_post_review_loop(
    post: str,
    label: str,
    context_str: str,
    repo_name: str | None = None,
) -> None:
    """Send a post for Telegram review and handle approve/improve/reject."""
    draft_path = storage.save_post_draft(post, label=label)
    log(f"💾 Draft saved: {draft_path.name}")
    await telegram_service.send_post_for_review(post, context_str)
    decision = await telegram_service.get_user_decision(timeout=86400)
    action = decision.get("action", "timeout")

    if action == "approve":
        approved_path = storage.save_approved_post(post, label=label)
        log(f"💾 Approved post saved: {approved_path.name}")
        storage.append_to_memory(post, repo_name)
        await telegram_service.send_message("✅ Post approved and saved!")

    elif action == "improve":
        feedback = decision.get("feedback", "")
        log(f"✏️  Improving post based on feedback: {feedback}")
        await telegram_service.send_message("✏️ Applying feedback and regenerating...")
        try:
            improved = await llm_service.generate_text(
                f"Improve this LinkedIn post based on feedback.\n\nOriginal post:\n{post}\n\n"
                f"Feedback: {feedback}\n\nRewrite the post:"
            )
        except Exception as exc:
            log(f"⚠️  Improve failed: {exc}")
            improved = post
        imp_draft = storage.save_post_draft(improved, label=f"{label}-improved")
        log(f"💾 Improved draft saved: {imp_draft.name}")
        await telegram_service.send_post_for_review(improved, f"{context_str} [IMPROVED]")
        d2 = await telegram_service.get_user_decision(timeout=86400)
        if d2.get("action") == "approve":
            approved_path = storage.save_approved_post(improved, label=label)
            log(f"💾 Approved improved post saved: {approved_path.name}")
            storage.append_to_memory(improved, repo_name)
            await telegram_service.send_message("✅ Improved post approved!")
        else:
            await telegram_service.send_message("⏭️ Post skipped.")

    elif action in ("reject", "timeout"):
        await telegram_service.send_message("⏭️ Post skipped.")


async def handle_custom_command(text: str) -> None:
    """Handle a request from the user via Telegram."""
    if text.startswith("/"):
        log(f"💬 Command received: {text[:80]}")
    else:
        log(f"💬 Message from user: {text[:80]}")

    if text.startswith("/status"):
        todo = storage.load_todo()
        pending = [t for t in todo if t.get("status") == "pending"]
        done = [t for t in todo if t.get("status") == "done"]
        state = storage.get_state()
        repos = storage.get_repos_data()
        last_posted = storage.get_last_posted_date()
        msg = (
            f"📊 *Agent Status*\n\n"
            f"✅ Initialized: {state.get('initialized', False)}\n"
            f"📦 Repos: {len(repos)}\n"
            f"📋 Pending tasks: {len(pending)}\n"
            f"✅ Done tasks: {len(done)}\n"
            f"📅 Last post date: {last_posted or 'never'}\n"
        )
        await telegram_service.send_message(msg)

    elif text.startswith("/todo"):
        args = text[5:].strip()

        if args.startswith("add "):
            task = args[4:].strip()
            if task:
                storage.add_todo(task, task_type="custom")
                await telegram_service.send_message(f"✅ Added task: _{task}_")
                log(f"📋 Todo added: {task}")
            else:
                await telegram_service.send_message("Usage: `/todo add <task description>`")

        elif args.startswith("done "):
            id_str = args[5:].strip()
            try:
                task_id = int(id_str)
                storage.complete_todo(task_id)
                await telegram_service.send_message(f"✅ Marked task #{task_id} as done!")
                log(f"📋 Todo #{task_id} completed.")
            except ValueError:
                await telegram_service.send_message(
                    f"❌ Invalid task ID: `{id_str}`\nUsage: `/todo done <id>`"
                )

        else:
            todo = storage.load_todo()
            pending = [t for t in todo if t.get("status") == "pending"][:10]
            if not pending:
                await telegram_service.send_message("📋 No pending tasks!")
            else:
                lines = [f"📋 *Pending Tasks ({len(pending)})*\n"]
                for t in pending:
                    lines.append(f"• `#{t['id']}` [{t['type']}] {t['task'][:80]}")
                lines.append("\n_Use /todo done <id> to complete a task_")
                lines.append("_Use /todo add <task> to add a task_")
                await telegram_service.send_message("\n".join(lines))

    elif text.startswith("/repos"):
        repos_md = storage.read_repos_md()
        if repos_md:
            await telegram_service.send_message(f"📦 *Repositories*\n\n{repos_md[:3000]}")
        else:
            await telegram_service.send_message(
                "No repos data yet. The agent will sync repos on the next startup."
            )

    elif text.startswith("/memory"):
        memory = storage.read_memory()
        if memory:
            await telegram_service.send_message(f"🧠 *Post Memory*\n\n{memory[:3500]}")
        else:
            await telegram_service.send_message(
                "📭 Memory is empty — no posts have been approved yet."
            )

    elif text.startswith("/readme"):
        repo_name = text[7:].strip()
        if not repo_name:
            await telegram_service.send_message(
                "Usage: `/readme <repo-name>`\nUse /repos to see available repos."
            )
            return
        readme = github_service.get_repo_readme(repo_name)
        if readme:
            await telegram_service.send_message(
                f"📄 *README: {repo_name}*\n\n{readme[:3500]}"
            )
        else:
            repos = storage.get_repos_data()
            known = [r.get("name", "") for r in repos]
            if repo_name in known:
                await telegram_service.send_message(
                    f"⚠️ I have `{repo_name}` in my list but its README hasn't been "
                    "fetched yet. The agent will fetch it on the next sync."
                )
            else:
                await telegram_service.send_message(
                    f"❌ I don't have any data for `{repo_name}`.\n\n"
                    "Use /repos to see all tracked repositories."
                )

    elif text.startswith("/pending"):
        posts = sorted(storage.POSTS_DIR.glob("*.txt"))
        if not posts:
            await telegram_service.send_message("📭 No pending draft posts.")
            return
        lines = [f"📝 *Pending Drafts ({len(posts)} total)*\n"]
        for p in posts[:5]:
            snippet = p.read_text(encoding="utf-8")[:120].replace("\n", " ")
            lines.append(f"📄 *{p.name}*\n_{snippet}_\n")
        if len(posts) > 5:
            lines.append(f"_...and {len(posts) - 5} more._")
        await telegram_service.send_message("\n".join(lines))

    elif text.startswith("/post"):
        topic = text[5:].strip()
        if not topic:
            await telegram_service.send_message(
                "Usage:\n"
                "• `/post <topic>` — draft a post on any topic\n"
                "• `/post repo:<name>` — draft a post for a specific repo"
            )
            return

        # Repo-specific post: /post repo:<name>
        if topic.lower().startswith("repo:"):
            repo_name = topic[5:].strip()
            repos = storage.get_repos_data()
            repo = next(
                (r for r in repos if r.get("name", "").lower() == repo_name.lower()), None
            )
            if not repo:
                await telegram_service.send_message(
                    f"❌ I don't have data for repo `{repo_name}`.\n\n"
                    "Use /repos to see all tracked repositories."
                )
                return
            log(f"✍️  Drafting repo post for: {repo_name}")
            await telegram_service.send_message(
                f"✍️ Drafting a LinkedIn post for repo `{repo_name}`..."
            )
            readme = github_service.get_repo_readme(repo_name)
            description = repo.get("generated_description") or repo.get("description") or ""
            memory_ctx = storage.read_memory()
            try:
                post = await llm_service.generate_linkedin_post(
                    repo, description, readme, memory_ctx
                )
                label = "repo-" + _post_label(repo_name)
                await _run_post_review_loop(post, label, f"Repo: {repo_name}", repo_name)
            except Exception as exc:
                log(f"❌ Repo post failed: {exc}")
                await telegram_service.send_message(f"❌ Failed to generate post: {exc}")
            return

        # Custom topic post
        log(f"✍️  Drafting custom post on: {topic}")
        await telegram_service.send_message(f"✍️ Drafting a post on: _{topic}_...")
        repos_md = storage.read_repos_md()
        memory_ctx = storage.read_memory()
        try:
            post = await llm_service.generate_custom_post(topic, repos_md, memory_ctx)
            label = "custom-" + _post_label(topic)
            await _run_post_review_loop(post, label, f"Custom: {topic}")
        except Exception as exc:
            log(f"❌ Custom post failed: {exc}")
            await telegram_service.send_message(f"❌ Failed to generate post: {exc}")

    elif text.startswith("/"):
        # Unknown slash command
        await telegram_service.send_message(
            f"🤔 Unknown command: `{text}`\n\nAvailable commands:\n"
            "/status — agent status\n"
            "/todo — pending tasks\n"
            "/todo add <task> — add a task\n"
            "/todo done <id> — complete a task\n"
            "/post <topic> — draft a post\n"
            "/post repo:<name> — draft a post for a specific repo\n"
            "/repos — tracked repositories\n"
            "/memory — post memory log\n"
            "/readme <repo> — show a repo's README\n"
            "/pending — pending draft posts\n"
            "/skip — skip current task"
        )

    else:
        # Casual / conversational message
        await _handle_casual_message(text)


async def _handle_casual_message(text: str) -> None:
    """Handle a casual/conversational message from the user with intent detection."""
    lower = text.lower()

    # Intent: show pending draft posts
    if any(kw in lower for kw in ["pending post", "draft post", "unsent post", "posts pending"]):
        posts = sorted(storage.POSTS_DIR.glob("*.txt"))
        if not posts:
            await telegram_service.send_message("📭 No pending draft posts at the moment.")
        else:
            lines = [f"📝 *Pending Drafts ({len(posts)} total)*\n"]
            for p in posts[:5]:
                snippet = p.read_text(encoding="utf-8")[:120].replace("\n", " ")
                lines.append(f"📄 *{p.name}*\n_{snippet}_\n")
            if len(posts) > 5:
                lines.append(f"_...and {len(posts) - 5} more._")
            await telegram_service.send_message("\n".join(lines))
        return

    # Intent: make / create / write a post (possibly for a specific repo)
    post_intent_keywords = [
        "make a post", "create a post", "write a post", "draft a post",
        "post about", "post from", "generate a post", "make post",
    ]
    if any(kw in lower for kw in post_intent_keywords):
        repos = storage.get_repos_data()
        matched_repo = _find_repo_in_text(text, repos)
        if matched_repo:
            repo_name = matched_repo.get("name", "")
            log(f"✍️  Drafting repo post (natural language request) for: {repo_name}")
            await telegram_service.send_message(
                f"✍️ Got it! Drafting a LinkedIn post for `{repo_name}`..."
            )
            readme = github_service.get_repo_readme(repo_name)
            description = (
                matched_repo.get("generated_description")
                or matched_repo.get("description")
                or ""
            )
            memory_ctx = storage.read_memory()
            try:
                post = await llm_service.generate_linkedin_post(
                    matched_repo, description, readme, memory_ctx
                )
                label = "repo-" + _post_label(repo_name)
                await _run_post_review_loop(post, label, f"Repo: {repo_name}", repo_name)
            except Exception as exc:
                log(f"❌ Post generation failed: {exc}")
                await telegram_service.send_message(f"❌ Failed to generate post: {exc}")
        else:
            # No specific repo identified — ask them to be more specific or use /post
            await telegram_service.send_message(
                "✍️ I'd be happy to draft a post! Please tell me which repo or topic:\n\n"
                "• `/post <topic>` — post on any topic\n"
                "• `/post repo:<name>` — post about a specific repo\n"
                "• `/repos` — see all repos I know about"
            )
        return

    # Intent: show repos / memory / todo via natural language
    if any(kw in lower for kw in ["show repos", "list repos", "my repos", "tracked repos"]):
        repos_md = storage.read_repos_md()
        if repos_md:
            await telegram_service.send_message(f"📦 *Repositories*\n\n{repos_md[:3000]}")
        else:
            await telegram_service.send_message("No repo data yet. Try /repos.")
        return

    if any(kw in lower for kw in ["show memory", "my memory", "past posts", "approved posts"]):
        memory = storage.read_memory()
        if memory:
            await telegram_service.send_message(f"🧠 *Post Memory*\n\n{memory[:3500]}")
        else:
            await telegram_service.send_message("📭 Memory is empty — no posts approved yet.")
        return

    if any(kw in lower for kw in ["show todo", "my tasks", "pending tasks", "what's next"]):
        todo = storage.load_todo()
        pending = [t for t in todo if t.get("status") == "pending"][:10]
        if not pending:
            await telegram_service.send_message("📋 No pending tasks!")
        else:
            lines = [f"📋 *Pending Tasks ({len(pending)})*\n"]
            for t in pending:
                lines.append(f"• `#{t['id']}` [{t['type']}] {t['task'][:80]}")
            await telegram_service.send_message("\n".join(lines))
        return

    # General conversational response via LLM with rich, truthful context
    try:
        state = storage.get_state()
        repos = storage.get_repos_data()
        todo = storage.load_todo()
        pending_tasks = [t for t in todo if t.get("status") == "pending"]
        repo_names = [r.get("name", "") for r in repos]

        context = (
            f"Initialized: {state.get('initialized', False)}. "
            f"Repos tracked ({len(repos)}): {', '.join(repo_names[:15])}. "
            f"Pending tasks: {len(pending_tasks)}. "
            f"Last post date: {storage.get_last_posted_date() or 'never'}."
        )
        reply = await llm_service.chat_response(text, context=context)
        await telegram_service.send_message(reply)
    except Exception as exc:
        log(f"⚠️  Chatbot response failed: {exc}")
        await telegram_service.send_message(
            "Hey! 👋 I'm your LinkedIn Agent. I'm here to help manage your posts and repos.\n\n"
            "Try: /status, /todo, /repos, /post <topic>"
        )


# ── Agent entrypoint ──────────────────────────────────────────────────────────

async def run_agent() -> None:
    """Main agent loop."""
    log("🤖 LinkedIn Agent starting up...")

    # Check and log configuration issues immediately
    check_config()

    # Register Telegram message callback
    telegram_service.set_message_callback(handle_custom_command)

    # Start Telegram bot in background (non-blocking — agent continues immediately)
    log("📱 Starting Telegram bot in background...")
    await telegram_service.start_bot(message_callback=handle_custom_command)

    # First-run initialization
    if storage.is_first_run():
        await first_run_setup()
    else:
        # Sync repos on every subsequent startup
        try:
            await sync_repos_on_startup()
        except Exception as exc:
            log(f"⚠️  Repo sync failed: {exc}")
            logger.exception("Repo sync error")

    # Main loop
    log("🔄 Entering main agent loop...")
    while True:
        try:
            # 1. Check if there are pending repo posts to process
            has_pending = bool(storage.get_next_pending_repo_task())
            if has_pending:
                log("📋 Processing next repo post from todo list...")
                await process_next_repo_post()
                await asyncio.sleep(RETRY_DELAY_SECONDS)
                continue

            # 2. All repo posts done — check for new GitHub activity
            log("🔍 All repo posts done. Checking GitHub for new activity...")
            found = await check_github_updates()
            if found:
                await asyncio.sleep(RETRY_DELAY_SECONDS)
                continue

            # 3. No GitHub activity — scrape tech news
            log("📰 No GitHub updates. Fetching latest tech news...")
            await post_from_news()

            # 4. Wait before next cycle (check every hour)
            log("💤 Sleeping for 1 hour before next cycle...")
            await asyncio.sleep(AGENT_CYCLE_INTERVAL_SECONDS)

        except asyncio.CancelledError:
            log("🛑 Agent loop cancelled.")
            break
        except Exception as exc:
            log(f"❌ Unhandled error in agent loop: {exc}")
            logger.exception("Agent loop error")
            await asyncio.sleep(30)


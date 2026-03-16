"""LLM service using LongCat OpenAI-format API."""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

LLM_MODEL = os.getenv("LLM_MODEL", "longcat-flash-lite")
LONGCAT_BASE_URL = os.getenv("LONGCAT_BASE_URL", "https://api.longcat.chat/openai").rstrip("/")
LONGCAT_API_KEY = os.getenv("LONGCAT_API_KEY") or os.getenv("OPENAI_API_KEY", "")
REQUEST_TIMEOUT = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))


def get_request_headers() -> dict[str, str]:
    if not LONGCAT_API_KEY:
        msg = (
            "LLM API key is NOT configured. "
            "Set LONGCAT_API_KEY (or OPENAI_API_KEY) in your .env file. "
            "All LLM-dependent features will fail until this is fixed."
        )
        logger.error(msg)
        raise ValueError(msg)
    return {
        "Authorization": f"Bearer {LONGCAT_API_KEY}",
        "Content-Type": "application/json",
    }


async def generate_text(prompt: str, temperature: float = 0.7) -> str:
    """Generate text using LongCat OpenAI-format chat completions."""
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            response = await client.post(
                f"{LONGCAT_BASE_URL}/chat/completions",
                headers=get_request_headers(),
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "LLM API HTTP error %s for model '%s': %s",
                exc.response.status_code, LLM_MODEL, exc.response.text[:300],
            )
            raise
        except httpx.RequestError as exc:
            logger.error("LLM API connection error: %s", exc)
            raise

    data = response.json()
    content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
    if not content:
        logger.error("LLM returned an empty completion. Full response: %s", data)
        raise ValueError("LongCat returned an empty completion response.")
    return content.strip()


async def generate_repo_description(repo: dict[str, Any], readme: str) -> str:
    """Generate a short description of a GitHub repo using its README."""
    prompt = f"""You are a technical writer. Based on the repository information below, 
write a concise 2-3 sentence description of what this project does.

Repository name: {repo.get('name', '')}
GitHub description: {repo.get('description') or 'None'}
Primary language: {repo.get('language') or 'Unknown'}
Topics: {', '.join(repo.get('topics', []))}
Stars: {repo.get('stargazers_count', 0)}

README (first 3000 chars):
{readme[:3000] if readme else 'Not available'}

Write only the description, no headers or labels."""
    return await generate_text(prompt, temperature=0.4)


async def generate_linkedin_post(
    repo: dict[str, Any],
    description: str,
    readme: str,
    memory_context: str = "",
    post_index: int = 1,
    total_posts: int = 1,
) -> str:
    """Generate a LinkedIn post about a GitHub repo."""
    post_focus = ""
    if total_posts > 1:
        focuses = {
            1: "Overview and motivation — what problem does this solve and why I built it.",
            2: "Technical deep-dive — key technologies, architecture, and interesting implementation details.",
            3: "Results, learnings, and future plans for this project.",
        }
        post_focus = f"\nFocus for this post ({post_index}/{total_posts}): {focuses.get(post_index, focuses[1])}"

    memory_note = ""
    if memory_context:
        memory_note = f"\n\nPrevious approved posts (for style reference — avoid repeating):\n{memory_context[:1000]}"

    prompt = f"""You are a LinkedIn content creator for a software developer. 
Write an engaging LinkedIn post about the following GitHub repository.{post_focus}

Repository: {repo.get('name', '')}
Description: {description}
Language: {repo.get('language') or 'Unknown'}
Stars: {repo.get('stargazers_count', 0)}
URL: {repo.get('html_url', '')}
Topics: {', '.join(repo.get('topics', []))}

README excerpt:
{readme[:1500] if readme else 'Not available'}{memory_note}

Guidelines:
- Write in first person as the developer
- Be genuine, enthusiastic, and technical but accessible
- Include 3-5 relevant hashtags at the end
- 150-300 words
- Do NOT use em-dashes (—) excessively
- End with a call to action (check it out, feedback welcome, etc.)
- Do NOT include placeholder text like [your name] or [link]

Write only the post content, nothing else."""
    return await generate_text(prompt, temperature=0.8)


async def generate_news_post(article: dict[str, Any], memory_context: str = "") -> str:
    """Generate a LinkedIn post from a news/research article."""
    memory_note = ""
    if memory_context:
        memory_note = f"\n\nPrevious approved posts for style reference:\n{memory_context[:800]}"

    prompt = f"""You are a LinkedIn content creator passionate about AI, ML, and technology.
Write an engaging LinkedIn post about this news/research item.{memory_note}

Title: {article.get('title', '')}
Source: {article.get('source', '')}
URL: {article.get('url', '')}
Summary: {article.get('summary', '')[:1200]}

Guidelines:
- Write in first person, sharing your perspective and excitement
- Explain why this matters to developers and the AI community
- Include 3-5 relevant hashtags at the end
- 150-250 words
- Be insightful, not just a summary

Write only the post content, nothing else."""
    return await generate_text(prompt, temperature=0.8)


async def generate_custom_post(topic: str, repos_md: str, memory_context: str = "") -> str:
    """Generate a post on a custom topic, incorporating repo context if relevant."""
    memory_note = ""
    if memory_context:
        memory_note = f"\n\nPrevious posts for style reference:\n{memory_context[:800]}"

    prompt = f"""You are a LinkedIn content creator for a software developer specializing in AI/ML.
Write an engaging LinkedIn post about: {topic}{memory_note}

Check if any of the developer's repos below are relevant to this topic and mention them if so:
{repos_md[:2000] if repos_md else 'Not available'}

Guidelines:
- Write in first person
- Be technical but accessible
- Include 3-5 relevant hashtags
- 150-300 words
- If a relevant repo exists, mention it with the GitHub link

Write only the post content, nothing else."""
    return await generate_text(prompt, temperature=0.8)


async def generate_commit_activity_post(
    repo_name: str,
    repo_info: dict[str, Any],
    file_path: str,
    file_content: str,
    activity_summary: str,
    memory_context: str = "",
    repos_context: str = "",
) -> str:
    """Generate a LinkedIn post about a newly implemented feature in a repo.

    The post should read as "I just implemented [functionality] in [repo]" style.
    """
    memory_note = ""
    if memory_context:
        memory_note = (
            f"\n\nPrevious approved posts (for style reference — avoid repeating):\n"
            f"{memory_context[:800]}"
        )

    repos_note = ""
    if repos_context:
        repos_note = f"\n\nYour repositories context:\n{repos_context[:800]}"

    prompt = f"""You are a LinkedIn content creator for a software developer.
I just pushed new code to my GitHub repository '{repo_name}'.
Write an engaging LinkedIn post about this new functionality/feature I implemented.

Repository: {repo_name}
Language: {repo_info.get('language') or 'Unknown'}
URL: {repo_info.get('html_url', '')}
What changed (summary): {activity_summary}

The file I worked on ({file_path}):
```
{file_content[:2500]}
```
{repos_note}{memory_note}

Guidelines:
- Write in first person as the developer
- Frame it as "I just implemented / built / added [feature] in [repo]"
- Explain what the new feature does and why it is useful or interesting
- Be technical but accessible; highlight design decisions if visible in the code
- Include 3-5 relevant hashtags at the end
- 150-300 words
- End with a call to action (check it out, feedback welcome, etc.)
- Do NOT include placeholder text like [your name] or [link]

Write only the post content, nothing else."""
    return await generate_text(prompt, temperature=0.8)


async def summarize_commit_activity(
    repo_name: str, commits: list[dict[str, Any]]
) -> str:
    """Summarize recent commit activity for deciding if it's worth a post."""
    if not commits:
        return ""
    commit_messages = "\n".join(
        f"- {c['commit']['message'].split(chr(10))[0]}"
        for c in commits[:10]
        if c.get("commit", {}).get("message")
    )
    prompt = f"""Analyze these recent commits to the '{repo_name}' repository:
{commit_messages}

In 1-2 sentences, describe what significant changes or features were added. 
If the changes are trivial (just docs, minor fixes), say "trivial".
Be concise."""
    return await generate_text(prompt, temperature=0.3)


async def is_activity_worth_posting(summary: str) -> bool:
    """Ask the LLM if activity is worth a LinkedIn post."""
    if not summary or summary.lower().strip() == "trivial":
        return False
    prompt = f"""Is this GitHub activity interesting enough to share as a LinkedIn post?
Activity: {summary}
Answer only "yes" or "no"."""
    answer = await generate_text(prompt, temperature=0.1)
    return answer.strip().lower().startswith("y")


async def chat_response(user_message: str, context: str = "") -> str:
    """Generate a friendly conversational reply to a user message."""
    system_note = (
        "You are a friendly AI assistant embedded in a LinkedIn content agent. "
        "You help the owner manage their LinkedIn posts and GitHub repos. "
        "Be concise, helpful, and conversational. "
        "If the user seems to be asking about the agent or their repos/posts, give a relevant helpful answer. "
        "Keep replies under 200 words."
    )
    ctx_block = f"\n\nAgent context:\n{context[:600]}" if context else ""
    prompt = f"""{system_note}{ctx_block}

User message: {user_message}

Reply:"""
    return await generate_text(prompt, temperature=0.7)


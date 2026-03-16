"""Scraper service - fetch latest AI/ML/tech news from multiple sources."""

import asyncio
import logging
import os
from typing import Any

import feedparser
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")

SOURCES: list[dict[str, Any]] = [
    {
        "name": "HuggingFace Blog",
        "feed_url": "https://huggingface.co/blog/feed.xml",
        "base_url": "https://huggingface.co",
        "type": "rss",
    },
    {
        "name": "ArXiv AI",
        "feed_url": "https://rss.arxiv.org/rss/cs.AI",
        "base_url": "https://arxiv.org",
        "type": "rss",
    },
    {
        "name": "ArXiv ML",
        "feed_url": "https://rss.arxiv.org/rss/cs.LG",
        "base_url": "https://arxiv.org",
        "type": "rss",
    },
    {
        "name": "Google AI Blog",
        "feed_url": "https://blog.research.google/feeds/posts/default",
        "base_url": "https://blog.research.google",
        "type": "rss",
    },
    {
        "name": "Papers With Code",
        "feed_url": "https://paperswithcode.com/latest.xml",
        "base_url": "https://paperswithcode.com",
        "type": "rss",
    },
    {
        "name": "The Gradient",
        "feed_url": "https://thegradient.pub/rss/",
        "base_url": "https://thegradient.pub",
        "type": "rss",
    },
    {
        "name": "Towards Data Science",
        "feed_url": "https://towardsdatascience.com/feed",
        "base_url": "https://towardsdatascience.com",
        "type": "rss",
    },
]

MAX_ARTICLES_PER_SOURCE = 3
MAX_SOURCES = 5


async def fetch_rss_feed(source: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch and parse an RSS feed."""
    feed_url = source["feed_url"]
    articles: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(feed_url, headers={"User-Agent": "LinkedInAgent/1.0"})
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
                summary = ""
                if hasattr(entry, "summary"):
                    soup = BeautifulSoup(entry.summary, "html.parser")
                    summary = soup.get_text(separator=" ", strip=True)[:800]
                articles.append({
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "summary": summary,
                    "source": source["name"],
                    "published": entry.get("published", ""),
                })
    except Exception as exc:
        logger.warning(f"Failed to fetch {source['name']}: {exc}")
    return articles


async def fetch_page_with_cloudflare(url: str) -> str:
    """Use Cloudflare Browser Rendering API for JS-heavy pages."""
    if not CLOUDFLARE_API_TOKEN or not CLOUDFLARE_ACCOUNT_ID:
        return ""
    cf_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/browser-rendering/content"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                cf_url,
                json={"url": url, "rejectResourceTypes": ["image", "media", "font"]},
                headers={"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"},
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("result", {}).get("content", "")
    except Exception as exc:
        logger.warning(f"Cloudflare scraping failed for {url}: {exc}")
    return ""


async def fetch_latest_tech_news(max_sources: int = MAX_SOURCES) -> list[dict[str, Any]]:
    """Fetch latest AI/ML/tech articles from all configured sources."""
    tasks = [fetch_rss_feed(source) for source in SOURCES[:max_sources]]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    articles: list[dict[str, Any]] = []
    for result in results:
        if isinstance(result, list):
            articles.extend(result)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique: list[dict[str, Any]] = []
    for article in articles:
        url = article.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(article)

    return unique

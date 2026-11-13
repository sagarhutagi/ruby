#!/usr/bin/env python3
"""
SearXNG-Compatible Local Search Gateway Service for Ruby.
Exposes SearXNG HTTP JSON Search API (GET /search?q={query}&format=json).
Provides high-speed, multi-engine aggregated web search:
- DDGS News (breaking / current news via Bing/DuckDuckGo/Yahoo)
- DDGS Web Text (metasearch across web engines)
- Wikipedia API (encyclopedic, academic, and technical knowledge)
- DuckDuckGo Instant Answers (official definitions, summaries, and quick facts)

Features strict latency boundaries (3.5s deadline) and IPv4 enforcement
to prevent timeouts and unreachable IPv6 connection stalls.
"""
import sys
import json
import logging
import asyncio
import re
import socket
import urllib.parse
from typing import List, Dict, Any, Optional

import httpx
from fastapi import FastAPI, Query
import uvicorn

# ---------------------------------------------------------------------------
# Force IPv4 socket resolution.
# Linux hosts lacking an active IPv6 default route will stall or fail with
# [Errno 101] Network is unreachable when DNS returns AAAA records first.
# ---------------------------------------------------------------------------
_orig_getaddrinfo = socket.getaddrinfo


def _getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)


socket.getaddrinfo = _getaddrinfo_ipv4

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] searxng-gateway: %(message)s",
)
logger = logging.getLogger("searxng_gateway")

app = FastAPI(title="SearXNG Local Search Gateway", version="1.1.0")

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
WIKI_UA = "RubyAcademicAI/1.0 (academic research assistant; contact@ruby.local)"


async def fetch_ddgs_news(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Fetch live news using ddgs news aggregator in a background thread."""
    try:
        from ddgs import DDGS

        def _sync_news():
            with DDGS(timeout=2.2) as d:
                return list(d.news(query, max_results=max_results))

        raw = await asyncio.to_thread(_sync_news)
        results = []
        for r in raw:
            title = r.get("title", "").strip()
            url = r.get("url", "").strip()
            snippet = r.get("body", "").strip()
            if title and url:
                results.append({
                    "title": title,
                    "url": url,
                    "content": snippet,
                    "engine": "bing_news",
                    "category": "news",
                })
        return results
    except Exception as e:
        logger.debug(f"ddgs.news failed for '{query}': {e}")
        return []


async def fetch_ddgs_text(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Fetch web text search results using ddgs in a background thread."""
    try:
        from ddgs import DDGS

        def _sync_text():
            with DDGS(timeout=2.2) as d:
                return list(d.text(query, max_results=max_results))

        raw = await asyncio.to_thread(_sync_text)
        results = []
        for r in raw:
            title = r.get("title", "").strip()
            url = r.get("href", "").strip()
            snippet = r.get("body", "").strip()
            if title and url:
                results.append({
                    "title": title,
                    "url": url,
                    "content": snippet,
                    "engine": "duckduckgo",
                    "category": "general",
                })
        return results
    except Exception as e:
        logger.debug(f"ddgs.text failed for '{query}': {e}")
        return []


async def fetch_wikipedia(query: str, limit: int = 4) -> List[Dict[str, Any]]:
    """Fetch Wikipedia articles using Wikipedia query full-text search API."""
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            resp = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "utf8": "",
                    "format": "json",
                    "srlimit": limit,
                },
                headers={"User-Agent": WIKI_UA},
            )
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for item in data.get("query", {}).get("search", []):
                    title = item.get("title", "").strip()
                    if not title:
                        continue
                    url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                    snippet = re.sub(r"<[^>]+>", "", item.get("snippet", "")).strip()
                    results.append({
                        "title": title,
                        "url": url,
                        "content": snippet or f"Wikipedia article on {title}",
                        "engine": "wikipedia",
                        "category": "general",
                    })
                return results
    except Exception as e:
        logger.debug(f"Wikipedia search failed for '{query}': {e}")
    return []


async def fetch_ddg_instant(query: str) -> List[Dict[str, Any]]:
    """Fetch DuckDuckGo Instant Answer / Abstract."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1},
                headers={"User-Agent": BROWSER_UA},
            )
            if resp.status_code == 200:
                data = resp.json()
                results = []
                heading = data.get("Heading", query)
                abstract = data.get("Abstract", "").strip()
                abstract_url = data.get("AbstractURL", "").strip()
                if abstract and abstract_url:
                    results.append({
                        "title": heading,
                        "url": abstract_url,
                        "content": abstract,
                        "engine": "duckduckgo_instant",
                        "category": "general",
                    })
                for topic in data.get("RelatedTopics", [])[:2]:
                    if isinstance(topic, dict):
                        txt = topic.get("Text", "").strip()
                        furl = topic.get("FirstURL", "").strip()
                        if txt and furl:
                            results.append({
                                "title": txt[:70],
                                "url": furl,
                                "content": txt,
                                "engine": "duckduckgo_instant",
                                "category": "general",
                            })
                return results
    except Exception as e:
        logger.debug(f"DDG Instant failed for '{query}': {e}")
    return []


@app.get("/health")
@app.get("/")
async def health_check():
    return {
        "status": "healthy",
        "service": "SearXNG-Compatible Search Gateway",
        "version": "1.1.0",
        "endpoint": "/search?q={query}&format=json",
    }


@app.get("/search")
async def search_endpoint(
    q: str = Query(..., description="Search query string"),
    format: str = Query("json", description="Output format"),
    categories: Optional[str] = Query(None),
):
    clean_q = q.strip()
    if clean_q == "ping":
        return {
            "query": "ping",
            "number_of_results": 1,
            "results": [
                {
                    "title": "SearXNG Gateway Operational",
                    "url": "http://127.0.0.1:8080",
                    "content": "SearXNG local JSON search gateway is healthy and operational.",
                    "engine": "searxng",
                    "category": "general",
                }
            ],
        }

    if not clean_q:
        return {"query": "", "number_of_results": 0, "results": []}

    # Dispatch parallel tasks with strict 3.5s deadline
    tasks = [
        asyncio.create_task(fetch_ddg_instant(clean_q)),
        asyncio.create_task(fetch_wikipedia(clean_q)),
        asyncio.create_task(fetch_ddgs_news(clean_q, max_results=5)),
        asyncio.create_task(fetch_ddgs_text(clean_q, max_results=5)),
    ]

    done, pending = await asyncio.wait(tasks, timeout=3.5)
    for p in pending:
        p.cancel()

    seen_urls = set()
    combined_results: List[Dict[str, Any]] = []

    for t in done:
        try:
            batch = t.result()
            for r in batch:
                u_norm = r["url"].rstrip("/").lower()
                if u_norm not in seen_urls:
                    seen_urls.add(u_norm)
                    combined_results.append(r)
        except Exception as e:
            logger.warning(f"Error gathering search task: {e}")

    logger.info(
        f"Search query='{clean_q}' completed with {len(combined_results)} results "
        f"({len(done)} tasks finished, {len(pending)} timed out)."
    )

    return {
        "query": clean_q,
        "number_of_results": len(combined_results),
        "results": combined_results,
    }


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    logger.info(f"Starting SearXNG Gateway on http://127.0.0.1:{port}...")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

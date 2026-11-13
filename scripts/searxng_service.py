#!/usr/bin/env python3
"""
SearXNG-Compatible Local Search Gateway Service for Ruby.
Exposes SearXNG HTTP JSON Search API (GET /search?q={query}&format=json).
Provides real-time web search results using multi-engine aggregation
(DuckDuckGo Search via ddgs + Wikipedia opensearch fallback).
"""
import sys
import json
import logging
from typing import List, Dict, Any, Optional
import urllib.parse
import urllib.request
from fastapi import FastAPI, Query
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] searxng-gateway: %(message)s")
logger = logging.getLogger("searxng_gateway")

app = FastAPI(title="SearXNG Local Search Gateway", version="1.0.0")


def search_duckduckgo(query: str, max_results: int = 6) -> List[Dict[str, Any]]:
    try:
        from ddgs import DDGS
        ddgs = DDGS()
        raw = list(ddgs.text(query, max_results=max_results))
        results = []
        for r in raw:
            title = r.get("title", "")
            url = r.get("href", "")
            snippet = r.get("body", "")
            if url and title:
                results.append({
                    "title": title,
                    "url": url,
                    "content": snippet,
                    "engine": "duckduckgo",
                    "category": "general",
                })
        return results
    except Exception as e:
        logger.warning(f"DuckDuckGo search error: {e}")
        return []


def search_wikipedia(query: str, limit: int = 4) -> List[Dict[str, Any]]:
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(query)}&limit={limit}&namespace=0&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "RubySearchGateway/1.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            titles, snippets, urls = data[1], data[2], data[3]
            results = []
            for t, s, u in zip(titles, snippets, urls):
                results.append({
                    "title": t,
                    "url": u,
                    "content": s or f"Wikipedia article on {t}",
                    "engine": "wikipedia",
                    "category": "general",
                })
            return results
    except Exception as e:
        logger.warning(f"Wikipedia search error: {e}")
        return []


@app.get("/health")
@app.get("/")
async def health_check():
    return {
        "status": "healthy",
        "service": "SearXNG-Compatible Search Gateway",
        "version": "1.0.0",
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

    # Aggregate search results
    results = search_duckduckgo(clean_q, max_results=6)
    if not results or len(results) < 2:
        wiki_results = search_wikipedia(clean_q, limit=3)
        results.extend(wiki_results)

    return {
        "query": clean_q,
        "number_of_results": len(results),
        "results": results,
    }


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    logger.info(f"Starting SearXNG Gateway on http://127.0.0.1:{port}...")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

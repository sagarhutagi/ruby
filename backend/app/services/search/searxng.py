import time
import logging
from typing import List, Optional, Dict, Any, Tuple
import httpx
from pydantic import BaseModel, Field
from app.core.config import settings

logger = logging.getLogger("ruby.search.searxng")


class WebSearchResultItem(BaseModel):
    title: str = Field(..., description="Page title")
    url: str = Field(..., description="Canonical page URL")
    snippet: str = Field(..., description="Snippet / excerpt text")
    engine: Optional[str] = Field(default=None, description="Search engine name")
    score: Optional[float] = Field(default=None, description="Relevance score from SearXNG")
    source_type: str = Field(default="web", description="Always 'web' to distinguish from local documents")


class WebSearchResponse(BaseModel):
    query: str
    results: List[WebSearchResultItem] = Field(default_factory=list)
    total_results: int = 0
    is_available: bool = True
    latency_ms: float = 0.0
    error: Optional[str] = None


class SearxngClient:
    """
    Client for SearXNG HTTP Search API.
    Docs: https://docs.searxng.org/dev/search_api.html
    Endpoint: GET {base_url}/search?q={query}&format=json
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        self._custom_url = base_url
        self.timeout = timeout or settings.searxng_timeout

    @property
    def base_url(self) -> Optional[str]:
        raw = self._custom_url or settings.searxng_url
        if raw:
            return raw.rstrip("/")
        return None

    def is_configured(self) -> bool:
        return bool(self.base_url)

    async def test_connection(self) -> Dict[str, Any]:
        """Test reachability of the configured SearXNG instance."""
        if not self.is_configured():
            return {
                "configured": False,
                "reachable": False,
                "message": "SearXNG URL is not configured. Set the SEARXNG_URL environment variable (e.g. http://localhost:8080).",
                "searxng_url": None,
                "latency_ms": 0.0,
            }

        start = time.perf_counter()
        try:
            url = f"{self.base_url}/search"
            async with httpx.AsyncClient(timeout=min(self.timeout, 5.0)) as client:
                res = await client.get(url, params={"q": "ping", "format": "json"})
                latency = round((time.perf_counter() - start) * 1000, 2)
                if res.status_code == 200:
                    data = res.json()
                    results_count = len(data.get("results", []))
                    return {
                        "configured": True,
                        "reachable": True,
                        "message": f"Successfully connected to SearXNG ({results_count} test results).",
                        "searxng_url": self.base_url,
                        "latency_ms": latency,
                    }
                return {
                    "configured": True,
                    "reachable": False,
                    "message": f"SearXNG responded with HTTP {res.status_code}: {res.text[:120]}",
                    "searxng_url": self.base_url,
                    "latency_ms": latency,
                }
        except httpx.TimeoutException:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {
                "configured": True,
                "reachable": False,
                "message": f"Connection to SearXNG at {self.base_url} timed out.",
                "searxng_url": self.base_url,
                "latency_ms": latency,
            }
        except Exception as e:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {
                "configured": True,
                "reachable": False,
                "message": f"Could not connect to SearXNG at {self.base_url}: {str(e)}",
                "searxng_url": self.base_url,
                "latency_ms": latency,
            }

    async def search(
        self,
        query: str,
        num_results: int = 5,
        categories: Optional[List[str]] = None,
    ) -> WebSearchResponse:
        """
        Execute web search query via SearXNG JSON API.
        Never fabricates results, handles timeouts and errors gracefully.
        """
        clean_query = query.strip()
        if not clean_query:
            return WebSearchResponse(
                query=query,
                results=[],
                total_results=0,
                is_available=True,
                error="Empty search query",
            )

        if not self.is_configured():
            return WebSearchResponse(
                query=clean_query,
                results=[],
                total_results=0,
                is_available=False,
                error="SearXNG URL is not configured. Set SEARXNG_URL (e.g. http://localhost:8080) to enable web search.",
            )

        start = time.perf_counter()
        params: Dict[str, Any] = {
            "q": clean_query,
            "format": "json",
        }
        if categories:
            params["categories"] = ",".join(categories)

        url = f"{self.base_url}/search"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, params=params)
                latency = round((time.perf_counter() - start) * 1000, 2)

                if res.status_code != 200:
                    err_msg = f"SearXNG API returned HTTP status {res.status_code}"
                    logger.warning("SearXNG search error: %s", err_msg)
                    return WebSearchResponse(
                        query=clean_query,
                        results=[],
                        total_results=0,
                        is_available=False,
                        latency_ms=latency,
                        error=err_msg,
                    )

                data = res.json()
                raw_results = data.get("results", [])
                items: List[WebSearchResultItem] = []

                for item in raw_results[:num_results]:
                    # Extract fields safely
                    title = item.get("title", "").strip() or "Web Resource"
                    item_url = item.get("url", "").strip()
                    snippet = item.get("content", "").strip() or item.get("snippet", "").strip()
                    engine = item.get("engine", "web")
                    score = item.get("score")

                    if not item_url:
                        continue

                    items.append(
                        WebSearchResultItem(
                            title=title,
                            url=item_url,
                            snippet=snippet,
                            engine=engine,
                            score=float(score) if score is not None else None,
                            source_type="web",
                        )
                    )

                return WebSearchResponse(
                    query=clean_query,
                    results=items,
                    total_results=len(items),
                    is_available=True,
                    latency_ms=latency,
                    error=None if items else "No web search results found for the query.",
                )

        except httpx.TimeoutException:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.warning("SearXNG search timed out after %s seconds for query: %s", self.timeout, clean_query)
            return WebSearchResponse(
                query=clean_query,
                results=[],
                total_results=0,
                is_available=False,
                latency_ms=latency,
                error=f"SearXNG search timed out after {self.timeout} seconds.",
            )
        except httpx.ConnectError as e:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.warning("SearXNG connection refused at %s: %s", self.base_url, e)
            return WebSearchResponse(
                query=clean_query,
                results=[],
                total_results=0,
                is_available=False,
                latency_ms=latency,
                error=f"Could not connect to SearXNG at {self.base_url}. Ensure the SearXNG daemon is running.",
            )
        except Exception as e:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.exception("Unexpected error during SearXNG search: %s", e)
            return WebSearchResponse(
                query=clean_query,
                results=[],
                total_results=0,
                is_available=False,
                latency_ms=latency,
                error=f"Web search error: {str(e)}",
            )

    def detect_web_search_need(self, query: str) -> bool:
        """
        Heuristic to determine if the user's prompt requires live web search.
        Used when manual toggle is not explicitly set in general/hybrid/research modes.
        """
        q = query.lower().strip()
        triggers = [
            "search the web",
            "search online",
            "look up online",
            "search google",
            "search internet",
            "latest research",
            "recent developments",
            "current state of",
            "news about",
            "release date of",
            "who is currently",
            "what is the latest",
            "in 2025",
            "in 2026",
            "arxiv",
            "github repo",
        ]
        return any(trigger in q for trigger in triggers)


searxng_client = SearxngClient()

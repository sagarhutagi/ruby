import pytest
from unittest.mock import AsyncMock, patch
import httpx
from app.services.search.searxng import SearxngClient, WebSearchResponse


@pytest.mark.asyncio
async def test_searxng_unconfigured():
    client = SearxngClient(base_url=None)
    res = await client.search("test query")
    assert not res.is_available
    assert "not configured" in res.error.lower()
    assert len(res.results) == 0

    conn = await client.test_connection()
    assert not conn["configured"]
    assert not conn["reachable"]


@pytest.mark.asyncio
async def test_searxng_successful_search():
    client = SearxngClient(base_url="http://test-searxng.local:8080")

    mock_json = {
        "query": "Dijkstra algorithm",
        "results": [
            {
                "title": "Dijkstra's Algorithm - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm",
                "content": "Dijkstra's algorithm is an algorithm for finding the shortest paths between nodes in a weighted graph.",
                "engine": "google",
                "score": 0.95,
            },
            {
                "title": "Dijkstra Algorithm - GeeksforGeeks",
                "url": "https://www.geeksforgeeks.org/dijkstras-shortest-path-algorithm-greedy-algo-7/",
                "content": "Given a graph and a source vertex in the graph, find shortest paths from source to all vertices.",
                "engine": "bing",
                "score": 0.88,
            },
        ],
    }

    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_json

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = await client.search("Dijkstra algorithm", num_results=2)
        assert res.is_available
        assert res.total_results == 2
        assert len(res.results) == 2
        assert res.results[0].title == "Dijkstra's Algorithm - Wikipedia"
        assert res.results[0].url == "https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm"
        assert res.results[0].source_type == "web"
        assert res.error is None


@pytest.mark.asyncio
async def test_searxng_timeout_handling():
    client = SearxngClient(base_url="http://test-searxng.local:8080", timeout=2)

    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
        res = await client.search("Timeout query")
        assert not res.is_available
        assert len(res.results) == 0
        assert "timed out" in res.error.lower()


@pytest.mark.asyncio
async def test_searxng_connection_refused_handling():
    client = SearxngClient(base_url="http://127.0.0.1:9999")

    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection refused")):
        res = await client.search("Offline query")
        assert not res.is_available
        assert len(res.results) == 0
        assert "could not connect" in res.error.lower()


@pytest.mark.asyncio
async def test_searxng_empty_results():
    client = SearxngClient(base_url="http://test-searxng.local:8080")

    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"query": "nonexistent term", "results": []}

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = await client.search("nonexistent term")
        assert res.is_available
        assert res.total_results == 0
        assert len(res.results) == 0
        assert "no web search results" in res.error.lower()


@pytest.mark.asyncio
async def test_searxng_heuristic_detection():
    client = SearxngClient()
    assert client.detect_web_search_need("Search the web for latest quantum computing papers")
    assert client.detect_web_search_need("Look up online who is the author of Kurose Ross")
    assert client.detect_web_search_need("What are recent developments in deep learning in 2025")
    assert not client.detect_web_search_need("Explain page table entry format")

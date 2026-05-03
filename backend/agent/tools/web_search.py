"""
Web search tool for E.V.A.

Uses Bing Search API when BING_SEARCH_API_KEY is configured, otherwise
falls back to DuckDuckGo HTML scraping (no key required).

Returns a list of dicts: [{"title": ..., "url": ..., "snippet": ...}, ...]
"""

from __future__ import annotations

import logging
from typing import Any

from backend import config

logger = logging.getLogger(__name__)

MAX_RESULTS = 5


def web_search(query: str, num_results: int = MAX_RESULTS) -> list[dict[str, str]]:
    """Search the web and return a list of result dicts."""
    if config.BING_SEARCH_API_KEY:
        return _bing_search(query, num_results)
    return _ddg_search(query, num_results)


# ── Bing Search ───────────────────────────────────────────────────────────

def _bing_search(query: str, num_results: int) -> list[dict[str, str]]:
    import requests  # type: ignore

    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": config.BING_SEARCH_API_KEY}
    params: dict[str, Any] = {"q": query, "count": num_results, "textDecorations": False}

    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("webPages", {}).get("value", [])[:num_results]:
        results.append(
            {
                "title": item.get("name", ""),
                "url": item.get("url", ""),
                "snippet": item.get("snippet", ""),
            }
        )
    logger.info("Bing search '%s' → %d results", query, len(results))
    return results


# ── DuckDuckGo fallback ───────────────────────────────────────────────────

def _ddg_search(query: str, num_results: int) -> list[dict[str, str]]:
    try:
        from duckduckgo_search import DDGS  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "duckduckgo_search is required as a fallback. "
            "Install with: pip install duckduckgo-search"
        ) from exc

    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=num_results):
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
            )
    logger.info("DDG search '%s' → %d results", query, len(results))
    return results

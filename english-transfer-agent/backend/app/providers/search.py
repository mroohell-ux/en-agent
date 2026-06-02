from __future__ import annotations

import os
from abc import ABC, abstractmethod
from urllib.parse import urlparse

import httpx

from app.schemas import SearchResult

PRESET_ARTICLE_DOMAINS = [
    "theconversation.com",
    "aeon.co",
    "nautil.us",
    "quantamagazine.org",
    "smithsonianmag.com",
    "newyorker.com",
    "theatlantic.com",
    "wired.com",
    "npr.org",
    "bbc.com",
]

EXCLUDED_LEARNER_DOMAINS = [
    "newsinlevels.com",
    "breakingnewsenglish.com",
    "simple.wikipedia.org",
    "englishclub.com",
    "english-online.at",
]


def _domains_from_env(name: str, fallback: list[str]) -> list[str]:
    configured = os.getenv(name, "").strip()
    if not configured:
        return fallback
    return [domain.strip() for domain in configured.split(",") if domain.strip()]


def _site_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host.removeprefix("www.")


def _is_excluded(url: str, excluded_domains: list[str]) -> bool:
    site = _site_from_url(url)
    return any(site == domain or site.endswith(f".{domain}") for domain in excluded_domains)


def _is_homepage_url(url: str) -> bool:
    path = urlparse(url).path.strip("/")
    return not path


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int) -> list[SearchResult]:
        raise NotImplementedError


class MockSearchProvider(SearchProvider):
    def search(self, query: str, max_results: int) -> list[SearchResult]:
        return [
            SearchResult(
                title="Ocean life and climate",
                url="https://example.com/ocean-life",
                content="Two back-to-back expeditions... buffering against climate change.",
                snippet="Deep-sea organisms play a role in carbon storage.",
                site="Example Science",
            )
        ]


class TavilySearchProvider(SearchProvider):
    def __init__(self) -> None:
        self.api_key = os.getenv("TAVILY_API_KEY", "")

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        if not self.api_key:
            return MockSearchProvider().search(query, max_results)

        include_domains = _domains_from_env("TAVILY_INCLUDE_DOMAINS", PRESET_ARTICLE_DOMAINS)
        exclude_domains = _domains_from_env("TAVILY_EXCLUDE_DOMAINS", EXCLUDED_LEARNER_DOMAINS)
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max(max_results * 2, 10),
            "search_depth": "basic",
            "include_domains": include_domains,
            "exclude_domains": exclude_domains,
        }
        response = httpx.post("https://api.tavily.com/search", json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        output: list[SearchResult] = []
        for item in data.get("results", []):
            url = item.get("url", "")
            if _is_excluded(url, exclude_domains) or _is_homepage_url(url):
                continue
            output.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=url,
                    content=item.get("content", ""),
                    snippet=item.get("content", "")[:180],
                    site=_site_from_url(url) if url else "",
                )
            )
            if len(output) >= max_results:
                break
        return output


def build_search_provider(name: str) -> SearchProvider:
    if name == "tavily":
        return TavilySearchProvider()
    return MockSearchProvider()

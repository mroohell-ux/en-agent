from __future__ import annotations

import os
from abc import ABC, abstractmethod
import httpx

from app.schemas import SearchResult


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

        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        }
        response = httpx.post("https://api.tavily.com/search", json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        output: list[SearchResult] = []
        for item in data.get("results", []):
            output.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    snippet=item.get("content", "")[:180],
                    site=item.get("url", "").split("/")[2] if item.get("url") else "",
                )
            )
        return output


def build_search_provider(name: str) -> SearchProvider:
    if name == "tavily":
        return TavilySearchProvider()
    return MockSearchProvider()

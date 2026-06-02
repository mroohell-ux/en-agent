from __future__ import annotations

import os
import re
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
    "bbc.co.uk",
    "scientificamerican.com",
    "nationalgeographic.com",
    "technologyreview.com",
    "bigthink.com",
]

DEFAULT_EXCLUDED_DOMAINS = [
    "youtube.com",
    "youtu.be",

    "newsinlevels.com",
    "breakingnewsenglish.com",
    "simple.wikipedia.org",
    "englishclub.com",
    "english-online.at",
    "english4real.com",
    "linguapress.com",
    "learnenglish.britishcouncil.org",
]

BAD_TITLE_OR_URL_KEYWORDS = [
    # ESL / learning / test pages
    "worksheet",
    "worksheets",
    "exercise",
    "exercises",
    "grammar",
    "lesson",
    "lessons",
    "ielts",
    "toefl",
    "esl",
    "quiz",
    "test",
    "practice",

    # course / school / index pages
    "classroom",
    "course",
    "courses",
    "class",
    "classes",
    "credit",
    "campus",
    "college",
    "university",
    "syllabus",
    "curriculum",
    "program",

    # file/video/transcript
    "pdf",
    "transcript",
    "video",
]

BAD_LEVEL_TOKENS = [
    "b1",
    "b2",
    "c1",
    "c2",
]


def _domains_from_env(name: str, fallback: list[str]) -> list[str]:
    configured = os.getenv(name, "").strip()
    if not configured:
        return fallback
    return [domain.strip().lower() for domain in configured.split(",") if domain.strip()]


def _site_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host.removeprefix("www.")


def _is_excluded_domain(url: str, excluded_domains: list[str]) -> bool:
    site = _site_from_url(url)
    return any(site == domain or site.endswith(f".{domain}") for domain in excluded_domains)


def _is_homepage_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    query = parsed.query.strip()
    return not path and not query


def _is_pdf_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    return path.endswith(".pdf") or ".pdf" in path


def _contains_bad_level_token(text: str) -> bool:
    # Avoid false positives like "b2b" or "c10".
    tokens = re.findall(r"\b[a-zA-Z]\d\b", text.lower())
    return any(token in BAD_LEVEL_TOKENS for token in tokens)


def _contains_bad_keyword(title: str, url: str) -> bool:
    haystack = f"{title} {url}".lower()

    if _contains_bad_level_token(haystack):
        return True

    return any(keyword in haystack for keyword in BAD_TITLE_OR_URL_KEYWORDS)


def _looks_like_index_page(title: str, content: str) -> bool:
    title_l = title.lower()
    content_l = content.lower()

    index_signals = [
        "resources",
        "list of",
        "collection of",
        "all articles",
        "advanced english reading",
        "reading texts",
        "free resources",
        "story zone",
        "classes at",
        "credit classes",
        "course catalog",
        "campus",
    ]

    if any(signal in title_l for signal in index_signals):
        return True

    if content_l.count("read more") >= 4:
        return True

    if content_l.count("|") >= 8 and ("classroom" in content_l or "campus" in content_l):
        return True

    return False


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def _rejection_reason(
    title: str,
    url: str,
    content: str,
    excluded_domains: list[str],
    min_content_words: int,
) -> str | None:
    if not url:
        return "missing_url"

    if _is_excluded_domain(url, excluded_domains):
        return "excluded_domain"

    if _is_homepage_url(url):
        return "homepage"

    if _is_pdf_url(url):
        return "pdf"

    if _contains_bad_keyword(title, url):
        return "bad_keyword"

    if _looks_like_index_page(title, content):
        return "index_page"

    if _word_count(content) < min_content_words:
        return "too_short"

    return None


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
                content=(
                    "Two back-to-back expeditions in the Southwest Atlantic Ocean have "
                    "highlighted the key role played by deep-sea organisms in locking away "
                    "carbon and buffering against climate change. Scientists say these organisms "
                    "are part of a larger ocean system that stores carbon and helps regulate the "
                    "planet's climate."
                ),
                snippet="Deep-sea organisms play a role in carbon storage.",
                site="example.com",
            )
        ][:max_results]


class TavilySearchProvider(SearchProvider):
    """
    Tavily should find natural, commonly readable articles.

    Important:
    - Do not search for B2/C1/ESL/English-learning material.
    - Search for real-world articles.
    - The LLM later adapts those articles into English-transfer cards.

    Environment variables:
    - TAVILY_API_KEY
    - ARTICLE_SOURCE_MODE=open|preferred
      open: broad search first, preferred domains as fallback
      preferred: preferred domains first, broad search as fallback
    - TAVILY_INCLUDE_DOMAINS=domain1,domain2
    - TAVILY_EXCLUDE_DOMAINS=domain1,domain2
    - TAVILY_SEARCH_DEPTH=basic|advanced
    - TAVILY_MIN_CONTENT_WORDS=60
    - TAVILY_MAX_RAW_RESULTS=15
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("TAVILY_API_KEY", "").strip()
        self.last_debug: dict[str, object] = {}

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        if not self.api_key:
            return MockSearchProvider().search(query, max_results)

        excluded_domains = _domains_from_env("TAVILY_EXCLUDE_DOMAINS", DEFAULT_EXCLUDED_DOMAINS)
        preferred_domains = _domains_from_env("TAVILY_INCLUDE_DOMAINS", PRESET_ARTICLE_DOMAINS)

        source_mode = os.getenv("ARTICLE_SOURCE_MODE", "open").strip().lower()
        search_depth = os.getenv("TAVILY_SEARCH_DEPTH", "basic").strip().lower()
        min_content_words = int(os.getenv("TAVILY_MIN_CONTENT_WORDS", "60"))
        raw_result_count = int(os.getenv("TAVILY_MAX_RAW_RESULTS", str(max(max_results * 3, 15))))

        query_variants = self._build_query_variants(query)
        search_plan = self._build_search_plan(
            query_variants=query_variants,
            preferred_domains=preferred_domains,
            source_mode=source_mode,
        )

        collected: list[SearchResult] = []
        seen_urls: set[str] = set()
        attempts: list[dict[str, object]] = []

        for query_variant, include_domains, mode in search_plan:
            results, rejected = self._search_once(
                query=query_variant,
                max_results=max_results,
                raw_result_count=raw_result_count,
                search_depth=search_depth,
                exclude_domains=excluded_domains,
                include_domains=include_domains,
                min_content_words=min_content_words,
            )

            added = 0
            for result in results:
                if result.url in seen_urls:
                    continue
                collected.append(result)
                seen_urls.add(result.url)
                added += 1

                if len(collected) >= max_results:
                    break

            attempts.append(
                {
                    "mode": mode,
                    "query": query_variant,
                    "include_domains": include_domains,
                    "usable_count": len(results),
                    "added_count": added,
                    "total_collected": len(collected),
                    "rejected": rejected[:10],
                }
            )

            if len(collected) >= max_results:
                break

        if collected:
            self.last_debug = {
                "query": query,
                "attempts": attempts,
                "results": [r.model_dump() for r in collected[:max_results]],
            }
            return collected[:max_results]

        self.last_debug = {
            "query": query,
            "attempts": attempts,
            "results": [],
        }

        raise RuntimeError(
            "Tavily returned no usable natural article pages after filtering. "
            "Try a broader topic or reduce filtering. Debug attempts: "
            + str(attempts)
        )

    def _build_search_plan(
        self,
        query_variants: list[str],
        preferred_domains: list[str],
        source_mode: str,
    ) -> list[tuple[str, list[str] | None, str]]:
        search_plan: list[tuple[str, list[str] | None, str]] = []

        if source_mode == "preferred":
            for query_variant in query_variants:
                search_plan.append((query_variant, preferred_domains, "preferred_domains"))

            for query_variant in query_variants:
                search_plan.append((query_variant, None, "broad_fallback"))

            return search_plan

        # Default: broad search first.
        for query_variant in query_variants:
            search_plan.append((query_variant, None, "broad"))

        # Then try preferred domains if broad search does not collect enough.
        for query_variant in query_variants:
            search_plan.append((query_variant, preferred_domains, "preferred_domains_fallback"))

        return search_plan

    def _build_query_variants(self, query: str) -> list[str]:
        cleaned = self._clean_query(query)

        return [
            cleaned,
            f"{cleaned} engaging article for general readers clear writing",
            (
                "engaging general-reader article about science culture technology "
                "psychology health environment modern life clear writing"
            ),
            (
                "interesting public-facing article about discovery human behavior "
                "technology culture environment clear prose"
            ),
        ]

    def _clean_query(self, query: str) -> str:
        """
        Remove learning-level / ESL terms from the query because those attract ESL resources.
        """
        cleaned = query

        banned_phrases = [
            "b2-c1",
            "b2",
            "c1",
            "c2",
            "esl",
            "english learner",
            "english learning",
            "english transfer practice",
            "transfer practice",
            "worksheet",
            "exercise",
            "ielts",
            "toefl",
            "grammar lesson",
            "essay",
        ]

        for phrase in banned_phrases:
            cleaned = re.sub(re.escape(phrase), "", cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r"[;|]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        if not cleaned:
            return "engaging general-reader article clear writing interesting ideas"

        return cleaned

    def _search_once(
        self,
        query: str,
        max_results: int,
        raw_result_count: int,
        search_depth: str,
        exclude_domains: list[str],
        include_domains: list[str] | None,
        min_content_words: int,
    ) -> tuple[list[SearchResult], list[dict[str, str]]]:
        payload: dict[str, object] = {
            "api_key": self.api_key,
            "query": query,
            "max_results": raw_result_count,
            "search_depth": search_depth,
            "include_answer": False,
            "include_raw_content": False,
            "exclude_domains": exclude_domains,
        }

        if include_domains:
            payload["include_domains"] = include_domains

        response = httpx.post(
            "https://api.tavily.com/search",
            json=payload,
            timeout=20,
        )
        response.raise_for_status()

        data = response.json()
        output: list[SearchResult] = []
        rejected: list[dict[str, str]] = []

        for item in data.get("results", []):
            title = item.get("title", "") or ""
            url = item.get("url", "") or ""
            content = item.get("content", "") or ""
            site = _site_from_url(url) if url else ""

            reason = _rejection_reason(
                title=title,
                url=url,
                content=content,
                excluded_domains=exclude_domains,
                min_content_words=min_content_words,
            )

            if reason:
                rejected.append(
                    {
                        "title": title,
                        "url": url,
                        "site": site,
                        "reason": reason,
                    }
                )
                continue

            output.append(
                SearchResult(
                    title=title,
                    url=url,
                    content=content,
                    snippet=content[:240],
                    site=site,
                )
            )

        output.sort(key=lambda r: _word_count(r.content), reverse=True)

        return output[:max_results], rejected


def build_search_provider(name: str) -> SearchProvider:
    normalized = (name or "mock").strip().lower()

    if normalized == "tavily":
        return TavilySearchProvider()

    return MockSearchProvider()
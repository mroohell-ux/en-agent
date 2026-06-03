from __future__ import annotations

import html as html_lib
import logging
import os
import re
from abc import ABC, abstractmethod
from urllib.parse import urlparse

import httpx

from app.logging_utils import color_request_log
from app.schemas import SearchResult


logger = logging.getLogger(__name__)


def _redact_search_payload(payload: dict[str, object]) -> dict[str, object]:
    return {
        key: ("[REDACTED]" if key == "api_key" else value)
        for key, value in payload.items()
    }


PRESET_ARTICLE_DOMAINS = [
    # General essays, science, technology, culture, and longform features.
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
    "atlasobscura.com",
    "longreads.com",
    "narratively.com",
    "lithub.com",
    "parisreview.org",
    "granta.com",

    # News and current affairs with strong feature writing.
    "apnews.com",
    "reuters.com",
    "theguardian.com",
    "time.com",
    "vox.com",
    "slate.com",
    "propublica.org",
    "restofworld.org",

    # Sports features and profiles.
    "espn.com",
    "si.com",
    "sports.yahoo.com",
    "olympics.com",
    "theplayerstribune.com",

    # Arts, design, film, music, and books.
    "artnews.com",
    "artsy.net",
    "hyperallergic.com",
    "vulture.com",
    "pitchfork.com",
    "rollingstone.com",
    "vanityfair.com",

    # Food, cooking, restaurants, and everyday culture.
    "seriouseats.com",
    "bonappetit.com",
    "foodandwine.com",
    "eater.com",
    "saveur.com",
    "tastecooking.com",
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

ARTICLE_BLOCK_RE = re.compile(r"<(article|main)\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
BODY_RE = re.compile(r"<body\b[^>]*>(.*?)</body>", re.IGNORECASE | re.DOTALL)
DROP_TAG_RE = re.compile(
    r"<(script|style|noscript|svg|form|nav|footer|header|aside|iframe)\b[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
BLOCK_BREAK_RE = re.compile(r"</?(p|br|div|section|h[1-6]|li|blockquote)\b[^>]*>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"[ \t\r\f\v]+")

BOILERPLATE_PATTERNS = [
    "the https:// ensures that you are connecting",
    "any information you provide is encrypted and transmitted securely",
    "share sensitive information only on official",
    "before sharing sensitive information",
    "skip to main content",
    "back to top",
]


def _env_flag(name: str, default: bool) -> bool:
    configured = os.getenv(name, "").strip().lower()
    if not configured:
        return default
    return configured in {"1", "true", "yes", "on"}


def _clean_article_text(text: str) -> str:
    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = WHITESPACE_RE.sub(" ", raw_line).strip()
        if not line:
            continue

        line_l = line.lower()
        if any(pattern in line_l for pattern in BOILERPLATE_PATTERNS):
            continue

        cleaned_lines.append(line)

    return "\n\n".join(cleaned_lines)


def _html_fragment_to_text(fragment: str) -> str:
    without_noise = DROP_TAG_RE.sub(" ", fragment)
    with_breaks = BLOCK_BREAK_RE.sub("\n", without_noise)
    without_tags = TAG_RE.sub(" ", with_breaks)
    decoded = html_lib.unescape(without_tags)
    return _clean_article_text(decoded)


def _extract_main_article_body(html: str) -> str:
    candidates = [match.group(2) for match in ARTICLE_BLOCK_RE.finditer(html)]

    if not candidates:
        body_match = BODY_RE.search(html)
        candidates = [body_match.group(1)] if body_match else [html]

    candidate_texts = [_html_fragment_to_text(candidate) for candidate in candidates]
    candidate_texts = [text for text in candidate_texts if text.strip()]

    if not candidate_texts:
        return ""

    return max(candidate_texts, key=_word_count)


def _fetch_main_article_body(url: str, timeout: float) -> str:
    response = httpx.get(
        url,
        follow_redirects=True,
        timeout=timeout,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; EnglishTransferAgent/1.0; "
                "+https://example.com/english-transfer-agent)"
            ),
        },
    )
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").lower()
    if "html" not in content_type:
        return ""

    return _extract_main_article_body(response.text)


def _extract_article_body_with_tavily(
    *,
    api_key: str,
    page_url: str,
    timeout: float,
    extract_depth: str,
    output_format: str,
) -> str:
    response = httpx.post(
        "https://api.tavily.com/extract",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "urls": page_url,
            "extract_depth": extract_depth,
            "format": output_format,
            "include_images": False,
            "timeout": timeout,
        },
        timeout=timeout + 5,
    )
    response.raise_for_status()

    data = response.json()
    results = data.get("results") or []
    if not results:
        return ""

    raw_content = results[0].get("raw_content") or ""
    return _clean_article_text(str(raw_content))


def _domains_from_env(name: str, fallback: list[str]) -> list[str]:
    configured = os.getenv(name, "").strip()
    if not configured:
        return fallback
    return [domain.strip().lower() for domain in configured.split(",") if domain.strip()]


def _int_from_env(name: str, default: int, minimum: int = 1) -> int:
    configured = os.getenv(name, "").strip()
    if not configured:
        return default

    try:
        return max(int(configured), minimum)
    except ValueError:
        logger.warning("Invalid integer env %s=%r; using default=%s", name, configured, default)
        return default


def _domain_batches(domains: list[str], batch_size: int) -> list[list[str]]:
    if not domains:
        return []

    return [domains[index:index + batch_size] for index in range(0, len(domains), batch_size)]


def _summarize_domains(domains: list[str] | None) -> list[str] | None:
    if not domains or len(domains) <= 5:
        return domains

    return domains[:5] + [f"...+{len(domains) - 5} more"]


def _site_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host.removeprefix("www.")


def normalize_article_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "https").lower()
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    return f"{scheme}://{host}{path}"


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


def _early_rejection_reason(title: str, url: str, excluded_domains: list[str]) -> str | None:
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

    return None


def _rejection_reason(
    title: str,
    url: str,
    content: str,
    excluded_domains: list[str],
    min_content_words: int,
) -> str | None:
    early_reason = _early_rejection_reason(title, url, excluded_domains)
    if early_reason:
        return early_reason

    if _looks_like_index_page(title, content):
        return "index_page"

    if _word_count(content) < min_content_words:
        return "too_short"

    return None


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int, excluded_urls: set[str] | None = None) -> list[SearchResult]:
        raise NotImplementedError


class MockSearchProvider(SearchProvider):
    def search(self, query: str, max_results: int, excluded_urls: set[str] | None = None) -> list[SearchResult]:
        excluded_urls = excluded_urls or set()
        result = SearchResult(
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
        if normalize_article_url(result.url) in excluded_urls:
            return []
        return [result][:max_results]


class TavilySearchProvider(SearchProvider):
    """
    Tavily should find natural, commonly readable articles.

    Important:
    - Do not search for B2/C1/ESL/English-learning material.
    - Search for real-world articles.
    - The LLM later adapts those articles into English-transfer cards.

    Environment variables:
    - TAVILY_API_KEY
    - ARTICLE_SOURCE_MODE=preferred|open
      preferred: preferred domains first, broad search as fallback (default)
      open: broad search first, preferred domains as fallback
    - TAVILY_INCLUDE_DOMAINS=domain1,domain2
    - TAVILY_INCLUDE_DOMAIN_BATCH_SIZE=12
    - TAVILY_PREFERRED_QUERY_VARIANTS=2
    - TAVILY_EXCLUDE_DOMAINS=domain1,domain2
    - TAVILY_SEARCH_DEPTH=basic|advanced
    - TAVILY_MIN_CONTENT_WORDS=60
    - TAVILY_MAX_RAW_RESULTS=15
    - TAVILY_FETCH_MAIN_ARTICLE=true
    - ARTICLE_CONTENT_SOURCE=tavily_extract|direct|search_content
    - TAVILY_EXTRACT_DEPTH=basic|advanced
    - TAVILY_EXTRACT_FORMAT=text|markdown
    - TAVILY_INCLUDE_RAW_CONTENT=false
    - ARTICLE_FETCH_TIMEOUT_SECONDS=12
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("TAVILY_API_KEY", "").strip()
        self.last_debug: dict[str, object] = {}

    def search(self, query: str, max_results: int, excluded_urls: set[str] | None = None) -> list[SearchResult]:
        excluded_urls = excluded_urls or set()
        if not self.api_key:
            logger.info(color_request_log("Tavily API key missing; sending search to MockSearchProvider query=%s max_results=%s"), query, max_results)
            return MockSearchProvider().search(query, max_results)

        excluded_domains = _domains_from_env("TAVILY_EXCLUDE_DOMAINS", DEFAULT_EXCLUDED_DOMAINS)
        preferred_domains = _domains_from_env("TAVILY_INCLUDE_DOMAINS", PRESET_ARTICLE_DOMAINS)
        preferred_domain_batch_size = _int_from_env("TAVILY_INCLUDE_DOMAIN_BATCH_SIZE", 12)
        preferred_query_variants = _int_from_env("TAVILY_PREFERRED_QUERY_VARIANTS", 2)

        source_mode = os.getenv("ARTICLE_SOURCE_MODE", "preferred").strip().lower()
        search_depth = os.getenv("TAVILY_SEARCH_DEPTH", "basic").strip().lower()
        min_content_words = int(os.getenv("TAVILY_MIN_CONTENT_WORDS", "60"))
        raw_result_count = int(os.getenv("TAVILY_MAX_RAW_RESULTS", str(max(max_results * 3, 15))))
        fetch_main_article = _env_flag("TAVILY_FETCH_MAIN_ARTICLE", True)
        article_fetch_timeout = float(os.getenv("ARTICLE_FETCH_TIMEOUT_SECONDS", "12"))
        include_raw_content = _env_flag("TAVILY_INCLUDE_RAW_CONTENT", False)
        article_content_source = os.getenv("ARTICLE_CONTENT_SOURCE", "tavily_extract").strip().lower()
        tavily_extract_depth = os.getenv("TAVILY_EXTRACT_DEPTH", "basic").strip().lower()
        tavily_extract_format = os.getenv("TAVILY_EXTRACT_FORMAT", "text").strip().lower()

        query_variants = self._build_query_variants(query)
        search_plan = self._build_search_plan(
            query_variants=query_variants,
            preferred_domains=preferred_domains,
            source_mode=source_mode,
            preferred_domain_batch_size=preferred_domain_batch_size,
            preferred_query_variants=preferred_query_variants,
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
                fetch_main_article=fetch_main_article,
                article_fetch_timeout=article_fetch_timeout,
                include_raw_content=include_raw_content,
                article_content_source=article_content_source,
                tavily_extract_depth=tavily_extract_depth,
                tavily_extract_format=tavily_extract_format,
                excluded_urls=excluded_urls,
            )

            added = 0
            for result in results:
                normalized_url = normalize_article_url(result.url)
                if normalized_url in seen_urls or normalized_url in excluded_urls:
                    continue
                collected.append(result)
                seen_urls.add(normalized_url)
                added += 1

                if len(collected) >= max_results:
                    break

            attempts.append(
                {
                    "mode": mode,
                    "query": query_variant,
                    "include_domains": _summarize_domains(include_domains),
                    "include_domains_count": len(include_domains) if include_domains else 0,
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
            "Try broader search settings or reduce filtering. Debug attempts: "
            + str(attempts)
        )

    def _build_search_plan(
        self,
        query_variants: list[str],
        preferred_domains: list[str],
        source_mode: str,
        preferred_domain_batch_size: int,
        preferred_query_variants: int,
    ) -> list[tuple[str, list[str] | None, str]]:
        search_plan: list[tuple[str, list[str] | None, str]] = []
        preferred_batches = _domain_batches(preferred_domains, preferred_domain_batch_size)
        preferred_queries = query_variants[:preferred_query_variants] or query_variants

        if source_mode == "open":
            for query_variant in query_variants:
                search_plan.append((query_variant, None, "broad"))

            for batch_index, domain_batch in enumerate(preferred_batches, start=1):
                for query_variant in preferred_queries:
                    search_plan.append(
                        (query_variant, domain_batch, f"preferred_domains_fallback_batch_{batch_index}")
                    )

            return search_plan

        # Default: try preferred article domains in smaller batches first. A very large
        # include_domains list can make Tavily return no results, even when a source
        # in that list has relevant articles.
        for batch_index, domain_batch in enumerate(preferred_batches, start=1):
            for query_variant in preferred_queries:
                search_plan.append((query_variant, domain_batch, f"preferred_domains_batch_{batch_index}"))

        for query_variant in query_variants:
            search_plan.append((query_variant, None, "broad_fallback"))

        return search_plan

    def _build_query_variants(self, query: str) -> list[str]:
        cleaned = self._clean_query(query)

        return [
            cleaned,
            "feature article science culture technology psychology lifestyle",
            "longform story human interest technology culture science food sports",
            "news feature arts food sports culture science clear writing",
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
            "or essay",
            "essay",
        ]

        for phrase in banned_phrases:
            cleaned = re.sub(re.escape(phrase), "", cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r"[;|]", " ", cleaned)
        cleaned = re.sub(r"\bor\s+(?=for\b)", "", cleaned, flags=re.IGNORECASE)
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
        fetch_main_article: bool,
        article_fetch_timeout: float,
        include_raw_content: bool,
        article_content_source: str,
        tavily_extract_depth: str,
        tavily_extract_format: str,
        excluded_urls: set[str],
    ) -> tuple[list[SearchResult], list[dict[str, str]]]:
        payload: dict[str, object] = {
            "api_key": self.api_key,
            "query": query,
            "max_results": raw_result_count,
            "search_depth": search_depth,
            "include_answer": False,
            "include_raw_content": include_raw_content,
            "exclude_domains": exclude_domains,
        }

        if include_domains:
            payload["include_domains"] = include_domains

        url = "https://api.tavily.com/search"
        include_domains_log = _summarize_domains(include_domains)
        logger.info(
            color_request_log("Search HTTP request -> url=%s query=%s max_results=%s include_domains_count=%s include_domains=%s"),
            url,
            query,
            raw_result_count,
            len(include_domains) if include_domains else 0,
            include_domains_log,
        )
        logger.debug(color_request_log("Search HTTP request payload=%s"), _redact_search_payload(payload))
        try:
            response = httpx.post(
                url,
                json=payload,
                timeout=20,
            )
            logger.info("Search HTTP response <- url=%s status=%s", url, response.status_code)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            logger.warning("Search HTTP request failed url=%s query=%s error=%s", url, query, exc)
            return [], [
                {
                    "title": "",
                    "url": url,
                    "site": _site_from_url(url),
                    "reason": "search_http_error",
                    "error": str(exc),
                }
            ]
        logger.debug("Search HTTP response payload=%s", data)
        output: list[SearchResult] = []
        rejected: list[dict[str, str]] = []

        for item in data.get("results", []):
            title = item.get("title", "") or ""
            url = item.get("url", "") or ""
            site = _site_from_url(url) if url else ""
            normalized_url = normalize_article_url(url) if url else ""

            if normalized_url in excluded_urls:
                rejected.append(
                    {
                        "title": title,
                        "url": url,
                        "site": site,
                        "reason": "already_used",
                        "content_source": "not_fetched",
                    }
                )
                continue

            early_reason = _early_rejection_reason(title, url, exclude_domains)
            if early_reason:
                rejected.append(
                    {
                        "title": title,
                        "url": url,
                        "site": site,
                        "reason": early_reason,
                        "content_source": "not_fetched",
                    }
                )
                continue

            tavily_content = item.get("raw_content") or item.get("content", "") or ""
            content_source = "tavily_raw_content" if item.get("raw_content") else "tavily_content"
            content = _clean_article_text(str(tavily_content))

            if fetch_main_article and url and article_content_source != "search_content":
                try:
                    if article_content_source == "direct":
                        fetched_content = _fetch_main_article_body(url, article_fetch_timeout)
                        fetched_source = "direct_fetch_main_article_body"
                    else:
                        fetched_content = _extract_article_body_with_tavily(
                            api_key=self.api_key,
                            page_url=url,
                            timeout=article_fetch_timeout,
                            extract_depth=tavily_extract_depth,
                            output_format=tavily_extract_format,
                        )
                        fetched_source = "tavily_extract_main_article_body"
                except (httpx.HTTPError, ValueError) as exc:
                    logger.debug("Could not extract main article body source=%s url=%s error=%s", article_content_source, url, exc)
                else:
                    if _word_count(fetched_content) >= min_content_words:
                        content = fetched_content
                        content_source = fetched_source

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
                        "content_source": content_source,
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
            logger.debug("Accepted search result url=%s content_source=%s words=%s", url, content_source, _word_count(content))

        output.sort(key=lambda r: _word_count(r.content), reverse=True)

        logger.debug(
            "Search filtered payload accepted=%s rejected=%s",
            [result.model_dump() for result in output[:max_results]],
            rejected,
        )
        return output[:max_results], rejected


def build_search_provider(name: str) -> SearchProvider:
    normalized = (name or "mock").strip().lower()

    if normalized == "tavily":
        return TavilySearchProvider()

    return MockSearchProvider()
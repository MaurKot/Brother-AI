"""Free web search + clean page extraction.

- DuckDuckGo for general queries (no key, no auth)
- Wikipedia REST API for fact-grounded summaries (no key)
- trafilatura for stripping boilerplate from fetched pages
All blocking calls run via asyncio.to_thread to keep the event loop free.
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import quote

import aiohttp
import trafilatura
from duckduckgo_search import DDGS

from ..logger import logger


MAX_FETCH_BYTES = 800_000
MAX_CLEAN_CHARS = 4000


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str


class WebSearch:
    def __init__(self, timeout: float = 8.0) -> None:
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={"User-Agent": "Kai/0.1 (+https://replit.com)"},
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def ddg(self, query: str, max_results: int = 4) -> List[SearchHit]:
        """DuckDuckGo HTML search via duckduckgo_search package."""
        def _go() -> List[SearchHit]:
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_results,
                                              region="ru-ru", safesearch="moderate"))
            except Exception as e:  # noqa: BLE001
                logger.warn("websearch", f"ddg failed: {e!r}")
                return []
            hits: List[SearchHit] = []
            for r in results:
                hits.append(SearchHit(
                    title=r.get("title", "")[:200],
                    url=r.get("href") or r.get("url", ""),
                    snippet=r.get("body", "")[:400],
                ))
            return hits
        try:
            return await asyncio.wait_for(asyncio.to_thread(_go), timeout=self.timeout + 2)
        except asyncio.TimeoutError:
            logger.warn("websearch", "ddg timeout")
            return []

    async def wikipedia(self, query: str, lang: str = "ru") -> Optional[str]:
        """First-paragraph summary from Wikipedia REST API."""
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(query)}"
        try:
            sess = await self._get_session()
            async with sess.get(url) as r:
                if r.status != 200:
                    return None
                data = await r.json()
        except Exception as e:  # noqa: BLE001
            logger.warn("websearch", f"wiki failed: {e!r}")
            return None
        extract = data.get("extract")
        if extract:
            return extract[:1200]
        return None

    async def fetch_clean(self, url: str) -> Optional[str]:
        """Fetch a page and return cleaned main text (boilerplate stripped)."""
        if not url.startswith(("http://", "https://")):
            return None
        try:
            sess = await self._get_session()
            async with sess.get(url) as r:
                if r.status != 200:
                    return None
                ct = r.headers.get("content-type", "")
                if "html" not in ct and "text" not in ct:
                    return None
                raw = await r.content.read(MAX_FETCH_BYTES)
        except Exception as e:  # noqa: BLE001
            logger.warn("websearch", f"fetch {url}: {e!r}")
            return None

        def _extract() -> Optional[str]:
            try:
                return trafilatura.extract(raw.decode("utf-8", "ignore"),
                                           include_comments=False,
                                           include_tables=False,
                                           favor_precision=True)
            except Exception:
                return None
        text = await asyncio.to_thread(_extract)
        if not text:
            return None
        return text[:MAX_CLEAN_CHARS]

    async def investigate(self, query: str) -> str:
        """High-level: combine wiki + first DDG result into a brief grounded note."""
        wiki_task = asyncio.create_task(self.wikipedia(query))
        hits_task = asyncio.create_task(self.ddg(query, max_results=3))
        wiki, hits = await asyncio.gather(wiki_task, hits_task,
                                          return_exceptions=True)
        parts: List[str] = []
        if isinstance(wiki, str) and wiki:
            parts.append(f"Википедия: {wiki}")
        if isinstance(hits, list) and hits:
            for h in hits[:3]:
                line = f"• {h.title} — {h.snippet}"
                parts.append(line.strip())
        if not parts:
            return ""
        return "\n".join(parts)[:3500]

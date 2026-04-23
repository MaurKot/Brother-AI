"""Free, keyless world APIs that feed Kai's perception of reality.

All APIs picked here:
- Require NO authentication, NO API key, NO account.
- Respect generous free rate limits (we cache to be polite).
- Fail soft: any error returns an empty/None result so the caller never crashes.
"""
from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import quote

import aiohttp

from ..logger import logger


@dataclass
class WeatherSnapshot:
    temperature_c: float
    cloud_cover_pct: float
    is_day: bool
    weather_code: int  # WMO code
    description: str


@dataclass
class ArxivPaper:
    title: str
    summary: str
    url: str


@dataclass
class HNStory:
    title: str
    url: str
    score: int


WMO_RU = {
    0: "ясно", 1: "почти ясно", 2: "переменная облачность", 3: "пасмурно",
    45: "туман", 48: "иней-туман",
    51: "морось", 53: "морось", 55: "сильная морось",
    61: "дождь", 63: "дождь", 65: "сильный дождь",
    71: "снег", 73: "снег", 75: "сильный снег",
    77: "снежные зёрна",
    80: "ливень", 81: "ливень", 82: "сильный ливень",
    85: "снежный заряд", 86: "сильный снежный заряд",
    95: "гроза", 96: "гроза с градом", 99: "сильная гроза с градом",
}


class WorldAPIs:
    def __init__(self, timeout: float = 6.0) -> None:
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: dict = {}  # key → (expires_at, value)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={"User-Agent": "Kai/0.2 (autonomous companion)"},
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    def _cached(self, key: str):
        v = self._cache.get(key)
        if v and v[0] > time.time():
            return v[1]
        return None

    def _put(self, key: str, value, ttl: int) -> None:
        self._cache[key] = (time.time() + ttl, value)

    # ---------- Open-Meteo (weather, no key) ----------
    async def weather(self, lat: float = 55.75, lon: float = 37.62) -> Optional[WeatherSnapshot]:
        """Default coords: Moscow. Override per brother location later."""
        key = f"wx:{lat:.2f}:{lon:.2f}"
        c = self._cached(key)
        if c:
            return c
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,cloud_cover,is_day,weather_code"
        )
        try:
            sess = await self._get_session()
            async with sess.get(url) as r:
                if r.status != 200:
                    return None
                data = await r.json()
        except Exception as e:  # noqa: BLE001
            logger.warn("world", f"weather failed: {e!r}")
            return None
        try:
            cur = data["current"]
            code = int(cur.get("weather_code", 0))
            snap = WeatherSnapshot(
                temperature_c=float(cur["temperature_2m"]),
                cloud_cover_pct=float(cur["cloud_cover"]),
                is_day=bool(cur.get("is_day", 1)),
                weather_code=code,
                description=WMO_RU.get(code, "погода"),
            )
            self._put(key, snap, ttl=1800)  # 30 min
            return snap
        except Exception as e:  # noqa: BLE001
            logger.warn("world", f"weather parse failed: {e!r}")
            return None

    # ---------- arXiv (no key) ----------
    async def arxiv(self, query: str, max_results: int = 3) -> List[ArxivPaper]:
        key = f"arxiv:{query}:{max_results}"
        c = self._cached(key)
        if c is not None:
            return c
        url = (
            "https://export.arxiv.org/api/query"
            f"?search_query=all:{quote(query)}"
            f"&max_results={max_results}&sortBy=relevance"
        )
        try:
            sess = await self._get_session()
            async with sess.get(url) as r:
                if r.status != 200:
                    return []
                xml = await r.text()
        except Exception as e:  # noqa: BLE001
            logger.warn("world", f"arxiv failed: {e!r}")
            return []

        # Lightweight XML parsing without lxml dependency
        import re
        entries = re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL)
        out: List[ArxivPaper] = []
        for e in entries[:max_results]:
            t = re.search(r"<title>(.*?)</title>", e, re.DOTALL)
            s = re.search(r"<summary>(.*?)</summary>", e, re.DOTALL)
            u = re.search(r'<id>(.*?)</id>', e, re.DOTALL)
            if not (t and s and u):
                continue
            out.append(ArxivPaper(
                title=" ".join(t.group(1).split())[:200],
                summary=" ".join(s.group(1).split())[:600],
                url=u.group(1).strip(),
            ))
        self._put(key, out, ttl=3600)
        return out

    # ---------- Hacker News (no key) ----------
    async def hn_top(self, n: int = 5) -> List[HNStory]:
        c = self._cached("hn_top")
        if c:
            return c[:n]
        try:
            sess = await self._get_session()
            async with sess.get("https://hacker-news.firebaseio.com/v0/topstories.json") as r:
                if r.status != 200:
                    return []
                ids = await r.json()
            ids = ids[:n]

            async def fetch(i):
                try:
                    async with sess.get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json") as rr:
                        return await rr.json()
                except Exception:
                    return None

            items = await asyncio.gather(*[fetch(i) for i in ids])
        except Exception as e:  # noqa: BLE001
            logger.warn("world", f"hn failed: {e!r}")
            return []

        out: List[HNStory] = []
        for it in items:
            if not it or it.get("type") != "story":
                continue
            out.append(HNStory(
                title=it.get("title", "")[:200],
                url=it.get("url") or f"https://news.ycombinator.com/item?id={it.get('id')}",
                score=int(it.get("score", 0)),
            ))
        self._put("hn_top", out, ttl=1800)
        return out[:n]

    # ---------- Wiktionary (no key) ----------
    async def define(self, word: str, lang: str = "ru") -> Optional[str]:
        """Short definition of a word — feeds linguistic curiosity."""
        url = f"https://{lang}.wiktionary.org/api/rest_v1/page/definition/{quote(word)}"
        try:
            sess = await self._get_session()
            async with sess.get(url) as r:
                if r.status != 200:
                    return None
                data = await r.json()
        except Exception:
            return None
        try:
            for lang_code in (lang, "ru", "en"):
                bucket = data.get(lang_code)
                if bucket and bucket[0].get("definitions"):
                    d = bucket[0]["definitions"][0].get("definition", "")
                    # Strip HTML
                    import re
                    d = re.sub(r"<[^>]+>", "", d)
                    return d.strip()[:400] or None
        except Exception:
            return None
        return None

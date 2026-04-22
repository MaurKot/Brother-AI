"""Hugging Face Inference API — free tier, optional HF_TOKEN.

Used for fast emotion classification (Russian) so contagion doesn't burn LLM calls.
Falls back gracefully when the API is rate-limited or unreachable.
"""
from __future__ import annotations
import asyncio
import os
from typing import Optional

import aiohttp

from ..logger import logger


# Russian emotion classifier from CEDR dataset; lightweight model.
EMOTION_MODEL = "cointegrated/rubert-tiny2-cedr-emotion-detection"

# Map HF labels (English) → Kai's Russian emotion vocabulary.
HF_TO_RU = {
    "joy": "радость",
    "sadness": "грусть",
    "surprise": "восторг",
    "fear": "тревога",
    "anger": "злость",
    "no_emotion": "нейтрально",
}


class HFClient:
    def __init__(self, token: Optional[str] = None, timeout: float = 6.0) -> None:
        self.token = token or os.environ.get("HF_TOKEN", "").strip() or None
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        self._failed_until: float = 0.0  # cool-down after rate-limit / 503

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def classify_emotion(self, text: str) -> Optional[str]:
        """Return Russian emotion word or None if HF unavailable."""
        loop = asyncio.get_event_loop()
        if loop.time() < self._failed_until:
            return None
        if not text.strip():
            return "нейтрально"
        url = f"https://api-inference.huggingface.co/models/{EMOTION_MODEL}"
        try:
            sess = await self._get_session()
            async with sess.post(url, json={"inputs": text[:500]}) as r:
                if r.status == 503:  # model loading
                    self._failed_until = loop.time() + 30
                    return None
                if r.status == 429:  # rate limit
                    self._failed_until = loop.time() + 120
                    logger.warn("hf", "rate-limited, cooling down 2min")
                    return None
                if r.status != 200:
                    logger.warn("hf", f"emotion {r.status}")
                    return None
                data = await r.json()
        except Exception as e:  # noqa: BLE001
            logger.warn("hf", f"emotion request failed: {e!r}")
            self._failed_until = loop.time() + 60
            return None

        # Response shape: [[{label, score}, ...]] — pick top
        try:
            items = data[0] if isinstance(data, list) and data and isinstance(data[0], list) else data
            top = max(items, key=lambda x: x.get("score", 0))
            label = top.get("label", "").lower()
            return HF_TO_RU.get(label, "нейтрально")
        except Exception as e:  # noqa: BLE001
            logger.warn("hf", f"emotion parse failed: {e!r} data={data!r}")
            return None

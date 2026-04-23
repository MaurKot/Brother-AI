"""Hugging Face Inference API — gracefully optional.

Without HF_TOKEN, only a handful of models stay on the free anonymous tier
(and that surface keeps shrinking). With a free read-token the multilingual
classifiers below all work reliably.

Each capability fails soft: any error → returns None, caller falls back to
its existing path (usually an LLM call).

Per-model cool-down means one broken model doesn't kill the whole client.
"""
from __future__ import annotations
import asyncio
import os
import time
from typing import Dict, List, Optional, Tuple

import aiohttp

from ..logger import logger


# All model IDs are overridable via env vars so you can swap to your own
# self-hosted endpoint or another HF model without touching the code.
EMOTION_MODEL = os.environ.get(
    "HF_EMOTION_MODEL",
    "cointegrated/rubert-tiny2-cedr-emotion-detection",
)
ZERO_SHOT_MODEL = os.environ.get(
    "HF_ZERO_SHOT_MODEL",
    "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
)
TOXICITY_MODEL = os.environ.get(
    "HF_TOXICITY_MODEL",
    "cointegrated/rubert-tiny-toxicity",
)
EMBED_MODEL = os.environ.get(
    "HF_EMBED_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

HF_API_BASE_URL = os.environ.get("HF_API_BASE_URL", "https://router.huggingface.co/hf-inference/models").rstrip("/")
HF_API_FALLBACK_URL = os.environ.get("HF_API_FALLBACK_URL", "https://api-inference.huggingface.co/models").rstrip("/")


HF_TO_RU_EMOTION = {
    "joy": "радость",
    "sadness": "грусть",
    "surprise": "восторг",
    "fear": "тревога",
    "anger": "злость",
    "no_emotion": "нейтрально",
    "neutral": "нейтрально",
}

# Default intent labels used by zero-shot classifier — covers most brother
# messages. You can override at the call site.
DEFAULT_INTENTS = [
    "вопрос",          # question / asking
    "просьба",         # request for help
    "разговор",        # casual chat
    "благодарность",   # thanks / praise
    "жалоба",          # complaint / venting
    "критика",         # criticism toward Kai
    "приветствие",     # greeting
    "прощание",        # farewell
]


class HFClient:
    def __init__(self, token: Optional[str] = None, timeout: float = 8.0) -> None:
        self.token = token or os.environ.get("HF_TOKEN", "").strip() or None
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        # Per-model cool-down: model_id -> unix_time when it can be tried again
        self._cooldown: Dict[str, float] = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {"Accept": "application/json"}
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

    def _is_cooled(self, model: str) -> bool:
        return self._cooldown.get(model, 0.0) <= time.time()

    def _cool(self, model: str, sec: float, why: str = "") -> None:
        self._cooldown[model] = time.time() + sec
        if why:
            logger.warn("hf", f"{model}: {why}, cooling down {int(sec)}s")

    async def _post(self, model: str, payload: dict, timeout: Optional[float] = None):
        if not self._is_cooled(model):
            return None

        bases = [HF_API_BASE_URL, HF_API_FALLBACK_URL]
        for base in bases:
            url = f"{base}/{model}"
            try:
                sess = await self._get_session()
                t = aiohttp.ClientTimeout(total=timeout or self.timeout)
                async with sess.post(url, json=payload, timeout=t) as r:
                    if r.status == 503:                       # model loading
                        self._cool(model, 30, "503 loading")
                        return None
                    if r.status == 429:                       # rate-limited
                        self._cool(model, 180, "429 rate-limit")
                        return None
                    if r.status == 404:
                        err = await r.text()
                        # If endpoint shape is unsupported on this host, try fallback base.
                        if "Cannot POST /models/" in err and base != HF_API_FALLBACK_URL:
                            continue
                        self._cool(model, 6 * 3600, "404 not on inference API")
                        return None
                    if r.status == 401 or r.status == 403:
                        self._cool(model, 6 * 3600, f"{r.status} auth — set HF_TOKEN")
                        return None
                    if r.status != 200:
                        self._cool(model, 120, f"http {r.status}")
                        return None
                    return await r.json()
            except asyncio.TimeoutError:
                self._cool(model, 60, "timeout")
                return None
            except Exception as e:  # noqa: BLE001
                self._cool(model, 60, f"err {e!r}")
                return None
        return None

    # ---------- Emotion (Russian, single-label) ----------
    async def classify_emotion(self, text: str) -> Optional[str]:
        if not text.strip():
            return "нейтрально"
        data = await self._post(EMOTION_MODEL, {"inputs": text[:500]})
        if not data:
            return None
        try:
            items = data[0] if isinstance(data, list) and data and isinstance(data[0], list) else data
            top = max(items, key=lambda x: x.get("score", 0))
            label = top.get("label", "").lower()
            return HF_TO_RU_EMOTION.get(label, "нейтрально")
        except Exception as e:  # noqa: BLE001
            logger.warn("hf", f"emotion parse failed: {e!r}")
            return None

    # ---------- Zero-shot intent (multilingual) ----------
    async def classify_intent(
        self, text: str, labels: Optional[List[str]] = None
    ) -> Optional[Tuple[str, float]]:
        if not text.strip():
            return None
        labels = labels or DEFAULT_INTENTS
        payload = {
            "inputs": text[:500],
            "parameters": {"candidate_labels": labels, "multi_label": False},
        }
        data = await self._post(ZERO_SHOT_MODEL, payload, timeout=12)
        if not data:
            return None
        try:
            top_label = data["labels"][0]
            top_score = float(data["scores"][0])
            return top_label, top_score
        except Exception as e:  # noqa: BLE001
            logger.warn("hf", f"zero-shot parse failed: {e!r}")
            return None

    # ---------- Toxicity / distress (Russian) ----------
    async def toxicity(self, text: str) -> Optional[float]:
        """Returns 0..1 score where >0.5 means likely toxic/aggressive."""
        if not text.strip():
            return 0.0
        data = await self._post(TOXICITY_MODEL, {"inputs": text[:500]})
        if not data:
            return None
        try:
            items = data[0] if isinstance(data, list) and data and isinstance(data[0], list) else data
            for it in items:
                if it.get("label", "").lower() in ("toxic", "label_1", "1", "toxicity"):
                    return float(it.get("score", 0.0))
            # If labels don't match, fall back to top score
            top = max(items, key=lambda x: x.get("score", 0))
            return float(top.get("score", 0.0))
        except Exception as e:  # noqa: BLE001
            logger.warn("hf", f"toxicity parse failed: {e!r}")
            return None

    # ---------- Sentence embedding (multilingual) ----------
    async def embed(self, text: str) -> Optional[List[float]]:
        """768-dim multilingual sentence embedding. Useful for memory search."""
        if not text.strip():
            return None
        data = await self._post(EMBED_MODEL, {"inputs": text[:1000]})
        if not data:
            return None
        try:
            if isinstance(data, list) and data and isinstance(data[0], (int, float)):
                return [float(x) for x in data]
            if isinstance(data, list) and data and isinstance(data[0], list):
                return [float(x) for x in data[0]]
        except Exception as e:  # noqa: BLE001
            logger.warn("hf", f"embed parse failed: {e!r}")
        return None

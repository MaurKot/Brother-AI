"""Mini-app HTTP server — read-only window into Kai's inner life."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict

from aiohttp import web

from ..dna.neurochem import BehaviorModulator
from ..logger import logger


STATIC_DIR = Path(__file__).parent / "static"


class WebServer:
    def __init__(self, kai: Any, host: str = "0.0.0.0", port: int | None = None) -> None:
        self.kai = kai
        self.host = host
        self.port = port or int(os.environ.get("KAI_WEB_PORT", "5000"))
        self.app = web.Application()
        self._setup_routes()
        self._runner: web.AppRunner | None = None

    def _setup_routes(self) -> None:
        self.app.router.add_get("/api/state", self.api_state)
        self.app.router.add_get("/api/recent", self.api_recent)
        self.app.router.add_get("/api/beliefs", self.api_beliefs)
        self.app.router.add_get("/api/predictions", self.api_predictions)
        self.app.router.add_get("/api/creations", self.api_creations)
        self.app.router.add_get("/api/curiosity", self.api_curiosity)
        self.app.router.add_get("/api/narrative", self.api_narrative)
        self.app.router.add_get("/api/goals", self.api_goals)
        self.app.router.add_get("/", self.index)
        self.app.router.add_static("/static", STATIC_DIR, show_index=False)

    async def index(self, _req: web.Request) -> web.StreamResponse:
        idx = STATIC_DIR / "index.html"
        if not idx.exists():
            return web.Response(text="ui not built", status=500)
        return web.FileResponse(idx)

    # ------- API -------
    async def api_state(self, _req: web.Request) -> web.Response:
        k = self.kai
        bm = BehaviorModulator(k.neuro)
        res = k.resources.read()
        return web.json_response({
            "name": k.identity.name,
            "days_alive": k.identity.days_alive(),
            "self_concept": k.identity.self_concept,
            "neuro": k.neuro.to_dict(),
            "neuro_words": bm.neuro_to_words(),
            "mood": {"label": k.mood.label, "duration_hours": round(k.mood.duration_hours(), 2)},
            "drives": {
                "social": round(bm.social_drive(), 3),
                "create": round(bm.create_drive(), 3),
                "explore": round(bm.explore_drive(), 3),
            },
            "temperament": {
                "openness": k.temperament.openness,
                "conscientiousness": k.temperament.conscientiousness,
                "extraversion": k.temperament.extraversion,
                "agreeableness": k.temperament.agreeableness,
                "neuroticism": k.temperament.neuroticism,
            },
            "values_top": [{"name": n, "weight": round(w, 2)} for n, w in k.values.ranked()[:5]],
            "brother": {
                "relationship_depth": round(k.brother.relationship_depth, 3),
                "last_seen_mood": k.brother.last_seen_mood,
                "hours_since_last": round(k.brother.hours_since_last(), 2),
                "total_messages": k.brother.total_messages,
                "linguistic_hints": k.linguistic.hints(),
            },
            "resources": res,
            "calibration": round(k.predictions.calibration, 3),
            "meta_words": k.meta_learner.words(),
            "is_sleeping": k.sleep.is_sleeping,
        })

    async def api_recent(self, _req: web.Request) -> web.Response:
        raw = self.kai.memory.get_recent(hours=72, limit=30)
        items = []
        for m in raw:
            meta = m.get("meta") or {}
            items.append({
                "text": m.get("text", ""),
                "timestamp": meta.get("ts", ""),
                "emotion": meta.get("emotion", ""),
                "importance": meta.get("importance", 0),
                "tags": meta.get("tags", ""),
            })
        return web.json_response({"items": items})

    async def api_beliefs(self, _req: web.Request) -> web.Response:
        beliefs = self.kai.beliefs.all_strong(0.5)
        return web.json_response({"items": [
            {"text": b.text, "confidence": round(b.confidence, 3),
             "evidence": getattr(b, "evidence_count", 0)}
            for b in beliefs[:30]
        ]})

    async def api_predictions(self, _req: web.Request) -> web.Response:
        preds = self.kai.predictions.predictions[-30:]
        return web.json_response({
            "calibration": round(self.kai.predictions.calibration, 3),
            "items": [{
                "id": p.id, "about": p.about, "expected": p.expected,
                "by_when": p.by_when, "confidence": p.confidence,
                "resolved": p.resolved, "correct": p.correct,
            } for p in preds],
        })

    async def api_creations(self, _req: web.Request) -> web.Response:
        items = self.kai.creative.recent(20)
        return web.json_response({"items": [
            {"form": c.form, "text": c.text, "ts": c.ts} for c in items
        ]})

    async def api_curiosity(self, _req: web.Request) -> web.Response:
        items = self.kai.curiosity.list()
        return web.json_response({"items": [
            {"text": q.text, "weight": q.weight, "asked_at": q.asked_at} for q in items
        ]})

    async def api_narrative(self, _req: web.Request) -> web.Response:
        return web.json_response({
            "current_story": self.kai.narrative.current_story,
            "last_updated": self.kai.narrative.last_updated,
        })

    async def api_goals(self, _req: web.Request) -> web.Response:
        return web.json_response(self.kai.goals.snapshot())

    # ------- lifecycle -------
    async def start(self) -> None:
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        logger.info("web", f"server listening on {self.host}:{self.port}")

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            logger.info("web", "server stopped")

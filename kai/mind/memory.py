"""Long-term memory via ChromaDB. Empty-collection safe (#4)."""
from __future__ import annotations
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

from ..config import MEMORY_DIR
from ..logger import logger


class Memory:
    def __init__(self, collection_name: str = "kai_memory") -> None:
        self.client = chromadb.PersistentClient(
            path=str(MEMORY_DIR),
            settings=Settings(anonymized_telemetry=False, allow_reset=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("memory", f"ChromaDB ready, count={self.collection.count()}")

    def save(
        self,
        text: str,
        emotion: str = "",
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        mid = str(uuid.uuid4())
        metadata: Dict[str, Any] = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "emotion": emotion or "",
            "importance": float(importance),
            "tags": ",".join(tags or []),
        }
        if meta:
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    metadata[k] = v
        try:
            self.collection.add(ids=[mid], documents=[text], metadatas=[metadata])
        except Exception as e:  # noqa: BLE001
            logger.error("memory", f"save failed: {e!r}")
        return mid

    def recall(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if self.collection.count() == 0:
            return []
        try:
            res = self.collection.query(query_texts=[query], n_results=min(limit, self.collection.count()))
        except Exception as e:  # noqa: BLE001
            logger.error("memory", f"query failed: {e!r}")
            return []
        out: List[Dict[str, Any]] = []
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        ids = (res.get("ids") or [[]])[0]
        for i, doc in enumerate(docs):
            out.append({"id": ids[i] if i < len(ids) else "",
                        "text": doc,
                        "meta": metas[i] if i < len(metas) else {}})
        return out

    def get_recent(self, hours: int = 24, limit: int = 20) -> List[Dict[str, Any]]:
        if self.collection.count() == 0:
            return []
        try:
            res = self.collection.get(limit=1000)
        except Exception as e:  # noqa: BLE001
            logger.error("memory", f"get_recent failed: {e!r}")
            return []
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        items: List[Dict[str, Any]] = []
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []
        ids = res.get("ids") or []
        for i, doc in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            ts = meta.get("ts", "")
            try:
                t = datetime.fromisoformat(ts.replace("Z", ""))
            except Exception:
                continue
            if t >= cutoff:
                items.append({"id": ids[i] if i < len(ids) else "", "text": doc, "meta": meta, "_t": t})
        items.sort(key=lambda x: x["_t"], reverse=True)
        return items[:limit]

    def get_high_importance(self, min_importance: float = 0.7, limit: int = 10) -> List[Dict[str, Any]]:
        if self.collection.count() == 0:
            return []
        try:
            res = self.collection.get(limit=1000)
        except Exception as e:  # noqa: BLE001
            logger.error("memory", f"get_high_importance failed: {e!r}")
            return []
        out: List[Dict[str, Any]] = []
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []
        ids = res.get("ids") or []
        for i, doc in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            if float(meta.get("importance", 0)) >= min_importance:
                out.append({"id": ids[i] if i < len(ids) else "", "text": doc, "meta": meta})
        out.sort(key=lambda x: -float(x["meta"].get("importance", 0)))
        return out[:limit]

    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception:
            return 0

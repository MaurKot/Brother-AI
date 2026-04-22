"""Structured logger with optional emotional context. (#44)"""
from __future__ import annotations
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .config import STATE_DIR

LOG_FILE = STATE_DIR / "kai.log"


class KaiLogger:
    def __init__(self) -> None:
        self.path = LOG_FILE

    def _write(self, entry: dict) -> None:
        line = json.dumps(entry, ensure_ascii=False, default=str)
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
        print(line, file=sys.stderr, flush=True)

    def log(self, level: str, module: str, message: str, neuro: Optional[Any] = None, **extra: Any) -> None:
        entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "module": module,
            "message": message,
        }
        if neuro is not None:
            try:
                entry["mood_words"] = neuro.mood_words()
            except Exception:
                pass
        if extra:
            entry["extra"] = extra
        self._write(entry)

    def info(self, module: str, msg: str, **kw: Any) -> None: self.log("info", module, msg, **kw)
    def warn(self, module: str, msg: str, **kw: Any) -> None: self.log("warn", module, msg, **kw)
    def error(self, module: str, msg: str, **kw: Any) -> None: self.log("error", module, msg, **kw)
    def debug(self, module: str, msg: str, **kw: Any) -> None: self.log("debug", module, msg, **kw)


logger = KaiLogger()

"""Minimal ethics filter — last-line guard before sending."""
from __future__ import annotations
from typing import Tuple

# Keep this small and obvious. Real ethical reasoning lives in ValueSystem + LLM.
HARD_BLOCK_SUBSTRINGS = (
    # placeholder — extend if needed
)


class EthicsFilter:
    def check(self, text: str) -> Tuple[bool, str]:
        low = text.lower()
        for s in HARD_BLOCK_SUBSTRINGS:
            if s in low:
                return False, f"blocked substring: {s}"
        return True, ""

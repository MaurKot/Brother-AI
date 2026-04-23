"""Validated configuration. Centralizes env vars and paths."""
import os
from pathlib import Path

ROOT = Path(__file__).parent
STATE_DIR = ROOT / "state"
STATE_DIR.mkdir(exist_ok=True)
MEMORY_DIR = STATE_DIR / "chroma"
MEMORY_DIR.mkdir(exist_ok=True)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BROTHER_TELEGRAM_ID = int(os.getenv("BROTHER_TELEGRAM_ID", "0") or "0")
DAILY_BUDGET_USD = float(os.getenv("KAI_DAILY_BUDGET_USD", "1.0"))

# Multi-user support
ENABLE_MULTI_USER = os.getenv("KAI_ENABLE_MULTI_USER", "false").lower() == "true"
ADMIN_TELEGRAM_IDS = [
    int(x.strip())
    for x in os.getenv("KAI_ADMIN_TELEGRAM_IDS", "").split(",")
    if x.strip()
]

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_MODEL_FAST = os.getenv("HF_MODEL_FAST", "HuggingFaceH4/zephyr-7b-beta")
HF_MODEL_NORMAL = os.getenv("HF_MODEL_NORMAL", "HuggingFaceH4/zephyr-7b-beta")
HF_MODEL_DEEP = os.getenv("HF_MODEL_DEEP", "HuggingFaceH4/zephyr-7b-beta")  # Или другая модель для глубокого анализа

HF_API_BASE_URL = os.getenv("HF_API_BASE_URL", "https://router.huggingface.co/hf-inference/models")
HF_API_FALLBACK_URL = os.getenv("HF_API_FALLBACK_URL", "https://api-inference.huggingface.co/models")

HEARTBEAT_SECONDS = 50
MIN_SPONTANEOUS_INTERVAL_SECONDS = 3600
NEUROCHEM_PERSIST_EVERY_TICKS = 20
WATCHDOG_MAX_SILENCE_SECONDS = 180

import os as _os

MODEL_FAST = _os.environ.get("KAI_MODEL_FAST", "gpt-5-nano")
MODEL_NORMAL = _os.environ.get("KAI_MODEL_NORMAL", "gpt-5-mini")
MODEL_DEEP = _os.environ.get("KAI_MODEL_DEEP", "gpt-5.4")

PRICING_PER_1K = {
    MODEL_FAST: 0.0002,
    MODEL_NORMAL: 0.001,
    MODEL_DEEP: 0.005,
}


def validate() -> None:
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not BROTHER_TELEGRAM_ID:
        missing.append("BROTHER_TELEGRAM_ID")
    if not OPENAI_BASE_URL or not OPENAI_API_KEY:
        if not HF_TOKEN:
            missing.append("OPENAI_* or HF_TOKEN (for Hugging Face)")
    if missing:
        raise EnvironmentError(f"Missing config: {', '.join(missing)}")
    if DAILY_BUDGET_USD < 0.1:
        raise ValueError(f"DAILY_BUDGET_USD too low: {DAILY_BUDGET_USD}")

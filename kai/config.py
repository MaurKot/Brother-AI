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

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

HEARTBEAT_SECONDS = 50
MIN_SPONTANEOUS_INTERVAL_SECONDS = 3600
NEUROCHEM_PERSIST_EVERY_TICKS = 20
WATCHDOG_MAX_SILENCE_SECONDS = 180

MODEL_FAST = "gpt-5-nano"
MODEL_NORMAL = "gpt-5-mini"
MODEL_DEEP = "gpt-5.4"

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
        missing.append("OPENAI_* (Replit AI Integrations not provisioned)")
    if missing:
        raise EnvironmentError(f"Missing config: {', '.join(missing)}")
    if DAILY_BUDGET_USD < 0.1:
        raise ValueError(f"DAILY_BUDGET_USD too low: {DAILY_BUDGET_USD}")

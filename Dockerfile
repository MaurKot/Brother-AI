FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System libs needed by chromadb / lxml / sqlite
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    libsqlite3-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY kai ./kai
COPY pyproject.toml .

# Run as non-root for better container security
RUN useradd --create-home --home-dir /home/kai --shell /usr/sbin/nologin kai \
    && mkdir -p /app/kai/state \
    && chown -R kai:kai /app /home/kai

# Persistent state lives here — mount a volume on this path in production
VOLUME ["/app/kai/state"]

# Web miniapp
EXPOSE 5000

# Health check: miniapp API should answer when Kai loop is alive
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/state', timeout=4)"

# Required env vars at runtime:
#   TELEGRAM_BOT_TOKEN — Telegram bot token
#   BROTHER_TELEGRAM_ID — your Telegram user id (whitelisted)
#   OPENAI_API_KEY — or use Replit's local proxy via OPENAI_BASE_URL
# Optional:
#   HF_TOKEN — Hugging Face token (raises free-tier limits for emotion classifier)
#   KAI_WEBAPP_URL — public https URL of the miniapp (for Telegram WebApp button)
#   DAILY_BUDGET_USD — cap LLM spend per day (default 1.00)

USER kai
CMD ["python", "-m", "kai.main"]

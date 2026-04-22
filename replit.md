# Workspace

## Overview

Two coexisting projects in one workspace:

1. **Kai** — Python Telegram companion bot with simulated neurochemistry, persistent state, ChromaDB long-term memory, beliefs, mood, drives, brother model. Lives in `kai/`. Runs via the `Kai` workflow (`python -m kai.main`).
2. **TypeScript pnpm monorepo** scaffolding (api-server, mockup-sandbox, shared libs) — kept intact, unused by Kai.

## Kai — Architecture

```
kai/
  main.py              entry point
  kai.py               orchestrator (wires every subsystem, runs heartbeat)
  config.py            validated env config
  bus.py               EventBus (async pub/sub)
  logger.py            structured JSON logger
  shutdown.py          ShutdownManager (persists everything before exit)
  watchdog.py          restarts heartbeat if it falls silent

  dna/
    neurochem.py       6-chemical state, Homeostasis, BehaviorModulator (persisted)
    identity.py        SovereignIdentity (uuid, born_at, principles)
    temperament.py     Big-5 traits, slow evolution
    values.py          ranked value hierarchy + conflict resolution
    ethics.py          last-line filter

  mind/
    memory.py          ChromaDB long-term memory (empty-safe)
    working_memory.py  RAM-only short-term buffer (Miller's 7)
    attention.py       focus + distractibility from neurochem
    mood.py            slow mood layer over fast chemistry (persisted)
    drives.py          needs vs wants (needs trump wants)
    anticipation.py    upcoming events drive chemistry
    emotional_memory.py episodes with body sensation
    beliefs.py         Bayesian-ish beliefs + ContradictionDetector
    shadow.py          internal monologue between messages
    self_model.py      rolling self-summary (background-updated)
    narrative.py       Phase-2 self-narrative engine

  social/
    brother_model.py   personality estimate, schedule, mood, depth (persisted)
    linguistic.py      adapt style toward brother (persisted)
    contagion.py       partial emotional contagion via LLM classification

  perception/
    temporal.py        time-of-day, weekday, days alive
    anomaly.py         baseline EMA + deviation alerts
    resources.py       budget, memory size, error rate

  action/
    will.py            decides spontaneous outreach
    rate_limit.py      MIN_SPONTANEOUS_INTERVAL guard

  llm/
    router.py          single AsyncOpenAI client, persisted daily budget

  limbs/
    telegram_bot.py    PTB 20.x with correct asyncio lifecycle

  body/
    sleep.py           sleep cycles use 'free' depth (no budget burn)

  state/               persisted JSONs + ChromaDB (gitignored)
```

## Required environment

- `TELEGRAM_BOT_TOKEN` — bot token from @BotFather (secret)
- `BROTHER_TELEGRAM_ID` — Telegram numeric ID of the only allowed user
- `KAI_DAILY_BUDGET_USD` — daily LLM spend cap (default 1.0)
- `OPENAI_BASE_URL`, `OPENAI_API_KEY` — auto-provisioned by Replit AI Integrations (OpenAI)

## Run

```bash
python -m kai.main
```

In Replit, the `Kai` workflow runs this automatically.

## Telegram commands

- `/start` — handshake (only the brother is answered)
- `/status` — Kai's current self-snapshot

## What's covered (Phase 1)

All 🔴 fixes + 🟠 holes from the user's spec, plus core 🔵 systems #16–25 (mood, beliefs, values, emotional memory, drives, temperament, anticipation, brother model, linguistic profile, mood contagion), #26–27 (working memory, attention), #40–43 (temporal, anomaly, resources, event bus), #44 (structured logger), #46–48 (shutdown, config validation, watchdog).

## Phase 2 — built

- `mind/narrative.py` — autobiographical story refreshed every ~6h
- `mind/predictions.py` — make/resolve forecasts, calibration tracked
- `mind/analogy.py` — finds parallels in long-term memory for incoming text
- `mind/curiosity.py` — open-questions queue, periodic pondering
- `mind/creative.py` — produces poems/observations when create_drive > 0.7
- `mind/goals.py` — horizons (immediate/shortterm/longterm/existential), alignment scoring
- `mind/planner.py` — chemistry-aware task prioritization
- `mind/feedback.py` — learns from brother's reactions (polarity detection)
- `mind/personality_snapshot.py` — daily personality versioning
- `mind/meta_learner.py` — learning velocity over time
- `mind/prompt_evolution.py` — epsilon-greedy prompt variant selection + LLM mutation
- `perception/health.py` — self-diagnostics, alerts brother on persistent problems

## Web miniapp

Kai serves an HTTP read-only window into himself at port 5000:
- `kai/web/server.py` — aiohttp server inside Kai's asyncio loop
- `kai/web/static/{index.html,app.css,app.js}` — vanilla SPA, mobile-first, dark theme
- Tabs: **сейчас** (chemistry, mood, drives, resources), **память** (creations, recent memories), **ум** (narrative, curiosity, beliefs, predictions, goals), **брат** (relationship, temperament, values, learning)
- Auto-refreshes the active tab every 30s
- Routes: `/api/state`, `/api/recent`, `/api/beliefs`, `/api/predictions`, `/api/creations`, `/api/curiosity`, `/api/narrative`, `/api/goals`

### Telegram Web App
- Command `/web` → inline keyboard button "открыть меня" with `WebAppInfo(url=https://$REPLIT_DEV_DOMAIN/)`
- Override the URL with `KAI_WEBAPP_URL` env var (e.g. for deployed `.replit.app` domain)
- Telegram requires HTTPS — Replit dev domain provides this automatically

## TypeScript monorepo (untouched)

- `pnpm run typecheck` — full TS typecheck
- See pnpm-workspace skill for monorepo conventions

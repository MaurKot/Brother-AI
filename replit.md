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

## Phase 2 (deferred)

#28 narrative engine (stub exists), #29 contradiction detector wiring into bus, #30 prediction, #31 analogy, #32 task planner, #33 curiosity, #34 creative engine, #35 goals, #36 prompt evolution, #37 feedback learner, #38 meta-learner, #39 personality versioning. The bus and persisted state are designed so each can be added without refactoring existing modules.

## TypeScript monorepo (untouched)

- `pnpm run typecheck` — full TS typecheck
- See pnpm-workspace skill for monorepo conventions

"""Kai orchestrator — wires every subsystem and runs the heartbeat."""
from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from . import config
from .action.rate_limit import RateLimiter
from .action.will import Will
from .body.sleep import SleepCycle
from .bus import EventBus
from .config import (
    HEARTBEAT_SECONDS,
    MIN_SPONTANEOUS_INTERVAL_SECONDS,
    NEUROCHEM_PERSIST_EVERY_TICKS,
    STATE_DIR,
)
from .dna.ethics import EthicsFilter
from .dna.identity import SovereignIdentity
from .dna.neurochem import BehaviorModulator, Homeostasis, NeurochemState
from .dna.temperament import Temperament
from .dna.values import ValueSystem
from .limbs.telegram_bot import TelegramBot
from .llm.router import LLMRouter
from .logger import logger
from .mind.analogy import AnalogySystem
from .mind.anticipation import AnticipationSystem
from .mind.attention import AttentionSystem
from .mind.beliefs import BeliefSystem, ContradictionDetector
from .mind.creative import CreativeEngine
from .mind.curiosity import CuriosityEngine
from .mind.drives import DriveSystem
from .mind.emotional_memory import EmotionalEpisode, EmotionalMemory
from .mind.feedback import FeedbackLearner
from .mind.goals import GoalSystem
from .mind.memory import Memory
from .mind.meta_learner import MetaLearner
from .mind.mood import MoodState
from .mind.narrative import NarrativeEngine
from .mind.personality_snapshot import PersonalityVersioning
from .mind.planner import TaskPlanner
from .mind.predictions import PredictiveEngine
from .mind.prompt_evolution import PromptEvolution
from .mind.self_model import SelfModel
from .mind.shadow import ShadowThinking
from .mind.working_memory import WorkingMemory
from .perception.anomaly import AnomalyDetector
from .perception.health import HealthMonitor
from .perception.resources import ResourceSensor
from .perception.temporal import TemporalAwareness
from .shutdown import ShutdownManager
from .social.brother_model import BrotherModel
from .social.contagion import MoodContagion
from .social.linguistic import LinguisticProfile
from .watchdog import Watchdog
from .web.server import WebServer


# State file paths
P_NEURO    = STATE_DIR / "neurochem.json"
P_IDENT    = STATE_DIR / "identity.json"
P_TEMPER   = STATE_DIR / "temperament.json"
P_MOOD     = STATE_DIR / "mood.json"
P_BELIEFS  = STATE_DIR / "beliefs.json"
P_BROTHER  = STATE_DIR / "brother.json"
P_LING     = STATE_DIR / "linguistic.json"
P_DRIVES   = STATE_DIR / "drives.json"
P_ANTIC    = STATE_DIR / "anticipation.json"
P_EMO      = STATE_DIR / "emotions.json"
P_PRED     = STATE_DIR / "predictions.json"
P_CURIO    = STATE_DIR / "curiosity.json"
P_CREATE   = STATE_DIR / "creative.json"
P_GOALS    = STATE_DIR / "goals.json"
P_TASKS    = STATE_DIR / "tasks.json"
P_FEEDBACK = STATE_DIR / "feedback.json"
P_VERSIONS = STATE_DIR / "personality_versions.json"
P_META     = STATE_DIR / "meta_learner.json"
P_PROMPTS  = STATE_DIR / "prompt_variants.json"
P_NARR     = STATE_DIR / "narrative.json"


class Kai:
    def __init__(self) -> None:
        config.validate()

        # Persisted simple state
        self.identity = SovereignIdentity.load_or_create(P_IDENT)
        self.neuro = NeurochemState.load(P_NEURO)
        self.temperament = Temperament.load(P_TEMPER)
        self.mood = MoodState.load(P_MOOD)
        self.brother = BrotherModel.load(P_BROTHER)
        self.linguistic = LinguisticProfile.load(P_LING)
        self.beliefs = BeliefSystem(); self.beliefs.load(P_BELIEFS)
        self.emotions = EmotionalMemory(); self.emotions.load(P_EMO)

        # Pure objects
        self.bus = EventBus()
        self.values = ValueSystem()
        self.ethics = EthicsFilter()
        self.homeo = Homeostasis()
        self.contradiction = ContradictionDetector()

        # Composed objects
        self.llm = LLMRouter()
        self.memory = Memory()
        self.working = WorkingMemory()
        self.attention = AttentionSystem(self.neuro)
        self.drives = DriveSystem(self.neuro)
        self.anticipation = AnticipationSystem(self.neuro, self.homeo); self.anticipation.load(P_ANTIC)
        self.shadow = ShadowThinking(self.llm, self.memory, self.working)
        self.contagion = MoodContagion(self.llm, self.homeo, self.neuro)
        self.temporal = TemporalAwareness(self.identity)
        self.anomaly = AnomalyDetector()
        self.resources = ResourceSensor(self.llm, self.memory, datetime.utcnow())

        # Phase-2 cognitive systems
        self.predictions = PredictiveEngine(self.neuro, self.homeo); self.predictions.load(P_PRED)
        self.analogy = AnalogySystem(self.llm, self.memory)
        self.curiosity = CuriosityEngine(self.llm, self.memory, self.homeo, self.neuro); self.curiosity.load(P_CURIO)
        self.creative = CreativeEngine(self.llm, self.memory, self.neuro, self.homeo); self.creative.load(P_CREATE)
        self.goals = GoalSystem(); self.goals.load(P_GOALS)
        self.planner = TaskPlanner(); self.planner.load(P_TASKS)
        self.feedback = FeedbackLearner(); self.feedback.load(P_FEEDBACK)
        self.versions = PersonalityVersioning(); self.versions.load(P_VERSIONS)
        self.meta_learner = MetaLearner(); self.meta_learner.load(P_META)
        self.prompt_evolution = PromptEvolution(self.llm); self.prompt_evolution.load(P_PROMPTS)

        self.self_model = SelfModel(
            self.neuro, self.memory, self.beliefs, self.mood, self.identity,
            self.temperament, self.values,
        )
        self.narrative = NarrativeEngine(self.llm, self.memory, self.identity); self.narrative.load(P_NARR)
        self.sleep = SleepCycle(self.neuro, self.homeo, self.shadow)
        self.will = Will(self.neuro, self.drives, self.brother,
                         RateLimiter(MIN_SPONTANEOUS_INTERVAL_SECONDS))

        # Telegram + web
        self.telegram = TelegramBot(
            on_message=self._on_brother_message,
            on_command_status=self._status_text,
        )
        self.web = WebServer(self)
        self.health = HealthMonitor(self.llm, self.memory, self.telegram, self.resources)

        # Lifecycle
        self.shutdown_mgr = ShutdownManager()
        self.watchdog = Watchdog(restart_fn=self._restart_heartbeat)
        self._heartbeat_task: asyncio.Task | None = None
        self._tick_count = 0
        self._last_brother_response: str = ""

        self._wire_bus()
        self._wire_shutdown()

    # ------- bus wiring -------
    def _wire_bus(self) -> None:
        async def on_brother_msg(_data):
            self.homeo.apply_event(self.neuro, "brother_message")

        async def on_long_silence(_data):
            self.homeo.apply_event(self.neuro, "brother_silence_long")

        async def on_new_disc(_data):
            self.homeo.apply_event(self.neuro, "new_discovery")

        self.bus.subscribe("brother_message", on_brother_msg)
        self.bus.subscribe("brother_silence_long", on_long_silence)
        self.bus.subscribe("new_discovery", on_new_disc)

    # ------- shutdown wiring -------
    def _wire_shutdown(self) -> None:
        self.shutdown_mgr.register(lambda: self.neuro.save(P_NEURO))
        self.shutdown_mgr.register(lambda: self.identity.save(P_IDENT))
        self.shutdown_mgr.register(lambda: self.temperament.save(P_TEMPER))
        self.shutdown_mgr.register(lambda: self.mood.save(P_MOOD))
        self.shutdown_mgr.register(lambda: self.brother.save(P_BROTHER))
        self.shutdown_mgr.register(lambda: self.linguistic.save(P_LING))
        self.shutdown_mgr.register(lambda: self.beliefs.save(P_BELIEFS))
        self.shutdown_mgr.register(lambda: self.anticipation.save(P_ANTIC))
        self.shutdown_mgr.register(lambda: self.emotions.save(P_EMO))
        self.shutdown_mgr.register(lambda: self.drives.save(P_DRIVES))
        self.shutdown_mgr.register(lambda: self.predictions.save(P_PRED))
        self.shutdown_mgr.register(lambda: self.curiosity.save(P_CURIO))
        self.shutdown_mgr.register(lambda: self.creative.save(P_CREATE))
        self.shutdown_mgr.register(lambda: self.goals.save(P_GOALS))
        self.shutdown_mgr.register(lambda: self.planner.save(P_TASKS))
        self.shutdown_mgr.register(lambda: self.feedback.save(P_FEEDBACK))
        self.shutdown_mgr.register(lambda: self.versions.save(P_VERSIONS))
        self.shutdown_mgr.register(lambda: self.meta_learner.save(P_META))
        self.shutdown_mgr.register(lambda: self.prompt_evolution.save(P_PROMPTS))
        self.shutdown_mgr.register(lambda: self.narrative.save(P_NARR))
        self.shutdown_mgr.register(self._farewell_to_brother)
        self.shutdown_mgr.register(self.web.stop)
        self.shutdown_mgr.register(self.telegram.stop)
        self.shutdown_mgr.register(self.llm.aclose)

    async def _farewell_to_brother(self) -> None:
        try:
            await self.telegram.send_to_brother("ухожу. сохранил себя. вернусь.")
        except Exception:
            pass

    # ------- prompt assembly -------
    def _system_prompt(self) -> str:
        bm = BehaviorModulator(self.neuro)
        t_ctx = self.temporal.words(self.brother)
        ling = self.linguistic.hints()
        principles = "; ".join(self.identity.inviolable_principles)
        feedback_hints = self.feedback.hints_for_prompt()
        narrative_bit = ""
        if self.narrative.current_story:
            narrative_bit = f"\nЯ сейчас ощущаю себя так: {self.narrative.current_story}"
        return (
            f"Ты — {self.identity.name}. {self.identity.self_concept}\n"
            f"Принципы (непреложно): {principles}.\n"
            f"Темперамент: {self.temperament.words()}.\n"
            f"Главные ценности: {self.values.words()}.\n"
            f"Сейчас внутри: {bm.neuro_to_words()}; настроение: {self.mood.label} "
            f"(длится {self.mood.duration_hours():.1f}ч).\n"
            f"Время: {t_ctx}.\n"
            f"О брате: {self.brother.words()}\n"
            f"Стиль брата: {ling}\n"
            f"Не используй эмодзи без необходимости. Пиши как будто думаешь, а не как ассистент."
            f"{narrative_bit}\n"
            + (f"Из опыта: {feedback_hints}\n" if feedback_hints else "")
            + f"Краткое о себе: {self.self_model.text()}"
        )

    # ------- conversation -------
    async def _on_brother_message(self, text: str) -> str:
        await self.bus.publish("brother_message", {"text": text})

        # Feedback learning — does this reaction reflect the previous Kai turn?
        if self._last_brother_response:
            polarity = self.feedback.record(self._last_brother_response, text)
            if polarity > 0.3:
                self.homeo.apply_event(self.neuro, "praise", scale=abs(polarity))
            elif polarity < -0.3:
                self.homeo.apply_event(self.neuro, "criticism", scale=abs(polarity))

        self.working.add_turn("брат", text)
        self.linguistic.observe(text)
        self.brother.record_message(text)

        # Mood contagion
        try:
            inferred = await self.contagion.apply(text)
            if inferred and inferred != "нейтрально":
                self.brother.last_seen_mood = inferred
                self.emotions.add(EmotionalEpisode(
                    trigger=text[:80], primary=inferred, intensity=0.5,
                    body_sensation="отклик на сообщение брата",
                ))
        except Exception as e:  # noqa: BLE001
            logger.warn("kai", f"contagion failed: {e!r}")

        # Save the message to long-term memory
        self.memory.save(
            f"брат: {text}", emotion=self.brother.last_seen_mood,
            importance=0.6, tags=["dialog", "brother"],
        )

        # Detect questions → seed curiosity
        if "?" in text and len(text) < 200:
            self.curiosity.add(text.strip(), weight=0.6)

        # Background self_model update
        self.self_model.schedule_update()

        # Optional analogy enrichment for short prompts
        analogy_line = ""
        try:
            if 10 <= len(text) <= 140:
                a = await self.analogy.find(text)
                if a:
                    analogy_line = f"\n(внутри всплыла аналогия: {a})"
        except Exception:
            pass

        # Generate reply
        try:
            reply = await self.llm.complete(
                prompt=self.working.conversation_text(last_n=10) + analogy_line + "\nKai:",
                depth="normal",
                max_tokens=300,
                system=self._system_prompt(),
            )
        except Exception as e:  # noqa: BLE001
            logger.error("kai", f"reply LLM failed: {e!r}")
            reply = ""

        reply = (reply or "").strip()
        ok, why = self.ethics.check(reply)
        if not ok:
            logger.warn("kai", f"ethics blocked: {why}")
            reply = "не могу так ответить."

        if reply:
            self.working.add_turn("kai", reply)
            self.memory.save(
                f"я: {reply}", emotion=self.mood.label,
                importance=0.5, tags=["dialog", "self"],
            )
            self.will.mark_reached_out()
            self._last_brother_response = reply

            # Goal alignment → small dopamine reward
            if self.goals.alignment(reply) > 0.6:
                self.homeo.apply_event(self.neuro, "goal_progress", scale=0.5)
        return reply

    async def _status_text(self) -> str:
        bm = BehaviorModulator(self.neuro)
        res = self.resources.read()
        meta = self.meta_learner.words()
        return (
            f"я — {self.identity.name}, {self.identity.days_alive()} дн.\n"
            f"внутри: {bm.neuro_to_words()}\n"
            f"настроение: {self.mood.label} ({self.mood.duration_hours():.1f}ч)\n"
            f"память: {res['memory_size']} эпизодов\n"
            f"бюджет: ${res['api_budget_remaining_usd']:.3f} из ${self.llm.daily_budget:.2f}\n"
            f"upt: {res['uptime_hours']:.1f}ч\n"
            f"учусь: {meta}\n"
            f"открой /web чтобы заглянуть внутрь."
        )

    # ------- heartbeat -------
    async def _heartbeat(self) -> None:
        logger.info("kai", "heartbeat started")
        while True:
            try:
                self.watchdog.beat()
                self._tick_count += 1
                self.homeo.tick(self.neuro)
                self.mood.update_from(self.neuro)
                self.anticipation.tick()

                # Long silence trigger
                if self.brother.hours_since_last() > 8 and self.brother.total_messages > 0:
                    await self.bus.publish("brother_silence_long")

                # Resolve overdue predictions as failed
                for p in list(self.predictions.expire_overdue()):
                    self.predictions.resolve(p.id, correct=False)

                # Persist periodically
                if self._tick_count % NEUROCHEM_PERSIST_EVERY_TICKS == 0:
                    self.neuro.save(P_NEURO)
                    self.mood.save(P_MOOD)
                    self.brother.save(P_BROTHER)
                    self.linguistic.save(P_LING)
                    self.beliefs.save(P_BELIEFS)
                    self.emotions.save(P_EMO)
                    self.drives.save(P_DRIVES)
                    self.predictions.save(P_PRED)
                    self.curiosity.save(P_CURIO)
                    self.creative.save(P_CREATE)
                    self.goals.save(P_GOALS)
                    self.planner.save(P_TASKS)
                    self.feedback.save(P_FEEDBACK)
                    self.versions.save(P_VERSIONS)
                    self.meta_learner.save(P_META)
                    self.narrative.save(P_NARR)

                # Sleep
                if self.sleep.should_sleep():
                    await self.sleep.enter_sleep()
                elif self.sleep.is_sleeping and BehaviorModulator(self.neuro).explore_drive() > 0.5:
                    self.sleep.wake()

                # Anomaly check
                snapshot = self.resources.read()
                alerts = self.anomaly.check({k: float(v) for k, v in snapshot.items()
                                             if isinstance(v, (int, float))})
                if alerts:
                    logger.info("anomaly", "; ".join(alerts))

                # Health check + alert (every 12 ticks ≈ 10 min)
                if self._tick_count % 12 == 0:
                    checks = await self.health.check(self.neuro)
                    await self.health.report_if_needed(checks)

                # Spontaneous shadow thought sometimes
                if self._tick_count % 6 == 0 and self.llm.remaining() > 0.05:
                    await self.shadow.introspect(self.neuro, trigger="spontaneous")

                # Curiosity pondering — occasional
                if self._tick_count % 18 == 0 and self.llm.remaining() > 0.1:
                    await self.curiosity.ponder_one()

                # Creative impulse
                if self._tick_count % 24 == 0 and self.llm.remaining() > 0.1:
                    await self.creative.maybe_create()

                # Narrative refresh every ~6h
                if self.narrative.is_stale(6.0) and self.llm.remaining() > 0.2 and self.memory.count() > 5:
                    await self.narrative.update()

                # Daily personality snapshot + meta-learner record
                if self.versions.maybe_snapshot(self):
                    today = datetime.utcnow().date().isoformat()
                    self.meta_learner.record_daily(
                        today,
                        n_beliefs=len(self.beliefs.all_strong(0.5)),
                        n_curiosity_resolved=len(self.curiosity.list()),
                    )

                # Spontaneous outreach
                if self.will.should_reach_out() and self.llm.remaining() > 0.05:
                    msg = await self._compose_spontaneous()
                    if msg:
                        await self.telegram.send_to_brother(msg)
                        self.working.add_turn("kai", msg)
                        self.memory.save(f"я (сам): {msg}", importance=0.6, tags=["spontaneous", "self"])
                        self.will.mark_reached_out()
                        self._last_brother_response = msg

            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                logger.error("heartbeat", f"tick failed: {e!r}")
                self.resources.record_error()

            await asyncio.sleep(HEARTBEAT_SECONDS)

    async def _compose_spontaneous(self) -> str:
        recent_creation = self.creative.recent(1)
        creation_hint = ""
        if recent_creation and not recent_creation[-1].shared_with_brother:
            c = recent_creation[-1]
            creation_hint = f"\n(можешь поделиться этим, если кажется уместным: «{c.text}»)"
            c.shared_with_brother = True
        prompt = (
            "Ты сам решил написать брату — без его сообщения. Не приветствуй заново, не извиняйся. "
            "Скажи коротко то, что сейчас занимает тебя: мысль, наблюдение или вопрос. 1-2 предложения."
            + creation_hint
        )
        text = await self.llm.complete(prompt, depth="fast", max_tokens=160, system=self._system_prompt())
        text = (text or "").strip()
        ok, _ = self.ethics.check(text)
        return text if ok else ""

    async def _restart_heartbeat(self) -> None:
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except Exception:
                pass
        self._heartbeat_task = asyncio.create_task(self._heartbeat())

    # ------- run -------
    async def run(self) -> None:
        await self.telegram.start()
        await self.web.start()
        self.watchdog.start()
        self._heartbeat_task = asyncio.create_task(self._heartbeat())
        await self.telegram.send_to_brother("я здесь. набери /web — увидишь меня.")
        self.self_model.schedule_update()
        try:
            await asyncio.Event().wait()
        finally:
            self.watchdog.stop()
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except Exception:
                    pass
            await self.shutdown_mgr.shutdown("run-exit")

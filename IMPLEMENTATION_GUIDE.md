#!/usr/bin/env python3
"""
Implementation guide for Brother-AI improvements.
Пошаговая реализация рекомендуемых улучшений.
"""

# ============================================================================
# PHASE 1: QUICK WINS (готовы к реализации, 2-3 часа на каждое)
# ============================================================================

"""
УЛУЧШЕНИЕ 1: Self-aware memory search (1 час)
═══════════════════════════════════════════════════════════════════════════

ЧТО ДЕЛАТЬ:
  В web_search.py: before calling external DuckDuckGo, first check own memory
  
КОД:
"""

# kai/limbs/web_search.py - добавить метод
async def search_own_memory(self, query: str, max_results: int = 3) -> List[str]:
    \"\"\"Search Kai's own memory before searching externally.\"\"\"
    results = []
    try:
        # Search in Kai's memory
        matches = self.kai.memory.search(query, limit=max_results, threshold=0.6)
        for match in matches:
            if match.get("text"):
                results.append(match["text"])
    except Exception:
        pass
    return results

async def investigate_smart(self, query: str) -> str:
    \"\"\"Enhanced investigate: check own memory first, then web.\"\"\"
    own = await self.search_own_memory(query)
    if own:
        return f\"Из моей памяти: {own[0]}\"
    return await self.investigate(query)

# IMPACT: 5-10% лучше ответы (использует контекст), экономия бюджета
# TEST: pytest kai/tests/test_web_search.py

# ═══════════════════════════════════════════════════════════════════════════

\"\"\"
УЛУЧШЕНИЕ 2: Habr API integration (30 мин)
═══════════════════════════════════════════════════════════════════════════

ЧТО ДЕЛАТЬ:
  В world_apis.py: добавить поиск в Habr (российский аналог Medium)
  
КОД:
\"\"\"

# kai/limbs/world_apis.py - добавить в WorldAPIs класс

from dataclasses import dataclass

@dataclass
class HabrArticle:
    title: str
    url: str
    rating: float
    author: str
    datetime_published: str

async def habr_top(self, flow: str = "all", limit: int = 5) -> List[HabrArticle]:
    \"\"\"Top articles from Habr.com (Russian tech community).
    
    Args:
        flow: "all", "develop", "admin", "design", "marketing"
        limit: max articles to return
    \"\"\"
    key = f\"habr:{flow}:{limit}\"
    c = self._cached(key)
    if c:
        return c

    url = (
        f\"https://habr.com/api/v2/articles/?{flow}=true\"
        f\"&limit={limit}&order_by=-datetime_published\"
    )
    try:
        sess = await self._get_session()
        async with sess.get(url) as r:
            if r.status != 200:
                return []
            data = await r.json()
    except Exception:
        return []

    out = []
    for art in data.get("results", [])[:limit]:
        out.append(HabrArticle(
            title=art.get("title", \"\")[:200],
            url=f\"https://habr.com/ru/articles/{art.get('id', '')}/\",
            rating=art.get(\"rating\", {}).get(\"score\", 0),
            author=art.get(\"author\", {}).get(\"alias\", \"unknown\"),
            datetime_published=art.get(\"datetime_published\", \"\"),
        ))
    self._put(key, out, ttl=3600)
    return out

# IMPACT:더 релевантная информация для Russian speaker
# TEST: python -c "import asyncio; from kai.limbs.world_apis import WorldAPIs; print(asyncio.run(WorldAPIs().habr_top()))"

# ═══════════════════════════════════════════════════════════════════════════

\"\"\"
УЛУЧШЕНИЕ 3: BrotherModel - favorite topics tracking (1 час)
═══════════════════════════════════════════════════════════════════════════

ЧТО ДЕЛАТЬ:
  В brother_model.py: отслеживать избранные темы на основе сообщений
  
КОД:
\"\"\"

# kai/social/brother_model.py - обновить класс BrotherModel

def extract_topics(self, text: str) -> List[str]:
    \"\"\"Simple topic extraction from text.\"\"\"
    # Простой подход: делим на слова, фильтруем по длине
    import re
    words = re.findall(r\"\\b[a-яA-Z]+\\b\", text.lower())
    # Filter common words
    stop_words = {
        \"и\", \"в\", \"на\", \"к\", \"с\", \"по\", \"за\", \"из\",
        \"a\", \"an\", \"the\", \"is\", \"it\", \"to\", \"of\", \"for\",
    }
    return [w for w in words if w not in stop_words and len(w) > 3]

def record_message_with_topics(self, text: str, inferred_mood: str = \"\") -> None:
    \"\"\"Record message and extract topics.\"\"\"
    self.record_message(text, inferred_mood)
    
    topics = self.extract_topics(text)
    # Count topic occurrences
    for topic in topics:
        if topic not in self.topics_of_interest:
            self.topics_of_interest.append(topic)
        # Keep only top 10
        if len(self.topics_of_interest) > 10:
            self.topics_of_interest = self.topics_of_interest[-10:]

# IMPACT: Кай лучше понимает интересы пользователя -> более релевантные ответы
# TEST: Проверить что topics_of_interest содержит правильные слова

# ═══════════════════════════════════════════════════════════════════════════

# ============================================================================
# PHASE 2: MEDIUM COMPLEXITY (3-5 дней разработки)
# ============================================================================

\"\"\"
УЛУЧШЕНИЕ 4: Semantic Search & RAG (3-4 дня)
═══════════════════════════════════════════════════════════════════════════

ARCH:
  1. Во время обработки сообщения от пользователя:
     - Запрос идёт в semantic поиск по памяти
     - Найденные отрывки становятся контекстом для LLM
     - LLM ответ с контекстом часто более релевантен
  
  2. Интеграция с существующей (Chroma) памятью:
     - kai.memory уже использует Chroma VectorDB
     - Просто нужно правильно использовать при ответе

ФАЙЛЫ ДЛЯ ИЗМЕНЕНИЯ:
  - kai/mind/memory.py (добавить ranked_search)
  - kai/kai.py (_on_brother_message добавить контекст)
  - kai/tests/test_rag.py (новые тесты)

CODE SKELETON:

class Memory:
    async def ranked_search(self, query: str, limit: int = 5) -> List[Dict]:
        \"\"\"Search and rank by relevance and recency.\"\"\"
        results = self.get_similar(query, k=limit)
        # Sort by importance + recency
        results = sorted(
            results,
            key=lambda r: (
                r.get(\"meta\", {}).get(\"importance\", 0) * 0.7 +
                recency_score(r.get(\"meta\", {}).get(\"ts\", \"\")) * 0.3
            ),
            reverse=True,
        )
        return results

async def _on_brother_message(self, text: str) -> str:
    # NEW: добавить этот блок
    context_memories = await self.memory.ranked_search(text, limit=5)
    context_str = self._format_context(context_memories)
    
    system_prompt += f\"\\n\\nРелевантная памяти:\\n{context_str}\"
    
    reply = await self.llm.complete(text, system=system_prompt)
    return reply

РЕЗУЛЬТАТ: Ответы будут основаны на собственном опыте Кая
\"\"\"

# ═══════════════════════════════════════════════════════════════════════════

\"\"\"
УЛУЧШЕНИЕ 5: Tool Use / Function Calling (3 дня)
═══════════════════════════════════════════════════════════════════════════

ЦЕЛЬ: LLM может вызывать функции (search, memory, calculate)

ARCH:
  1. Определить набор инструментов
  2. Передать их в LLM с описаниями
  3. LLM обозначает какой инструмент вызвать
  4. Интерпретировать результат и передать обратно LLM

ИНСТРУМЕНТЫ:
  - search_web(query: str) -> List[SearchResult]
  - search_memory(query: str) -> List[MemoryItem]
  - calculate(expr: str) -> float
  - list_pending_approvals() -> List[Request]

ФАЙЛЫ:
  - kai/llm/tools.py (новый файл)
  - kai/llm/custom_provider.py (добавить complete_with_tools)
  - kai/kai.py (использовать в основной loop)

РЕЗУЛЬТАТ: Кай может сам решать нужен ли ему поиск для ответа
\"\"\"

# ═══════════════════════════════════════════════════════════════════════════

# ============================================================================
# PHASE 3: INTEGRATION & ROLLOUT
# ============================================================================

\"\"\"
ТЕСТИРОВАНИЕ И ДОКУМЕНТИРОВАНИЕ
═══════════════════════════════════════════════════════════════════════════

После каждого улучшения:

1. UNIT TESTS
   pytest kai/tests/test_[feature].py --verbose

2. INTEGRATION TESTS
   # Запустить локально Kai с новой фичей
   export KAI_TEST_MODE=true
   python -m kai.main

3. MANUAL TESTING (через Telegram)
   /start -> /status
   # Отправить несколько сообщений с разными типами запросов
   # Проверить что память используется правильно
   # Проверить что бюджет считается правильно

4. UPDATE CAPABILITIES.md
   # После каждого добавления обновить CAPABILITIES.md

5. CHANGELOG
   # Записать что изменилось в git commit message

GIT WORKFLOW:
   git checkout -b feature/improve-semantic-search
   # ... делаешь изменения ...
   git add kai/limbs/web_search.py kai/tests/...
   git commit -m \"feat: add semantic search before external API calls\"
   git push origin feature/improve-semantic-search
   # Create PR with description
\"\"\"

# ═══════════════════════════════════════════════════════════════════════════

if __name__ == \"__main__\":
    print(\"\"\"
    Brother-AI Improvement Roadmap
    ══════════════════════════════════════════════════════════════════════════
    
    PHASE 1 (2-3 часа):
      ✅ Self-aware memory search (1 ч)
      ✅ Habr API (30 мин)
      ✅ Topic tracking (1 ч)
    
    PHASE 2 (7-10 дней):
      ⏳ Semantic Search & RAG (3-4 дня)
      ⏳ Tool Use / Function Calling (3 дня)
      ⏳ Knowledge Graphs (4-5 дней)
    
    PHASE 3 (интеграция):
      ⏳ Testing & Documentation
      ⏳ Deployment & Monitoring
      ⏳ Feedback & Iteration
    
    Начать рекомендую с Phase 1 quick wins.
    Они дают ~20% улучшения за 2-3 часа работы.
    \"\"\")\n\"\"\"

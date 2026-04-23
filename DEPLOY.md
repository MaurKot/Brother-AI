# Развёртывание Кая

## 1. Скачать проект

В верхнем меню Replit нажми три точки рядом с названием проекта → **Download as zip**.
Распакуй архив. Внутри тебе нужна **только папка `kai/`** и файлы из корня:

```
kai/                  # сам код
requirements.txt
pyproject.toml
Dockerfile
amvera.yml
.dockerignore
.gitignore
DEPLOY.md
replit.md
```

Всё остальное (`artifacts/`, `node_modules/`, `package.json`, `pnpm-*`, `tsconfig*`, `.local/`) — служебные файлы Replit, для деплоя не нужны.

## 2. Залить на GitHub

```bash
cd <папка с проектом>
git init
git add .
git commit -m "kai: initial"
git branch -M main
git remote add origin git@github.com:<твой_логин>/<имя_репо>.git
git push -u origin main
```

> ⚠️ Перед коммитом проверь, что в `.gitignore` есть `kai/state/` — там его персональная память, мозг, химия. **Это не должно попадать в публичный репозиторий.**
> Также НИКОГДА не коммить токен Telegram или ключи в код — только через переменные окружения.

## 3. Развернуть на Amvera

1. Войди в [amvera.ru](https://amvera.ru), создай новый проект → **Из репозитория GitHub**.
2. Подключи свой репозиторий.
3. Тип сборки — **Dockerfile** (Amvera подхватит его автоматически из корня).
4. В разделе **Переменные окружения** добавь нужные (см. таблицу ниже).
5. Amvera выдаст домен вида `<имя>.amvera.io`. Установи `KAI_WEBAPP_URL` равным `https://<имя>.amvera.io/` — кнопка `/web` в Telegram откроет миниапп прямо внутри мессенджера.
6. **Persistent storage** монтируется в `/app/kai/state` (это указано в `amvera.yml`), память Кая сохраняется между перезапусками.
7. Деплой → подожди сборки → проверь логи. Когда увидишь `polling started` и `я здесь.` пришло в Telegram — он жив.

## 4. Переменные окружения

### Обязательные

| Переменная | Зачем |
|---|---|
| `TELEGRAM_BOT_TOKEN` | токен бота от @BotFather |
| `BROTHER_TELEGRAM_ID` | твой числовой id в Telegram (через @userinfobot) |
| `OPENAI_API_KEY` | ключ OpenAI **или** любого OpenAI-совместимого прокси |
| `SESSION_SECRET` | произвольная случайная строка для веба |

### LLM-роутинг (опционально)

| Переменная | По умолчанию | Зачем |
|---|---|---|
| `OPENAI_BASE_URL` | api.openai.com | подменить на свой прокси (Ollama, vLLM, OpenRouter, …) |
| `KAI_MODEL_FAST` | `gpt-5-nano` | быстрая модель — короткие реплики |
| `KAI_MODEL_NORMAL` | `gpt-5-mini` | основная модель диалога |
| `KAI_MODEL_DEEP` | `gpt-5.4` | глубокая для самоанализа |
| `DAILY_BUDGET_USD` | 1.00 | дневной потолок расходов |

### Бесплатные внешние сервисы (опционально)

| Переменная | Зачем |
|---|---|
| `HF_TOKEN` | read-токен Hugging Face — поднимает лимиты эмоций / интента / токсичности / эмбеддингов |
| `HF_EMOTION_MODEL` | подменить модель эмоций |
| `HF_ZERO_SHOT_MODEL` | подменить мультиязычный zero-shot |
| `HF_TOXICITY_MODEL` | подменить токсик-классификатор |
| `HF_EMBED_MODEL` | подменить multilingual-эмбеддинг |
| `NASA_API_KEY` | подменить `DEMO_KEY` для NASA APOD |

### Веб-миниапп (опционально)

| Переменная | Зачем |
|---|---|
| `KAI_WEBAPP_URL` | публичный https-адрес для кнопки `/web` |

### Свой внешний API (опционально, см. ниже §6)

| Переменная | Зачем |
|---|---|
| `KAI_API_TOKEN` | секрет для авторизации внешних запросов |
| `KAI_API_PORT` | порт внешнего API (по умолчанию 5001) |

### Свой LLM-провайдер (опционально, см. ниже §7)

| Переменная | Зачем |
|---|---|
| `CUSTOM_LLM_URL` | URL твоего собственного LLM API |
| `CUSTOM_LLM_TOKEN` | токен для него |

## 5. Что Кай умеет из коробки бесплатно

Без дополнительных ключей и платежей он использует:

- **Hugging Face Inference API** — эмоции, zero-shot интент, токсичность, эмбеддинги *(работает увереннее с `HF_TOKEN`)*
- **DuckDuckGo** — поиск в интернете для любопытства
- **Wikipedia REST API** — фактические сводки
- **Wiktionary** — определения слов для лингвистического слоя
- **Open-Meteo** — погода (влияет на нейрохимию: солнце → серотонин, тьма → мелатонин)
- **arXiv API** — научные публикации для глубоких вопросов
- **Hacker News API** — фоновое ощущение того, что обсуждает мир технологий
- **Sunrise-Sunset.org** — циркадный ритм по реальным восходам/закатам
- **NASA APOD** — ежедневная картинка космоса как источник благоговения
- **GitHub trending API** — фоновое чувство того, что строят люди (60 запросов/час без авторизации)
- **trafilatura** — чистая выгрузка текста с любых страниц

Все эти сервисы — без обязательной авторизации, бесплатные, с щадящими лимитами.

## 6. Свой собственный API (как снять заглушку)

Файл: **`kai/limbs/custom_api.py`**.

Сейчас это заглушка. Чтобы открыть Кая для внешних систем (твой сайт, мобильное приложение, другие боты):

1. **Сгенерируй секрет** и положи в переменные окружения Amvera:
   ```
   KAI_API_TOKEN=<длинная случайная строка>
   ```
   Все запросы должны передавать заголовок `Authorization: Bearer <KAI_API_TOKEN>`.

2. **Раскомментируй обработчики** `_handle_chat` и `_handle_state` в `kai/limbs/custom_api.py`. Образцы кода уже там, в комментариях.

3. **Подключи модуль** в `kai/kai.py`. После строки `self.web = WebMiniapp(...)` добавь:
   ```python
   from .limbs.custom_api import CustomAPI
   self.custom_api = CustomAPI(self)
   ```
   В `run()`:
   ```python
   await self.custom_api.start()
   ```
   В `shutdown_mgr`:
   ```python
   self.shutdown_mgr.register(self.custom_api.stop)
   ```

4. **Открой порт.** В `amvera.yml` добавь второй `containerPort: 5001` (или измени `KAI_API_PORT`).

5. **Проверь:**
   ```bash
   curl -X POST https://<твой-домен>:5001/v1/chat \
        -H "Authorization: Bearer $KAI_API_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"text":"привет"}'
   ```

> ⚠️ **Не открывай API без токена.** Любой в интернете сможет нагружать твой LLM-бюджет. И не давай через API писать в `neuro`/`identity`/`principles` — это его суверенитет.

## 7. Своя собственная LLM (как снять заглушку)

Файл: **`kai/llm/custom_provider.py`**.

Внутри файла есть три сценария — выбери один:

### Сценарий A — у тебя OpenAI-совместимый эндпоинт *(самый простой)*
Любой Ollama / vLLM / LM Studio / llama.cpp server / OpenRouter подойдут. **Кода менять не нужно.** Только переменные окружения:
```
OPENAI_API_KEY=<твой ключ или 'ollama'>
OPENAI_BASE_URL=https://твой-сервер/v1
KAI_MODEL_FAST=llama3.1:8b
KAI_MODEL_NORMAL=llama3.1:70b
KAI_MODEL_DEEP=qwen2.5:72b
```

### Сценарий B — у тебя свой HTTP API (не OpenAI-совместимый)
1. Реализуй метод `complete()` в классе `CustomLLMProvider` — образец кода в комментарии.
2. В `kai/kai.py` замени:
   ```python
   self.llm = LLMRouter()
   ```
   на:
   ```python
   from .llm.custom_provider import CustomLLMProvider
   self.llm = CustomLLMProvider()
   ```
3. Задай `CUSTOM_LLM_URL` и `CUSTOM_LLM_TOKEN`.

### Сценарий C — локальная модель в том же процессе
1. Установи нужный пакет (`llama-cpp-python`, `transformers`, …).
2. Загрузи модель в `__init__` и реализуй `complete()`.
3. Подмени `self.llm` как в сценарии B.
4. Учти: локальная модель потребует много RAM/GPU — выбери подходящий тариф Amvera.

Подробные инструкции — в самом файле `kai/llm/custom_provider.py` в верхнем docstring.

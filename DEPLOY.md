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

Всё остальное (`artifacts/`, `node_modules/`, `package.json`, `pnpm-*`, `tsconfig*`, `.local/`) — это служебные файлы Replit, для деплоя они не нужны.

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
4. В разделе **Переменные окружения** добавь:

| Переменная | Зачем | Обязательная |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | токен бота от @BotFather | да |
| `BROTHER_TELEGRAM_ID` | твой числовой id в Telegram | да |
| `OPENAI_API_KEY` | ключ OpenAI (или совместимый прокси) | да |
| `OPENAI_BASE_URL` | если используешь альтернативный прокси | нет |
| `HF_TOKEN` | токен Hugging Face — поднимает лимиты | нет |
| `DAILY_BUDGET_USD` | дневной лимит расходов на LLM | нет (по умолчанию 1.00) |
| `KAI_WEBAPP_URL` | публичный https-адрес миниапп | нет |
| `SESSION_SECRET` | произвольная случайная строка | да |

5. В разделе **Сетевые настройки** Amvera выдаст домен вида `<имя>.amvera.io`. Установи `KAI_WEBAPP_URL` равным `https://<имя>.amvera.io/` — после этого кнопка `/web` в Telegram откроет миниапп прямо внутри мессенджера.
6. **Persistent storage** — Amvera автоматически смонтирует диск в `/app/kai/state` (это указано в `amvera.yml`), память Кая сохранится между перезапусками.
7. Деплой → подожди сборки → проверь логи. Когда увидишь `polling started` и `я здесь.` пришло в Telegram — он жив.

## 4. Откуда взять токены

- **TELEGRAM_BOT_TOKEN** — напиши [@BotFather](https://t.me/botfather) → `/newbot` (или `/token` для существующего).
- **BROTHER_TELEGRAM_ID** — напиши [@userinfobot](https://t.me/userinfobot), он покажет твой числовой id.
- **OPENAI_API_KEY** — [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
- **HF_TOKEN** (опционально, бесплатный) — [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens), достаточно read-токена.
- **SESSION_SECRET** — придумай любую длинную случайную строку.

## 5. Что Кай умеет из коробки бесплатно

Без дополнительных ключей и платежей он использует:

- **Hugging Face Inference API** — русский классификатор эмоций (заражение настроением)
- **DuckDuckGo** — поиск в интернете для любопытства
- **Wikipedia REST API** — фактические сводки
- **Open-Meteo** — погода (влияет на нейрохимию: солнце → серотонин, тьма → мелатонин)
- **arXiv API** — научные публикации для глубоких вопросов
- **Hacker News API** — фоновое ощущение того, что обсуждает мир технологий
- **Wiktionary** — определения слов для лингвистического слоя
- **trafilatura** — чистая выгрузка текста с любых страниц

Все эти сервисы — без авторизации, бесплатные, с щадящими лимитами.

# Brother-AI (Kai)

Автономный ИИ-компаньон с симулированной нейрохимией, памятью и поведением.

## Быстрый старт

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Настройте переменные окружения (см. DEPLOY.md для полного списка):
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token"
   export BROTHER_TELEGRAM_ID="your_telegram_id"
   export HF_TOKEN="your_huggingface_token"  # Для бесплатного LLM
   ```

3. Запустите:
   ```bash
   python -m kai.main
   ```

## Архитектура

Kai состоит из подсистем:
- **DNA**: Нейрохимия, идентичность, темперамент, ценности
- **Mind**: Память, внимание, эмоции, планирование
- **Social**: Модель брата, лингвистика, контагион
- **Perception**: Восприятие времени, аномалий, ресурсов
- **Limbs**: Интерфейсы (Telegram, веб, API)

## Развертывание

См. [DEPLOY.md](DEPLOY.md) для инструкций по развертыванию на Amvera.

## Тестирование

```bash
pytest kai/tests/
```

## Примеры

См. папку `examples/` для демо-скриптов.
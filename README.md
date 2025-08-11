# Llamie Telegram Bot

Telegram бот для взаимодействия с Ollama API. Бот может работать как с внешним сервисом Ollama, так и с локальной установкой через Docker.

## Возможности

- 🤖 Интеграция с Ollama для генерации ответов
- 💬 Поддержка групповых чатов (реагирует на упоминания и ответы)
- 🧠 Сохранение контекста беседы
- 📝 Подробное логирование всех действий
- 🔄 Команда сброса контекста
- 🐳 Готовая Docker-конфигурация

## Быстрый старт с Docker

### 1. Клонируйте репозиторий
```bash
git clone <repo-url>
cd llamie
```

### 2. Настройте переменные окружения
```bash
cp .env.example .env
```

Отредактируйте `.env` файл:
```env
BOT_TOKEN=your_telegram_bot_token_here
OLLAMIE_TOKEN=your_ollama_token_here  # Оставьте пустым для локального Ollama
OLLAMA_MODEL=gpt-oss:120b
```

### 3. Запустите с Docker Compose
```bash
# Запуск всех сервисов (бот + локальный Ollama + веб-интерфейс)
docker-compose up -d

# Или только бот (если используете внешний Ollama)
docker-compose up -d llamie-bot
```

### 4. Загрузите модель в Ollama
```bash
# Подключитесь к контейнеру Ollama
docker exec -it llamie-ollama ollama pull gpt-oss:120b

# Или через веб-интерфейс на http://localhost:3000
```

## Сервисы в Docker Compose

- **llamie-bot** - Telegram бот (порт не требуется)
- **ollama** - Локальный сервер Ollama (порт 11434)
- **ollama-webui** - Веб-интерфейс для Ollama (порт 3000)

## Команды бота

- `/start` - Начать работу с ботом
- `/reset` - Сбросить контекст беседы
- Упоминание `@OllamieBot` - Отправить сообщение боту в группе
- Ответ на сообщение бота - Продолжить беседу

## Логи

- Логи бота сохраняются в `./logs/llamie_bot.log`
- Также выводятся в консоль контейнера

Для просмотра логов:
```bash
# Логи в реальном времени
docker-compose logs -f llamie-bot

# Все логи
docker-compose logs llamie-bot
```

## Локальная разработка

### 1. Установите зависимости
```bash
pip install -r requirements.txt
```

### 2. Настройте .env файл
```bash
cp .env.example .env
# Отредактируйте .env
```

### 3. Запустите бота
```bash
python bot.py
```

## Настройка GPU (опционально)

Для использования GPU с Ollama раскомментируйте секцию в `docker-compose.yml`:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

Убедитесь, что установлен NVIDIA Docker runtime.

## Управление контейнерами

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Просмотр статуса
docker-compose ps

# Очистка (удаление volumes)
docker-compose down -v
```

## Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BOT_TOKEN` | Токен Telegram бота | *обязательно* |
| `OLLAMIE_TOKEN` | Токен для внешнего Ollama | *опционально* |
| `OLLAMA_MODEL` | Модель для использования | `gpt-oss:120b` |
| `OLLAMA_HOST` | Хост Ollama сервера | `http://ollama:11434` |

## Устранение неполадок

### Бот не отвечает
- Проверьте токен бота в `.env`
- Убедитесь, что Ollama запущен и доступен
- Проверьте логи: `docker-compose logs llamie-bot`

### Ollama не работает
- Проверьте, что контейнер запущен: `docker-compose ps`
- Убедитесь, что модель загружена: `docker exec -it llamie-ollama ollama list`
- Проверьте логи: `docker-compose logs ollama`

### Проблемы с GPU
- Установите NVIDIA Docker runtime
- Проверьте драйверы NVIDIA
- Убедитесь, что GPU доступно в контейнере: `docker exec -it llamie-ollama nvidia-smi`

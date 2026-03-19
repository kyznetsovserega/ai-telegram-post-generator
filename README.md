# AI-генератор постов для Telegram

Сервис автоматизирует MVP pipeline для новостного Telegram-канала:

- собирает новости из внешних источников
- фильтрует новости
- генерирует посты через AI
- публикует готовые посты в Telegram

---

## Реализовано

- FastAPI-приложение с `/docs` и health endpoint
- сбор новостей с Habr RSS
- JSONL storage для новостей и постов
- AI generation через OpenAI и Gemini
- abstraction layer для LLM:
  - `TextGenerationClient`
  - factory
  - `PostGenerator`
- Celery + Redis
- Celery Beat
- pipeline: `collect -> filter -> generate -> publish`
- публикация в Telegram через Telethon
- history API: `GET /api/posts`
- сохранение `external_message_id` после публикации

---

## Архитектура

Pipeline построен через Celery chain:

collect → filter → generate → publish

### Этапы:

1. **Collect**
   - сбор новостей (например Habr RSS)

2. **Filter**
   - отбор релевантных новостей

3. **Generate**
   - генерация Telegram-постов через AI (OpenAI / Gemini)

4. **Publish**
   - публикация в Telegram через Telethon

---

## Технологии

- FastAPI
- Celery
- Redis
- Telethon
- OpenAI API
- Google Gemini API
- Pydantic
- JSONL storage (MVP)

---

## Установка

```bash
git clone https://github.com/your-repo/ai-telegram-post-generator.git
cd ai-telegram-post-generator

python -m venv venv
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

---

## Настройка окружения

Создай файл .env на основе .env.example.

```env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
FASTAPI_BASE_URL=http://127.0.0.1:8000
COLLECT_SITES_DEFAULT=habr

LLM_PROVIDER=gemini

OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.2

GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

TELEGRAM_CHANNEL=https://t.me/link

TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_SESSION_NAME=telegram_publisher
```
---

## Запуск проекта

1. Redis
```bash
docker-compose -f docker-compose.redis.yml up -d
```
2. FastAPI
```bash
uvicorn app.main:app --reload
```
  Swagger UI будет доступен по адресу:
http://127.0.0.1:8000/docs
3. Celery worker
```bash
celery -A app.tasks worker --loglevel=info
```
4. Celery Beat
```bash
celery -A app.tasks beat --loglevel=info
```
---

## Pipeline

Запуск вручную:
```
POST /api/collect/sites
POST /api/generate/from-news
```
через Celery:
```
pipeline_chain_task
```
В pipeline входят этапы:
- collect_sites_task
- filter_news_task
- generate_posts_task
- publish_posts_task

---

## API

Service endpoints
- *GET /health* — проверка состояния сервиса
- *GET /api/posts* — история сгенерированных и опубликованных постов

Документация API
- *Swagger UI: /docs*
- *OpenAPI schema: /openapi.json*

---

## AI слой

Поддерживаются провайдеры:
- OpenAI
- Gemini

Архитектура:
- TextGenerationClient (protocol)
- factory
- generator
  (позволяет переключать AI provider без переписывания бизнес-логики)

---

## Telegram publish

Для публикации используется Telethon.

Текущие возможности publish stage:
- синхронная публикация
- async публикация
- публикация через pipeline
- сохранение external_message_id
- обновление статуса поста после успешной публикации
- перевод поста в FAILED при ошибке публикации

---

## Хранилище данных

Используется JSONL storage:
- data/news.jsonl
- data/posts.jsonl

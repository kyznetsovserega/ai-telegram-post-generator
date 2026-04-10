# AI Telegram Post Generator

Автоматизированный сервис для сбора новостей, фильтрации, AI-генерации постов и публикации в Telegram-канал.

Проект реализует полный pipeline обработки контента:

```text
collect -> filter -> generate -> publish
```

---

## Возможности

- Сбор новостей с RSS-источников и Telegram-каналов
- Фильтрация по ключевым словам, источникам, языку и дедупликация
- Генерация Telegram-постов через LLM (OpenAI / Gemini)
- Публикация в Telegram через Telethon
- Автоматический запуск pipeline и служебных фоновых задач по расписанию через Celery Beat
- REST API для управления источниками, keywords, просмотра новостей, постов и логов
- Переключаемый storage backend: JSONL или Redis

---

## Основная идея проекта

<details> <summary><strong>Сервис автоматизирует работу новостного Telegram-канала:</strong></summary> <br>

1. собирает свежие материалы из внешних источников;
2. отбирает только релевантные новости;
3. генерирует краткие посты в формате Telegram;
4. публикует результат в канал;
5. позволяет управлять всем процессом через FastAPI API.

Pipeline построен на основе статусов сущностей и orchestrated через Celery tasks (chain / group).

</details>

---

## Pipeline обработки

### Этапы

1. **Collect**
   - парсинг RSS и Telegram-каналов;
   - нормализация данных в `NewsItem`;
   - сохранение новостей в storage.

2. **Filter**
   - include / exclude keyword filtering;
   - source filtering;
   - language filtering;
   - дедупликация.

3. **Generate**
   - генерация текста поста через LLM;
   - валидация результата;
   - защита от повторной генерации.

4. **Schedule Publish**
   - выбор постов со статусом `generated`;
   - планирование отдельных publish-задач;
   - постановка задач в очередь Celery с задержкой.

5. **Publish (асинхронно)**
   - публикация выполняется отдельными Celery-задачами;
   - каждый пост публикуется отдельно;
   - между публикациями применяется задержка (`PUBLISH_DELAY_SECONDS`);
   - обновляются `status`, `external_message_id`, `published_at`.

## Пример жизненного цикла новости

<details>

1. Source  
   Источник (RSS или Telegram-канал) включён в системе и доступен для сбора.

2. Collect  
   Парсер забирает данные из источника и преобразует их в NewsItem:
   - title
   - url
   - summary
   - source
   - published_at
   - raw_text (если есть)

   На этом этапе новость получает статус: `new`

3. Filter  

Фильтрация включает:
- проверку по include/exclude keywords
- проверку по enabled sources
- дедупликацию:
  - in-memory в рамках текущего batch
  - storage-level через Redis content_hash

NewsItem проходит цепочку фильтров:
- source filter
- language filter
- dedup filter
- keyword filter

Результат:
- если новость релевантна → статус `filtered`
- если отклонена → статус `dropped`

4. Generate  
   Для новостей со статусом `filtered` вызывается LLM.  
   На основе NewsItem создаётся PostItem.

   Результат:
   - создаётся PostItem со статусом `generated`

5. Schedule Publish  
   Сервис выбирает PostItem со статусом `generated`  
   и планирует их публикацию через Celery.

   Для каждого поста создаётся отдельная задача:
   - первая публикация — без задержки;
   - последующие — с увеличивающимся `countdown`;
   - используется `PUBLISH_DELAY_SECONDS`.

6. Publish (асинхронно)  
   Каждая публикация выполняется отдельной Celery-задачей.

   Результат:
   - PostItem получает status = `published`
   - сохраняется `external_message_id`
   - `published_at` заполняется временем публикации

   Если публикация завершается ошибкой:
   - PostItem получает status = `failed`

</details>

Схема: Трансформация данных в pipeline
```text
Source
  |
Collect
  |
NewsItem(status=new)
  |
Filter
  |- accepted  -> NewsItem(status=filtered)
  └─ rejected  -> NewsItem(status=dropped)
  |
Generate
  |
PostItem(status=generated)
  |
Schedule Publish
  |
PostItem(status=generated, scheduled for publish)
  |
Publish (async, Celery)
  |- success -> PostItem(status=published)
  |_ error   -> PostItem(status=failed)
```

---

## Архитектура

Проект разделён на несколько слоёв:

- **API слой**  
  FastAPI routers, Pydantic-схемы, обработка ошибок и dependency injection.

- **Service слой**  
  Бизнес-логика приложения:
  фильтрация, генерация, планирование публикации, работа с сущностями.

- **Storage слой**  
  Абстракция хранения данных через factory (`jsonl` / `redis`) без привязки к реализации.

- **Tasks слой**  
  Celery-задачи и orchestration pipeline:  
  `collect → filter → generate → schedule_publish → publish (async)`.

- **AI слой**  
  Унифицированный интерфейс работы с LLM (OpenAI / Gemini / Free LLM).

- **Parser слой**  
  Сбор данных из внешних источников (RSS и Telegram).

- **Infrastructure слой**  
  Конфигурация, DI-контейнер, Redis, Celery.

---

## Поддерживаемые источники

### RSS

- Habr
- RBC
- VC
- Tproger

### Telegram

публичные Telegram-каналы (`tg:*`) :

`tg:<username>`

Примеры:

- `tg:thehackernews`
- `tg:itsfoss_official`

---

## AI-генерация

### Выбор LLM-провайдера

Провайдер задаётся через переменную окружения:

```env
LLM_PROVIDER=openai
# или
LLM_PROVIDER=gemini
# или
LLM_PROVIDER=free_llm
```

Поддерживаются провайдеры:

- OpenAI
- Google Gemini
- Free LLM (apifreellm.com)

Архитектура AI-слоя:

- TextGenerationClient — общий интерфейс 
- factory (app/ai/factory.py) — выбор провайдера
- реализации:
   > openai_client.py
   > gemini_client.py
   > free_llm_client.py
- генератор (generator.py)
- валидация (validators.py)

Особенности

- retry выполняется только для временных ошибок (AiTemporaryUnavailableError);
- при rate limit повторные запросы не выполняются в рамках одного элемента;
- используется ограничение batch и задержка между генерациями (для защиты от API лимитов);
- результат проходит:
    > очистку (sanitize)
    > валидацию (validate)
- при невалидном ответе:
    > выполняется локальная попытка исправления без повторного запроса к LLM;
- при ошибках генерации:
    > задача не падает полностью
    > ошибка логируется
    > обработка продолжается для следующих элементов

## Throttling публикации

Для соблюдения rate limits Telegram используется отложенная публикация постов.

```env
PUBLISH_DELAY_SECONDS=90
```
Механика работы:

- публикация не выполняется пачкой;
- каждый пост отправляется отдельной Celery-задачей;
- задачи создаются на этапе schedule_publish;
- используется параметр countdown в Celery;
- задержка между постами увеличивается:
  >первый пост — без задержки
  >второй — через PUBLISH_DELAY_SECONDS
  >третий — через 2 * PUBLISH_DELAY_SECONDS, ...

Это позволяет:

- избежать блокировок Telegram;
- контролировать нагрузку;
- безопасно публиковать даже большие batch-пакеты постов.

---

## Публикация в Telegram

Публикация реализована через Telethon.

Особенности:

- используется строковая сессия (`TELEGRAM_SESSION_STRING`);
- publisher работает в sync-first режиме (для Celery);
- каждый пост публикуется отдельной Celery-задачей;
- сохраняется `external_message_id`;
- обновляются `status` и `published_at`.

### Гарантии и ограничения

- **Idempotency**  
  публикация не выполняется повторно, если:
  - статус уже `published`;
  - установлен `external_message_id`;
  - заполнено `published_at`.

- **Поштучная публикация**  
  посты публикуются по одному через Celery-задачи  
  с задержкой между публикациями (см. throttling).

- **Защита от дублей**  
  повторная отправка одного и того же поста исключена.

- **Обработка ошибок**  
  при сбое публикации:
  - пост получает статус `failed`;
  - ошибка логируется.

---

## Хранилище данных

Проект поддерживает два storage backend'а:

- `redis` — основной runtime backend проекта;
- `jsonl` — резервный dev/fallback backend для локальной отладки.

В текущей конфигурации все данные pipeline хранятся и читаются из Redis.

Переключение backend'а выполняется через переменную окружения:

```env
STORAGE_BACKEND=redis
# или
STORAGE_BACKEND=jsonl
```
Архитектура хранения:

- используется factory (`app/storage/__init__.py`);
- все сервисы работают через абстракции storage;
- реализация backend'а полностью скрыта от бизнес-логики.

Особенности Redis backend:

- хранение сущностей:
    > news
    > posts
    > sources
    > keywords
    > logs
- используются индексы (например: news:ids, posts:ids, logs:ids);
- применяется TTL для автоматической очистки данных;
- отдельная Celery-задача выполняет cleanup индексов.

---

## Статусы сущностей

### NewsItem

Статусы новостей:

- `new` — получена на этапе collect
- `filtered` — прошла фильтрацию
- `dropped` — отклонена фильтрами
- `generated` — для новости уже создан PostItem

> статус `generated` используется для предотвращения повторной генерации поста

### PostItem

Статусы постов:

- `generated` — текст успешно сгенерирован и готов к публикации
- `published` — опубликован в Telegram
- `failed` — ошибка при публикации

> В модели также определён статус `new`, но в текущем pipeline он не используется —  
> PostItem создаётся сразу со статусом `generated`.

Жизненный цикл PostItem:

- создаётся на этапе генерации (`Generate`);
- получает статус `generated`;
- передаётся в этап `schedule_publish`;
- публикуется отдельной Celery-задачей;

После успешной публикации:
- статус → `published`
- сохраняется `external_message_id`
- заполняется `published_at`

При ошибке публикации:
- статус → `failed`

---

## Структура проекта

<details>

```text
AI Telegram Post Generator
│
├── app/
│   ├── __init__.py                         
│   ├── celery_app.py                 # настройка Celery и Celery Beat          
│   ├── config.py                     # загрузка конфигурации из .env      
│   ├── main.py                       # точка входа FastAPI, регистрация роутеров и /health 
│   ├── models.py                     # доменные модели (News, Post, Source, Keyword, Log)                 
│   │                                       
│   ├── ai/                           # AI слой    
│   │   ├── base.py                   # интерфейс LLM-клиента (контракт)             
│   │   ├── errors.py                 # типизация и обработка ошибок AI                
│   │   ├── factory.py                # выбор провайдера (OpenAI / Gemini)                 
│   │   ├── gemini_client.py          # клиент Gemini API                                                 
│   │   ├── openai_client.py          # клиент OpenAI API
│   │   ├── free_llm_client.py        # клиент Free LLM API
│   │   ├── generator.py              # orchestration генерации (retry, fallback)                                                                                              
│   │   └── validators.py             # валидация и нормализация текста                                              
│   │                                                           
│   ├── api/                          # API слой                                  
│   │   ├── __init__.py               # инициализация API модуля                                              
│   │   ├── errors.py                 # единый формат ошибок API                                            
│   │   ├── schemas.py                # Pydantic схемы (request/response)                                             
│   │   ├── dependencies/             # DI слой                                                         
│   │   │   └── services.py           # прокидывание сервисов через Depends  
│   │   │                                                        
│   │   └── routers/                  # роутеры API                                                   
│   │       ├── __init__.py           # регистрация роутеров                                                          
│   │       ├── collect.py            # endpoint для запуска сбора новостей                                                         
│   │       ├── generate.py           # endpoint генерации постов                                                          
│   │       ├── keywords.py           # CRUD для keyword-фильтров                                                          
│   │       ├── logs.py               # получение логов                                                      
│   │       ├── news.py               # получение списка новостей                                                      
│   │       ├── posts.py              # получение постов                                                      
│   │       └── sources.py            # управление источниками                                                         
│   │                                                                    
│   ├── core/                         # инфраструктура                                            
│   │   └── container.py              # DI-контейнер (сборка сервисов и storage)                                                       
│   │                                                                  
│   ├── news_parser/                  # слой парсинга                                                   
│   │   ├── __init__.py               # инициализация модуля                                                      
│   │   ├── sites.py                  # registry парсеров + orchestration сбора 
│   │   │                                                 
│   │   └── sources/                  # реализации парсеров                                                   
│   │       ├── __init__.py                                                                 
│   │       ├── habr.py               # RSS парсер Habr                                                      
│   │       ├── rbc.py                # RSS парсер RBC                                                     
│   │       ├── rss_common.py         # общая логика RSS (fetch, parse, normalize)                                                           
│   │       ├── telegram_channels.py  # парсер Telegram-каналов (Telethon)                                                                                                                   
│   │       ├── tproger.py            # RSS парсер Tproger                                                                                                                                                   
│   │       └── vc.py                 # RSS парсер VC                                                                                                                                              
│   │                                                                                                                                                             
│   ├── services/                     # бизнес-логика                                                                                                                                         
│   │   ├── __init__.py               # экспорт сервисов                                                                                                                                                             
│   │   ├── filter_service.py         # orchestration фильтрации (pipeline правил)                                                                                                                                                     
│   │   ├── generation_service.py     # генерация постов через LLM + batch                                                                                                                                                         
│   │   ├── keyword_service.py        # управление include/exclude keywords                                                                                                                                                      
│   │   ├── log_service.py            # централизованное логирование                                                                                                                                                  
│   │   ├── news_service.py           # сбор, нормализация и сохранение новостей                                                                                                                                                   
│   │   ├── post_service.py           # работа с постами (read/update)                                                                                                                                                   
│   │   ├── publish_service.py        # публикация постов + обновление статусов                                                                                                                                                       
│   │   ├── source_service.py         # управление источниками (catalog + user sources)     
│   │   │                                                                                                                                                 
│   │   └── filters/                  # набор фильтров (Strategy pattern)                                                                                                                                             
│   │       ├── __init__.py           # экспорт фильтров                                                                                                                                                    
│   │       ├── base.py               # базовые абстракции (FilterRule, FilterContext)                                                                                                                                                
│   │       ├── dedup_filter.py       # дедупликация внутри батча                                                                                                                                                       
│   │       ├── keyword_filter.py     # include/exclude фильтрация                                                                                                                                                          
│   │       ├── language_filter.py    # фильтрация по языку                                                                                                                                                           
│   │       └── source_filter.py      # фильтрация по источникам                                                                                                                                                         
│   │
│   ├── storage/                      # слой хранения 
│   │   ├── __init__.py               # factory (jsonl ↔ redis)                          
│   │   ├── keywords.py               # хранение keyword-фильтров                          
│   │   ├── logs.py                   # хранение логов                     
│   │   ├── news.py                   # хранение новостей + дедупликация                     
│   │   ├── posts.py                  # хранение постов                      
│   │   ├── redis_client.py           # клиент Redis (connection + helpers)                              
│   │   └── sources.py                # хранение источников                                           
│   │                                         
│   ├── tasks/                        # Celery pipeline                                                                                                     
│   │   ├── __init__.py               # регистрация задач 
│   │   ├── cleanup.py                # служебная очистка битых Redis-индексов                                                                                                                       
│   │   ├── collect.py                # задача сбора новостей                                                                                                            
│   │   ├── filter.py                 # задача фильтрации                                                                                                          
│   │   ├── generate.py               # задача генерации постов                                                                                                            
│   │   ├── pipeline.py               # orchestration pipeline (Celery chain)                                                                                                           
│   │   ├── publish.py                # задача публикации                                                                                                            
│   │   └── task_helpers.py           # sync/async bridge + вспомогательные утилиты                                                                                                                
│   │                                                                                                                          
│   └── telegram/                     # интеграция с Telegram                                                                                                       
│       ├── __init__.py               # экспорт модуля                                                                                                             
│       └── publisher.py              # публикация постов через Telethon                                                                                                              
│                                                                                                                                
├── celery_worker.py                  # точка входа для Celery worker                                                                                                         
├── docker-compose.redis.yml          # запуск Redis (broker + storage)                                                                                                                  
├── requirements.txt                  # зависимости проекта              
├── README.md                         # документация проекта        
├── .gitignore                        # исключения Git                                
├── .env.example                      # пример конфигурации 
│ 
└── scripts                      
    └── generate_telegram_session.py  # утелита генерация TELEGRAM_SESSION_STRING


```
**Celery использует sync-first подход с изоляцией async-операций**

## Почему так спроектировано

- Celery используется для выполнения pipeline вне API, чтобы не блокировать HTTP-запросы;
- FastAPI остаётся async, Celery — sync-first:
  - async-операции (LLM, Telethon) изолированы внутри задач;
  - используется отдельный event loop или bridge-слой;
- Storage реализован через factory:
  - можно менять backend без изменения бизнес-логики;
- Фильтрация построена через Strategy pattern:
  - легко добавлять новые правила;
- Генерация и публикация разделены:
  - независимые этапы с разной логикой и нагрузкой;
- Публикация вынесена в отдельный этап (`schedule_publish` + Celery tasks):
  - позволяет контролировать rate limit и нагрузку;
- Pipeline построен через статусы сущностей:
  - упрощает отслеживание состояния системы и отладку.
  
</details>

---

## Запуск проекта

### 1. Клонирование и окружение

```bash
git clone https://github.com/kyznetsovserega/ai-telegram-post-generator.git
cd ai-telegram-post-generator
python -m venv .venv
```

#### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

#### Linux / macOS

```bash
source .venv/bin/activate
```

### 2. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 3. Настройка переменного окружения

```bash
pip install -r requirements.txt
```
---
## Конфигурация окружения

Создай `.env` на основе `.env.example`.

```bash
cp .env.example .env
```

Пример:

```env
# Celery / Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Storage backend
STORAGE_BACKEND=redis
APP_REDIS_URL=redis://localhost:6379/0

# API
FASTAPI_BASE_URL=http://127.0.0.1:8000

# Collect defaults
COLLECT_SITES_DEFAULT=habr

# Filter
FILTER_INCLUDE_KEYWORDS=ai,llm,gpt,openai,gemini,python,fastapi,telegram,devops,docker,redis,celery
FILTER_EXCLUDE_KEYWORDS=

# LLM
LLM_PROVIDER=free_llm

OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.2

GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

FREE_LLM_API_KEY=
FREE_LLM_BASE_URL=https://apifreellm.com/api/v1/chat
FREE_LLM_TIMEOUT=20

# Telegram publish
TELEGRAM_CHANNEL=https://t.me/link
TELEGRAM_API_ID=
TELEGRAM_API_HASH=

# Единая строковая сессия для publisher и parser
TELEGRAM_SESSION_STRING=

# Telegram ingest
TELEGRAM_SOURCE_CHANNELS=thehackernews,itsfoss_official

# Redis retention policy
REDIS_NEWS_ITEM_TTL_SECONDS=604800
REDIS_NEWS_CONTENT_HASH_TTL_SECONDS=1209600
REDIS_POST_ITEM_TTL_SECONDS=7776000
REDIS_LOG_ITEM_TTL_SECONDS=1209600

# Redis cleanup schedule (UTC)
REDIS_CLEANUP_SCHEDULE_HOUR_UTC=3
REDIS_CLEANUP_SCHEDULE_MINUTE_UTC=0

# Pipeline
PUBLISH_DELAY_SECONDS=90
```
---
### 4. Запуск Redis

```bash
docker compose -f docker-compose.redis.yml up -d
```

### 5. Запуск FastAPI

```bash
uvicorn app.main:app --reload
```

После запуска доступны:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`
- Health endpoint: `http://127.0.0.1:8000/health`

### 6. Запуск Celery Worker

```bash
celery -A app.celery_app:celery_app worker --pool=solo --loglevel=info
```

Для Windows параметр `--pool=solo` обязателен.

### 7. Telegram авторизация (Telethon)

Перед использованием публикации постов и парсинга Telegram-каналов
необходимо один раз получить строковую сессию Telethon.

Проект использует **единую строковую сессию**:

`TELEGRAM_SESSION_STRING` — общая сессия для publisher и parser

Выполните в терминале:

```bash
python -m scripts.generate_telegram_session
```
Скрипт:
- запросит номер телефона
- запросит код из Telegram
- при необходимости — пароль 2FA

После успешной авторизации вы получите строку:
```text
===== Сохраните эту строку в TELEGRAM_SESSION_STRING =====
<ваша строка>
==========================================================
```

Сохраните её в .env:

`TELEGRAM_SESSION_STRING`=ваша_строковая_сессия

## Celery Beat и расписание задач

<details>

`Celery Beat` отвечает за периодический автоматический запуск фоновых задач по расписанию.

Расписание задаётся в app/celery_app.py.

Запускаются два процесса:

1. **Основной pipeline каждые 30 минут**
   - задача: `app.tasks.pipeline_chain_task`
   - выполняет:
     - сбор новостей из включённых источников
     - фильтрация
     - генерация постов
     - публикация в Telegram
     
    Важно: публикация не выполняется сразу —
    она ставится в очередь как отдельные задачи с задержкой.

2. **Очистка Redis-индексов один раз в сутки**
   - задача: `app.tasks.cleanup.cleanup_indexes`
   - назначение:
     - удаление битых ссылок из Redis-индексов:
       - `news:ids`
       - `posts:ids`
       - `logs:ids`
   - расписание задаётся через переменные окружения:
     - `REDIS_CLEANUP_SCHEDULE_HOUR_UTC`
     - `REDIS_CLEANUP_SCHEDULE_MINUTE_UTC`

</details>

### 8. Запуск Celery Beat

```bash
celery -A app.celery_app:celery_app beat --loglevel=info
```
---

## Проверка работоспособности

### Проверка импортов и синтаксиса

```bash
python -m compileall app
```

### Проверка health endpoint

```bash
curl http://127.0.0.1:8000/health
```

Ожидаемый ответ:

```json
{
   "status": "ok",
   "storage_backend": "redis",
   "llm_provider": "free_llm",
   "redis_configured": true
}
```

### Проверка Celery

```bash
python -c "from app.tasks import ping; print(ping())"
```

### Проверка pipeline

```bash
python -c "from app.tasks import collect_sites_task, filter_news_task, generate_posts_task, publish_posts_task; print(collect_sites_task()); print(filter_news_task()); print(generate_posts_task()); print(publish_posts_task())"
```

---

## Основные API endpoints

### API prefix

Все эндпоинты доступны под префиксом `/api`.

Versioning (`/api/v1`) не используется, так как в проекте одна актуальная версия API.  
При необходимости его можно добавить через router prefix без изменения логики приложения.

> Публикация не вынесена в отдельный REST endpoint.  
> Она выполняется как фоновая задача в pipeline (Celery).  
> Позволяет избежать блокировки API и обеспечить стабильность системы.

---

### System

- `GET /health` — проверка состояния сервиса

---

### Collect

- `POST /api/collect/sites` — собрать новости по списку источников

---

### Generate

- `POST /api/generate/` — сгенерировать пост из произвольного текста
- `POST /api/generate/from-news` — сгенерировать пост по `news_id`

---

### Sources

- `GET /api/sources` — список источников
- `POST /api/sources` — создать пользовательский источник
- `PATCH /api/sources/{source_id}` — обновить источник
- `DELETE /api/sources/{source_id}` — удалить пользовательский источник

---

### Keywords

- `GET /api/keywords` — список keywords
- `POST /api/keywords` — добавить keyword
- `DELETE /api/keywords/{keyword_type}/{value}` — удалить keyword

---

## Данные pipeline

### News

- `GET /api/news` — история news

Поддерживает query-параметры:
- `limit`
- `offset`

---

### Posts

- `GET /api/posts` — история сгенерированных и опубликованных постов

Поддерживает query-параметры:
- `limit`
- `offset`

---

### Logs

- `GET /api/logs` — просмотр логов

Поддерживает query-параметры:
- `level`
- `source`
- `limit`
- `offset`
---

## Примеры запросов

### Сбор новостей

```bash
curl -X POST "http://127.0.0.1:8000/api/collect/sites" -H "Content-Type: application/json" -d '{"sites":["habr","vc"],"limit_per_site":3}'
```
### Посмотреть сырые новости

```bash
curl "http://127.0.0.1:8000/api/news?limit=10&offset=0"
```
Возьмите значение из поля `id` у нужной новости

### Генерация поста по новости

```bash
curl -X POST "http://127.0.0.1:8000/api/generate/from-news" -H "Content-Type: application/json" -d '{"news_id":"<news_id>"}'
```
`<news_id>` можно получить из ответа `/api/news`

### Добавление keyword

```bash
curl -X POST "http://127.0.0.1:8000/api/keywords" -H "Content-Type: application/json" -d "{\"value\":\"python\",\"type\":\"include\"}"
```

### Получение истории постов

```bash
curl "http://127.0.0.1:8000/api/posts?limit=10&offset=0"
```

### Просмотр логов

```bash
curl "http://127.0.0.1:8000/api/logs?level=info&limit=10&offset=0"
```

---

## Ключевые архитектурные решения

- Архитектура построена слоями: API, services, storage, tasks, AI, parsers.

- Pipeline разделён на независимые этапы:  
  `collect → filter → generate → schedule_publish → publish (async)`.

- Публикация вынесена в отдельный этап:
  - сначала выполняется планирование (`schedule_publish`);
  - затем посты публикуются отдельными Celery-задачами с задержкой.

- Фильтрация реализована через Strategy pattern:
  - позволяет легко добавлять новые правила.

- Storage слой абстрагирован через factory:
  - backend (Redis / JSONL) можно менять без изменения бизнес-логики.

- Генерация и публикация разделены:
  - независимые этапы с разной нагрузкой и логикой.

- FastAPI (async) и Celery (sync-first) разделены осознанно:
  - API не блокируется;
  - pipeline выполняется стабильно в фоне;
  - async-операции изолированы внутри задач.
  
---

## Автор

Сергей Кузнецов  
[GitHub — @kyznetsovserega](https://github.com/kyznetsovserega)

---

Учебный проект: **AI-генератор постов для Telegram**

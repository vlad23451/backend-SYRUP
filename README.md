# Backend — Документация проекта (RU)

Этот документ описывает архитектуру, окружение, ключевые компоненты и соглашения проекта. Он также содержит инструкции по локальному запуску и основные сценарии работы.

## Содержание
- [Часть 1 — Обзор, стек, установка, конфигурация и архитектура](#part-1)
- [Часть 2 — Слой БД и ORM (SQLAlchemy 2.0, Async)](#part-2)
- [Часть 3 — Кэширование и инвалидация (Redis)](#part-3)
- [Часть 4 — Менеджеры и бизнес‑операции](#part-4)
- [Часть 5 — API и роутеры (эндпоинты и соглашения)](#part-5)
- [Часть 6 — Схемы (Pydantic v2) и контракты API](#part-6)
- [Часть 7 — Безопасность и аутентификация (JWT + Cookies)](#part-7)
- [Часть 8 — Обработка ошибок и исключения](#part-8)
- [Часть 9 — Логирование и наблюдаемость](#part-9)
- [Часть 10 — WebSocket и real‑time](#part-10)
- [Часть 11 — Тестирование и CI](#part-11)
- [Часть 12 — Деплой, мониторинг, troubleshooting, глоссарий](#part-12)
- [Заключение, масштабирование и Roadmap](#final)

<a id="part-1"></a>
## Часть 1 — Обзор, стек, установка, конфигурация и архитектура

Эта часть открывает расширенную документацию. Здесь — высокоуровневый обзор, стек технологий, быстрый старт, конфигурация через `.env` и архитектура приложения (входная точка, роутинг, middleware). Последующие части дополнят руководство подробностями по БД/ORM, кэшу, менеджерам (бизнес-логике), API-эндпоинтам, схемам, безопасности, обработке ошибок, логированию, вебсокетам, деплою, мониторингу, FAQ и глоссарию.

### Ключевые возможности
- Высокопроизводительный REST API на FastAPI (ASGI) с чистой модульной структурой
- Разделение на слои: `core`, `api`, `database` (ORM-модели), `database/managers` (бизнес-логика), `services`, `schemas`
- Глобальная обработка ошибок через `ErrorHandlerMiddleware`
- JWT (access/refresh), поддержка HTTP-only куки
- Конфигурация через `pydantic-settings` и `.env`
- Подготовленные сервисы для кэширования и инвалидации (Redis)

### Быстрый старт
1) Подготовка окружения и установка зависимостей:

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

2) Создайте файл `.env` в корне проекта с необходимыми переменными (см. ниже).

3) Запуск приложения:

```bash
python -m app.run
```

4) Swagger UI: `http://localhost:8000/docs`

### Конфигурация через `.env`
Класс настроек расположен в `app/core/config.py` и загружает значения из `.env`:

- `APP_NAME` — имя сервиса (по умолчанию `Syrup Chat API`)
- `DEBUG` — включение режима отладки (`true/false`)
- `DATABASE_URL` — строка подключения к БД (по умолчанию SQLite + aiosqlite)
- `JWT_SECRET_KEY`, `JWT_ALGORITHM` — параметры подписи JWT
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS` — сроки жизни токенов
- `CORS_ORIGINS` — список доверенных источников (UI)
- `HOST`, `PORT` — адрес и порт приложения
- `REDIS_URL` — адрес Redis для кэша

Рекомендации по безопасности:
- Держите секреты вне репозитория (ENV, менеджеры секретов)
- Для продакшена используйте куки `Secure`, `HttpOnly`, `SameSite`
- Минимизируйте TTL access-токена, применяйте refresh-токены

### Архитектура (входная точка и роутинг)
- Входная точка `app/main.py`: инициализация БД в `lifespan`, конфигурация CORS, подключение `ErrorHandlerMiddleware`, инклюд `main_router`
- Главный роутер `app/api/router.py`: агрегирует подроутеры (`auth`, `user`, `followers`, `friends`, `history`, `comment`, `like`, `dislike`, `comment_like`, `comment_dislike`, `websocket`, `message`)
- Глобальный обработчик ошибок `app/core/error_middleware.py`: нормализует известные исключения в единый JSON-ответ, остальные — 500 с логированием

Поток данных (high level):
- HTTP-запрос → роут → вызов метода менеджера → работа с БД/кэшем → возврат Pydantic-схемы в ответ

— В «Части 2» будут подробно раскрыты слой БД/ORM, кэширование, менеджеры и практики оптимизации запросов.

<a id="part-2"></a>
## Часть 2 — Слой БД и ORM (SQLAlchemy 2.0, Async)

В этой части подробно разбирается устройство слоя данных: конфигурация движка и сессий, базовый класс `Base`, структуры ORM‑моделей, связи, индексы/ограничения, шаблоны работы с асинхронными сессиями, транзакции, пагинация, оптимизация запросов и обработка ошибок.

### Обзор слоя данных
- Конфигурация и базовые сущности находятся в `app/database/`:
  - `config.py` — `engine`, `AsyncSessionLocal`, базовый класс `Base`
  - `init_db.py` — создание таблиц в `lifespan`
  - `models/` — ORM‑модели домена (пользователи, истории, комментарии, лайки, подписки, дружба, сообщения)
  - `managers/` — слой бизнес‑доступа к данным (CRUD, выборки, агрегации)

### Конфигурация движка и сессий
- Async‑движок создаётся в `database/config.py`:
  - `create_async_engine(url=settings.database_url, echo=settings.debug, pool_pre_ping=True)`
  - Фабрика сессий: `AsyncSessionLocal = async_sessionmaker(expire_on_commit=False, autoflush=False)`
- Инициализация БД выполняется один раз на старте приложения (см. `app/main.py` → lifespan → `init_db()` → `Base.metadata.create_all`).
- Корректное завершение: `engine.dispose()` на остановке приложения.

### Базовый класс ORM
- `class Base(DeclarativeBase): ...` — общий предок для всех моделей.
- Все ORM‑модели наследуются от `Base` и объявляют `__tablename__` и поля через `Mapped[...] = mapped_column(...)`.

### Соглашения по моделям
- Явно задавать типы и ограничения там, где критично (строки, индексы, уникальность, ссылки на внешние ключи, JSON, Enum).
- Временные поля (например, `created_at`, `updated_at`) хранятся в таймзоне UTC (`datetime.now(timezone.utc)`).
- Для каскадного удаления использовать `cascade='all, delete'` или `ondelete='CASCADE'` на внешних ключах.
- Для динамических коллекций (followers/following) применяется `lazy='dynamic'` и `DynamicMapped`.

### Модели домена (обзор)
- `users` (`User`):
  - Поля: `id`, `login` (unique, String(100)), `password_hash`, `role` (int, indexed), `avatar_url`, `about`
  - Связи: `histories`, `comments`, `history_likes`/`history_dislikes`, `comment_likes`/`comment_dislikes`
  - Подписки и дружба: `followers` (на меня), `following` (мои подписки), `initiated_friendships`, `received_friendships`

- `histories` (`History`):
  - Поля: `id`, `title`, `description`, `likes`, `dislikes`, `comments`, `created_at` (UTC, indexed), `updated_at`
  - Внешний ключ: `author_id -> users.id` (indexed)
  - Связи: `author`, `history_likes`/`history_dislikes`, `comments_rel`

- `comments` (`Comment`):
  - Поля: `id`, `content`, `created_at` (UTC, indexed), `updated_at`, `comment_type` (Enum: text/image/file/system), `comment_metadata` (JSON)
  - Внешние ключи: `user_id -> users.id (CASCADE)`, `history_id -> histories.id (CASCADE)` (оба indexed)
  - Связи: `user`, `history`, `comment_likes`/`comment_dislikes`

- Лайки/дизлайки историй (`HistoryLike`, `HistoryDislike`):
  - Поля: `id`, `created_at`
  - Внешние ключи: `user_id -> users.id (CASCADE)`, `history_id -> histories.id (CASCADE)`
  - Уникальность: `UniqueConstraint('user_id', 'history_id')` для предотвращения дубликатов

- Лайки/дизлайки комментариев (`CommentLike`, `CommentDislike`):
  - Поля: `id`, `created_at`
  - Внешние ключи: `user_id -> users.id (CASCADE)`, `comment_id -> comments.id (CASCADE)`
  - Уникальность: `UniqueConstraint('user_id', 'comment_id')`

- Подписки (`Follower`):
  - Составной ключ: `(user_id, follower_id)` — оба `primary_key=True`
  - Ограничения и индексы: `Check(user_id != follower_id)`, `Index(user_id, follower_id)`
  - Временная метка: `created_at` (UTC)

- Дружба (`Friend`):
  - Составной ключ: `(user_id, friend_id)` — оба `primary_key=True`
  - Ограничения и индексы: `Check(user_id < friend_id)` для уникального порядка пары, `Index(user_id, friend_id)`
  - Временная метка: `created_at` (UTC)

- Сообщения (`Message`):
  - Поля: `id`, `sender_id`, `room_id` (indexed), `text`, `message_type` (Enum), `timestamp` (UTC, indexed), `is_read`, `message_metadata` (JSON)
  - Связи: `sender`

### Связи и каскадирование
- `relationship(..., cascade='all, delete')` на коллекциях моделей истории/комментариев/лайков удаляет зависимые записи вместе с родителем.
- Для таблиц‑связок используется `ondelete='CASCADE'` в внешних ключах, чтобы БД чистила зависимые строки.
- Динамические отношения (`DynamicMapped`) для подписок дают возможность строить запросы к коллекции (фильтры/пагинация) без предварительной загрузки.

### Индексы и ограничения (важное)
- Уникальные пары:
  - История/лайк: `(user_id, history_id)`
  - Комментарий/лайк: `(user_id, comment_id)`
- Логическая непротиворечивость:
  - Подписки: `user_id != follower_id`
  - Дружба: `user_id < friend_id` (исключает дубликаты в обратном порядке)
- Индексы на часто фильтруемые поля: `created_at`, `author_id`, `room_id`, `sender_id`, `role`.

### JSON и Enum поля
- JSON: `comment_metadata`, `message_metadata` — для расширяемых атрибутов.
- Enum: `CommentType`, `MessageType` — сохраняются как строки значений.
- Рекомендации:
  - Для полей‑словари всегда задавайте `mapped_column(JSON, ...)`
  - Для Enum используйте `values_callable` для устойчивого маппинга значений

### Паттерны работы с async‑сессиями
- Единая точка: `database/managers/session_manager.py` — класс `Manager` предоставляет `get_async_session()` как контекст.
- Базовый CRUD: `BaseManager[TModel, TUpdate]` инкапсулирует типовой create/read/update/delete с безопасными коммитами/роллбэками и логированием.
- Пример частичного обновления: `update_obj(id, updated_obj)` — применяет только поля, указанные в Pydantic‑модели `updated_obj` (`exclude_unset=True`).
- Рекомендации:
  - Используйте `async with manager.get_async_session() as session:` для каждого юнит‑операции
  - В одном методе предпочитайте один коммит; при ошибке — обязательно `rollback()`

### Построители запросов и оптимизация
- Используйте `select(Model)` и `joinedload(...)` для подгрузки связей (например, история + автор).
- Для подсчётов используйте `func.count(...)` и группировки с `.group_by(...)`.
- Для больших выборок применяйте пагинацию: `.offset(skip).limit(limit)` и индексы на сортируемых полях.
- В менеджерах историй реализованы:
  - Быстрые билдеры: `_select_with_author()`, `_select_like_count_map(...)`, `_select_users_who_liked_histories(...)` и т.п.
  - Картографирование результатов в словари `history_id -> count/users` для минимизации запросов.
  - Сборка ответов через схемы: `HistoryOut`, `HistoryOutShort`.

### Транзакции и согласованность
- Каждая операция записи (create/update/delete) коммитится атомарно.
- При ошибке — `rollback()` с последующим выбросом доменного исключения (`DatabaseError`, `ModelNotFoundError`, и т.д.).
- Инвалидация кэшей выполняется после успешного коммита (см. менеджеры и сервис инвалидации).

### Обработка ошибок
- Базовый слой ошибок конвертируется глобальным middleware в единый ответ JSON.
- Менеджеры логируют ошибки через `app_logger.*_event` и выбрасывают доменные исключения.
- Валидация входных данных происходит на уровне Pydantic‑схем во входных/выходных контрактах.

### Пагинация и сортировка
- Все публичные выборки принимают `skip`/`limit`.
- Сортировка по времени используется через `order_by(desc(Model.created_at))` для истории/сообщений.
- Рекомендован лимит по умолчанию 10–100, в зависимости от сущности.

### Производительность и лучшие практики
- Индексируйте поля, используемые для выборок/сортировок (`created_at`, foreign keys, `room_id`).
- Избегайте N+1 через `joinedload` и агрегирующие запросы.
- Для массивов ID используйте `IN (...)` и групповую агрегацию (maps) вместо отдельных запросов по одному ID.
- Кэшируйте дорогие выборки (истории друзей/подписок, карточки пользователей) и грамотно инвалидируйте по событиям.

### Миграции (рекомендация)
- Для эволюции схемы БД используйте Alembic:
  - Инициализация: `alembic init alembic`
  - Автогенерация: `alembic revision --autogenerate -m "msg"`
  - Применение: `alembic upgrade head`
- Правило: любые структурные изменения моделей должны сопровождаться миграцией.

### Примеры запросов (сниппеты)
Подгрузка историй с автором и пагинацией:
```python
result = await session.execute(
    select(History).options(joinedload(History.author))
    .order_by(desc(History.created_at))
    .offset(skip).limit(limit)
)
histories = list(result.scalars().all())
```

Подсчёт лайков по группе историй:
```python
likes_map_rows = await session.execute(
    select(HistoryLike.history_id, func.count(HistoryLike.id))
    .where(HistoryLike.history_id.in_(history_ids))
    .group_by(HistoryLike.history_id)
)
likes_map = {hid: int(cnt) for hid, cnt in likes_map_rows.all()}
```

Получение пользователей, лайкнувших историю:
```python
rows = await session.execute(
    select(User)
    .join(HistoryLike, HistoryLike.user_id == User.id)
    .where(HistoryLike.history_id == history_id)
)
users = rows.scalars().all()
```

Удаление дружбы (с проверкой существования):
```python
result = await session.execute(
    select(Friend).where((Friend.user_id == min(u, f)) & (Friend.friend_id == max(u, f)))
)
friendship = result.scalars().first()
if not friendship:
    raise ModelNotFoundError()
await session.delete(friendship)
await session.commit()
```

— В «Части 3» мы разберём кэширование и инвалидацию: ключи, TTL, стратегии, привязку к событиям домена и типичные ошибки при работе с Redis.

<a id="part-3"></a>
## Часть 3 — Кэширование и инвалидация (Redis)

В этой части описана стратегия кэширования, реализации сервисов кэша, правила формирования ключей, политика TTL, централизованная инвалидация и практики безопасности. Кэш оптимизирует чтение «дорогих» выборок: ленты историй, агрегаты лайков/комментариев, карточки пользователей и результаты поиска.

### Технология и сериализация
- Хранилище: Redis (async клиент `redis.asyncio.Redis`)
- Сериализация: `pickle` с максимальным протоколом — быстро и компактно
- Замечание безопасности: не использовать кэшированные бинарные объекты извне сервиса. Для внешних клиентов предпочтителен JSON

### Базовая обёртка `RedisCache`
- `get(key)` — возвращает объект или `None` (с ловлей ошибок десериализации)
- `set(key, value, ttl=...)` — устанавливает значение с TTL
- `delete_by_prefix(prefix)` — безопасная инвалидация пачек через `SCAN` вместо блокирующего `KEYS`

Пример использования:
```python
value = await RedisCache.get("friends_histories:42:0:10:7")
await RedisCache.set("friends_histories:42:0:10:7", data, ttl=120)
await RedisCache.delete_by_prefix("friends_histories:42:")
```

### Формирование ключей (детерминированные префиксы)
- Общая схема: `<namespace>:<id>[:<skip>[:<limit>[:<me_user_id>]]]`
- Причины включать `me_user_id`:
  - Карточки пользователей и некоторые представления зависят от контекста текущего пользователя (follow_status)
  - Списки друзей/подписок и истории тоже меняются в зависимости от «меня»
- Примеры пространств имён:
  - `user_info:{user_id}:{me_user_id}`
  - `history_with_counts:{history_id}:{me_user_id}`
  - `followers:{user_id}:{skip}:{limit}` / `following:{user_id}:{skip}:{limit}`
  - `friends:{user_id}:{skip}:{limit}`
  - `histories_by_author:{author_id}:{skip}:{limit}:{me_user_id}`
  - `friends_histories:{user_id}:{skip}:{limit}:{me_user_id}`
  - `following_histories:{user_id}:{skip}:{limit}:{me_user_id}`
  - `users_search:{me_user_id}:{query}:{skip}:{limit}`
  - `comments_by_history:{history_id}:{skip}:{limit}:{me_user_id}`

### Политики TTL (рекомендации)
- Карточки пользователя: 10–30 минут (редкие изменения, но важна актуальность статуса)
- Ленты друзей/подписок и истории по авторам: 1–5 минут (умеренная динамика)
- Комментарии и поиск: 30–120 секунд (высокая динамика)
- Истории с агрегатами (лайки/дизлайки/комменты): 3–5 минут

### Реализованные кэш‑сервисы
В `app/services/cache_service.py` доступны специализированные сервисы:
- `UserCacheService`: `get_user_info`, `set_user_info`, `invalidate_user_cache`
- `HistoryCacheService`: `get_history_with_counts`, `set_history_with_counts`, `invalidate_history_cache`
- `FollowersCacheService`: `get_followers`/`set_followers` + `invalidate_followers`; `get_following`/`set_following` + `invalidate_following`
- `FriendsCacheService`: `get_friends`/`set_friends` + `invalidate_friends`
- `HistoriesByAuthorCacheService`: `get_histories`/`set_histories` + `invalidate_histories`
- `FriendsHistoriesCacheService`: `get_histories`/`set_histories` + `invalidate_histories`
- `FollowingHistoriesCacheService`: `get_histories`/`set_histories` + `invalidate_histories`
- `UsersSearchCacheService`: `get_search`/`set_search` + `invalidate_for_user`
- `CommentsByHistoryCacheService`: `get_comments`/`set_comments` + `invalidate_comments`

### Централизованная инвалидация
Класс `CacheInvalidationService` в `app/services/cache_invalidation_service.py` определяет обработчики событий домена:
- `on_reaction_changed(history_id, comment_author_ids, me_user_id)`
  - Инвалидирует кэш истории и карточки затронутых пользователей (авторы комментариев, текущий пользователь)
- `on_history_changed(history_id, author_id)`
  - Очищает кэш конкретной истории, карточку автора и ленты автора
- `on_user_changed(user_id)`
  - Сбрасывает карточку пользователя и ленту его историй
- `on_comment_changed(history_id)`
  - Сбрасывает комментарии по истории и кэш истории
- `on_friend_changed(user_id)`
  - Инвалидирует кэш друзей и их ленты для пользователя
- `on_follow_changed(user_id, follower_id)`
  - Массовая инвалидация: карточки обоих пользователей, followers/following, friends, ленты following, результаты поиска (зависят от follow_status)

Связка: менеджеры данных вызывают методы инвалидации ПОСЛЕ успешного коммита транзакции.

### Встраивание кэша в менеджеры
- Менеджеры сначала пытаются прочитать из кэша. Если кэш пуст — формируют ответ из БД, затем записывают результат в кэш.
- Пример (истории автора):
```python
cached = await HistoriesByAuthorCacheService.get_histories(author_id, skip, limit, me_user_id or 0)
if cached is not None:
    return cached
histories = await self._fetch_histories_by_author_with_author(author_id, skip, limit)
result = await self._build_histories_with_counts(histories, HistoryOutShort, me_user_id)
await HistoriesByAuthorCacheService.set_histories(author_id, skip, limit, me_user_id or 0, result)
return result
```

### Типичные ошибки и анти‑паттерны
- Ключ без `me_user_id` там, где ответ зависит от текущего пользователя → «переливание» чужого состояния
- TTL = бесконечность на динамичных данных → устаревшие данные для пользователей
- Массовая инвалидация через `KEYS` → блокировки Redis; используйте `SCAN`
- Смешивание сериализаций (pickle и json) под одним префиксом → ошибки десериализации

### Диагностика и мониторинг
- Логи операций кэша пишутся через `app_logger` (ошибки сериализации/десериализации, массовые удаления)
- Рекомендуется включить метрики Redis (keys, hits, misses, latency) и алерты по росту размеров/времени ответа

### Безопасность
- Не передавать бинарные объекты кэша во внешние API
- Избегать хранения персональных данных в кэше без шифрования/редакции
- Регулярно ревизовать префиксы и TTL, чтобы не держать лишние данные

### Чек‑лист внедрения нового кэш‑кейса
1) Определите стабильный формат ключа и необходимость `me_user_id`
2) Подберите TTL по динамике данных
3) Реализуйте `get_*`, `set_*`, `invalidate_*` в специализированном сервисе
4) Подключите чтение/запись кэша в менеджер до/после запроса к БД
5) Добавьте вызовы инвалидации в нужные места (после коммита)
6) Протестируйте корректность ключей и инвалидации при изменениях данных

— В «Части 4» опишем менеджеры и бизнес‑операции детально (паттерны, транзакции, согласованность, агрегации, расширенные примеры).

<a id="part-4"></a>
## Часть 4 — Менеджеры и бизнес‑операции

В этой части разбираются шаблоны использования менеджеров данных, их обязанности, обработка ошибок, агрегации, оптимизация запросов и встраивание кэширования. Примеры даны на реальных менеджерах: `UserManager`, `HistoryManager`, `FollowersManager`, `FriendsManager`, `MessageManager`, `CommentManager`, а также семейства `*LikeManager`.

### Роль менеджеров
- Инкапсулируют доступ к БД и бизнес‑инварианты
- Предоставляют высокоуровневые операции (подборки, агрегации, проверки)
- Управляют транзакциями (commit/rollback) и логированием
- Встроенно взаимодействуют с кэшем (read‑through + write‑back) и сервисом инвалидации

### Базовый класс `BaseManager`
- Типизирован: `BaseManager[TModel, TUpdate]`
- CRUD‑методы: `create_obj`, `get_obj_by_id`, `get_all_obj`, `update_obj`, `delete_obj`
- Использует `Manager.get_async_session()` как контекст, оборачивает ошибки в доменные (`DatabaseError`, `ModelNotFoundError`) и логирует через `app_logger`

### Менеджер пользователей `UserManager`
- Создание: захешировать пароль (`bcrypt`), обработать `IntegrityError` → `UserAlreadyExistsError`
- Поиск по логину, ID, поиск по подстроке (`ilike`)
- Проверка учётных данных: `bcrypt.checkpw` и выброс `InvalidCredentialsError` при несоответствии

### Менеджер историй `HistoryManager`
- Билдеры запросов: `_select_with_author`, `_select_like_count_map`, `_select_users_who_liked*`
- Сбор агрегатов: карты лайков/дизлайков/комментариев, списки пользователей
- Публичные методы: 
  - `get_histories(skip, limit, me_user_id)`
  - `get_histories_by_author_id(author_id, ...)` (с кэшем)
  - `get_following_histories(...)` и `get_friends_histories(...)` (с кэшем)
  - `get_history_by_id(id, ...)` (с кэшем)
- Инвалидация: после create/delete обновляет кэши истории и списков автора

### Подписки `FollowersManager`
- `follow(target_id, follower_id)`: коммит → `CacheInvalidationService.on_follow_changed(...)`
- `unfollow(...)`: аналогично, с обработкой отсутствия записи (`ModelNotFoundError`)
- `get_followers`/`get_following`: read‑through кэш (запись при пропуске, `FollowersCacheService`)

### Дружба `FriendsManager`
- Добавление только при взаимной подписке (проверки через `FollowersManager`)
- Инвалидация после изменения: список друзей обоих пользователей, карточки пользователей (влияние на `follow_status`)

### Сообщения `MessageManager`
- Выборки: история комнаты, последние сообщения по комнатам, последний по комнате, уникальные `room_id` пользователя
- Предикат чата (`_get_chat_filter`) и `joinedload` для отправителя/получателя

### Комментарии `CommentManager`
- Получение комментариев по истории, агрегация лайков/дизлайков и пользователей, параллельные запросы (`asyncio.create_task`)
- Read‑through кэш с `CommentsByHistoryCacheService`

### Реакции `LikeManager`/`DislikeManager`/`CommentLikeManager`/`CommentDislikeManager`
- Обобщённый базовый `BaseReactionManager` на целевое поле (`history_id`/`comment_id`)
- Операции: получить/удалить запись по паре (user_id, target_id)

### Паттерны согласованности
- Мутации → коммит → инвалидация соответствующих кэшей (строго после успешного коммита)
- Запрет смешивания логики инвалидации до коммита (во избежание разногласий между БД и кэшем)

### Обработка ошибок
- Ошибки уровня БД переводятся в доменные исключения и единый формат ответа middleware‑ом
- Для API‑хендлеров может использоваться декоратор `@handle_api_errors(...)` из `services/error_handler_service.py`

### Оптимизация запросов в менеджерах
- `joinedload` для N+1‑чувствительных связей
- Агрегации по картам `select(...).group_by(...)` для массовых подсчётов
- Параллельная загрузка независимых наборов через `asyncio.gather`/`create_task`
- Индексация полей, участвующих в фильтрации/сортировке (см. Часть 2)

### Тестируемость
- Вынесение построителей запросов в статические методы облегчает юнит‑тестирование
- Менеджеры изолируют логику транзакций → можно мокать `get_async_session`

— В «Части 5» опишем API и роутеры: соглашения, эндпоинты, статусы ответов, схемы входа/выхода, и примеры запросов.

<a id="part-5"></a>
## Часть 5 — API и роутеры (эндпоинты и соглашения)

Эта часть документирует публичные HTTP‑эндпоинты, их поведение, статусы ответов, схемы запросов/ответов и основные зависимости (аутентификация, пагинация, проверка владения ресурсом).

### Общие соглашения API
- Авторизация: все эндпоинты, кроме `auth`, требуют аутентификации через текущего пользователя (`Depends(get_current_user)`) и используют HTTP‑only cookies для JWT
- Пагинация: зависимости `get_small_pagination` и `get_large_pagination` возвращают кортеж `(skip, limit)`
- Ошибки: неожиданные исключения конвертируются в единый формат через глобальный middleware и/или декоратор `@handle_api_errors`
- Теги и префиксы: каждый роутер имеет `prefix` и `tags` для группировки в Swagger

### Аутентификация (`/auth`)
- POST `/auth/register` — регистрация, 201, устанавливает `access_token` и `refresh_token` в куки
- POST `/auth/login` — вход, 200, возвращает `user_id`, ставит куки токенов
- POST `/auth/refresh` — обновление access‑токена по refresh‑куке, 200
- POST `/auth/logout` — очистка токенов, 200

Пример:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login": "user1", "password": "p@ssw0rd"}' -i
```

### Пользователи (`/user`)
- PATCH `/user/me` — обновить профиль, 200
- GET `/user/me` — получить свой профиль + агрегаты, 200
- GET `/user/me/histories` — получить свои истории (пагинация), 200
- DELETE `/user/me` — удалить аккаунт, 204
- GET `/user/profile/{id}` — получить профиль пользователя по ID, 200
- GET `/user/profile/{id}/histories` — получить истории пользователя по ID (пагинация), 200
- GET `/user/search?q=...` — поиск пользователей по логину (пагинация), 200

Особенности:
- Формирование расширенного профиля — параллельные вызовы (истории, подписчики, подписки, друзья)
- Поиск кешируется (`UsersSearchCacheService`), ключ включает `me_user_id`

### Истории (`/history`)
- POST `/history/` — создать историю, 201
- GET `/history/` — лента историй (пагинация), 200
- GET `/history/id/{id}` — история по ID с агрегатами, 200
- GET `/history/id/{id}/comments` — комментарии к истории (пагинация), 200
- GET `/history/following` — истории подписок (пагинация), 200
- GET `/history/friends` — истории друзей (пагинация), 200
- PUT `/history/{id}` — изменить историю, 200
- DELETE `/history/{id}` — удалить историю, 204

Особенности:
- Чтение лент друзей/подписок — read‑through кэш (`FriendsHistoriesCacheService`, `FollowingHistoriesCacheService`)
- После мутаций вызывается централизованная инвалидация (`CacheInvalidationService.on_history_changed`)

### Комментарии (`/comments`)
- POST `/comments/` — создать комментарий, 201
- GET `/comments/{id}` — получить комментарий по ID, 200
- PUT `/comments/{id}` — изменить комментарий, 200
- DELETE `/comments/{id}` — удалить комментарий, 204

Особенности:
- Ответ включает карточку автора, счётчики и списки пользователей лайков/дизлайков
- После мутаций — инвалидация `comments_by_history` и `history_with_counts`

### Лайки/Дизлайки историй (`/likes`, `/dislikes`)
- POST `/likes/` — создать лайк истории, 201
- GET `/likes/{history_id}` — получить мой лайк по ID истории, 200
- DELETE `/likes/{history_id}` — удалить мой лайк, 204
- POST `/dislikes/` — создать дизлайк истории, 201
- GET `/dislikes/{history_id}` — получить мой дизлайк истории, 200
- DELETE `/dislikes/{history_id}` — удалить мой дизлайк, 204

### Лайки/Дизлайки комментариев (`/comment-likes`, `/comment-dislikes`)
- POST `/comment-likes/` — создать лайк комментария, 201
- GET `/comment-likes/{comment_id}` — получить мой лайк комментария, 200
- DELETE `/comment-likes/{comment_id}` — удалить мой лайк комментария, 204
- POST `/comment-dislikes/` — создать дизлайк комментария, 201
- GET `/comment-dislikes/{comment_id}` — получить мой дизлайк комментария, 200
- DELETE `/comment-dislikes/{comment_id}` — удалить мой дизлайк комментария, 204

### Подписки (`/followers`)
- POST `/followers/` — подписаться, 201
- DELETE `/followers/` — отписаться, 200
- GET `/followers/{id}` — подписчики пользователя (пагинация), 200
- GET `/followers/following/{id}` — подписки пользователя (пагинация), 200

Особенности:
- При подписке/отписке проверяется дружба (взаимные подписки) и выполняется каскадная инвалидация кэшей

### Сообщения и чаты (`/messages`, `/ws`)
- GET `/messages/chats` — список чатов пользователя с превью последнего сообщения, 200
- WS `/ws/` — WebSocket‑соединение (аутентификация через начальный JSON с access‑токеном)
- POST `/ws/get_room_id` — получить `room_id` по логину собеседника, 201
- POST `/ws/send_message` — отправить сообщение в комнату, 200

Особенности WebSocket:
- При подключении клиент отправляет `{ "type": "access_token", "token": "..." }`
- Поддерживается рассылка в комнатах (`ConnectionManager.room_connections`)
- Ошибки подключения/отправки логируются, клиенту возвращается JSON с описанием

### Коды ошибок (общее)
- 400/422 — валидационные ошибки Pydantic
- 401 — требуется аутентификация или просрочен токен
- 403 — нарушение владения ресурсом/прав
- 404 — сущность не найдена
- 409 — конфликт уникальности (например, повторная регистрация)
- 500 — внутренняя ошибка сервера (логируется)

### Версионирование и расширяемость
- Добавление нового роутера: создать файл в `app/api/routers`, экспортировать в `__init__.py`, подключить в `app/api/router.py`
- Соблюдать префиксы и теги для консистентной документации в Swagger
- Общие проверки (аутентификация, владение, пагинация) выносить в зависимости

— В «Части 6» опишем схемы (Pydantic): контракты входа/выхода, правила сериализации и примеры.

<a id="part-6"></a>
## Часть 6 — Схемы (Pydantic v2) и контракты API

Эта часть описывает Pydantic‑схемы входа/выхода, правила сериализации (`from_attributes`), enum‑ы, валидаторы и вспомогательные методы построения ответов. Схемы гарантируют стабильные контракты API и типобезопасность.

### Общие принципы
- Версия: Pydantic v2
- Все публичные ответы сериализуются через схемы в `app/schemas/*`
- Для ORM‑моделей включён `Config.from_attributes = True` (бывший `orm_mode`)
- Для частичных обновлений используйте модели с опциональными полями и `exclude_unset=True`

### Пользователи (`schemas/user.py`)
- Enum `FollowStatus`: `not_following`, `followed_by_me`, `following_me`, `mutual`, `me`
- `UserBase`: базовые поля профиля (`login`, `about?`, `avatar_url?`)
- `UserCreate`: добавляет `password`
- `UserOut`: расширенный профиль (id, role, friends/followers/following?)
- `UserShortOut`: укороченный профиль (id, login, about?, avatar_url?)
  - Валидатор `about` обрезает длинные описания до 20 символов
- `UserShortOutWithFollowStatus`: `UserShortOut` + `follow_status`
- `UserAuth`: логин/пароль
- `UpdateUser` и `UpdateMe`: частичные обновления
- `ProfileOutFull`: агрегированный профиль с метриками (друзья/подписчики/подписки/истории)

### Истории (`schemas/history.py`)
- `HistoryCreate`: `title`, `description?`
- `HistoryOut`: подробная история (id, title, description?, likes, dislikes, comments, liked_users[], disliked_users[], author?, created_at, updated_at?)
  - `from_model_with_counts(...)` дополняет базовую валидацию агрегированными полями
- `HistoryOutShort`: компактный вариант без автора, тот же `from_model_with_counts`
- `HistoryUpdate`: частичное обновление `title?`, `description?`

### Комментарии (`schemas/comment.py`)
- `CommentCreate`: `content`, `history_id`, `comment_type` (default `text`), `comment_metadata` (dict)
- `CommentUpdate`: частичное поле `content?`
- `CommentOut`: полный ответ с `user_info`, лайками/дизлайками и их списками, типом и метаданными
  - Класс‑метод `from_model_with_counts(...)` строит полноценный ответ из ORM‑модели + агрегатов

### Реакции (`schemas/like.py`)
- Истории:
  - `HistoryLikeCreate`, `HistoryLikeOut` (id, user_id, history_id, created_at, user_info)
  - `HistoryDislikeCreate`, `HistoryDislikeOut` (аналогично)
- Комментарии:
  - `CommentLikeCreate`, `CommentLikeOut`
  - `CommentDislikeCreate`, `CommentDislikeOut`

### Чаты и сообщения
- `schemas/chat.py`:
  - `ChatOut`: превью чата (companion_login, last_message, last_message_time, room_id, from_me, is_read)
  - `ChatCreate`: `room_id`
- `schemas/message.py`:
  - Enum `MessageType`: `text`, `image`, `file`, `system`
  - `MessageOut`: id, sender_id, room_id, text, message_type, timestamp, is_read, metadata{}, from_me
  - `MessageCreate` и `MessageUpdate`: для создания/обновления

### Подписки/друзья/ответы
- `schemas/followers.py`: `FollowerCreate` (target_id)
- `schemas/friends.py`: `FriendCreate` (user_id, friend_id)
- `schemas/response.py`: `SuccessResponse`, `FollowResponse` (содержит `FollowStatus`)
- `schemas/author.py`: `AuthorOut` — минимальная карточка автора

### Правила сериализации и обновления
- `from_attributes = True` позволяет подавать ORM‑модели в `.model_validate(...)`
- Для частичных обновлений:
  - Соберите `updated_data = updated_schema.model_dump(exclude_unset=True)`
  - Примените только изменённые поля к ORM‑объекту
- Для составных ответов используйте фабрики/класс‑методы (`from_model_with_counts`) вместо ручного конструирования в роутерах

### Советы по эволюции схем
- Не ломать обратную совместимость: новые поля делать опциональными с дефолтами
- Версионировать API при больших изменениях контрактов
- Документировать значения enum‑ов и диапазоны числовых полей
- Сохранять соответствие схем и каскадов инвалидации кэша (например, добавление `follow_status` → ключи кэша с `me_user_id`)

— В «Части 7» разберём безопасность и аутентификацию: JWT, куки (HttpOnly/Secure/SameSite), ротация токенов, и лучшие практики.

<a id="part-7"></a>
## Часть 7 — Безопасность и аутентификация (JWT + Cookies)

Эта часть описывает аутентификацию на JWT, хранение токенов в cookies, валидацию и лучшие практики безопасности. Также приводятся замечания по CORS и WebSocket‑безопасности.

### JWT и параметры
- Алгоритм: настраивается через `settings.jwt_algorithm` (по умолчанию `HS256`)
- Секрет: `settings.jwt_secret_key` — хранить вне репозитория (ENV/Secret Manager)
- Сроки жизни: `jwt_access_token_expire_minutes`, `jwt_refresh_token_expire_days`
- Функции: `create_access_token`, `create_refresh_token`, `decode_token` в `app/core/jwt.py`

### Cookies для токенов
- Имена cookies берутся из `settings`: `jwt_access_cookie_name`, `jwt_refresh_cookie_name`
- Установка/очистка — в `app/core/cookie.py` (`set_auth_cookies`, `clear_auth_cookies`)
- Рекомендации для PROD:
  - `httponly=True` (сейчас в коде `False`, поднять в проде)
  - `secure=True` (только HTTPS)
  - `samesite='lax'|'strict'` — защита от CSRF
  - `max_age` по бизнес‑требованиям (обычно refresh 7–30 дней)

Пример политики (prod):
```python
response.set_cookie(name, value, httponly=True, secure=True, samesite='lax', max_age=max_age)
```

### Валидация пользователя и refresh‑токена
- `get_current_user`: читает access‑токен из cookie, декодирует JWT (`decode_token`), загружает пользователя по `sub`
- `validate_refresh_token`: читает refresh‑токен из cookie, возвращает `user_id` при валидном токене
- Ошибки маппятся на доменные (`PermissionError`, `ValidationError`, `UserNotFoundError`) и конвертируются middleware‑ом в JSON

### Потоки аутентификации
- Регистрация/логин (`/auth/register`, `/auth/login`): создают токены и устанавливают их в cookies
- Обновление access (`/auth/refresh`): требует валидного refresh‑токена; выдает новый access и устанавливает в cookie
- Logout (`/auth/logout`): очищает обе cookies

### CORS и защита от CSRF
- CORS: разрешайте запросы только от доверенных доменов (`settings.cors_origins`)
- Для cookie‑аутентификации:
  - Включайте `SameSite=lax/strict` и `Secure` в продакшене
  - Для state‑changing запросов используйте CSRF‑токен/двойную отправку (рекомендация к внедрению)

### WebSocket безопасность
- Подключение требует отправки JSON с `{ "type": "access_token", "token": "..." }`
- Токен проверяется так же, как в HTTP (через `get_current_user`), не хранить токен в URL
- При ошибке — закрытие соединения и логирование события

### Логирование и аудит
- Все ключевые события (`login`, `logout`, `refresh`, ошибки декодирования) логируются через `app_logger`
- Рекомендуется добавить аудит‑лог с IP/UA и ограничение попыток логина (rate‑limit)

### Ротация токенов (рекомендации)
- Меняйте refresh‑токен при каждом обновлении access (token rotation)
- Храните «серый список» отозванных refresh‑токенов (например, в Redis) при критических случаях
- Принудительно инвалидируйте токены при смене пароля/ролей

### Мини‑чеклист безопасности
- Секреты — только из ENV/Secret Manager
- Cookies: `HttpOnly=True`, `Secure=True`, `SameSite=lax/strict` в PROD
- Сроки жизни access минимальны, refresh — ограничен и ротируется
- Ограничить CORS, отключить `*` в продакшене
- Включить rate‑limiting/капчу для логина при необходимости
- Логи — без утечки секретов и токенов

— В «Части 8» разберём обработку ошибок и исключения: доменная модель ошибок, глобальный middleware, и согласованные ответы.

<a id="part-8"></a>
## Часть 8 — Обработка ошибок и исключения

В этой части описана доменная модель исключений, глобальный middleware ошибок и единый формат ответов. Цель — предсказуемые коды статусов и сообщения для клиента, а также корректное логирование инцидентов.

### Доменные исключения (`app/exceptions/*`)
- Базовые: `ValidationError (400)`, `PermissionError (403)`, `DatabaseError (500)`, `UnknownDatabaseError (500)`, `ModelNotFoundError (404)`
- Пользователи: `UserAlreadyExistsError (409)`, `UserNotFoundError (404)`, `InvalidCredentialsError (401)`, `InvalidUserDataError (400)`
- Истории: `HistoryNotFoundError (404)`, `OwnershipHistoryError (403)`
- Комментарии: `CommentNotFoundError (404)`, `OwnershipCommentError (403)`
- Реакции: `LikeNotFoundError (404)`, `OwnershipLikeError (403)`, `DislikeNotFoundError (404)`, `OwnershipDislikeError (403)`, `CommentLikeNotFoundError (404)`, `OwnershipCommentLikeError (403)`, `CommentDislikeNotFoundError (404)`, `OwnershipCommentDislikeError (403)`
- Подписки: `FollowAlredyExists (409)`
- Сообщения: `MessageNotFoundError (404)`, `OwnershipMessageError (403)`

### Глобальный middleware ошибок
- `ErrorHandlerMiddleware` перехватывает перечисленные выше исключения и формирует JSON:
```json
{
  "error": "Сообщение об ошибке",
  "status_code": 404
}
```
- Неожиданные исключения логируются как событие `unhandled_exception` и возвращают 500 с нейтральным сообщением

### Где генерируются исключения
- В менеджерах при отсутствии сущности — `ModelNotFoundError`/специфичные `*NotFoundError`
- При конфликте уникальности (регистрация, follow) — `409`
- При нарушении прав/владения — `403`
- При неверных данных/токенах — `400/401`

### Декоратор для роутов
- `@handle_api_errors("Сообщение")` нормализует неожиданные ошибки в `DatabaseError` (500) с логированием
- Используется для тонких контроллеров, где логика вынесена в менеджеры

### Рекомендации
- Не пробрасывать сырые исключения БД наружу; маппить на доменные
- Сообщения ошибок — без утечки секретов/внутренних деталей
- В логах хранить контекст (path/method/client/error) по стандарту структурированного логгера

— В «Части 9» рассмотрим логирование: формат, ротацию логов и практики наблюдаемости.

<a id="part-9"></a>
## Часть 9 — Логирование и наблюдаемость

Система логирования обеспечивает структурированные записи с ротацией и цветной консолью. Логи хранятся в `logs/` и используются для аудита и диагностики.

### Архитектура логгера (`app/core/logger.py`)
- Формат сообщений: `%(asctime)s | %(levelname)s | %(name)s | %(message)s` + сериализация `extra` в `k=v`
- Ротация файлов: `RotatingFileHandler` (5MB, 3 бэкапа)
- Консоль: цветной формат через `colorlog`
- Уровень по умолчанию: `DEBUG` (можно поднять в проде до `INFO/WARNING`)

### Структурированные события
- Помощники: `info_event`, `warning_event`, `error_event` — единый стиль записи событий
- Пример:
```python
app_logger.info_event("user_registered", user_id=42, login="john")
```
- В результате в файле лога появится строка вида:
```text
2025-01-01 12:00:00 | INFO | app | user_registered | user_id=42 login=john
```

### Что логируем
- Аутентификация: `user_logged_in`, `user_registered`, `user_logged_out`, ошибки токенов
- Мутации данных: `history_created/updated/deleted`, `comment_*`, `follow_*`, `friend_*`
- Ошибки: `*_failed`, `unhandled_exception` с контекстом запроса

### Рекомендации по наблюдаемости
- Отдельные каналы для access‑логов (reverse‑proxy) и бизнес‑логов приложения
- Метрики (в будущих частях): количество ошибок/сек, латентность ответов, кэшь‑хиты/промахи
- Трассировка: интеграция с OpenTelemetry (Span для запроса, атрибуты path/method/status)

— В «Части 10» опишем WebSocket и real‑time обмен: жизненный цикл, комнаты, форматы сообщений и обработку ошибок.

<a id="part-10"></a>
## Часть 10 — WebSocket и real‑time

Реалтайм‑подсистема обеспечивает приватные чаты и доставку сообщений по комнатам.

### Компоненты
- Роутер: `/ws` (`app/api/routers/websocket.py`)
- Менеджер соединений: `ConnectionManager` (`app/database/managers/connection_manager.py`)
- Сервисы: `chat_service.create_room_id`, `message_service.send_message_to_room`
- Менеджер сообщений: `MessageManager`

### Подключение WebSocket
- Эндпоинт: `GET WS /ws/`
- Клиент после `accept()` обязан отправить JSON с токеном:
```json
{ "type": "access_token", "token": "<JWT>" }
```
- Токен валидируется через зависимость `get_current_user`; при ошибке соединение закрывается

### Комнаты и пересылка
- Связка `room_id → [user_ids]` хранится в памяти процесса (`room_connections`)
- Для приватного чата `room_id` генерируется детерминированно (MD5 от `creator_id+companion_id`)
- Отправка сообщения по комнате распространяет JSON всем активным участникам комнаты

### Хранение сообщений
- Сообщения сохраняются в БД через `MessageManager.save_message`
- Формат ответа на отправку дополняется полем `from_me` для клиента

### Обработка ошибок
- `WebSocketDisconnect` → отключение пользователя и выпиливание из комнаты
- Любое исключение логируется и возвращается клиенту JSON‑ошибка; сокет закрывается

### Рекомендации
- В продакшене используйте sticky‑sessions или внешний брокер/шину для масштабирования WS
- Валидируйте размер/тип сообщений, ограничивайте частоту (rate limit)
- Не передавайте токены в URL, только в телах первых сообщений

— В «Части 11» опишем тестирование и CI: уровни тестов, фикстуры, проверка контрактов и базовый pipeline.

<a id="part-11"></a>
## Часть 11 — Тестирование и CI

### Рекомендованные инструменты
- Тесты: `pytest`, `pytest-asyncio`
- HTTP‑клиент: `httpx` или `fastapi.testclient`
- Линтеры/форматтеры: `ruff`/`flake8`, `isort`, `black`
- Типы: `mypy` (для стабильности контрактов)

### Стратегия тестирования
- Юнит‑тесты: менеджеры, сервисы, функции билдеров, валидация схем
- Интеграционные: эндпоинты FastAPI, фикстуры БД (временная БД/транзакции), мок Redis
- Контрактные: проверка схем API (JSON‑снапшоты), негативные сценарии
- Нагрузочные (опционально): профилирование медленных агрегатов/кэша

### Примеры
- Юнит менеджера:
```python
@pytest.mark.asyncio
async def test_get_histories_returns_counts(history_manager):
    res = await history_manager.get_histories(skip=0, limit=5, me_user_id=1)
    assert isinstance(res, list)
```

- Интеграция эндпоинта:
```python
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_history_feed(auth_client: AsyncClient):
    resp = await auth_client.get("/history?skip=0&limit=5")
    assert resp.status_code == 200
```

### CI (минимальный pipeline)
- Этапы:
  - Установка зависимостей
  - Линтинг/типизация (`ruff`/`flake8`, `mypy`)
  - Тесты (`pytest -q`)
  - Сбор артефактов (отчёты)

Шаблон GitHub Actions (фрагмент):
```yaml
name: backend-ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: python -m pip install -r requirements.txt
      - run: pip install pytest httpx pytest-asyncio mypy ruff
      - run: ruff check .
      - run: mypy app
      - run: pytest -q
```

— В «Части 12» финализируем деплой, мониторинг, troubleshooting и дадим краткий глоссарий.

<a id="part-12"></a>
## Часть 12 — Деплой, мониторинг, troubleshooting, глоссарий

### Деплой (варианты)
- Docker/Compose: оборачиваем FastAPI + Redis, на входе `nginx`
- Systemd/PM2/Supervisor: для монолитного запуска без контейнеров
- PaaS (Railway/Fly/Render): быстрый запуск с переменными окружения

#### Docker Compose (скелет)
```yaml
services:
  api:
    build: .
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    ports:
      - "8000:8000"
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Мониторинг/наблюдаемость
- Метрики: экспорт ASGI (latency, throughput), Redis (hits/misses, memory)
- Логи: централизованный сбор (ELK/Vector/CloudWatch)
- Трейсинг: OpenTelemetry (Spans: запросы, SQL, Redis)

### Troubleshooting (частые кейсы)
- 500 при пике — проверьте пул соединений и долгие SQL, включите профайлер
- Кэш не инвалидируется — проверьте префиксы ключей и вызовы `on_*` после коммита
- CORS блокирует — добавьте домен в `CORS_ORIGINS`, проверьте `Secure/SameSite`
- JWT недействителен — проверьте время на сервере, секрет и алгоритм

### Глоссарий (дополнение)
- Sticky‑sessions — закрепление клиента за инстансом для WS
- Rate limit — ограничение частоты запросов
- TTL — время жизни кэш‑ключа в Redis
- WS — WebSocket, двунаправленный канал связи

<a id="final"></a>
## Заключение, масштабирование и Roadmap

### Заключение
Проект структурирован по слоям (ядро, API, БД/ORM, менеджеры, сервисы, схемы), использует асинхронный стек Python (FastAPI + SQLAlchemy 2.0 + Redis) и готов к расширению: добавление роутеров, моделей, кэш‑кейсов и бизнес‑операций.

### Рекомендации по масштабированию
- Горизонтальное масштабирование API за reverse‑proxy (Nginx) + sticky‑sessions для WS или вынос WS в отдельный сервис/брокер
- Переезд на внешнюю БД (Postgres/MySQL) и настройка пула соединений
- Введение Alembic‑миграций и миграционного процесса
- Расширение кэша: сегментация ключей, отдельные Redis‑инстансы для разных нагрузок
- Наблюдаемость: Prometheus/Grafana, централизованные логи, OpenTelemetry трассировка
- Безопасность: ротация токенов, серые списки, строгие CORS/CSRF, секрет‑менеджер

### Roadmap (примерный)
- v0.2: Alembic, Docker Compose full (Nginx, API, Redis), базовые метрики ASGI
- v0.3: Трассировка OpenTelemetry, rate‑limiting, улучшение кэш‑стратегий
- v0.4: Масштабирование WS (брокер/шина), отложенные задачи (RQ/Celery)
- v0.5: E2E/контрактные тесты, автогенерация API‑документации, чекстлисты релизов


### Быстрые проверки готовности окружения
```bash
# Проверка версии Python
python --version

# Быстрый импорт FastAPI
python -c "import fastapi, sqlalchemy, pydantic; print('ok')"

# Доступность Redis (если используете)
redis-cli -h 127.0.0.1 -p 6379 PING
```


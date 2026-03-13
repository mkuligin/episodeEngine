# episodeEngine

`episodeEngine` - это локальный episodic agent runtime для работы по пользовательским задачам в текстовой консоли. Проект больше не запускает встроенный тестовый сценарий автоматически: после старта он читает системный промпт, поднимает `rich`-интерфейс и ждет задачи от пользователя.

Основная идея проекта осталась прежней: каждая пользовательская задача оформляется как отдельный эпизод, проходит через планирование, исполнение и верификацию, после чего результат и след выполнения сохраняются в память и журнал событий.

## Что изменилось

Проект переведен из демо-режима в рабочий интерактивный режим:

- убран автоматический запуск тестового demo-flow из `main.py`;
- все настройки вынесены в `.env`;
- добавлен роутер моделей с ручным выбором и failover;
- сохранена поддержка `ollama`;
- добавлены провайдеры `openrouter` и `z.ai`;
- после старта открывается текстовый TUI на `rich`;
- добавлено подробное файловое логирование в `log/`.

## Как теперь работает система

Точка входа - [main.py](C:\Users\mk\code\episodeEngine\main.py).

После запуска приложение:

1. Загружает конфигурацию из `.env`.
2. Читает системный промпт из файла `SYSTEM_PROMPT_FILE`.
3. Настраивает логирование в `log/session-YYYYMMDD-HHMMSS.log`.
4. Создает модельный роутер и инициализирует episodic runtime.
5. Показывает `rich`-интерфейс с командами и доступными маршрутами моделей.
6. Ждет текстовый запрос пользователя.
7. Каждый ввод пользователя превращает в `Task` и запускает новый эпизод.

## Архитектура

### Основные модули

[main.py](C:\Users\mk\code\episodeEngine\main.py)

- запускает приложение;
- читает системный промпт;
- поднимает интерактивный TUI через `rich`;
- принимает пользовательские команды и задачи.

[llm/model_interface.py](C:\Users\mk\code\episodeEngine\llm\model_interface.py)

- содержит роутер моделей;
- поддерживает ручной режим `manual`;
- поддерживает автоматический режим `auto` с переключением по списку fallback-маршрутов;
- работает с OpenAI-compatible API для `ollama`, `openrouter`, `z.ai`.

[utils/config.py](C:\Users\mk\code\episodeEngine\utils\config.py)

- загружает `.env`;
- описывает провайдеров, primary route и fallback routes;
- собирает единый объект конфигурации приложения.

[utils/logging_config.py](C:\Users\mk\code\episodeEngine\utils\logging_config.py)

- создает директорию `log/`;
- настраивает подробный файловый лог текущей сессии.

[agent/orchestrator.py](C:\Users\mk\code\episodeEngine\agent\orchestrator.py)

- управляет lifecycle эпизода;
- выполняет `register -> initialize -> plan -> execute -> close`;
- пишет события в журнал и сохраняет карточку эпизода.

[agent/context_builder.py](C:\Users\mk\code\episodeEngine\agent\context_builder.py)

- формирует planning prompt и execution prompt;
- теперь ожидает JSON-ответы, чтобы сделать интеграцию с внешними моделями более устойчивой.

[agent/planner.py](C:\Users\mk\code\episodeEngine\agent\planner.py)

- парсит JSON-план;
- поддерживает fallback на обычный текстовый план;
- определяет `action_type` даже если модель не прислала его явно.

[agent/executor.py](C:\Users\mk\code\episodeEngine\agent\executor.py)

- получает от модели JSON-действие;
- передает его в `ToolRunner`;
- журналирует выбранное действие.

[agent/verifier.py](C:\Users\mk\code\episodeEngine\agent\verifier.py)

- делает более общий post-check;
- проверяет возврат кода, изменения файлов и базовую успешность шагов.

[tools/tool_runner.py](C:\Users\mk\code\episodeEngine\tools\tool_runner.py)

- выполняет разрешенные действия:
  - `shell`
  - `list_dir`
  - `read_file`
  - `write_file`
- пишет подробные записи в лог.

[memory/episode_store.py](C:\Users\mk\code\episodeEngine\memory\episode_store.py)

- сохраняет `EpisodeCard` в `storage/cards/`;
- архивирует состояние эпизода в `storage/episodes/`.

[runtime/event_journal.py](C:\Users\mk\code\episodeEngine\runtime\event_journal.py)

- append-only журнал событий в `storage/events.jsonl`.

## Роутер моделей

Роутер умеет работать в двух режимах.

### 1. Manual

Используется один выбранный маршрут `provider:model`.

Примеры:

- `ollama:qwen2.5-coder:7b`
- `openrouter:openai/gpt-4.1-mini`
- `zai:glm-4.5-air`

Можно переключить маршрут прямо в TUI:

```text
/use openrouter openai/gpt-4.1-mini
/use zai glm-4.5-air
```

### 2. Auto

Система сначала пробует `MODEL_PROVIDER + MODEL_NAME`, затем по очереди идет по `MODEL_FALLBACKS`.

Если маршрут недоступен из-за сетевой ошибки, недоступного API или отсутствующего ключа, роутер автоматически переходит к следующему маршруту.

## Поддерживаемые провайдеры

### Ollama

- используется OpenAI-compatible endpoint;
- по умолчанию: `http://localhost:11434/v1`;
- API-ключ не обязателен.

### OpenRouter

- по умолчанию: `https://openrouter.ai/api/v1`;
- нужен `OPENROUTER_API_KEY`;
- поддерживаются дополнительные заголовки `OPENROUTER_HTTP_REFERER` и `OPENROUTER_APP_TITLE`.

### Z.AI

- по умолчанию: `https://api.z.ai/api/paas/v4`;
- нужен `ZAI_API_KEY`;
- модель задается через `ZAI_MODEL`.

## Конфигурация

Все настройки вынесены в `.env`. Шаблон лежит в [\.env.example](C:\Users\mk\code\episodeEngine\.env.example), рабочий локальный файл - `.env`.

Ключевые переменные:

```env
MODEL_MODE=auto
MODEL_PROVIDER=ollama
MODEL_NAME=qwen2.5-coder:7b
MODEL_FALLBACKS=openrouter:openai/gpt-4.1-mini,zai:glm-4.5-air

OLLAMA_BASE_URL=http://localhost:11434/v1
OPENROUTER_API_KEY=
ZAI_API_KEY=
SYSTEM_PROMPT_FILE=system_prompt.md
LOG_DIR=log
STORAGE_DIR=storage
```

## Системный промпт

По умолчанию приложение читает [system_prompt.md](C:\Users\mk\code\episodeEngine\system_prompt.md).

Его задача:

- задать общее поведение агента;
- потребовать JSON-ответы в planning/execution режимах;
- ограничить работу только доступными инструментами;
- запретить выдумывание результатов.

При необходимости можно заменить файл и просто поменять `SYSTEM_PROMPT_FILE` в `.env`.

## TUI-команды

После запуска доступны команды:

- `/help` - показать список команд;
- `/models` - показать таблицу маршрутов;
- `/mode auto|manual` - переключить режим роутера;
- `/use <provider> <model>` - выбрать конкретный маршрут вручную;
- `/prompt` - показать текущий системный промпт;
- `/exit` - выйти.

Любая строка, не начинающаяся с `/`, считается новой задачей и запускает отдельный эпизод.

## Жизненный цикл эпизода

Для каждой задачи выполняется стандартный цикл:

1. `Registration`
2. `Initialization`
3. `Planning`
4. `Execution Loop`
5. `Verification`
6. `Closure`

На выходе пользователь получает `Episode Summary`, а система сохраняет:

- события в `storage/events.jsonl`;
- карточку опыта в `storage/cards/`;
- архив подробного состояния в `storage/episodes/`.

## Логирование

Подробные технические логи теперь пишутся в директорию `log/`.

Туда попадают:

- запуск приложения;
- выбранный режим роутера;
- попытки вызова моделей;
- ошибки failover;
- выбранные tool actions;
- результаты shell-команд;
- этапы выполнения эпизода.

Формат логов рассчитан на разбор проблем интеграции с моделями и отладку исполнения.

## Установка и запуск

Требования:

- Python 3.11+

Установка зависимости:

```bash
python -m pip install -r requirements.txt
```

Запуск:

```bash
python main.py
```

## Пример рабочего сценария

После старта можно дать задачу в духе:

```text
Найди в проекте основные точки входа и составь краткий план рефакторинга
```

Или:

```text
Проверь структуру репозитория и предложи следующие шаги по стабилизации конфигурации
```

Агент создаст эпизод, построит план, выполнит шаги через доступные инструменты и покажет summary по итогу.

## Ограничения текущей версии

Несмотря на переход к рабочему режиму, это все еще компактный runtime, а не production-grade агент:

1. Выполнение ограничено базовым набором инструментов.
2. Верификация шагов остается эвристической.
3. Успех сильно зависит от того, насколько модель соблюдает JSON-формат.
4. Планирование пока не использует сложную память, embeddings или внешний state backend.
5. В TUI нет полноценного многошагового chat memory между пользовательскими запросами: каждая задача запускается как отдельный эпизод.

## Источники интеграций

При настройке провайдеров использовались официальные страницы:

- [OpenRouter Docs](https://openrouter.ai/docs)
- [Ollama Docs](https://ollama.com/docs/openai)
- [Z.AI Docs](https://docs.z.ai)

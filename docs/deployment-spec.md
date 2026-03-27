# 🚀 Deployment Specification | SciVerify

Данный документ содержит инструкции по развертыванию, настройке и эксплуатации системы **SciVerify** в локальной и production средах.

---

## 1. Системные требования

| Компонент | Минимальные требования | Рекомендуемые |
|:---|:---|:---|
| **OS** | Windows 10 / macOS 12 / Ubuntu 20.04 | Windows 11 / macOS 14 / Ubuntu 22.04 |
| **CPU** | 2 ядра | 4+ ядер |
| **RAM** | 4 GB | 8+ GB |
| **Storage** | 5 GB свободного места | 10+ GB |
| **Python** | 3.11+ | 3.11+ |
| **Docker** | 24.0+ (опционально) | 24.0+ |

---

## 2. Переменные окружения

Создайте файл `.env` в корне проекта на основе следующего шаблона:

```bash
# --- OpenRouter & LLM ---
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-or-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_BASE=https://openrouter.ai/api/v1

# --- Qdrant Cloud (Vector DB) ---
QDRANT_URL=https://xxxxxxxx-xxxx.cloud.qdrant.io
QDRANT_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# --- LangFuse (Observability) ---
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx-xxxx-xxxx-xxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx-xxxx-xxxx-xxxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## 3. Локальный запуск (Development)

### Шаг 1: Установка зависимостей
```bash
# Клонирование репозитория
git clone <repository-url>
cd sci-verify

# Создание и активация venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Установка пакетов
pip install -r requirements.txt
```

### Шаг 2: Настройка и индексация
```bash
cp .env.example .env  # Создайте и заполните ключи в .env
python scripts/ingest.py  # Загрузка и индексация статей в Qdrant
```

### Шаг 3: Запуск компонентов
Система требует одновременной работы двух компонентов:

1.  **MCP Сервер (Поиск):**
    ```bash
    python -m mcp_server.server
    # Ожидаемый лог: Starting MCP server on 127.0.0.1:8002
    ```
2.  **Агент (CLI интерфейс):**
    ```bash
    python main.py
    ```

---

## 4. Запуск через API

Если вы планируете использовать SciVerify как бэкенд для фронтенда:

```bash
# Терминал 1: Запуск MCP сервера
python -m mcp_server.server

# Терминал 2: Запуск FastAPI
uvicorn app.api:api --host 0.0.0.0 --port 8000 --reload
```

**Проверка работы API:**
```bash
# Healthcheck
curl http://localhost:8000/health

# Запрос к агенту
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Что такое BERT?"}'
```

---

## 5. Docker Compose (Production)

Для развертывания в контейнерах используйте `docker-compose.yml`.

### Конфигурация сервисов
```yaml
version: '3.8'

services:
  mcp_server:
    build: .
    ports:
      - "8002:8002"
    env_file: .env
    command: python -m mcp_server.server
    restart: unless-stopped

  agent_api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - mcp_server
    environment:
      - MCP_SERVER_URL=http://mcp_server:8002/mcp
    env_file: .env
    command: uvicorn app.api:api --host 0.0.0.0 --port 8000
    restart: unless-stopped
```

**Управление:**
```bash
docker-compose up --build -d  # Запуск в фоне
docker-compose logs -f        # Просмотр логов
docker-compose down           # Остановка
```

---

## 6. Структура проекта

```text
my_project/
├── app/                  # Логика LangGraph агента
│   ├── graph.py          # Определение графа состояний
│   ├── state.py          # Схема состояния (State)
│   └── api.py            # FastAPI эндпоинты
├── mcp_server/           # Сервер протокола поиска
│   ├── server.py         # Точка входа сервера
│   └── retriever.py      # Логика поиска в Qdrant
├── scripts/              # Скрипты автоматизации
│   └── ingest.py         # Загрузка данных в векторную БД
├── data/                 # Локальное хранилище данных
│   ├── papers_list.txt   # Реестр статей
│   └── arxiv_papers/     # PDF-архив
├── docs/                 # Техническая документация
├── main.py               # CLI версия агента
├── Dockerfile            # Инструкция сборки образа
└── requirements.txt      # Список зависимостей
```

---

## 7. Устранение неполадок (Troubleshooting)

| Проблема | Решение |
|:---|:---|
| **Порт 8002 занят** | Проверьте процессы: `lsof -i :8002` (Mac/Linux) или `netstat -ano \| findstr :8002` (Win). |
| **Qdrant Connection Error** | Проверьте `QDRANT_URL`. Убедитесь, что ключ в `.env` не имеет лишних пробелов. |
| **Трейсы не в LangFuse** | Выполните: `python -c "from langfuse import Langfuse; print(Langfuse().auth_check())"`. |
| **ModuleNotFoundError** | Убедитесь, что вы находитесь в корне проекта и выполнили `pip install -e .` или установили зависимости в активный venv. |

---

## 8. Полезные ссылки

*   📚 [OpenRouter API Docs](https://openrouter.ai/docs)
*   🛡️ [Qdrant Cloud Console](https://cloud.qdrant.io/)
*   📊 [LangFuse Dashboard](https://cloud.langfuse.com)
*   🦜 [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
# 🔍 Module Specification: Retriever (MCP Server)

## 1. Назначение
Модуль **Retriever** является поисковым ядром системы SciVerify. Он инкапсулирует логику взаимодействия с векторной базой данных **Qdrant** и предоставляет унифицированный интерфейс для выполнения гибридного поиска (Dense + Sparse) по специализированным коллекциям научных статей.

## 2. Интерфейс (MCP Tool)

Инструментарий предоставляется через протокол MCP для использования LLM-агентами.

### `search_scientific_papers`
Основной инструмент для поиска релевантных чанков текста.

**Сигнатура:**
```python
@mcp.tool()
def search_scientific_papers(
    query: str,
    collection_mode: str = "collection_normal_chunks",
    limit: int = 3
) -> List[Dict[str, Any]]:
    """Поиск научных статей в Qdrant."""
```

**Входные параметры:**
| Параметр | Тип | Обяз. | По умолчанию | Описание |
|:---|:---|:---:|:---|:---|
| `query` | `str` | Да | - | Поисковый запрос на английском языке. |
| `collection_mode` | `str` | Нет | `"collection_normal_chunks"` | Целевая коллекция (см. раздел 3). |
| `limit` | `int` | Нет | `3` | Максимальное кол-во результатов (1-20). |

**Формат ответа (JSON):**
```json
[
  {
    "score": 0.89,
    "title": "BioBERT: a pre-trained biomedical language representation model...",
    "arxiv_id": "1901.08746",
    "text": "We introduce BioBERT, a domain-specific language representation model...",
    "file_path": "data/arxiv_papers/BioBERT_2019.pdf",
    "date": "2019-01-24",
    "categories": ["cs.CL", "cs.LG"],
    "_source_query_type": "translated"
  }
]
```

---

## 3. Поведение и логика

### Алгоритм поиска
Модуль реализует **Hybrid Search**:
1.  **Dense Retrieval**: Генерация эмбеддинга запроса (модель `qwen3_8b`).
2.  **Sparse Retrieval**: Вычисление разреженного вектора `BM25` (через fastembed).
3.  **Qdrant Query**: Выполнение гибридного поиска с порогом схожести `score_threshold=0.5`.
4.  **Deduplication**: Дедупликация результатов по `file_path`. Если для одной статьи найдено несколько чанков, выбирается чанк с наивысшим `score`.

### Поддерживаемые коллекции
| Коллекция | Назначение | Dim |
|:---|:---|:---|
| `collection_normal_chunks` | Основной семантический поиск (512-1024 токенов). | 4096 |
| `collection_big_chunks` | Поиск с расширенным контекстом (1024-2048 токенов). | 4096 |
| `collection_summary_chunks` | Поиск по метаданным (Заголовок + Аннотация). | 4096 |
| `collection_llm_summary` | Поиск по сгенерированным LLM саммари статей. | 4096 |
| `collection_questions` | Поиск по синтетическим вопросам (Question-Answering). | 4096 |

---

## 4. Обработка ошибок

### Retry Policy (Exponential Backoff)

При ошибках эмбеддинга или временной недоступности Qdrant используется стратегия повторных попыток с экспоненциальной задержкой:

| Попытка | Задержка | Описание |
|:---:|:---:|:---|
| 1 | 1 сек | Первая повторная попытка |
| 2 | 2 сек | Вторая повторная попытка |
| 3 | 4 сек | Третья повторная попытка |

- **Максимум попыток:** 3 (настраивается через `MAX_RETRIES`)
- **Алгоритм:** `wait = 2 ** attempt` (1, 2, 4 секунды)
- **Применимо к:** Ошибкам эмбеддинга (`EMBEDDING_FAILED`) и сетевым таймаутам

**Пример кода:**
```python
def search_with_backoff(self, query: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return self.search(query)
        except Exception as e:
            wait = 2 ** attempt
            print(f"Attempt {attempt + 1} failed, retrying in {wait}s")
            time.sleep(wait)
    raise Exception("Max retries exceeded")
```


### Коды ответов
| Ошибка | Причина | Стратегия |
|:---|:---|:---|
| `DATABASE_UNAVAILABLE` | Qdrant недоступен | Возврат пустого списка + Log Error. |
| `TIMEOUT` | Запрос > 5 секунд | Прерывание операции + Log Warning. |
| `INVALID_COLLECTION` | Ошибка в имени коллекции | Fallback на `normal_chunks`. |
| `EMBEDDING_FAILED` | Ошибка API эмбеддингов | Retry (3 раза) с экспоненциальной задержкой. |



---

## 5. Конфигурация

Система настраивается через переменные окружения (`.env`):

```bash
# Подключение
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=xxxxxxxxxxxx

# Параметры моделей
EMBEDDING_MODEL=qwen/qwen3-embedding-8b
SPARSE_MODEL=Qdrant/bm25

# Лимиты
TIMEOUT_SECONDS=5
MAX_RETRIES=3
RETRY_BACKOFF_BASE=2 
```

---

## 6. Тестирование

### Модульные тесты (на pytest)
*   `test_search_normal_chunks`: Проверка базовой выдачи и структуры словаря.
*   `test_search_invalid_collection`: Валидация обработки некорректных входных данных.
*   `test_deduplication`: Проверка того, что в `limit` попадают уникальные статьи.

### Интеграционные тесты
Проверка доступности MCP-сервера через curl:
```bash
curl -X POST http://localhost:8002/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"search_scientific_papers","arguments":{"query":"BERT"}}}'
```

---

## 7. Мониторинг и логирование

### Структура JSON-лога
```json
{
  "timestamp": "2026-03-25T10:00:00.123Z",
  "level": "INFO",
  "service": "mcp_retriever",
  "trace_id": "lf_12345",
  "operation": "search",
  "collection": "collection_normal_chunks",
  "duration_ms": 450,
  "results_count": 3
}
```

### Метрики (Prometheus)
*   `mcp_search_requests_total`: Общее кол-во запросов.
*   `mcp_search_errors_total`: Кол-во ошибок по типам.
*   `mcp_search_duration_seconds`: Гистограмма времени выполнения поиска.

---
**SciVerify Project** | *Retriever Module v1.0*
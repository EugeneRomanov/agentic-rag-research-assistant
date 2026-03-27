# 🔭 Observability Specification | SciVerify

Данная спецификация описывает систему мониторинга, трассировки и логирования проекта **SciVerify**. Система построена на базе **LangFuse** для LLM-трассировки и стандартного JSON-логирования для системных событий.

---

## 1. LangFuse Integration

### Trace Structure
Каждый запрос пользователя создает отдельный трейс в LangFuse.

| Поле | Значение |
|:---|:---|
| **Trace Name** | `SciVerify Query` |
| **Trace ID** | Уникальный идентификатор (UUID), генерируется автоматически |
| **Input** | `{"query": "вопрос пользователя"}` |
| **Output** | `{"answer": "ответ агента"}` |

### Spans
Каждый узел графа (LangGraph) логируется как отдельный span:

| Span | Описание | Входные данные | Выходные данные |
|:---|:---|:---|:---|
| **Safeguard** | Проверка научности запроса | `user_query` | `is_scientific: bool` |
| **Translator** | Анализ и генерация поискового запроса | `user_query` | `processed_query`, `main_entity` |
| **Retrieval** | Поиск в Qdrant через MCP | `processed_query` | `retrieved_context`, `sources` |
| **Generate** | Генерация ответа с цитированием | `context + query` | `answer` |
| **Critic** | Проверка ответа на галлюцинации | `answer + context` | `criticism: APPROVED/REFETCH` |

### Пример трейса в LangFuse
```json
{
  "id": "1db3f001-7709-4b64-a0ff-cb19c6adc465",
  "name": "SciVerify Query",
  "input": {"query": "Что такое BERT?"},
  "output": {"answer": "BERT - это двунаправленный Transformer..."},
  "metadata": {
    "user_id": "test_user",
    "session_id": "session_123"
  },
  "spans": [
    {"name": "safeguard", "duration_ms": 234},
    {"name": "translator", "duration_ms": 456},
    {"name": "retrieval", "duration_ms": 1234},
    {"name": "generate", "duration_ms": 2345},
    {"name": "critic", "duration_ms": 567}
  ]
}
```

---

## 2. Метрики

### Основные показатели (SLI/SLO)
| Метрика | Способ сбора | Целевое значение | Действие при нарушении |
|:---|:---|:---|:---|
| **Success Rate** | LangFuse traces с output | > 95% | Алерт в Slack |
| **Response Time (p95)** | Span duration всех узлов | < 30 сек | Алерт в Slack |
| **Hallucination Rate** | Critic REFETCH / total | < 5% | Анализ качества промптов |
| **Token Usage** | OpenRouter response | Мониторинг | Алерт при превышении бюджета |

### Детальные метрики
| Метрика | Описание | Формула |
|:---|:---|:---|
| **Retrieval Recall** | Релевантность выдачи | % запросов с >0 результатами |
| **Retry Rate** | Частота повторных попыток | `REFETCH` / `total_requests` |
| **Avg Tokens/Req** | Среднее потребление токенов | `total_tokens` / `requests` |

---

## 3. Логирование

### Уровни логирования
*   **INFO**: Нормальное выполнение узлов (Пример: `Found 9 unique articles`)
*   **WARNING**: Повторные попытки (Retry), частичные ошибки (Пример: `Attempt 2 failed, retrying...`)
*   **ERROR**: Ошибки API, критические сбои (Пример: `MCP connection failed`)

### Формат логов (JSON)
```json
{
  "timestamp": "2026-03-27T10:00:00.123Z",
  "level": "INFO",
  "service": "orchestrator",
  "trace_id": "1db3f001-7709-4b64-a0ff-cb19c6adc465",
  "node": "retrieval",
  "event": "search_completed",
  "duration_ms": 1234,
  "details": {
    "collections_searched": 5,
    "results_count": 9,
    "unique_articles": 3
  }
}
```

**Лог ошибки:**
```json
{
  "timestamp": "2026-03-27T10:00:00.123Z",
  "level": "ERROR",
  "service": "mcp_server",
  "trace_id": "1db3f001-7709-4b64-a0ff-cb19c6adc465",
  "node": "retrieval",
  "event": "search_failed",
  "error": "Connection timeout",
  "collection": "collection_normal_chunks"
}
```

---

## 4. Алертинг

| Приоритет | Условие | Канал | Реакция |
|:---|:---|:---|:---|
| **P0 (Critical)** | Error rate > 10% (5 мин) | Telegram/Slack | Немедленная проверка API/Qdrant |
| **P0 (Critical)** | Response time > 60 сек (5 мин) | Telegram/Slack | Проверка сетевых задержек |
| **P1 (Warning)** | Hallucination rate > 10% (1 ч) | Slack | Анализ качества ответов/промптов |
| **P1 (Warning)** | Token usage > $10/день | Slack | Проверка лимитов бюджета |
| **P2 (Info)** | Ежедневная статистика | Email | Анализ отчета за сутки |

---

## 5. Dashboard (LangFuse)

**URL:** [https://cloud.langfuse.com](https://cloud.langfuse.com)

**Основные разделы:**
*   **Traces**: Список всех входящих запросов и их детальный путь.
*   **Scores**: Оценки качества (включая результаты работы Critic).
*   **Sessions**: Группировка запросов по сессиям пользователей.
*   **Users**: Аналитика активности пользователей.

**Виджеты на главном экране:**
1.  **Request Volume**: Динамика количества запросов.
2.  **Success Rate**: Процент успешных выполнений.
3.  **Latency Distribution**: Распределение времени ответа по перцентилям.
4.  **Token Usage**: Расход токенов в разрезе моделей.
5.  **Hallucination Rate**: Частота срабатывания `REFETCH`.

---

## 6. Хранение данных (Retention)

| Тип данных | Хранилище | Срок хранения |
|:---|:---|:---|
| **LangFuse Traces** | LangFuse Cloud | 30 дней |
| **Системные логи** | Docker Logs / ELK | 14 дней |
| **Метрики** | LangFuse / Prometheus | 30 дней |

---

## 7. Доступ и права

| Роль | Доступ | Права |
|:---|:---|:---|
| **Разработчик** | LangFuse Dashboard | Просмотр трейсов, анализ сессий |
| **Администратор** | LangFuse + Серверные логи | Полный доступ, управление алертами |
| **Внешний пользователь** | — | Нет доступа |
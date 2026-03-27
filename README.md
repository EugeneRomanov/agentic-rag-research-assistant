# 🔬 SciVerify Agent: Autonomous Research Assistant

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**SciVerify Agent** — это продвинутая RAG-система с агентной верификацией для глубокого анализа научных публикаций из базы arXiv. Система использует архитектуру LangGraph для циклической обработки запросов и MCP (Model Context Protocol) для изолированного поиска.

---

## 📕 О проекте

### Задача
Автоматизация поиска и критического анализа научных данных с жесткой привязкой к первоисточникам.

### Проблема (The Pain)
LLM часто галлюцинируют, искажая цифры, формулы и методологии научных работ. **SciVerify** минимизирует этот риск через многоэтапную проверку (Critic) и обязательное цитирование конкретных чанков данных.

### Для кого
- **Исследователи и ученые:** быстрый обзор состояния области (State-of-the-art).
- **Студенты:** поиск ответов в проверенных публикациях.
- **ML-инженеры:** извлечение архитектурных подробностей нейросетей.

---

## ⚙️ Технологический стек

| Компонент | Технология |
|:--- |:--- |
| **Оркестрация** | LangGraph (Циклические графы) |
| **LLM** | Gemini 2.0 Flash (via OpenRouter) |
| **База знаний** | Qdrant Cloud (Vector DB) |
| **Поиск** | MCP Server (FastMCP) |
| **Эмбеддинги** | BAAI/bge-small-en-v1.5 |
| **Мониторинг** | LangFuse (Tracing & Observability) |
| **Парсинг PDF** | PyMuPDF (Markdown conversion) |

---

## ✅ Функциональные возможности PoC

1.  **Интеллектуальный поиск:** Анализирует запрос и переводит его на английский (если нужно) для лучшего поиска по arXiv.
2.  **RAG-цикл:** `Translator` → `Retrieval` → `Generate` → `Critic` → `Router`.
3.  **Верификация (Critic):** Отдельный агент проверяет ответ на наличие галлюцинаций и соответствие найденным источникам.
4.  **Самокоррекция:** Если данных недостаточно, агент автоматически расширяет поисковый запрос и пробует снова.
5.  **Цитирование:** Строгая привязка утверждений к источникам в формате `[1], [2]`.
6.  **Трейсинг:** Визуализация каждого шага размышления агента в LangFuse.

### ❌ Out-of-scope (Что не реализовано)
- Многопользовательский чат и авторизация.
- Стриминг ответов (потоковая выдача текста).
- Полнотекстовый поиск (используется только семантический векторный).

---

## 🚀 Реализованные этапы

| Возможность | Статус | Описание |
|:--- |:---:|:--- |
| **Safeguard** | ✅ | Фильтрация нецелевых запросов |
| **Agentic RAG** | ✅ | Полный цикл обработки в LangGraph |
| **Цитирование** | ✅ | Ответы с кликабельными ссылками на arXiv |
| **LangFuse Tracking** | ✅ | Полная трассировка узлов графа |
| **Multi-Index Retrieval** | 🔄 | Поддержка нескольких коллекций (в работе) |
| **HyDE / Debate** | 📋 | В планах на следующие релизы |

---

## 🛠 Установка и запуск

### Требования
- Python 3.11+
- Аккаунты: OpenRouter, Qdrant Cloud, LangFuse.

### 1. Клонирование и установка
```bash
git clone https://github.com/your-repo/sciverify-agent.git
cd sciverify-agent
pip install -r requirements.txt
```

### 2. Настройка окружения
Создайте файл `.env` на основе примера:
```env
OPENROUTER_API_KEY=sk-or-your-key
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-api-key
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 3. Подготовка данных и запуск
1. **Индексация** (загрузка 100+ статей в Qdrant):
   ```bash
   python scripts/ingest.py
   ```
2. **Запуск MCP сервера** (отдельное окно терминала):
   ```bash
   python -m mcp_server.server
   ```
3. **Запуск основного агента**:
   ```bash
   python main.py
   ```

---

## 📂 Структура проекта

```text
├── app/                   # Логика LangGraph агента
│   ├── graph.py           # Определение узлов и переходов графа
│   ├── state.py           # Описание состояния (State) агента
│   └── api.py             # Интерфейс (FastAPI/CLI)
├── mcp_server/            # Model Context Protocol сервер
│   ├── server.py          # FastMCP реализация
│   └── retriever.py       # Логика поиска в Qdrant
├── scripts/               # Служебные скрипты
│   └── ingest.py          # Парсинг и эмбеддинг PDF в облако
├── docs/                  # Проектная документация
│   ├── system-design.md   # Архитектура системы
│   └── diagrams/          # Схемы LangGraph
├── data/                  # Локальные копии статей (для ingest)
├── main.py                # Точка входа
└── requirements.txt
```

---

## 💬 Пример работы

**Запрос:** *«Какие основные архитектурные особенности у модели BERT?»*

**Ответ агента:**
> 🤖 **Agent:** BERT (Bidirectional Encoder Representations from Transformers) базируется на многослойном двунаправленном Transformer-кодировщике [1]. В отличие от классических моделей, BERT обучается на задачах Masked Language Modeling (MLM) и Next Sentence Prediction (NSP) [1][2].
> 
> **Источники:**
> [1] [arXiv:1810.04805](https://arxiv.org/abs/1810.04805) - Devlin et al., "BERT: Pre-training of Deep Bidirectional Transformers..."
> [2] [arXiv:1901.07291](https://arxiv.org/abs/1901.07291) - "Linguistics in BERT..."

---

## 📚 Дополнительная документация

Для более глубокого изучения проекта обратитесь к разделу `/docs`:
- [System Design](./docs/system-design.md) — подробное описание логики графа.
- [Product Proposal](./docs/product-proposal.md) — бизнес-цели и риски.
- [Governance](./docs/governance.md) — этика и правила работы с данными.

"""LangGraph агент с интеграцией MCP сервера и цитированием"""

import os
import json
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from fastmcp import Client

from app.state import AgentState

load_dotenv()

# Конфигурация
MCP_SERVER_URL = "http://localhost:8002/mcp"
COLLECTIONS = [
    "collection_normal_chunks",
    "collection_big_chunks", 
    "collection_summary_chunks",
    "collection_llm_summary_chunks",
    "collection_questions_chunks"
]

# LLM модели
llm = ChatOpenAI(
    model="google/gemini-2.0-flash-001",
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base=os.getenv("OPENAI_API_BASE"),
    temperature=0.3
)


async def call_mcp_search(query: str, collection: str, limit: int = 10) -> List[Dict]:
    """Асинхронный вызов MCP сервера для поиска"""
    try:
        async with Client(MCP_SERVER_URL) as client:
            result = await client.call_tool(
                name="search_scientific_papers",
                arguments={
                    "query": query,
                    "collection_mode": collection,
                    "limit": limit
                }
            )
            
            if result and result.content:
                return json.loads(result.content[0].text)
            return []
    except Exception as e:
        print(f"   ⚠️ MCP error ({collection}): {e}")
        return []


async def search_all_collections(query: str, limit_per_collection: int = 5) -> List[Dict]:
    """Поиск по всем коллекциям"""
    all_results = []
    
    for collection in COLLECTIONS:
        print(f"   🔍 Поиск в {collection}...")
        results = await call_mcp_search(query, collection, limit_per_collection)
        all_results.extend(results)
    
    return all_results


def deduplicate_results(results: List[Dict]) -> List[Dict]:
    """Дедупликация результатов по arxiv_id"""
    seen = {}
    for item in results:
        arxiv_id = item.get("arxiv_id", "")
        if arxiv_id not in seen or item.get("score", 0) > seen[arxiv_id].get("score", 0):
            seen[arxiv_id] = item
    
    return sorted(seen.values(), key=lambda x: x.get("score", 0), reverse=True)


def format_context_with_citations(results: List[Dict]) -> tuple[str, List[Dict]]:
    """Форматирует контекст с добавлением ссылок на источники
    
    Returns:
        (formatted_context, sources_list)
    """
    citations = []
    formatted_chunks = []
    
    for i, item in enumerate(results[:3]):  # Берем топ-3
        arxiv_id = item.get("arxiv_id", "Unknown")
        text = item.get("text", "")
        score = item.get("score", 0)
        
        # Создаем ссылку
        citation_id = i + 1
        citations.append({
            "id": citation_id,
            "arxiv_id": arxiv_id,
            "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id != "Unknown" else None
        })
        
        # Форматируем чанк с указанием источника
        formatted_chunk = f"[{citation_id}] {text}"
        formatted_chunks.append(formatted_chunk)
    
    formatted_context = "\n\n---\n\n".join(formatted_chunks)
    return formatted_context, citations


# ========== УЗЛЫ ==========

def safeguard_node(state: AgentState):
    """Проверка запроса на научность"""
    print("\n🛡️ [Safeguard] Проверка запроса...")
    last_query = state["messages"][-1].content
    
    prompt = f"Is this a scientific/technical question? Answer YES or NO. Query: {last_query}"
    res = llm.invoke([HumanMessage(content=prompt)])
    
    is_scientific = "YES" in res.content.upper()
    print(f"   Результат: {'✅ научный' if is_scientific else '❌ не научный'}")
    
    return {"is_scientific": is_scientific}


def translator_node(state: AgentState):
    """Анализ темы и генерация поискового запроса"""
    if not state.get("is_scientific"):
        return {"processed_query": "", "main_entity": ""}
    
    print("🌐 [Translator] Анализирую тему и ключевые слова...")
    user_query = state["messages"][-1].content
    
    is_retry = state.get("revision_number", 0) > 0
    instruction = "Create a specific search query." if not is_retry else "Create a DIFFERENT broader search query."
    
    prompt = (
        f"Instructions: {instruction} Output JSON with 'query' and 'entity'.\n"
        f"User question: {user_query}"
    )
    
    res = llm.invoke([HumanMessage(content=prompt)])
    
    try:
        clean_res = res.content.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_res)
        processed_query = data['query']
        main_entity = data['entity']
        print(f"   Запрос: {processed_query}")
        print(f"   Сущность: {main_entity}")
        return {"processed_query": processed_query, "main_entity": main_entity}
    except:
        print(f"   Запрос: {res.content.strip()}")
        return {"processed_query": res.content.strip(), "main_entity": ""}


# В retrieval_node убираем цикл по коллекциям
async def retrieval_node(state: AgentState):
    """Поиск по одной коллекции"""
    if not state.get("is_scientific"):
        return {"retrieved_context": [], "sources": []}
    
    query = state.get("processed_query")
    entity = state.get("main_entity", "")
    print(f"🔍 [Retrieval] Поиск по теме: {entity if entity else query}")
    
    try:
        # Поиск в одной коллекции
        async with Client(MCP_SERVER_URL) as client:
            result = await client.call_tool(
                name="search_scientific_papers",
                arguments={"query": query, "limit": 10}
            )
            
            if result and result.content:
                all_results = json.loads(result.content[0].text)
            else:
                all_results = []
        
        if not all_results:
            print("   ❌ Ничего не найдено")
            return {"retrieved_context": [], "sources": []}
        
        # Дедупликация и форматирование
        unique_results = deduplicate_results(all_results)
        
        # Форматируем с цитированием
        formatted_context, sources = format_context_with_citations(unique_results)
        
        print(f"   ✅ Найдено {len(unique_results)} уникальных статей")
        return {"retrieved_context": [formatted_context], "sources": sources}
        
    except Exception as e:
        print(f"❌ Ошибка Qdrant: {e}")
    # Логируем в текущий трейс
    try:
        from langfuse import get_current_span
        span = get_current_span()
        span.update(level="ERROR", status_message=str(e))
    except:
        pass
    return {"retrieved_context": []}


def generate_node(state: AgentState):
    """Генерация ответа с цитированием"""
    print(f"✍️ [Generate] Формирую ответ (Попытка #{state.get('revision_number', 0) + 1})...")
    
    context_list = state.get("retrieved_context", [])
    context = context_list[0] if context_list else ""
    user_query = state["messages"][-1].content
    sources = state.get("sources", [])
    
    if not context.strip():
        return {"messages": [HumanMessage(content="I NEED MORE DATA")], "revision_number": state.get("revision_number", 0) + 1}
    
    # Формируем список источников для промпта
    sources_text = "\n".join([f"[{s['id']}] arXiv:{s['arxiv_id']} - {s['url']}" for s in sources])
    
    prompt = f"""You are a Research Assistant. Answer based ONLY on the context below.

Guidelines:
- If context is insufficient, say "I NEED MORE DATA"
- Provide detailed, comprehensive answers
- Include key facts: what, why, how, results, metrics
- Structure the answer clearly with paragraphs
- **CITE YOUR SOURCES** using [1], [2], etc. in the text
- At the end, add a "**Источники:**" section with full references
- Answer in Russian

CONTEXT (with citations):
{context}

SOURCES:
{sources_text}

QUESTION: {user_query}

ANSWER:"""
    
    try:
        res = llm.invoke([HumanMessage(content=prompt)])
        return {"messages": [res], "revision_number": state.get("revision_number", 0) + 1}
    except Exception as e:
        print(f"❌ LLM ошибка: {e}")
        # Логируем в трейс
        try:
            from langfuse import get_current_span
            span = get_current_span()
            span.update(level="ERROR", status_message=str(e))
        except:
            pass
        # Возвращаем fallback ответ
        fallback_message = HumanMessage(
            content="Сервис временно недоступен. Пожалуйста, попробуйте позже."
        )
        return {"messages": [fallback_message], "revision_number": state.get("revision_number", 0) + 1}


def critic_node(state: AgentState):
    """Проверка ответа на галлюцинации и полноту"""
    print("🧐 [Critic] Проверка ответа...")
    answer = state["messages"][-1].content
    
    # Если генератор сам признал, что данных нет
    if "I NEED MORE DATA" in answer.upper():
        print("   -> Требуется повторный поиск")
        return {"criticism": "REFETCH"}
    
    context_list = state.get("retrieved_context", [])
    context = context_list[0] if context_list else ""
    sources = state.get("sources", [])
    
    sources_text = "\n".join([f"[{s['id']}] arXiv:{s['arxiv_id']}" for s in sources])
    
    prompt = f"""Evaluate the answer against the context and sources.

Context:
{context}

Sources used:
{sources_text}

Answer:
{answer}

Check:
1. Is the answer 100% grounded in the context? (no hallucinations)
2. Does the answer include citations [1], [2], etc.?
3. Does the answer include a "Источники:" section?
4. Does the answer include key facts from the context?

Output exactly one word:
- "APPROVED" if answer is grounded, properly cited, and comprehensive
- "REFETCH" if answer contains hallucinations OR misses important information OR lacks citations"""
    
    res = llm.invoke([HumanMessage(content=prompt)])
    decision = "REFETCH" if "REFETCH" in res.content.upper() else "APPROVED"
    
    print(f"   Решение: {decision}")
    return {"criticism": decision}


def router_logic(state: AgentState):
    """Логика маршрутизации после критика"""
    if state["criticism"] == "REFETCH" and state["revision_number"] < 2:
        print("🔄 [Router] Данных недостаточно. Возвращаюсь к Translator для нового запроса.")
        return "translator"
    
    print("🏁 [Router] Завершаю работу.")
    return END


# ========== СБОРКА ГРАФА ==========

def build_graph():
    """Сборка LangGraph графа"""
    
    workflow = StateGraph(AgentState)
    
    # Добавляем узлы
    workflow.add_node("safeguard", safeguard_node)
    workflow.add_node("translator", translator_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("critic", critic_node)
    
    # Связи
    workflow.add_edge(START, "safeguard")
    workflow.add_edge("safeguard", "translator")
    workflow.add_edge("translator", "retrieval")
    workflow.add_edge("retrieval", "generate")
    workflow.add_edge("generate", "critic")
    
    # Условный переход после критика
    workflow.add_conditional_edges("critic", router_logic, {
        "translator": "translator",
        END: END
    })
    
    return workflow.compile()


# Создаем экземпляр графа
app = build_graph()
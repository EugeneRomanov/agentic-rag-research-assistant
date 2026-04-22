"""Запуск агента с LangFuse трейсингом и метриками"""

import asyncio
import os
import time
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()

from langfuse import Langfuse

# Инициализация LangFuse
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)


async def run_agent(user_input: str):
    from app.graph import app
    
    # Засекаем время начала
    start_time = time.time()
    
    # Создаем трейс
    trace = langfuse.trace(
        name="SciVerify Query",
        input={"query": user_input}
    )
    trace_id = trace.id
    
    print(f"📊 Trace ID: {trace_id}")
    
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "revision_number": 0,
        "criticism": "",
        "sources": []
    }
    
    final_answer = ""
    criticism_result = ""
    
    try:
        async for event in app.astream(initial_state):
            for node_name, output in event.items():
                if node_name == "generate" and "messages" in output:
                    final_answer = output['messages'][-1].content
                    print(f"\n🤖 Agent: {final_answer}")
                elif node_name == "critic":
                    if "criticism" in output:
                        criticism_result = output['criticism']
                    print("🧐 Проверяю ответ...")
                elif node_name == "translator":
                    print("🌐 Анализирую запрос...")
                elif node_name == "retrieval":
                    print("🔍 Ищу в базе знаний...")
        
        # Вычисляем длительность
        duration_ms = (time.time() - start_time) * 1000
        
        # ========== ПУНКТ 2: МЕТРИКИ ==========
        # Успешность ответа (не содержит сообщение об ошибке)
        success = 1.0 if final_answer and "недоступен" not in final_answer.lower() else 0.0
        
        # Галлюцинации (Critic сказал REFETCH)
        hallucination = 1.0 if criticism_result == "REFETCH" else 0.0
        
        # Отправляем метрики в LangFuse
        langfuse.score(
            trace_id=trace_id,
            name="success",
            value=success
        )
        
        langfuse.score(
            trace_id=trace_id,
            name="hallucination",
            value=hallucination
        )
        
        langfuse.score(
            trace_id=trace_id,
            name="latency_ms",
            value=duration_ms
        )
        
        # Выводим метрики в консоль
        print(f"\n📊 Метрики:")
        print(f"   - Success: {success}")
        print(f"   - Hallucination: {hallucination}")
        print(f"   - Latency: {duration_ms:.0f} ms")
        
        # Обновляем трейс с результатом
        trace.update(output={"answer": final_answer})
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        trace.update(level="ERROR", status_message=str(e))
        
        # Отправляем метрику ошибки
        langfuse.score(
            trace_id=trace_id,
            name="success",
            value=0.0
        )
    
    finally:
        langfuse.flush()
    
    print(f"\n🔗 Trace ID: {trace_id}")
    print(f"   Смотрите в LangFuse Dashboard: https://cloud.langfuse.com")


def main():
    print("\n" + "="*50)
    print("🎓 SciVerify Agent with LangFuse")
    print("Введите 'exit' для выхода")
    print("="*50)
    
    # Проверка LangFuse
    try:
        if langfuse.auth_check():
            print("✅ LangFuse подключен")
    except Exception as e:
        print(f"⚠️ LangFuse: {e}")
    
    while True:
        user_input = input("\n❓ User: ")
        if user_input.lower() in ["exit", "quit", "выход"]:
            break
        
        asyncio.run(run_agent(user_input))


if __name__ == "__main__":
    main()
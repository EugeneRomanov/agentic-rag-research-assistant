"""Запуск агента с LangFuse трейсингом"""

import asyncio
import os
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
    
    # Создаем трейс
    trace = langfuse.trace(
        name="SciVerify Query",
        input={"query": user_input}
    )
    
    print(f"📊 Trace ID: {trace.id}")
    
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "revision_number": 0,
        "criticism": "",
        "sources": []
    }
    
    final_answer = ""
    
    try:
        async for event in app.astream(initial_state):
            for node_name, output in event.items():
                if node_name == "generate" and "messages" in output:
                    final_answer = output['messages'][-1].content
                    print(f"\n🤖 Agent: {final_answer}")
                elif node_name == "critic":
                    print("🧐 Проверяю ответ...")
                elif node_name == "translator":
                    print("🌐 Анализирую запрос...")
                elif node_name == "retrieval":
                    print("🔍 Ищу в базе знаний...")
        
        # Обновляем трейс с результатом
        trace.update(output={"answer": final_answer})
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        trace.update(level="ERROR", status_message=str(e))
    
    finally:
        langfuse.flush()
    
    print(f"\n🔗 Trace ID: {trace.id}")
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
"""FastAPI сервер для агента с A2A форматом ответа"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import asyncio
import uuid
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()

from langfuse import Langfuse
from app.graph import app

# Инициализация LangFuse
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)

api = FastAPI(title="SciVerify Agent API", version="1.0.0")


# ========== A2A Models ==========

class Citation(BaseModel):
    """Цитата источника"""
    source: str = Field(..., description="arXiv ID или другой идентификатор")
    url: str = Field(..., description="Ссылка на источник")
    text: Optional[str] = Field(None, description="Цитируемый фрагмент")


class A2AResponse(BaseModel):
    """Ответ в формате A2A (Agent-to-Agent)"""
    message_id: str = Field(..., description="Уникальный идентификатор сообщения")
    content: str = Field(..., description="Текст ответа")
    citations: List[Citation] = Field(default_factory=list, description="Список источников")
    confidence: float = Field(..., description="Уверенность в ответе (0-1)")
    metadata: dict = Field(default_factory=dict, description="Дополнительная информация")


class QuestionRequest(BaseModel):
    """Запрос к агенту"""
    question: str = Field(..., description="Вопрос пользователя")


# ========== Endpoints ==========

@api.get("/health")
async def health():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "service": "agent_api"}


@api.post("/ask", response_model=A2AResponse)
async def ask_question(request: QuestionRequest):
    """Отправить вопрос агенту (A2A формат)"""
    
    # Создаем трейс
    trace = langfuse.trace(
        name="SciVerify Query",
        input={"query": request.question}
    )
    trace_id = trace.id
    
    initial_state = {
        "messages": [HumanMessage(content=request.question)],
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
                elif node_name == "critic" and "criticism" in output:
                    criticism_result = output['criticism']
        
        trace.update(output={"answer": final_answer})
        
        # Вычисляем confidence на основе проверки Critic
        confidence = 0.95 if criticism_result != "REFETCH" else 0.7
        
        return A2AResponse(
            message_id=str(uuid.uuid4()),
            content=final_answer,
            citations=[],  # Здесь можно добавить источники из state
            confidence=confidence,
            metadata={
                "trace_id": trace_id,
                "model": "google/gemini-2.0-flash-001",
                "hallucination_check": criticism_result
            }
        )
        
    except Exception as e:
        trace.update(level="ERROR", status_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        langfuse.flush()


@api.get("/trace/{trace_id}")
async def get_trace(trace_id: str):
    """Получить информацию о трейсе"""
    return {"trace_id": trace_id, "url": f"https://cloud.langfuse.com/trace/{trace_id}"}
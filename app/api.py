"""FastAPI сервер для агента"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
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

api = FastAPI(title="SciVerify Agent API")


class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    answer: str
    trace_id: str


@api.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """Отправить вопрос агенту"""
    
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
    
    try:
        async for event in app.astream(initial_state):
            for node_name, output in event.items():
                if node_name == "generate" and "messages" in output:
                    final_answer = output['messages'][-1].content
        
        trace.update(output={"answer": final_answer})
        
    except Exception as e:
        trace.update(level="ERROR", status_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        langfuse.flush()
    
    return AnswerResponse(answer=final_answer, trace_id=trace_id)


@api.get("/health")
async def health():
    return {"status": "healthy"}
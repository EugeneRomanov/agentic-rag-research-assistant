from typing import Annotated, List, TypedDict, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    processed_query: str
    retrieved_context: List[str]
    is_scientific: bool
    criticism: str
    revision_number: int
    sources: List[Dict[str, Any]]  # Добавляем поле для хранения источников
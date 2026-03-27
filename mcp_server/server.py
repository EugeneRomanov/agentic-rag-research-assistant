"""MCP сервер для поиска научных статей"""

import logging
import json
from typing import List, Dict, Any

from fastmcp import FastMCP

from .config import COLLECTION_NAME, MCP_HOST, MCP_PORT
from .retriever import get_retriever

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

mcp = FastMCP("SciVerify Retriever")


@mcp.tool()
def search_scientific_papers(
    query: str,
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    Поиск научных статей в Qdrant.
    
    Args:
        query: Поисковый запрос (на английском)
        limit: Максимальное количество результатов (1-10)
    
    Returns:
        Список найденных статей с метаданными
    """
    logger.info(f"Search: query='{query[:50]}...', limit={limit}")
    
    limit = min(max(1, limit), 10)
    
    try:
        retriever = get_retriever()
        results = retriever.search(query, limit)
        logger.info(f"Found {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []


@mcp.tool()
def list_collections() -> List[str]:
    """Получить список доступных коллекций"""
    return [COLLECTION_NAME]


@mcp.tool()
def health_check() -> Dict[str, Any]:
    """Проверка состояния сервиса"""
    retriever = get_retriever()
    return retriever.health_check()


def main():
    logger.info(f"Starting MCP server on {MCP_HOST}:{MCP_PORT}")
    logger.info(f"Using collection: {COLLECTION_NAME}")
    
    retriever = get_retriever()
    health = retriever.health_check()
    
    if health["status"] == "healthy":
        logger.info("✅ All systems ready")
    else:
        logger.warning(f"⚠️ Health check warning: {health}")
    
    mcp.run(transport="http", host=MCP_HOST, port=MCP_PORT)


if __name__ == "__main__":
    main()
"""Логика поиска в Qdrant"""

import os
import json
import time
import logging
import requests
from typing import List, Dict, Any
from functools import lru_cache
from dotenv import load_dotenv
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from .config import (
    QDRANT_URL, QDRANT_API_KEY,
    EMBEDDING_MODEL, COLLECTION_NAME,
    DEFAULT_LIMIT, SCORE_THRESHOLD, TIMEOUT_SECONDS, MAX_RETRIES
)

load_dotenv()
logger = logging.getLogger(__name__)


def parse_node_content(payload: Dict) -> Dict:
    """Распарсить _node_content из формата LlamaIndex"""
    result = {
        "text": "",
        "title": "Unknown",
        "arxiv_id": payload.get("arxiv_id", "Unknown")
    }
    
    node_content = payload.get("_node_content")
    if node_content:
        try:
            node_data = json.loads(node_content) if isinstance(node_content, str) else node_content
            result["text"] = node_data.get("text", "")
            metadata = node_data.get("metadata", {})
            if metadata:
                result["title"] = metadata.get("title", result["arxiv_id"])
                result["arxiv_id"] = metadata.get("arxiv_id", result["arxiv_id"])
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse _node_content: {e}")
    
    return result


class QdrantRetriever:
    def __init__(self):
        self.embed_model = None
        self._init_clients()
    
    def _init_clients(self):
        """Инициализация эмбеддинг модели"""
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        self.embed_model = HuggingFaceEmbedding(model_name=EMBEDDING_MODEL)
        logger.info("✅ Embedding model loaded")
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """Получить вектор для запроса"""
        try:
            embedding = self.embed_model.get_query_embedding(query)
            return embedding
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise
    
    def _search_via_http(self, query_vector: List[float], limit: int) -> List[Dict]:
        """Поиск через HTTP API"""
        url = f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/search"
        
        payload = {
            "vector": query_vector,
            "limit": limit * 2,
            "with_payload": True,
            "score_threshold": SCORE_THRESHOLD
        }
        
        headers = {"Content-Type": "application/json"}
        if QDRANT_API_KEY:
            headers["api-key"] = QDRANT_API_KEY
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
            if response.status_code == 200:
                data = response.json()
                return data.get("result", [])
            else:
                logger.warning(f"HTTP search failed: {response.status_code}")
                return []
        except Exception as e:
            logger.warning(f"HTTP search error: {e}")
            return []
    
    def search(self, query: str, limit: int = 3) -> List[Dict]:
        """Основной метод поиска"""
        start_time = time.time()
        
        for attempt in range(MAX_RETRIES):
            try:
                vector = self._get_query_embedding(query)
                results = self._search_via_http(vector, limit)
                
                formatted = []
                for hit in results:
                    parsed = parse_node_content(hit.get("payload", {}))
                    formatted.append({
                        "score": hit.get("score", 0),
                        "title": parsed["title"],
                        "arxiv_id": parsed["arxiv_id"],
                        "text": parsed["text"][:500],
                        "file_path": "",
                        "date": "",
                        "categories": []
                    })
                
                # Дедупликация по arxiv_id
                seen = {}
                for item in formatted:
                    key = item["arxiv_id"]
                    if key not in seen or item["score"] > seen[key]["score"]:
                        seen[key] = item
                
                unique = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
                final_results = unique[:limit]
                
                duration = time.time() - start_time
                logger.info(f"Search: {len(final_results)} results, duration={duration:.2f}s")
                
                return final_results
                
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(1)
        
        return []
    
    def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья"""
        try:
            return {
                "status": "healthy",
                "collection": COLLECTION_NAME,
                "embedding_model": EMBEDDING_MODEL,
                "dimension": EMBEDDING_DIMENSION
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


_retriever = None

def get_retriever() -> QdrantRetriever:
    global _retriever
    if _retriever is None:
        _retriever = QdrantRetriever()
    return _retriever
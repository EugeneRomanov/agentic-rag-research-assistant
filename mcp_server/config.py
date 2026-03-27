"""Конфигурация MCP сервера"""

import os
from dotenv import load_dotenv

load_dotenv()

# Qdrant
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)

# Эмбеддинг модель
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSION = 384  # <--- ДОБАВИТЬ ЭТУ СТРОКУ

# Одна коллекция для поиска
COLLECTION_NAME = "collection_normal_chunks"

# Имя вектора в Qdrant
DENSE_VECTOR_NAME = "default"

# Параметры поиска
DEFAULT_LIMIT = 20
SCORE_THRESHOLD = 0.5
TIMEOUT_SECONDS = 5
MAX_RETRIES = 2

# Сервер
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "8002"))
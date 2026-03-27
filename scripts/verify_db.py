import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

load_dotenv()

# Те же настройки, что и при загрузке
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "collection_normal_chunks"

print("🔄 Инициализация модели поиска...")
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

def test_search(query_text):
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    # 1. Превращаем вопрос в вектор
    query_vector = embed_model.get_query_embedding(query_text)
    
    # 2. Ищем в Qdrant
    print(f"🔍 Ищу в облаке: '{query_text}'")
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=2
    )
    
    if not results:
        print("❌ Ничего не найдено. Проверь коллекцию в Dashboard.")
        return

    for i, res in enumerate(results):
        print(f"\n--- Результат #{i+1} (Score: {res.score:.4f}) ---")
        print(f"Статья ID: {res.payload.get('arxiv_id')}")
        # Печатаем первые 200 символов текста
        text_snippet = res.payload.get('text', 'Текст отсутствует')[:200]
        print(f"Текст: {text_snippet}...")

if __name__ == "__main__":
    # Попробуем найти что-то про DeepSeek (она была в твоем списке)
    test_search("What is DeepSeek-V3 architecture?")
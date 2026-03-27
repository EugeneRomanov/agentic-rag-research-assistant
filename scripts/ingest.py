import os
import re
import arxiv
import ssl
import fitz
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Отключаем SSL проверку
ssl._create_default_https_context = ssl._create_unverified_context

load_dotenv()

INPUT_FILE = "data/papers_list.txt"
SAVE_FOLDER = "data/arxiv_papers"
COLLECTION_NAME = "collection_normal_chunks"
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

print("🔄 Загружаю модель эмбеддингов...")
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5", device="cpu")

def extract_arxiv_ids(file_path):
    if not os.path.exists(file_path): return []
    with open(file_path, "r") as f:
        content = f.read()
    return re.findall(r"(\d{4}\.\d{4,5})", content)

def connect_to_qdrant():
    print(f"🔌 Подключаюсь к Qdrant...")
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    try:
        client.get_collections()
        return client
    except Exception as e:
        print(f"❌ Ошибка Qdrant: {e}")
        return None

def parse_pdf(file_path):
    """Парсинг PDF"""
    try:
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
        return text
    except Exception as e:
        print(f"   ❌ Ошибка парсинга: {e}")
        return None

def main():
    ids = extract_arxiv_ids(INPUT_FILE)
    print(f"📚 Найдено статей: {len(ids)}")
    
    q_client = connect_to_qdrant()
    if not q_client: return

    if not q_client.collection_exists(COLLECTION_NAME):
        q_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
        )

    vector_store = QdrantVectorStore(client=q_client, collection_name=COLLECTION_NAME)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    for paper_id in ids:
        print(f"\n--- 📄 Обработка {paper_id} ---")
        file_path = os.path.join(SAVE_FOLDER, f"{paper_id}.pdf")
        os.makedirs(SAVE_FOLDER, exist_ok=True)

        # Скачиваем если нет
        if not os.path.exists(file_path):
            print("📥 Скачиваю...")
            try:
                search = arxiv.Search(id_list=[paper_id])
                client = arxiv.Client()
                paper = next(client.results(search))
                paper.download_pdf(dirpath=SAVE_FOLDER, filename=f"{paper_id}.pdf")
                print("   ✅ Скачано")
            except Exception as e:
                print(f"   ❌ Ошибка скачивания: {e}")
                continue
        
        # Проверяем, что файл существует
        if not os.path.exists(file_path):
            print(f"   ❌ Файл не найден")
            continue
        
        # Парсим PDF
        print("⚡ Парсинг PDF...")
        full_text = parse_pdf(file_path)
        
        if not full_text or len(full_text) < 100:
            print(f"   ⚠️ Текст слишком короткий ({len(full_text) if full_text else 0} символов)")
            continue
        
        print(f"   ✅ Текст получен: {len(full_text)} символов")
        
        # Создаем документ
        doc = Document(text=full_text, metadata={"arxiv_id": paper_id})
        
        # Чанкинг
        splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=100)
        nodes = splitter.get_nodes_from_documents([doc])
        
        print(f"📤 Загружаю {len(nodes)} чанков в Qdrant...")
        VectorStoreIndex(nodes, storage_context=storage_context, embed_model=embed_model)
        print(f"✅ Готово!")

    print("\n🏁 МИССИЯ ВЫПОЛНЕНА!")

if __name__ == "__main__":
    main()
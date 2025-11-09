import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from zht_sparse_embed import ZHTSparseEmbed
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

# 環境變數
api_key = os.getenv("GENAI_EMBEDDING_API_KEY")
qdrant_url = os.getenv("QDRANT_CLIENT", "http://localhost:6333")
collection_name = os.getenv("COLLECTION_NAME")

# 建立 Qdrant 客戶端 (物件而非字串)
client = QdrantClient(url=qdrant_url)

# 嵌入模型
dense_embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
    google_api_key=api_key,
)
sparse_embeddings = ZHTSparseEmbed()

# Qdrant 向量存儲
qdrant_hybrid_vector_store = QdrantVectorStore(
    client=client,
    collection_name=collection_name,
    embedding=dense_embeddings,
    sparse_embedding=sparse_embeddings,
    retrieval_mode=RetrievalMode.HYBRID,
    vector_name="dense",
    sparse_vector_name="bm25",
)


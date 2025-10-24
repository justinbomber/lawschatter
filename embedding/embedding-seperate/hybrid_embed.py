import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from zht_sparse_embed import ZHTSparseEmbed
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GENAI_EMBEDDING_API_KEY")
qdrant_url = os.getenv("QDRANT_SERVER")
collection_name = os.getenv("COLLECTION_NAME")

_vector_store_instance = None

def get_qdrant_hybrid_vector_store():
    global _vector_store_instance
    
    if _vector_store_instance is None:
        client = QdrantClient(url="http://localhost:6333/")
        # client = QdrantClient(
        #     url=qdrant_url,
        #     timeout=120.0
        # )
        embeddings = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001",
            google_api_key=api_key,
        )
        sparse_embeddings = ZHTSparseEmbed()
        
        _vector_store_instance = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings,
            sparse_embedding=sparse_embeddings,
            retrieval_mode=RetrievalMode.HYBRID,
            vector_name="dense",
            sparse_vector_name="bm25",
        )
    
    return _vector_store_instance

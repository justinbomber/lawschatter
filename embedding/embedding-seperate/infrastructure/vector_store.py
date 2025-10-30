import logging
import requests
from typing import List
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient
from ..domain import VectorStore, EmbeddingDocument
from .sparse_embedding import ZHTSparseEmbed

logger = logging.getLogger(__name__)


class QdrantHybridVectorStore(VectorStore):
    
    def __init__(
        self,
        qdrant_url: str,
        collection_name: str,
        embedding_api_key: str,
        stopwords_path: str = "zh-t.txt",
        dict_path: str = "dict.txt.big",
        embedding_model: str = "gemini-embedding-001",
    ):
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        
        logger.info(f"初始化 Qdrant 客戶端: {qdrant_url}")
        self.client = QdrantClient(url=qdrant_url, timeout=120.0)
        
        logger.info(f"初始化 Google Generative AI Embeddings: {embedding_model}")
        self.dense_embeddings = GoogleGenerativeAIEmbeddings(
            model=embedding_model,
            google_api_key=embedding_api_key,
        )
        
        logger.info("初始化中文稀疏嵌入")
        self.sparse_embeddings = ZHTSparseEmbed(
            stopwords_path=stopwords_path,
            dict_path=dict_path
        )
        
        logger.info(f"建立 Qdrant 向量儲存: {collection_name}")
        self.store = QdrantVectorStore(
            client=self.client,
            collection_name=collection_name,
            embedding=self.dense_embeddings,
            sparse_embedding=self.sparse_embeddings,
            retrieval_mode=RetrievalMode.HYBRID,
            vector_name="dense",
            sparse_vector_name="bm25",
        )
    
    def get_collection_count(self) -> int:
        collection_url = f"{self.qdrant_url}/collections/{self.collection_name}"
        response = requests.get(collection_url)
        count = response.json()["result"]["points_count"]
        logger.info(f"目前集合點數: {count}")
        return count
    
    def add_documents(self, documents: List[EmbeddingDocument]) -> None:
        logger.info(f"準備加入 {len(documents)} 個文件到 Qdrant")
        
        langchain_docs = []
        ids = []
        
        for doc in documents:
            langchain_doc = Document(
                page_content=doc.content,
                metadata=doc.metadata
            )
            langchain_docs.append(langchain_doc)
            ids.append(doc.document_id)
        
        self.store.add_documents(documents=langchain_docs, ids=ids)
        logger.info(f"成功加入 {len(documents)} 個文件")


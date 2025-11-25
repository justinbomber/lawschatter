import logging
import requests
from typing import List
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient, models
from ..domain import VectorStore, EmbeddingDocument, JudgmentSearchDocument
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
    
    def upsert_judgment(self, document: JudgmentSearchDocument) -> None:
        logger.info(f"準備 upsert 判決 {document.judgment_id} 到 V2 collection")
        
        dense_vector = self.dense_embeddings.embed_query(document.summary_content)
        sparse_vector = self.sparse_embeddings.embed_query(document.summary_content)
        
        point = models.PointStruct(
            id=document.judgment_id,
            vector={
                "summary_dense": dense_vector,
                "summary_sparse": models.SparseVector(
                    indices=sparse_vector.indices,
                    values=sparse_vector.values
                )
            },
            payload=document.to_payload()
        )
        
        v2_collection = f"{self.collection_name}_v2"
        self.client.upsert(
            collection_name=v2_collection,
            points=[point]
        )
        
        logger.info(f"成功 upsert 判決 {document.judgment_id}")
    
    def create_v2_collection(self) -> None:
        v2_collection = f"{self.collection_name}_v2"
        
        logger.info(f"建立 V2 collection: {v2_collection}")
        
        collections = self.client.get_collections().collections
        if any(col.name == v2_collection for col in collections):
            logger.info(f"Collection {v2_collection} 已存在")
            return
        
        self.client.create_collection(
            collection_name=v2_collection,
            vectors_config={
                "summary_dense": models.VectorParams(
                    size=768,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={
                "summary_sparse": models.SparseVectorParams()
            }
        )
        
        logger.info("建立 Payload 索引")
        
        self.client.create_payload_index(
            collection_name=v2_collection,
            field_name="jid",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        
        self.client.create_payload_index(
            collection_name=v2_collection,
            field_name="has_guilt",
            field_schema=models.PayloadSchemaType.BOOL,
        )
        
        self.client.create_payload_index(
            collection_name=v2_collection,
            field_name="used_messaging_app",
            field_schema=models.PayloadSchemaType.BOOL,
        )
        
        self.client.create_payload_index(
            collection_name=v2_collection,
            field_name="has_recidivism",
            field_schema=models.PayloadSchemaType.BOOL,
        )
        
        logger.info(f"成功建立 V2 collection: {v2_collection}")


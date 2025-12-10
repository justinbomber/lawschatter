import logging
import requests
from typing import List, Dict, Optional
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    VectorParams,
    Distance,
    SparseVectorParams,
    SparseIndexParams,
    SparseVector,
)
from ..domain import VectorStore, EmbeddingDocument
from .sparse_embedding import ZHTSparseEmbed

logger = logging.getLogger(__name__)


class QdrantHybridVectorStore(VectorStore):
    
    UNKNOWN_CONTENT_VALUE = "未知"
    MAX_EMBEDDING_CHARS = 8000
    
    # TODO: 增加欄位
    JUDGMENT_VECTOR_NAMES = [
        "role",
        "A_fact",
        "B_claim",
        "C_court_finding",
        "D_court_reason",
        "E_legal_eval",
        "statement_inconsistency_with_previous",
        "justification_reason",
        "excuse_reason",
        "case_fact_summary",
        "case_highlights",
        "conduct_count_analysis"
    ]
    
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
        
        self._vector_dimension = None
    
    def _is_unknown_content(self, content: str) -> bool:
        return content.strip() == self.UNKNOWN_CONTENT_VALUE
    
    def _prepare_embedding_text(self, content: str) -> str:
        content = content.strip()
        length = len(content)
        if length <= self.MAX_EMBEDDING_CHARS:
            return content
        logger.info(
            f"嵌入內容長度 {length} 超過上限 {self.MAX_EMBEDDING_CHARS}，將截斷後再送出嵌入請求"
        )
        return content[:self.MAX_EMBEDDING_CHARS]
    
    def _get_vector_dimension(self) -> int:
        if self._vector_dimension is None:
            example_embedding = self.dense_embeddings.embed_query("dimension_probe")
            self._vector_dimension = len(example_embedding)
            logger.info(f"向量維度: {self._vector_dimension}")
        return self._vector_dimension
    
    def _get_empty_dense_vector(self) -> List[float]:
        dim = self._get_vector_dimension()
        return [0.0] * dim
    
    def _get_empty_sparse_vector(self) -> SparseVector:
        return SparseVector(indices=[], values=[])
    
    def recreate_judgment_collection(self, collection_name: Optional[str] = None) -> None:
        target_collection = collection_name if collection_name else f"{self.collection_name}_judgment"
        
        if self.client.collection_exists(target_collection):
            logger.info(f"judgment 多向量 collection 已存在，跳過建立: {target_collection}")
            return
        
        logger.info(f"建立 judgment 多向量 collection（含 sparse）: {target_collection}")
        
        example_embedding = self.dense_embeddings.embed_query("dimension_probe")
        dim = len(example_embedding)
        
        vectors_config = {
            name: VectorParams(size=dim, distance=Distance.COSINE)
            for name in self.JUDGMENT_VECTOR_NAMES
        }
        
        sparse_vectors_config = {
            f"{name}_bm25": SparseVectorParams(
                index=SparseIndexParams()
            )
            for name in self.JUDGMENT_VECTOR_NAMES
        }
        
        self.client.create_collection(
            collection_name=target_collection,
            vectors_config=vectors_config,
            sparse_vectors_config=sparse_vectors_config,
        )
    
    def get_collection_count(self, collection_name: Optional[str] = None) -> int:
        target_collection = collection_name if collection_name else self.collection_name
        collection_url = f"{self.qdrant_url}/collections/{target_collection}"
        response = requests.get(collection_url)
        count = response.json()["result"]["points_count"]
        logger.info(f"目前集合 {target_collection} 點數: {count}")
        return count
    
    def add_documents(self, documents: List[EmbeddingDocument], collection_name: Optional[str] = None) -> None:
        target_collection = collection_name if collection_name else self.collection_name
        logger.info(f"準備加入 {len(documents)} 個文件到 Qdrant collection: {target_collection}")
        
        normal_docs = []
        normal_ids = []
        unknown_docs = []
        
        for doc in documents:
            if self._is_unknown_content(doc.content):
                unknown_docs.append(doc)
                logger.info(f"文件 {doc.document_id} 內容為未知，將使用空向量")
            else:
                langchain_doc = Document(
                    page_content=doc.content,
                    metadata=doc.metadata
                )
                normal_docs.append(langchain_doc)
                normal_ids.append(doc.document_id)
        
        if normal_docs:
            if collection_name:
                temp_store = QdrantVectorStore(
                    client=self.client,
                    collection_name=target_collection,
                    embedding=self.dense_embeddings,
                    sparse_embedding=self.sparse_embeddings,
                    retrieval_mode=RetrievalMode.HYBRID,
                    vector_name="dense",
                    sparse_vector_name="bm25",
                )
                temp_store.add_documents(documents=normal_docs, ids=normal_ids)
            else:
                self.store.add_documents(documents=normal_docs, ids=normal_ids)
            logger.info(f"成功加入 {len(normal_docs)} 個正常文件到 {target_collection}")
        
        if unknown_docs:
            self._add_unknown_documents(unknown_docs, target_collection)
            logger.info(f"成功加入 {len(unknown_docs)} 個未知內容文件（空向量）到 {target_collection}")
        
        logger.info(f"總計加入 {len(documents)} 個文件到 {target_collection}")
    
    def _add_unknown_documents(self, documents: List[EmbeddingDocument], collection_name: str) -> None:
        empty_dense = self._get_empty_dense_vector()
        empty_sparse = self._get_empty_sparse_vector()
        
        points = []
        for doc in documents:
            point = PointStruct(
                id=doc.document_id,
                vector={
                    "dense": empty_dense,
                    "bm25": empty_sparse,
                },
                payload=doc.metadata,
            )
            points.append(point)
        
        self.client.upsert(
            collection_name=collection_name,
            points=points
        )
    
    def add_judgment_points(self, documents_by_jid: Dict[str, List[EmbeddingDocument]], collection_name: Optional[str] = None) -> None:
        target_collection = collection_name if collection_name else f"{self.collection_name}_judgment"
        logger.info(f"準備加入 {len(documents_by_jid)} 個判決 points 到 collection: {target_collection}")
        
        collection_url = f"{self.qdrant_url}/collections/{target_collection}"
        response = requests.get(collection_url)
        collection_data = response.json()
        
        available_vectors = set()
        if "result" in collection_data and "config" in collection_data["result"]:
            vectors_config = collection_data["result"]["config"]["params"].get("vectors", {})
            if isinstance(vectors_config, dict):
                available_vectors = set(vectors_config.keys())
                logger.info(f"Collection 支援的向量名稱: {available_vectors}")
        
        points = []
        
        for jid, documents in documents_by_jid.items():
            if not documents:
                continue
            
            case_fact_doc_id = None
            for doc in documents:
                if doc.metadata.get('summary_type') == 'case_fact_summary':
                    case_fact_doc_id = doc.document_id
                    break
            
            documents_by_defendant = {}
            all_defendants_set = set()
            all_defendants_detail = []
            common_docs = []
            base_metadata = None
            
            for doc in documents:
                defendants = doc.metadata.get('defendants', [])
                
                if base_metadata is None:
                    base_metadata = {
                        'jid': doc.metadata.get('jid'),
                        'jid_full': doc.metadata.get('jid_full'),
                        'jyear': doc.metadata.get('jyear'),
                        'jcase': doc.metadata.get('jcase'),
                        'jno': doc.metadata.get('jno'),
                        'jdate': doc.metadata.get('jdate'),
                        'jtitle': doc.metadata.get('jtitle'),
                        'case_type': doc.metadata.get('case_type'),
                        'case_metadata': doc.metadata.get('case_metadata', {}),
                    }
                    if not all_defendants_detail and len(doc.metadata.get('defendants', [])) > 1:
                        all_defendants_detail = doc.metadata.get('defendants', [])
                
                if len(defendants) > 1:
                    all_defendants_detail = defendants
                
                if len(defendants) == 1:
                    defendant_name = defendants[0].get('defendant_name', 'no_defendant')
                    all_defendants_set.add(defendant_name)
                    if defendant_name not in documents_by_defendant:
                        documents_by_defendant[defendant_name] = []
                    documents_by_defendant[defendant_name].append(doc)
                else:
                    common_docs.append(doc)
                    if 'all' not in documents_by_defendant:
                        documents_by_defendant['all'] = []
                    documents_by_defendant['all'].append(doc)
                    for defendant in defendants:
                        defendant_name = defendant.get('defendant_name')
                        if defendant_name:
                            all_defendants_set.add(defendant_name)
            
            if not documents_by_defendant:
                documents_by_defendant['all'] = documents
                all_defendants_detail = all_defendants_detail or documents[0].metadata.get('defendants', [])
                for defendant in all_defendants_detail:
                    name = defendant.get('defendant_name')
                    if name:
                        all_defendants_set.add(name)
            
            if not all_defendants_set and all_defendants_detail:
                for defendant in all_defendants_detail:
                    name = defendant.get('defendant_name')
                    if name:
                        all_defendants_set.add(name)
            
            if common_docs and all_defendants_set:
                for defendant_name in all_defendants_set:
                    if defendant_name not in documents_by_defendant:
                        documents_by_defendant[defendant_name] = []
                    documents_by_defendant[defendant_name].extend(common_docs)
            
            for defendant_key, defendant_docs in documents_by_defendant.items():
                point_id = None
                
                if defendant_key != 'all':
                    for doc in defendant_docs:
                        if doc.metadata.get('summary_type') == 'A_fact':
                            point_id = doc.document_id
                            break
                    if point_id is None and case_fact_doc_id is not None:
                        point_id = case_fact_doc_id
                else:
                    if case_fact_doc_id is not None:
                        point_id = case_fact_doc_id
                    else:
                        for doc in defendant_docs:
                            if doc.metadata.get('summary_type') == 'A_fact':
                                point_id = doc.document_id
                                break
                
                if point_id is None:
                    point_id = defendant_docs[0].document_id
                
                grouped_by_type = {}
                for doc in defendant_docs:
                    summary_type = doc.metadata.get('summary_type', 'unknown')
                    if summary_type not in grouped_by_type:
                        grouped_by_type[summary_type] = []
                    grouped_by_type[summary_type].append(doc)
                
                judgment_metadata = base_metadata.copy()
                if defendant_key == 'all':
                    if all_defendants_detail:
                        judgment_metadata['defendants'] = all_defendants_detail
                    else:
                        judgment_metadata['defendants'] = list(all_defendants_set) if all_defendants_set else []
                else:
                    matching_defendant = None
                    for doc in defendant_docs:
                        defendants = doc.metadata.get('defendants', [])
                        if len(defendants) == 1:
                            matching_defendant = defendants[0]
                            break
                    judgment_metadata['defendants'] = [matching_defendant] if matching_defendant else []
                
                named_vectors = {}
                
                for summary_type, type_docs in grouped_by_type.items():
                    contents = [d.content for d in type_docs]
                    combined_content = " ".join(contents)
                    combined_content = self._prepare_embedding_text(combined_content)
                    
                    vector_name = summary_type
                    
                    if available_vectors and vector_name not in available_vectors:
                        logger.warning(f"跳過未定義的向量名稱: {vector_name}")
                        continue
                    
                    if self._is_unknown_content(combined_content):
                        logger.info(f"判決 {jid} 的 {summary_type} 內容為未知，使用空向量")
                        dense_vector = self._get_empty_dense_vector()
                    else:
                        dense_vector = self.dense_embeddings.embed_query(combined_content)
                    named_vectors[vector_name] = dense_vector
                
                if not named_vectors:
                    logger.warning(f"判決 {jid} defendant {defendant_key} 沒有可用的向量，跳過")
                    continue
                
                point = PointStruct(
                    id=point_id,
                    vector=named_vectors,
                    payload=judgment_metadata,
                )
                points.append(point)
                logger.info(f"為判決 {jid} defendant {defendant_key} 建立 point，ID: {point_id}")
        
        if not points:
            logger.warning("沒有有效的 points 可以加入")
            return
        
        self.client.upsert(
            collection_name=target_collection,
            points=points
        )
        
        logger.info(f"成功加入 {len(points)} 個判決 points 到 {target_collection}")


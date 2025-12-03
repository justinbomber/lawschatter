import logging
from typing import Dict, Any, AsyncGenerator
from entities.models import SearchRequest, SearchResponse, CollectionInfo, HealthStatus
from domain.interfaces import IQdrantClient, IDocumentSearchOrchestrator, IConversationRepository
from config.settings import Settings
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class SearchController:
    def __init__(
        self,
        qdrant_client: IQdrantClient,
        document_search_orchestrator: IDocumentSearchOrchestrator,
        conversation_repository: IConversationRepository,
        settings: Settings,
        chunk_strong_weak_orchestrator: IDocumentSearchOrchestrator = None
    ):
        self.qdrant_client = qdrant_client
        self.document_search_orchestrator = document_search_orchestrator
        self.conversation_repository = conversation_repository
        self.settings = settings
        self.chunk_strong_weak_orchestrator = chunk_strong_weak_orchestrator

    async def search_documents(self, request: SearchRequest, token: str, user_id: str) -> SearchResponse:
        history = []
        
        if request.conversation_id:
            has_access = await self.conversation_repository.verify_user_conversation_access(
                token, user_id, request.conversation_id
            )
            
            if not has_access:
                raise HTTPException(status_code=403, detail="無權訪問此對話")
            
            history = await self.conversation_repository.get_conversation_messages(
                token, request.conversation_id, limit=10
            )
            logger.info(f"取得對話 {request.conversation_id} 的 {len(history)} 筆歷史訊息")
        else:
            logger.info("沒有提供 conversation_id，使用空歷史記錄進行搜尋")
        
        collection = "embedding-seperate"
        mode = "hybrid"
        limit = 5
        score_threshold = 0.95
        logic = "AND"
        
        max_retries = 3
        retries = 0
        while retries < max_retries:
            simplified_results = await self.document_search_orchestrator.orchestrate_search(
                collection=collection,
                query_text=request.query_text,
                mode=mode,
                limit=limit,
                logic=logic,
                history_messages=history
            )
            retries += 1
            if len(simplified_results) > 0:
                break
            else:
                continue
        
        return SearchResponse(
            results=simplified_results,
            total=len(simplified_results),
            query=request.query_text,
            mode=mode,
            collection=collection
        )
    
    async def search_documents_stream(self, request: SearchRequest, token: str, user_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        history = []
        
        if request.conversation_id:
            has_access = await self.conversation_repository.verify_user_conversation_access(
                token, user_id, request.conversation_id
            )
            
            if not has_access:
                raise HTTPException(status_code=403, detail="無權訪問此對話")
            
            history = await self.conversation_repository.get_conversation_messages(
                token, request.conversation_id, limit=10
            )
            logger.info(f"取得對話 {request.conversation_id} 的 {len(history)} 筆歷史訊息")
        else:
            logger.info("沒有提供 conversation_id，使用空歷史記錄進行串流搜尋")
        
        collection = "embedding-seperate"
        mode = "hybrid"
        limit = 5
        logic = "AND"
        
        async for chunk in self.document_search_orchestrator.orchestrate_search_stream(
            collection=collection,
            query_text=request.query_text,
            mode=mode,
            limit=limit,
            logic=logic,
            history_messages=history
        ):
            yield chunk
    
    async def list_collections(self) -> Dict[str, Any]:
        collections = await self.qdrant_client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        return {
            "collections": collection_names,
            "count": len(collection_names)
        }
    
    async def get_collection_info(self, collection: str) -> CollectionInfo:
        info = await self.qdrant_client.get_collection(collection)
        
        return CollectionInfo(
            name=collection,
            vectors_count=info.vectors_count,
            points_count=info.points_count,
            status=info.status.value
        )
    
    async def health_check(self) -> HealthStatus:
        collections = await self.qdrant_client.get_collections()
        return HealthStatus(
            status="healthy",
            qdrant_connection="connected",
            collections_count=len(collections.collections)
        )
    
    async def search_documents_advanced(self, request: SearchRequest, token: str, user_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        history = []
        
        if request.conversation_id:
            has_access = await self.conversation_repository.verify_user_conversation_access(
                token, user_id, request.conversation_id
            )
            
            if not has_access:
                raise HTTPException(status_code=403, detail="無權訪問此對話")
            
            history = await self.conversation_repository.get_conversation_messages(
                token, request.conversation_id, limit=10
            )
            logger.info(f"取得對話 {request.conversation_id} 的 {len(history)} 筆歷史訊息")
        else:
            logger.info("沒有提供 conversation_id，使用空歷史記錄進行搜尋")
        
        search_mode = request.search_mode or "chunk"
        mode = "hybrid"
        limit = 5
        logic = "AND"
        
        # if search_mode == "chunk-strong-weak":
        if not self.chunk_strong_weak_orchestrator:
            raise HTTPException(status_code=501, detail="Chunk strong-weak 搜尋模式未啟用")
        
        collection = self.settings.qdrant.collection_name
        orchestrator = self.chunk_strong_weak_orchestrator
        logger.info(f"使用 chunk-strong-weak 搜尋模式，collection: {collection}")
        
        # else:
        #     collection = self.settings.qdrant.collection_name
        #     orchestrator = self.document_search_orchestrator
        #     logger.info(f"使用標準 chunk 搜尋模式，collection: {collection}")
        
        async for chunk in orchestrator.orchestrate_search_stream(
            collection=collection,
            query_text=request.query_text,
            mode=mode,
            limit=limit,
            logic=logic,
            history_messages=history
        ):
            yield chunk


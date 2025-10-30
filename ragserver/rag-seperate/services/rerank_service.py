import cohere
from typing import List
from domain.interfaces import IRerankService
from config.settings import Settings


class RerankService(IRerankService):
    def __init__(self, settings: Settings):
        self.cohere_client = cohere.ClientV2(api_key=settings.cohere.api_key)
        self.settings = settings
    
    def rerank(
        self, 
        query: str, 
        documents: List[str],
        top_n: int = 10
    ) -> List[tuple]:
        response = self.cohere_client.rerank(
            model=self.settings.cohere.model,
            query=query, 
            documents=documents, 
            top_n=top_n
        )
        
        results = []
        for result in response.results:
            results.append((result.index, result.relevance_score))
        return results


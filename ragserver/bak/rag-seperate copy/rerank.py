import cohere
import os
from dotenv import load_dotenv
load_dotenv()

class ReRanker:
    def __init__(self, api_key: str):
        self.cohere = cohere.ClientV2(api_key=api_key)

    def rerank(
        self, 
        query: str, 
        documents: list[str],
        top_n: int=10
    ) -> list[str]:
        response = self.cohere.rerank(
            model="rerank-v3.5",
            query=query, 
            documents=documents, 
            top_n=top_n)

        for result in response.results:
            yield result.index, result.relevance_score
    
    
if __name__ == "__main__":
    reranker = ReRanker(api_key=os.getenv("COHERE_API_KEY"))
    query = "What is the capital of France?"
    documents = ["The capital of France is Paris.", "The capital of Germany is Berlin.", "The capital of Italy is Rome."]
    results = reranker.rerank(query, documents)
    print([(index, score) for index, score in results])
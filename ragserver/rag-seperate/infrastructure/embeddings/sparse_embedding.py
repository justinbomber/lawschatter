import os
import asyncio
from typing import Any, Iterable, Union, List
import numpy as np
from fastembed.sparse.bm25 import Bm25
from fastembed.sparse.sparse_embedding_base import SparseEmbedding
from langchain_qdrant import FastEmbedSparse
from qdrant_client import models
from infrastructure.tokenizer import JiebaLawTokenizer
from domain.interfaces import IEmbeddingProvider
from config.settings import Settings


class ZHTBm25Jieba(Bm25):
    def __init__(self, stopwords_path: str, model_name: str = "Qdrant/bm25"):
        super().__init__(model_name=model_name, disable_stemmer=True)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        stopwords_full_path = os.path.join(project_root, stopwords_path)
        self.stopwords = self.load_stopwords(stopwords_full_path)
        dict_path = os.path.join(project_root, "dict.txt.big")
        self.tokenizer = JiebaLawTokenizer(
            dict_path=dict_path,
            cut_all=False,
            doc_hmm=False,
            query_hmm=True,
        )

    def load_stopwords(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            stopwords = set(line.strip() for line in f if line.strip())
        return stopwords
    
    def raw_embed(
        self,
        documents: list[str],
    ) -> list[SparseEmbedding]:
        embeddings: list[SparseEmbedding] = []
        for document in documents:
            tokens = [
                t.strip() for t in self.tokenizer.run_doc(document)
                if t.strip() and t.strip() not in self.stopwords
            ]

            token_id2value = self._term_frequency(tokens)
            embeddings.append(SparseEmbedding.from_dict(token_id2value))
        return embeddings
    
    def query_embed(
        self, query: Union[str, Iterable[str]], **kwargs: Any
    ) -> Iterable[SparseEmbedding]:
        if isinstance(query, str):
            query = [query]

        for text in query:
            tokens = [
                t.strip() for t in self.tokenizer.run_query(text)
                if t.strip() and t.strip() not in self.stopwords
            ]
            if not tokens:
                yield SparseEmbedding(indices=[], values=[])
            
            else:
                token_ids = np.array(
                    list(set(self.compute_token_id(t) for t in tokens)),
                    dtype=np.int32,
                )
                values = np.ones_like(token_ids)
                yield SparseEmbedding(indices=token_ids, values=values)


class ZHTSparseEmbed(FastEmbedSparse):
    def __init__(self, stopwords_path: str):
        super().__init__()
        self._model = ZHTBm25Jieba(stopwords_path=stopwords_path)


class SparseEmbeddingProvider(IEmbeddingProvider):
    def __init__(self, settings: Settings):
        self.embeddings = ZHTSparseEmbed(stopwords_path=settings.embedding.stopwords_path)
    
    async def embed_query(self, text: str) -> models.SparseVector:
        return await asyncio.to_thread(self.embeddings.embed_query, text)
    
    async def embed_documents(self, texts: List[str]) -> List[models.SparseVector]:
        return await asyncio.to_thread(self.embeddings.embed_documents, texts)


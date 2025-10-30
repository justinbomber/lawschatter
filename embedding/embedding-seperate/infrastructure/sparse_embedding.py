import logging
from typing import Any, Iterable, Union
import numpy as np
from fastembed.sparse.bm25 import Bm25
from fastembed.sparse.sparse_embedding_base import SparseEmbedding
from langchain_qdrant import FastEmbedSparse
from .tokenizer import JiebaLawTokenizer

logger = logging.getLogger(__name__)


class ZHTBm25Jieba(Bm25):
    
    def __init__(
        self, 
        stopwords_path: str = "zh-t.txt", 
        dict_path: str = "dict.txt.big",
        model_name: str = "Qdrant/bm25"
    ):
        super().__init__(model_name=model_name, disable_stemmer=True)
        logger.info(f"初始化 ZHTBm25Jieba，stopwords: {stopwords_path}")
        self.stopwords = self._load_stopwords(stopwords_path)
        self.tokenizer = JiebaLawTokenizer(
            dict_path=dict_path,
            cut_all=False,
            doc_hmm=False,
            query_hmm=True,
        )
    
    def _load_stopwords(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            stopwords = set(line.strip() for line in f if line.strip())
        logger.info(f"載入 {len(stopwords)} 個停用詞")
        return stopwords
    
    def raw_embed(self, documents: list[str]) -> list[SparseEmbedding]:
        embeddings: list[SparseEmbedding] = []
        
        for document in documents:
            tokens = [
                t.strip() 
                for t in self.tokenizer.run_doc(document)
                if t.strip() and t.strip() not in self.stopwords
            ]
            
            token_id2value = self._term_frequency(tokens)
            embeddings.append(SparseEmbedding.from_dict(token_id2value))
        
        return embeddings
    
    def query_embed(
        self, 
        query: Union[str, Iterable[str]], 
        **kwargs: Any
    ) -> Iterable[SparseEmbedding]:
        if isinstance(query, str):
            query = [query]
        
        for text in query:
            tokens = [
                t.strip() 
                for t in self.tokenizer.run_query(text)
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
    
    def __init__(
        self, 
        stopwords_path: str = "zh-t.txt",
        dict_path: str = "dict.txt.big"
    ):
        super().__init__()
        self._model = ZHTBm25Jieba(
            stopwords_path=stopwords_path,
            dict_path=dict_path
        )


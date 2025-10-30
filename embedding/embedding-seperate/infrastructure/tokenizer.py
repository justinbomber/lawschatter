import jieba
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class JiebaLawTokenizer:
    
    def __init__(
        self,
        dict_path: Optional[str] = None,
        cut_all: bool = False,
        doc_hmm: bool = False,
        query_hmm: bool = True,
    ):
        if dict_path:
            logger.info(f"載入 jieba 字典: {dict_path}")
            jieba.set_dictionary(dict_path)
        
        self.cut_all = cut_all
        self.doc_hmm = doc_hmm
        self.query_hmm = query_hmm
    
    def run_doc(self, text: str) -> List[str]:
        return [
            t.strip() 
            for t in jieba.cut(text, cut_all=self.cut_all, HMM=self.doc_hmm) 
            if t.strip()
        ]
    
    def run_query(self, text: str) -> List[str]:
        return [
            t.strip() 
            for t in jieba.cut(text, cut_all=self.cut_all, HMM=self.query_hmm) 
            if t.strip()
        ]


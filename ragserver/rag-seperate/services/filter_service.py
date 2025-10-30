import os
import logging
from typing import List, Dict, Any
from openai import OpenAI
from qdrant_client import models
from entities.filters import Filter
from infrastructure.tokenizer import JiebaLawTokenizer
from domain.interfaces import IFilterService
from config.settings import Settings


logger = logging.getLogger(__name__)


class FilterService(IFilterService):
    def __init__(self, settings: Settings):
        self.client = OpenAI(api_key=settings.openai.api_key)
        self.settings = settings
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        dict_path = os.path.join(parent_dir, "dict.txt.big")
        self.tokenizer = JiebaLawTokenizer(
            dict_path=dict_path,
            cut_all=False,
            doc_hmm=False,
            query_hmm=True,
        )
    
    def extract_filter_conditions(self, user_question: str) -> List[Dict[str, Any]]:
        system_prompt = """
你是法律判決查詢的過濾條件抽取助理，請根據使用者的問題，抽取出過濾條件。

請嚴格按照 JSON schema 格式輸出，包含以下主要結構：

1. case_metadata: 案件元資料
   - first_instance: 是否為地方法院判決
   - second_instance: 是否為高等法院判決
   - third_instance: 是否為最高法院判決
   - case_type: 案件類型（刑法/民法/行政法）
   - jtitle_type: 案件標題類型（詐欺/毒品/竊盜/侵占/妨害性自主/傷害/公共危險/槍砲彈藥刀械/偽造文書/其他刑事/債務給付類/侵權行為／損害賠償類/婚姻家庭類/物權類/公司／商事類/勞資爭議類/保險類/其他民事）

2. defendants: 被告相關資訊（數組格式）

輸出要求：
- 只需要輸出實際存在的過濾條件，不要推測或添加不存在的條件
- 數組字段使用列表格式，如 ["詐欺", "洗錢"]
- 布林值使用 true/false
- 字符串使用引號包裹
- 如果問題中沒有提到任何過濾條件，請忽略，並且不允許猜測或添加預設值
- "defendants_role", "A_fact", "B_claim", "C_court_finding", "D_court_reason", "E_legal_eval"一定至少要選一個填入，也可以一至多個填入
"""
        response = self.client.responses.parse(
            # model=self.settings.openai.model,
            model="gpt-5",
            input=[
                {"role": "system", "content": system_prompt}, 
                {"role": "user", "content": user_question}
            ],
            text_format=Filter,
            timeout=120
            # reasoning_effort="high"
        )
        result = response.output_parsed
        structured_output = result.model_dump(exclude_none=True, exclude_unset=True)
        logger.info(f"結構化輸出: {structured_output}")
        
        output_lst = []
        summary_fields = ["defendants_role", "A_fact", "B_claim", "C_court_finding", "D_court_reason", "E_legal_eval", "case_fact_summary"]
        _metadata = structured_output
        tmp_summary = {}
        
        for field in summary_fields:
            if field in structured_output and structured_output[field]:
                tmp_summary[field] = _metadata[field]
                del _metadata[field]
        
        for summary_type in tmp_summary:
            tmp_metadata = _metadata.copy()
            tmp_metadata[summary_type] = tmp_summary[summary_type]
            tmp_metadata["summary_type"] = [summary_type]
            output_lst.append(tmp_metadata)
                
        return output_lst
    
    def to_qdrant_filter(self, filter_dict: dict) -> models.Filter:
        must_conditions = []
        
        for key in ["jid_full", "jyear", "jcase", "jno", "jdate", "summary_type"]:
            value = filter_dict.get(key)
            
            if key == "summary_type" and value is not None:
                list_conditions = []
                for item in value:
                    if item == "defendants_role":
                        item = "role"
                    list_conditions.append(
                        models.FieldCondition(
                            key=f"metadata.summary_type",
                            match=models.MatchPhrase(phrase=item)
                        )
                    )
                if list_conditions:
                    if len(list_conditions) == 1:
                        must_conditions.append(list_conditions[0])
                    else:
                        must_conditions.append(models.Filter(should=list_conditions))
            
            elif key == "jid_full" and value is not None:
                pass
            elif key == "jyear" and value is not None:
                if isinstance(value, int):
                    must_conditions.append(
                        models.FieldCondition(
                            key=f"metadata.{key}",
                            match=models.MatchValue(value=value)
                        )
                    )
            elif key == "jdate" and value is not None:
                if isinstance(value, int):
                    must_conditions.append(
                        models.FieldCondition(
                            key=f"metadata.{key}",
                            match=models.MatchValue(value=value)
                        )
                    )
            elif value is not None:
                if isinstance(value, (str, bool)):
                    must_conditions.append(
                        models.FieldCondition(
                            key=f"metadata.{key}",
                            match=models.MatchValue(value=value)
                        )
                    )
        
        cm = filter_dict.get("case_metadata")
        if cm:
            for key in ["first_instance", "second_instance", "third_instance", "case_type", "jtitle_type"]:
                value = cm.get(key)
                if value is not None:
                    if isinstance(value, (str, bool)):
                        must_conditions.append(
                            models.FieldCondition(
                                key=f"metadata.case_metadata.{key}",
                                match=models.MatchValue(value=value)
                            )
                        )
        
        defendants_list = filter_dict.get("defendants") or []
        if isinstance(defendants_list, list):
            for d in defendants_list:
                pass
        
        return models.Filter(must=must_conditions) if must_conditions else models.Filter()
    
    def format_jid_full(self, jid_full: str) -> str:
        if not jid_full:
            return jid_full
            
        result = []
        for i, char in enumerate(jid_full):
            if char.isdigit():
                if i > 0 and not jid_full[i-1].isdigit() and jid_full[i-1] != ' ':
                    result.append(' ')
            result.append(char)
        
        return ''.join(result)


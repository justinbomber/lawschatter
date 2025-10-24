import os
from openai import OpenAI
from typing import Optional, Literal, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from qdrant_client import models

load_dotenv()
class Defendant(BaseModel):
    defendant_id: Optional[str] = Field(default=None, description="被告名字（例：郭俊賢、余志霆等）")
    confession: Optional[bool] = Field(default=None, description="被告是否自白/認罪。false=最後法庭上否認犯行；true=最後法庭上認罪")
    conviction: Optional[Literal["true", "false", "partial", "none"]] = Field(
        default=None, description="法院認定被告有罪（含判刑、科刑）。partial=僅部分犯行有罪；none=無特別說明",
    )
    acquittal: Optional[Literal["true", "false", "partial", "none"]] = Field(
        default=None, description="法院判無罪或認不能證明犯罪。partial=部分事實無罪；none=無特別說明",
    )
    crime: Optional[List[str]] = Field(
        default=None, description="直接填具體罪名（例：洗錢、詐欺、背信、侵占、恐嚇取財、傷害、毒品、偽造文書等），注意不要加上'罪'字",
    )
    contravene_law: Optional[List[str]] = Field(
        default=None, description="直接填適用之法條，因條件內容可能會簡寫，可以多使用關鍵字並在array中區隔開來，（例如：刑法第339條、刑法339之4、339、修正前(後)洗錢防制法第14條、詐欺犯罪危害防制條例第47條等）",
    )
    old_law_applied_more_favorable: Optional[Literal["true", "false", "partial"]] = Field(
        default=None, description="從舊從輕原則，法院適用較有利之舊法。partial=僅提及爭點或尚未確定採用",
    )
    mitigation_claim_accepted: Optional[Literal["true", "false", "partial"]] = Field(
        default=None, description="法院是否採納減刑主張（含第47條或其他法定/裁量減輕）。partial=僅部分採納或改以他法條減輕",
    )
    probation_granted: Optional[bool] = Field(default=None, description="是否宣告緩刑。")
    verdict: Optional[bool] = Field(default=None, description='宣判結果，「true」（有罪）或 「false」（無罪）')
    fixed_term_imprisonment: Optional[bool] = Field(default=None, description="是否判處有期徒刑（true/false）")
    fixed_term_years: Optional[int] = Field(default=None, description="有期徒刑的年數（整數，無則 0）")
    fixed_term_months: Optional[int] = Field(default=None, description="有期徒刑的月數（整數，無則 0）")
    life_imprisonment: Optional[bool] = Field(default=None, description="是否判處無期徒刑（true/false）")
    death_penalty: Optional[bool] = Field(default=None, description="是否判處死刑（true/false）")
    detention: Optional[bool] = Field(default=None, description="是否判處拘役（true/false）")
    detention_days: Optional[int] = Field(default=None, description="拘役日數（整數，無則 0）")
    fine_amount_twd: Optional[int] = Field(default=None, description="罰金金額（新臺幣，無則 0）")
    fine_is_combined: Optional[bool] = Field(default=None, description="是否為併科罰金（與徒刑同時科處的罰金，true/false）")
    may_convert_to_fine: Optional[bool] = Field(default=None, description="是否得易科罰金（以金額折算取代入監，true/false）")
    fine_conversion_rate_twd_per_day: Optional[int] = Field(default=None, description="易科罰金折算標準（每一日折算多少新臺幣，無則 0）")
    probation_years: Optional[int] = Field(default=None, description="緩刑期間（以年計，無則 0）")
    probation_months: Optional[int] = Field(default=None, description="緩刑期間（以月計，無則 0）")
    community_service_hours: Optional[int] = Field(default=None, description="易服社會勞動時數（無則 0）")
    labor_service_days: Optional[int] = Field(default=None, description="勞役天數（無則 0；視制度適用）")


class CaseMetadata(BaseModel):
    first_instance: Optional[bool] = Field(default=None, description="是否為地方法院判決")
    second_instance: Optional[bool] = Field(default=None, description="是否為高等法院判決")
    third_instance: Optional[bool] = Field(default=None, description="是否為最高法院判決")
    is_additional_prosecution: Optional[bool] = Field(
        default=None, description="是否追加起訴，如有追加罪名或事實則填「true」，未提及或不明則填「false」",
    )
    ideal_concurrence: Optional[bool] = Field(
        default=None, description="是否構成想像競合處理，判斷法院是否認定同一行為同時觸犯數罪，true為是，false為否或未知",
    )
    case_type: Optional[Literal["刑法", "民法", "行政法"]] = Field(
        default=None, description="案件類型，只能為：刑法，民法，行政法其中一種",
    )

class Filter(BaseModel):
    jid: Optional[str] = Field(default=None, description="判決書ID（例：TPHM,113,上訴,6418,20250617,1）")
    jid_full: Optional[str] = Field(default=None, description="完整判決書名稱，（例：臺灣高等法院刑事判決113年度上訴字第6418號）必填",)
    jyear: Optional[int] = Field(default=None, description="年度（例：113）")
    jcase: Optional[str] = Field(default=None, description="案件類型（例：上訴）")
    jno: Optional[str] = Field(default=None, description="案件編號（例：6418）")
    jdate: Optional[int] = Field(default=None, description="判決日期（例：20250617）")
    jtitle: Optional[str] = Field(default=None, description="案件標題（例：詐欺等）")
    defendants: Optional[List[Defendant]] = Field(
        default=None, description="逐一被告之結構化資訊清單（可省略）"
    )
    case_metadata: Optional[CaseMetadata] = Field(
        default=None, description="案件元資料與審級/類型等資訊（可省略）"
    )
    reconstruct_question: Optional[str] = Field(default=None, description="去除掉問題中已經被量化的條件後，重新組合的問題，必須一定要填")
    


def to_qdrant_filter(filter_dict: dict) -> dict:
    """Convert structured filter dict to Qdrant filter format.
    
    Converts the structured output from extract_filter_conditions() into a Qdrant-compatible
    filter JSON. Uses simple mode: all conditions go into 'must' clause.
    
    Args:
        filter_dict: Structured filter dict from extract_filter_conditions()
        
    Returns:
        dict: Qdrant filter format like {"filter": {"must": [...]}}
    """
    must = []
    
    for key in ["jid", "jid_full", "jyear", "jcase", "jno", "jdate", "jtitle"]:
        value = filter_dict.get(key)
        if value is not None:
            # 對 jid_full 進行格式化處理，在數字前面加空格
            if key == "jid_full":
                value = format_jid_full(value)
            must.append({"key": f"metadata.{key}", "match": {"value": value}})
    
    # Case metadata (dot key under metadata)
    cm = filter_dict.get("case_metadata")
    if cm:
        for key in [
            "first_instance",
            "second_instance",
            "third_instance",
            "is_additional_prosecution",
            "ideal_concurrence",
            "case_type",
        ]:
            value = cm.get(key)
            if value is not None:
                must.append({"key": f"metadata.case_metadata.{key}", "match": {"value": value}})
        
        
    # Defendants (projected keys: metadata.defendants[].<field>)
    defendants_list = filter_dict.get("defendants") or []
    if isinstance(defendants_list, list):
        for d in defendants_list:
            defendant_fields = [
                "defendant_id", "confession", "conviction", "acquittal", "crime",
                "old_law_applied_more_favorable", "mitigation_claim_accepted", 
                "probation_granted", "verdict", "fixed_term_imprisonment", 
                "fixed_term_years", "fixed_term_months", "life_imprisonment", 
                "death_penalty", "detention", "detention_days", "fine_amount_twd", 
                "fine_is_combined", "may_convert_to_fine", "fine_conversion_rate_twd_per_day", 
                "probation_years", "probation_months", "community_service_hours", 
                "labor_service_days", "reconstruct_question"
            ]
            for key in defendant_fields:
                value = d.get(key)
                if key == "crime":
                    if value:  # 非空 list
                        must.append({"key": f"metadata.defendants[].{key}", "match": {"any": value}})
                else:
                    if value is not None:  # 保留 False/0
                        must.append({"key": f"metadata.defendants[].{key}", "match": {"value": value}})

    return {"filter": {"must": must}} if must else {}

def format_jid_full(jid_full: str) -> str:
    """在數字組前面加空格的格式化函數
    
    當遇到數字組時在前面加一個空格，例如：
    "臺灣高等法院臺中分院113年度金上訴字第1464號" -> "臺灣高等法院臺中分院 113年度金上訴字第 1464號"
    
    Args:
        jid_full: 原始的 jid_full 字符串
        
    Returns:
        str: 格式化後的字符串
    """
    if not jid_full:
        return jid_full
        
    result = []
    for i, char in enumerate(jid_full):
        # 如果當前字符是數字
        if char.isdigit():
            # 檢查是否是數字組的開始（前一個字符不是數字且不是空格）
            if i > 0 and not jid_full[i-1].isdigit() and jid_full[i-1] != ' ':
                result.append(' ')
        result.append(char)
    
    return ''.join(result)

def to_qdrant_filter_python(filter_dict: dict) -> models.Filter:
    """Convert structured filter dict to Qdrant Python client format.
    
    Converts the structured output from extract_filter_conditions() into a Qdrant
    Python client Filter object using models.FieldCondition.
    
    Args:
        filter_dict: Structured filter dict from extract_filter_conditions()
        
    Returns:
        models.Filter: Qdrant Python client Filter object
    """
    
    must_conditions = []
    reconstruct_question = filter_dict.get("reconstruct_question")
    
    # Top-level fields (prefix with metadata.)
    # for key in ["jid", "jid_full", "jyear", "jcase", "jno", "jdate", "jtitle"]:
    for key in ["jid_full", "jyear", "jcase", "jno", "jdate", "jtitle"]:
        value = filter_dict.get(key)
        if key == "jid_full" and value is not None:
            # 對 jid_full 進行格式化處理，在數字前面加空格
            # formatted_value = format_jid_full(value)
            # must_conditions.append(
            #     models.FieldCondition(
            #         key=f"metadata.{key}",
            #         match=models.MatchText(text=formatted_value)
            #     )
            # )
            # print(f"---> metadata.jid_full: {formatted_value}")
            pass
        elif key == "jid" and value is None:
            pass
        elif value is not None:
            must_conditions.append(
                models.FieldCondition(
                    key=f"metadata.{key}",
                    match=models.MatchValue(value=value)
                )
            )
    
    # Case metadata (fields directly under metadata)
    cm = filter_dict.get("case_metadata")
    if cm:
        for key in ["first_instance", "second_instance", "third_instance", 
                   "is_additional_prosecution", "ideal_concurrence", "case_type"]:
            value = cm.get(key)
            if value is not None:
                must_conditions.append(
                    models.FieldCondition(
                        key=f"metadata.case_metadata.{key}",
                        match=models.MatchValue(value=value)
                    )
                )
    
    # Defendants (array projection under metadata)
    defendants_list = filter_dict.get("defendants") or []
    if isinstance(defendants_list, list):
        for d in defendants_list:
            defendant_fields = [
                "defendant_id", "confession", "conviction", "acquittal", "crime", "contravene_law",
                "old_law_applied_more_favorable", "mitigation_claim_accepted", 
                "probation_granted", "verdict", "fixed_term_imprisonment", 
                "fixed_term_years", "fixed_term_months", "life_imprisonment", 
                "death_penalty", "detention", "detention_days", "fine_amount_twd", 
                "fine_is_combined", "may_convert_to_fine", "fine_conversion_rate_twd_per_day", 
                "probation_years", "probation_months", "community_service_hours", 
                "labor_service_days", "reconstruct_question"
            ]
            
            for key in defendant_fields:
                value = d.get(key)
                if key == "crime":
                    if value:
                        # crime 是列表，需要為每個罪名創建條件
                        crime_conditions = []
                        for crime_name in value:
                            crime_conditions.append(
                                models.FieldCondition(
                                    key=f"metadata.defendants[].{key}[]",
                                    match=models.MatchPhrase(phrase=crime_name)
                                )
                            )
                        # 使用 OR 條件，任何一個罪名匹配即可
                        if crime_conditions:
                            if len(crime_conditions) == 1:
                                must_conditions.append(crime_conditions[0])
                            else:
                                must_conditions.append(models.Filter(should=crime_conditions))
                elif key == "defendant_id":
                    # 使用 phrase match 進行包含匹配，而不是完全匹配
                    if value is not None:
                        must_conditions.append(
                            models.FieldCondition(
                                key=f"metadata.defendants[].{key}",
                                match=models.MatchPhrase(phrase=value)
                            )
                        )
                elif key == "contravene_law":
                    if value:
                        # contravene_law 是列表，需要為每個法條創建條件
                        law_conditions = []
                        for law_name in value:
                            law_conditions.append(
                                models.FieldCondition(
                                    key=f"metadata.defendants[].{key}[]",
                                    match=models.MatchPhrase(phrase=law_name)
                                )
                            )
                        # 使用 OR 條件，任何一個法條匹配即可
                        if law_conditions:
                            if len(law_conditions) == 1:
                                must_conditions.append(law_conditions[0])
                            else:
                                must_conditions.append(models.Filter(should=law_conditions))
                else:
                    if value is not None:
                        must_conditions.append(
                            models.FieldCondition(
                                key=f"metadata.defendants[].{key}",
                                match=models.MatchValue(value=value)
                            )
                        )
    
    # return models.Filter(must=must_conditions) if must_conditions else models.Filter(), reconstruct_question
    return models.Filter(must=must_conditions) if must_conditions else models.Filter()

def extract_filter_conditions(user_question: str) -> dict:
    """Extract filter conditions from user question.
    
    Returns:
        dict: structured output (cleaned dict)
    """
    system_prompt = """
        你是法律判決查詢的過濾條件抽取助理，請根據使用者的問題，抽取出過濾條件。

        範例：
        - 題示：「幫我查上訴至高等法院的詐欺案件」
        合法最小輸出之一：
        {
            "case_metadata": { "second_instance": true },
            "defendants": [ { "crime": ["詐欺"] } ]
        }

        輸出要求：
        - 如果問題中沒有提到個過濾條件，請忽略，並且不可以猜測"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable is required")
    client = OpenAI(api_key=api_key)    
    response = client.responses.parse(
        model="o3",
        input=[
            {"role": "system", "content": system_prompt}, 
            {"role": "user", "content": user_question}],
        text_format=Filter,
    )
    
    result = response.output_parsed
    structured_output = result.model_dump(exclude_none=True, exclude_unset=True)
    print("結構化輸出:", structured_output)
    
    return structured_output


if __name__ == "__main__":
    # Test cases
    test_questions = [
        "有沒有未認罪，但法院還是給予緩刑的詐欺車手案例",
        "請問有沒有提供帳戶的詐欺案件，被告沒有提供任何對話紀錄，法院還是給予無罪的案例",
        "有沒有被告在二審主張依詐欺犯罪危害防制條例第47條，可以減輕其刑，然後在洗錢防制部分應該適用舊法成功改判減輕的案例"
    ]
    
    for question in test_questions:
        print(f"\n問題: {question}")
        print("-" * 50)
        structured = extract_filter_conditions(question)
        print("結構化輸出:", structured)
        qdrant = to_qdrant_filter(structured)
        print("Qdrant Filter:", qdrant)
        qdrant_python = to_qdrant_filter_python(structured)
        print("Qdrant Python Filter:", qdrant_python)
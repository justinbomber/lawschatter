import os
from law_tokenize import JiebaLawTokenizer
from openai import OpenAI
from typing import Optional, Literal, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from qdrant_client import models

current_dir = os.path.dirname(os.path.abspath(__file__))
# parent_dir = os.path.dirname(current_dir)
dict_path = os.path.join(current_dir, "dict.txt.big")
tokenizer = JiebaLawTokenizer(
            dict_path=dict_path,
            cut_all=False,
            doc_hmm=False,
            query_hmm=True,
        )

load_dotenv()
class Defendant(BaseModel):
    # 基本信息
    defendant_name: Optional[str] = Field(default=None, description="被告姓名")

    # 辯護人相關
    has_defense_attorney: Optional[bool] = Field(default=None, description="被告是否有選任辯護人")
    defense_attorney_name: Optional[str] = Field(default=None, description="辯護人名稱（若 has_defense_attorney 為 true 時填寫，否則填空字串）")

    # 起訴法條變更
    indictment_changed: Optional[bool] = Field(default=None, description="是否變更起訴法條（若同一條文但項次不同，仍視為變更）")
    original_indictment_articles: Optional[List[str]] = Field(default=None, description="原本起訴法條（若 indictment_changed 為 true 時填寫，有幾條填幾條）")
    changed_indictment_articles: Optional[List[str]] = Field(default=None, description="變更起訴法條（若 indictment_changed 為 true 時填寫，有幾條填幾條）")

    # 新舊法問題
    has_new_old_law_issue: Optional[bool] = Field(default=None, description="本件是否有新舊法適用的問題")
    new_old_law_disputed_article: Optional[str] = Field(default=None, description="新舊法爭議的法條（若 has_new_old_law_issue 為 true 時填寫）")

    # 自白與陳述
    has_contradictory_statements: Optional[bool] = Field(default=None, description="是否有審理中與偵查中就核心事實或主要辯解內容出現矛盾、否認、或重大變更之陳述")
    confession_status: Optional[Literal["完全認罪", "完全否認", "部分"]] = Field(default=None, description="是否在本次審理中認罪")

    # 判決結果
    is_full_acquittal: Optional[bool] = Field(default=None, description="本件是否為全部無罪判決")
    is_acquittal_due_to_insufficient_evidence: Optional[bool] = Field(default=None, description="是否因為罪證不足而獲得全部無罪判決（若 is_full_acquittal 為 true 時填寫）")
    is_other_verdict: Optional[bool] = Field(default=None, description="本件是否為無罪、有罪以外的判決結果")
    is_conviction: Optional[bool] = Field(default=None, description="本件是否為有罪判決")

    # 罪名與法條
    crime_list: Optional[List[str]] = Field(default=None, description="本次罪名清單（若 is_conviction 為 true 時填寫，例如：「三人以上共同詐欺取財罪」、「洗錢未遂罪」，關鍵字是 XXX 罪）")
    violated_law_articles: Optional[List[str]] = Field(default=None, description="所違反的法律條文（若 is_conviction 為 true 時填寫，列出具體法條與條次，關鍵字 XXX 條 XXX 項）")

    # 刑罰
    is_fixed_term_imprisonment: Optional[bool] = Field(default=None, description="本件是否為有期徒刑")
    fixed_term_years: Optional[int] = Field(default=None, description="有期徒刑年數（若 is_fixed_term_imprisonment 為 true 時填寫，否則填 0）")
    fixed_term_months: Optional[int] = Field(default=None, description="有期徒刑月數（若 is_fixed_term_imprisonment 為 true 時填寫，否則填 0）")
    is_life_imprisonment: Optional[bool] = Field(default=None, description="本件是否為無期徒刑")
    is_death_penalty: Optional[bool] = Field(default=None, description="本件是否為死刑")
    is_detention: Optional[bool] = Field(default=None, description="本件是否為拘役")
    detention_days: Optional[int] = Field(default=None, description="拘役天數（若 is_detention 為 true 時填寫，否則填 0）")

    # 罰金
    has_concurrent_fine: Optional[bool] = Field(default=None, description="本件是否併科罰金")
    fine_amount: Optional[int] = Field(default=None, description="罰金金額（新臺幣，若 has_concurrent_fine 為 true 時填寫，否則填 0）")
    may_convert_to_fine: Optional[bool] = Field(default=None, description="本件是否得易科罰金（易科罰金不需要折算率）")

    # 緩刑
    has_probation: Optional[bool] = Field(default=None, description="本件是否給予緩刑")
    probation_period: Optional[str] = Field(default=None, description="給予緩刑之期間（若 has_probation 為 true 時填寫，例如：「2年」、「3年6月」）")

    # 減刑
    has_mitigation_articles: Optional[bool] = Field(default=None, description="本件是否有適用減刑的條文")
    mitigation_articles: Optional[str] = Field(default=None, description="適用減刑的條文為（若 has_mitigation_articles 為 true 時填寫）")

    # 和解
    has_settlement: Optional[bool] = Field(default=None, description="本件是否與被害人或告訴人和解")
    settlement_amount: Optional[int] = Field(default=None, description="和解之總金額（新臺幣，若 has_settlement 為 true 時填寫，否則填 0）")
    is_settlement_fulfilled: Optional[bool] = Field(default=None, description="法院是否認定和解已經履行（若 has_settlement 為 true 時填寫）")
    is_settlement_installment: Optional[bool] = Field(default=None, description="本件和解是否分期（若 has_settlement 為 true 時填寫）")

    # 證人
    has_witnesses: Optional[bool] = Field(default=None, description="本件是否有證人（被告以外之人，包含共同被告）")
    witness_testified_in_investigation: Optional[bool] = Field(default=None, description="證人是否有在偵查中作證（若 has_witnesses 為 true 時填寫）")
    witness_testified_in_trial: Optional[bool] = Field(default=None, description="證人是否有在審判中作證（若 has_witnesses 為 true 時填寫）")

    # 扣押沒收
    has_seized_items: Optional[bool] = Field(default=None, description="本件是否有遭扣押物品")
    seized_items: Optional[List[str]] = Field(default=None, description="本件遭扣押物品（若 has_seized_items 為 true 時填寫）")
    has_confiscated_items: Optional[bool] = Field(default=None, description="本件是否遭沒收物品")
    confiscated_items: Optional[List[str]] = Field(default=None, description="本件遭沒收物品（若 has_confiscated_items 為 true 時填寫）")

    # 接續犯
    is_continuous_offense: Optional[Literal["是", "否", "未提及"]] = Field(default=None, description="本件被告是否屬於接續犯")

    # 審級
    is_first_instance: Optional[bool] = Field(default=None, description="是否為一審判決")
    is_second_instance: Optional[bool] = Field(default=None, description="是否為二審判決")
    is_third_instance: Optional[bool] = Field(default=None, description="是否為三審判決")
    has_previous_instance: Optional[bool] = Field(default=None, description="是否有原審（前審）判決（是否為上訴案件）")

    # 上訴相關
    is_reversed_and_remanded: Optional[bool] = Field(default=None, description="是否撤銷改判（若 has_previous_instance 為 true 時填寫）")
    is_sentence_reduced: Optional[bool] = Field(default=None, description="是否減輕量刑（若 is_reversed_and_remanded 為 true 時填寫）")
    is_sentence_increased: Optional[bool] = Field(default=None, description="是否加重量刑（若 is_reversed_and_remanded 為 true 時填寫）")
    is_law_article_changed_from_previous: Optional[bool] = Field(default=None, description="是否變更原審（前審）適用法條（若 has_previous_instance 為 true 時填寫）")
    changed_law_articles: Optional[List[str]] = Field(default=None, description="變更法條為（若 is_law_article_changed_from_previous 為 true 時填寫，有幾條填幾條）")
    previous_instance_confession_status: Optional[Literal["完全認罪", "完全否認", "部分", "不適用"]] = Field(default=None, description="原審（前審）是否有認罪（若 has_previous_instance 為 true 時填寫）")
    current_instance_confession_status: Optional[Literal["完全認罪", "完全否認", "部分", "不適用"]] = Field(default=None, description="本件（上訴案件）是否有認罪（若 has_previous_instance 為 true 時填寫）")
    has_inconsistent_statements_with_previous: Optional[bool] = Field(default=None, description="是否有與原審答辯或主要陳述內容不一致之情形（若 has_previous_instance 為 true 時填寫）")
    statement_difference_description: Optional[str] = Field(default=None, description="若有，請以一句話描述前後陳述的主要差異（若 has_inconsistent_statements_with_previous 為 true 時填寫）")

class CaseMetadata(BaseModel):
    first_instance: Optional[bool] = Field(default=None, description="是否為地方法院判決")
    second_instance: Optional[bool] = Field(default=None, description="是否為高等法院判決")
    third_instance: Optional[bool] = Field(default=None, description="是否為最高法院判決")
    case_type: Optional[Literal["刑法", "民法", "行政法"]] = Field(
        default=None, description="案件類型，只能為：刑法，民法，行政法其中一種"
    )
    jtitle_type: Optional[Literal[
        "詐欺", "毒品", "竊盜", "侵占", "妨害性自主", "傷害", "公共危險",
        "槍砲彈藥刀械", "偽造文書", "其他刑事", "債務給付類", "侵權行為／損害賠償類",
        "婚姻家庭類", "物權類", "公司／商事類", "勞資爭議類", "保險類", "其他民事"
    ]] = Field(
        default=None, description="案件標題類型，刑事案件包括：詐欺、毒品、竊盜、侵占、妨害性自主、傷害、公共危險、槍砲彈藥刀械、偽造文書、其他刑事；民事案件包括：債務給付類、侵權行為／損害賠償類、婚姻家庭類、物權類、公司／商事類、勞資爭議類、保險類、其他民事"
    )

class Filter(BaseModel):
    jid: Optional[str] = Field(default=None, description="判決書ID（例：TPHM,113,上訴,6418,20250617,1）")
    jid_full: Optional[str] = Field(default=None, description="完整判決書名稱，（例：臺灣高等法院刑事判決113年度上訴字第6418號）必填",)
    jyear: Optional[int] = Field(default=None, description="年度（例：113）")
    jcase: Optional[str] = Field(default=None, description="案件類型（例：上訴）")
    jno: Optional[str] = Field(default=None, description="案件編號（例：6418）")
    jdate: Optional[int] = Field(default=None, description="判決日期（例：20250617）")
    defendants: Optional[List[Defendant]] = Field(
        default=None, description="逐一被告之結構化資訊清單（可省略）"
    )
    case_metadata: Optional[CaseMetadata] = Field(
        default=None, description="案件元資料與審級/類型等資訊（可省略）"
    )
    # reconstruct_question: Optional[str] = Field(default=None, description="去除掉問題中已經被量化的條件後，重新組合的問題，必須一定要填")
    defendants_role: Optional[str] = Field(default=None, description="被告角色定位與功能，說明被告在整體犯罪結構中的位置與職能。若問句與此項無關直接留空。")
    A_fact: Optional[str] = Field(default=None, description="法院確認的行為事實與過程，純描述，不含法律用語。敘述法院確認的客觀行為內容與過程，包含行為時間、地點、方式、參與人等要素。若問句與此項無關直接留空。")
    B_claim: Optional[str] = Field(default=None, description= "被告主張與抗辯理由，無論採信與否均完整列出。列出被告於偵查或審理階段的抗辯內容與理由，無論法院是否採信都必須完整保留。若有多次不同說法可取主要版本或最終陳述。不得混入法院評論。若問句與此項無關直接留空。")
    C_court_finding: Optional[str] = Field(default=None, description="法院認定哪些事實成立，採信哪些證據或供述。敘述法院最終認為哪些事實成立、採信哪些證據、排除哪些辯詞。可含「法院認為」「法院採信」「法院不採信」等語。若問句與此項無關直接留空。")
    D_court_reason: Optional[str] = Field(default=None, description="法院推論、採信理由、法條適用與量刑考量。敘述法院的推論過程、採信邏輯、法律適用與量刑考量。可包含法律詞彙、判斷語氣與條文引用。若問句與此項無關直接留空。")
    E_legal_eval: Optional[str] = Field(default=None, description="法院最終法律評價、罪名與競合處理結果。簡述法院最終的法律結論，包括罪名、競合與量刑方向。可使用法律用語（如「共同正犯」「想像競合」「從一重詐欺罪處斷」等）。若問句與此項無關直接留空。")
    case_fact_summary: Optional[str] = Field(default=None, description="無法律評價。提供整體可閱讀的案件輪廓，描述被害人、主要行為流程、整體案件脈絡。若問句與此項無關直接留空。")


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
    
    for key in ["jid", "jid_full", "jyear", "jcase", "jno", "jdate"]:
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
            "case_type",
            "jtitle_type",
        ]:
            value = cm.get(key)
            if value is not None:
                must.append({"key": f"metadata.case_metadata.{key}", "match": {"value": value}})
        
        
    # Defendants (projected keys: metadata.defendants[].<field>)
    defendants_list = filter_dict.get("defendants") or []
    if isinstance(defendants_list, list):
        for d in defendants_list:
            defendant_fields = [
                # 基本信息
                "defendant_name",
                # 辯護人相關
                "has_defense_attorney", "defense_attorney_name",
                # 起訴法條變更
                "indictment_changed", "original_indictment_articles", "changed_indictment_articles",
                # 新舊法問題
                "has_new_old_law_issue", "new_old_law_disputed_article",
                # 自白與陳述
                "has_contradictory_statements", "confession_status",
                # 判決結果
                "is_full_acquittal", "is_acquittal_due_to_insufficient_evidence", "is_other_verdict", "is_conviction",
                # 罪名與法條
                "crime_list", "violated_law_articles",
                # 刑罰
                "is_fixed_term_imprisonment", "fixed_term_years", "fixed_term_months",
                "is_life_imprisonment", "is_death_penalty", "is_detention", "detention_days",
                # 罰金
                "has_concurrent_fine", "fine_amount", "may_convert_to_fine",
                # 緩刑
                "has_probation", "probation_period",
                # 減刑
                "has_mitigation_articles", "mitigation_articles",
                # 和解
                "has_settlement", "settlement_amount", "is_settlement_fulfilled", "is_settlement_installment",
                # 證人
                "has_witnesses", "witness_testified_in_investigation", "witness_testified_in_trial",
                # 扣押沒收
                "has_seized_items", "seized_items", "has_confiscated_items", "confiscated_items",
                # 接續犯
                "is_continuous_offense",
                # 審級
                "is_first_instance", "is_second_instance", "is_third_instance", "has_previous_instance",
                # 上訴相關
                "is_reversed_and_remanded", "is_sentence_reduced", "is_sentence_increased",
                "is_law_article_changed_from_previous", "changed_law_articles",
                "previous_instance_confession_status", "current_instance_confession_status",
                "has_inconsistent_statements_with_previous", "statement_difference_description"
            ]
            for key in defendant_fields:
                value = d.get(key)
                # 處理列表類型字段
                if key in ["crime_list", "violated_law_articles", "original_indictment_articles", "changed_indictment_articles", "seized_items", "confiscated_items", "changed_law_articles"]:
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
    
    # Top-level fields (prefix with metadata.)
    for key in ["jid_full", "jyear", "jcase", "jno", "jdate", "summary_type"]:
        value = filter_dict.get(key)
        print("------> values:" , value)
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
        elif key == "jyear" and value is not None:
            # 特殊處理年份字段，確保是整數
            if isinstance(value, int):
                must_conditions.append(
                    models.FieldCondition(
                        key=f"metadata.{key}",
                        match=models.MatchValue(value=value)
                    )
                )
        elif key == "jdate" and value is not None:
            # 特殊處理日期字段，確保是整數
            if isinstance(value, int):
                must_conditions.append(
                    models.FieldCondition(
                        key=f"metadata.{key}",
                        match=models.MatchValue(value=value)
                    )
                )
        elif value is not None:
            # 處理其他字段，確保是字符串或布林值
            if isinstance(value, (str, bool)):
                must_conditions.append(
                    models.FieldCondition(
                        key=f"metadata.{key}",
                        match=models.MatchValue(value=value)
                    )
                )
    
    # Case metadata (fields directly under metadata)
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
    
    # Defendants (array projection under metadata)
    defendants_list = filter_dict.get("defendants") or []
    if isinstance(defendants_list, list):
        for d in defendants_list:
            defendant_fields = [
                # 基本信息
                "defendant_name",
                # 辯護人相關
                "has_defense_attorney", "defense_attorney_name",
                # 起訴法條變更
                "indictment_changed", "original_indictment_articles", "changed_indictment_articles",
                # 新舊法問題
                "has_new_old_law_issue", "new_old_law_disputed_article",
                # 自白與陳述
                "has_contradictory_statements", "confession_status",
                # 判決結果
                "is_full_acquittal", "is_acquittal_due_to_insufficient_evidence", "is_other_verdict", "is_conviction",
                # 罪名與法條
                "crime_list", "violated_law_articles",
                # 刑罰
                "is_fixed_term_imprisonment", "fixed_term_years", "fixed_term_months",
                "is_life_imprisonment", "is_death_penalty", "is_detention", "detention_days",
                # 罰金
                "has_concurrent_fine", "fine_amount", "may_convert_to_fine",
                # 緩刑
                "has_probation", "probation_period",
                # 減刑
                "has_mitigation_articles", "mitigation_articles",
                # 和解
                "has_settlement", "settlement_amount", "is_settlement_fulfilled", "is_settlement_installment",
                # 證人
                "has_witnesses", "witness_testified_in_investigation", "witness_testified_in_trial",
                # 扣押沒收
                "has_seized_items", "seized_items", "has_confiscated_items", "confiscated_items",
                # 接續犯
                "is_continuous_offense",
                # 審級
                "is_first_instance", "is_second_instance", "is_third_instance", "has_previous_instance",
                # 上訴相關
                "is_reversed_and_remanded", "is_sentence_reduced", "is_sentence_increased",
                "is_law_article_changed_from_previous", "changed_law_articles",
                "previous_instance_confession_status", "current_instance_confession_status",
                "has_inconsistent_statements_with_previous", "statement_difference_description"
            ]
            
            # for key in defendant_fields:
            #     value = d.get(key)
            #     # 處理列表類型字段
            #     if key in ["crime_list", "violated_law_articles", "original_indictment_articles", "changed_indictment_articles", "seized_items", "confiscated_items", "changed_law_articles"]:
            #         if value and isinstance(value, list):
            #             # 列表字段，需要為每個項目創建條件
            #             list_conditions = []
            #             for item in value:
            #                 if isinstance(item, str):
            #                     # 對每個項目進行分詞
            #                     seperate_item_lst = tokenizer.run_doc(item)
            #                     for seperate_item in seperate_item_lst:
            #                         if seperate_item.strip():  # 確保不添加空字符串
            #                             list_conditions.append(
            #                                 models.FieldCondition(
            #                                     key=f"metadata.defendants[].{key}[]",
            #                                     match=models.MatchPhrase(phrase=seperate_item)
            #                                 )
            #                             )
            #             # 使用 OR 條件，任何一個項目匹配即可
            #             if list_conditions:
            #                 if len(list_conditions) == 1:
            #                     must_conditions.append(list_conditions[0])
            #                 else:
            #                     must_conditions.append(models.Filter(should=list_conditions))
            #     elif key == "defendant_name":
            #         # 使用 phrase match 進行包含匹配，而不是完全匹配
            #         if value is not None and isinstance(value, str):
            #             must_conditions.append(
            #                 models.FieldCondition(
            #                     key=f"metadata.defendants[].{key}",
            #                     match=models.MatchPhrase(phrase=value)
            #                 )
            #             )
            #     else:
            #         # 處理其他字段，確保是正確的數據類型
            #         if value is not None:
            #             if isinstance(value, (str, bool, int)):
            #                 must_conditions.append(
            #                     models.FieldCondition(
            #                         key=f"metadata.defendants[].{key}",
            #                         match=models.MatchValue(value=value)
            #                     )
            #                 )
    
    # return models.Filter(must=must_conditions) if must_conditions else models.Filter(), reconstruct_question
    return models.Filter(must=must_conditions) if must_conditions else models.Filter()

def extract_filter_conditions(user_question: str) -> list:
    """Extract filter conditions from user question.

    Returns:
        list: list of structured output with summary_type
    """
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
           - defendant_name: 被告姓名
           - has_defense_attorney: 是否有辯護人
           - defense_attorney_name: 辯護人姓名（需要 has_defense_attorney 為 true）
           - indictment_changed: 是否變更起訴法條
           - original_indictment_articles: 原本起訴法條（需要 indictment_changed 為 true）
           - changed_indictment_articles: 變更後法條（需要 indictment_changed 為 true）
           - confession_status: 認罪狀態（完全認罪/完全否認/部分）
           - is_conviction: 是否為有罪判決
           - crime_list: 罪名清單（需要 is_conviction 為 true）
           - violated_law_articles: 違反法條清單（需要 is_conviction 為 true）
           - 刑罰相關：is_fixed_term_imprisonment, fixed_term_years, fixed_term_months, is_life_imprisonment, is_death_penalty, is_detention, detention_days, has_concurrent_fine, fine_amount, may_convert_to_fine, has_probation, probation_period 等
           - 其他：has_witnesses, has_seized_items, seized_items, has_confiscated_items, confiscated_items, is_continuous_offense 等

        範例：
        - 問題：「幫我查上訴至高等法院的詐欺案件」
        合法輸出：
        {
            "case_metadata": { "second_instance": true, "jtitle_type": "詐欺" },
            "defendants": [ { "crime_list": ["詐欺"] } ]
        }

        - 問題：「找有期徒刑被告認罪但獲得緩刑的案例」
        合法輸出：
        {
            "defendants": [
                {
                    "is_fixed_term_imprisonment": true,
                    "confession_status": "完全認罪",
                    "has_probation": true
                }
            ]
        }

        輸出要求：
        - 只需要輸出實際存在的過濾條件，不要推測或添加不存在的條件
        - 數組字段使用列表格式，如 ["詐欺", "洗錢"]
        - 布林值使用 true/false
        - 字符串使用引號包裹
        - 如果問題中沒有提到任何過濾條件，請忽略，並且不允許猜測或添加預設值
        - "defendants_role", "A_fact", "B_claim", "C_court_finding", "D_court_reason", "E_legal_eval", "case_fact_summary"一定要選一個填入
        """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable is required")
    client = OpenAI(api_key=api_key)    
    response = client.responses.parse(
        model="gpt-5",
        input=[
            {"role": "system", "content": system_prompt}, 
            {"role": "user", "content": user_question}],
        text_format=Filter,
    )
    result = response.output_parsed
    non_clean_structured_output = result.model_dump(exclude_none=False, exclude_unset=False)
    print(f"---> non_clean_structured_output: {non_clean_structured_output}")
    structured_output = result.model_dump(exclude_none=True, exclude_unset=True)
    # structured_output = {'defendants': [{'crime_list': ['詐欺', '偽造文書']}], 'case_metadata': {'jtitle_type': '詐欺'}, 'defendants_role': '詐欺集團一線面交車手，依上游指示偽造並使用工作證、收據出面收款，收款後轉交收水以切斷金流。'}
    print("結構化輸出:", structured_output)

    # 檢查並處理 A_fact, B_claim, C_court_finding, D_court_reason, E_legal_eval, case_fact_summary 欄位
    output_lst = []
    summary_fields = ["defendants_role", "A_fact", "B_claim", "C_court_finding", "D_court_reason", "E_legal_eval", "case_fact_summary"]
    _metadata = structured_output
    tmp_summary = {}
    for field in summary_fields:
        if field in structured_output and structured_output[field]:
            tmp_summary[field] = _metadata[field]
            del _metadata[field]
    print("---> tmp_metadata: ", _metadata)
    print("---> tmp summary: ", tmp_summary)
    for summary_type in tmp_summary:
        tmp_metadata = _metadata
        tmp_metadata[summary_type] = tmp_summary[summary_type]
        # 根據字段類型設置正確的summary_type值
        tmp_metadata["summary_type"] = [summary_type]
        output_lst.append(tmp_metadata)
            
    return output_lst


if __name__ == "__main__":
    # Test cases
    test_questions = [
        "有沒有未認罪，但法院還是給予緩刑的詐欺車手案例",
        "請問有沒有提供帳戶的詐欺案件，被告沒有提供任何對話紀錄，法院還是給予無罪的案例",
        "有沒有被告在二審主張依詐欺犯罪危害防制條例第47條，可以減輕其刑，然後在洗錢防制部分應該適用舊法成功改判減輕的案例",
        "幫我查上訴至高等法院的詐欺案件",
        "找有期徒刑被告認罪但獲得緩刑的案例"
    ]

    for question in test_questions:
        print(f"\n問題: {question}")
        print("-" * 50)
        structured_list = extract_filter_conditions(question)
        print("結構化輸出列表:", structured_list)

        # 處理每個結果項目
        for i, structured in enumerate(structured_list):
            print(f"結果 {i+1}:", structured)
            qdrant = to_qdrant_filter(structured)
            print("Qdrant Filter:", qdrant)
            qdrant_python = to_qdrant_filter_python(structured)
            print("Qdrant Python Filter:", qdrant_python)
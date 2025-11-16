# Filter 架構設計（簡化版）

## 設計原則

**開發階段：簡單優先，所有邏輯都在 `query_strategy.py`**

## 架構

```
使用者查詢
    ↓
QueryStrategy._build_filter()  # 在 query_strategy.py 中
    ↓ 轉換
Qdrant Filter 物件
    ↓
QueryStrategy.hybrid_search()
```

## 實作位置

所有 filter 相關邏輯都在 `query_strategy.py` 中：

1. **`_build_filter()` 方法**：將 filter 字典轉換為 Qdrant Filter
2. **`search()` 方法**：接受 filter 參數並使用

## Filter 字典結構

```python
filter_dict = {
    # 基本欄位
    "doc_level": "case",  # 或 "defendant"（重要！）
    "jid": "COURT,114,簡上,121,20250630,1",
    "jyear": 113,
    "jcase": "簡上",
    "jno": "121",
    "case_type": "刑法",  # 頂層欄位
    
    # case_metadata
    "case_metadata": {
        "first_instance": True,
        "second_instance": False,
        "jtitle_type": "詐欺"
    },
    
    # defendants（簡化：只處理第一個）
    "defendants": [{
        "has_probation": True,
        "is_conviction": True,
        "fixed_term_months": 5
    }],
    
    # 否定欄位
    "negated_fields": ["case_metadata.first_instance", "defendants.has_probation"]
}
```

## 實作建議

在 `query_strategy.py` 中加入：

```python
def _build_filter(self, filter_dict: Dict[str, Any]) -> Optional[models.Filter]:
    """
    將 filter 字典轉換為 Qdrant Filter
    
    所有邏輯都在這裡，方便修改和測試
    """
    # TODO: 實作轉換邏輯
    # 參考: rag-seperate/services/filter_service.py 的 to_qdrant_filter()
    pass
```

## 與 rag-seperate 的差異

| 特性 | rag-seperate | rag-concat |
|------|-------------|------------|
| **doc_level** | ❌ 沒有 | ✅ 有（重要！） |
| **case_type** | `case_metadata.case_type` | 頂層 `case_type` |
| **summary_type** | ✅ 有 | ❌ 沒有 |
| **架構複雜度** | 多檔案分離 | 單一檔案 |

## 未來擴展

如果 filter 邏輯變複雜，再考慮：
1. 抽成 `filter_builder.py`（單一檔案）
2. 加入 `filter_extraction_service.py`（自動提取）

但目前：**保持簡單，都在 query_strategy.py**

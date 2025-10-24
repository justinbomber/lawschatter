# 判決書重複內容防範指南

## 概述

這個解決方案旨在防止在 `main_judgments` 表中插入內容相同的判決書，即使其他欄位（如 `jid`、`jyear` 等）可能不同。

## 主要功能

### 1. 精確重複檢測
- **雜湊機制**：使用 SHA256 雜湊值檢測完全相同的 `jfull` 內容
- **自動防護**：插入觸發器會在插入前自動檢查重複
- **唯一性約束**：`jfull_hash` 欄位具有唯一性約束

### 2. 智能相似度檢測
- **PGroonga 支援**：利用 PGroonga 全文搜索進行相似度分析
- **可調閾值**：可設定相似度閾值（預設 0.8）
- **警告機制**：發現高相似度內容時會產生通知

## 使用方式

### 初始設定

1. **執行主要架構**：
```sql
\i supabase/db_schema/laws.sql
```

2. **執行防重複方案**：
```sql
\i supabase/db_schema/prevent_duplicate_content.sql
```

3. **為現有資料生成雜湊值**：
```sql
SELECT update_existing_jfull_hashes();
```

### 日常使用

#### 插入新判決書
```sql
-- 正常插入，系統會自動檢查重複
INSERT INTO lawschatter.main_judgments 
(jid, jyear, jcase, jno, jdate, jtitle, jfull, jpdf)
VALUES 
('CHDM,113,易,100,20250129,1', '113', '易', '100', '20250129', 
 '詐欺案件', '判決書全文內容...', 'https://example.com/pdf');
```

#### 檢查重複前預先驗證
```sql
-- 檢查特定內容是否已存在
SELECT check_duplicate_jfull_content('您要檢查的判決書內容...');

-- 檢查相似內容
SELECT * FROM check_similar_jfull_content('您要檢查的判決書內容...', 0.8);
```

#### 查看重複資料
```sql
-- 檢視所有重複內容
SELECT * FROM lawschatter.duplicate_content_analysis;
```

#### 合併重複資料
```sql
-- 合併特定雜湊值的重複記錄（保留最早的一筆）
SELECT merge_duplicate_content_records('your_hash_value_here');
```

## 錯誤處理

### 重複內容錯誤
當插入重複內容時，會收到以下錯誤：
```
ERROR: 判決書內容重複：已存在相同內容的判決書記錄 (Hash: abc123...)
HINT: 請檢查是否為重複資料
```

### 解決方案
1. **確認是否真的重複**：使用雜湊值查詢現有記錄
2. **更新現有記錄**：如果新資料有更完整的資訊
3. **忽略插入**：如果確實是重複資料

## 監控和維護

### 定期檢查
```sql
-- 檢查系統中的重複狀況
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT jfull_hash) as unique_content,
    COUNT(*) - COUNT(DISTINCT jfull_hash) as duplicate_count
FROM lawschatter.main_judgments 
WHERE jfull_hash IS NOT NULL;
```

### 效能優化
- **PGroonga 索引**：定期重建全文搜索索引
- **雜湊索引**：確保 `jfull_hash` 索引效能
- **清理作業**：定期清理確認的重複資料

## 技術細節

### 雜湊計算
- 演算法：SHA256
- 預處理：移除多餘空白，標準化格式
- 長度：64 字元十六進位字串

### PGroonga 設定
- 索引類型：全文搜索索引
- 相似度演算法：TF-IDF 基礎
- 預設閾值：0.8 (80% 相似度)

### 效能考量
- 插入效能：每次插入需額外計算雜湊值（約 1-2ms）
- 查詢效能：雜湊查詢為 O(1) 複雜度
- 儲存空間：每筆記錄額外 64 bytes

## 注意事項

1. **備份重要性**：在執行合併操作前請先備份資料
2. **相似度設定**：根據實際需求調整相似度閾值
3. **內容標準化**：確保輸入的 `jfull` 內容格式一致
4. **定期維護**：建議定期檢查和清理重複資料

## 常見問題

### Q: 如何處理格式略有不同但內容相同的判決書？
A: 使用 PGroonga 相似度檢測功能，可以捕捉到高相似度的內容。

### Q: 可以停用重複檢查嗎？
A: 可以暫時停用觸發器：
```sql
ALTER TABLE lawschatter.main_judgments DISABLE TRIGGER prevent_duplicate_jfull_trigger;
```

### Q: 如何調整相似度閾值？
A: 修改 `check_similar_jfull_content` 函數的預設參數，或在呼叫時指定不同的閾值。

## 支援

如需技術支援或有任何問題，請查閱：
- PostgreSQL 官方文件
- PGroonga 官方文件
- 專案內部技術文件

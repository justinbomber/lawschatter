# Judgment RAR Upload Service

## 功能特點

1. **自動判決ID提取**: 從判決全文的前兩個換行符提取判決ID
2. **檔案自動清理**: 處理完每個JSON檔案後自動刪除，全部處理完後刪除整個資料夾
3. **啟動時自動處理**: 程式啟動時自動處理extracted目錄中的現有檔案（按日期優先級）
4. **檔案處理排隊**: 支援在處理檔案時接受新的上傳檔案並排隊處理

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your actual values
```

3. Run the service:
```bash
cd /home/justin/law-chatbot/scrapy/zipupdate
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python main.py
```

或者

```bash
cd /home/justin/law-chatbot/scrapy/zipupdate
python -m src.api.main
```

## API 端點

- `POST /upload-rar` - 上傳包含JSON判決檔案的RAR檔案
- `GET /health` - 健康檢查端點
- `GET /queue-status` - 獲取處理佇列狀態
- `POST /process-extracted` - 手動觸發處理現有的extracted目錄

## Environment Variables

- `SUPABASE_URL`: Supabase 資料庫 URL
- `SUPABASE_SERVICE_KEY`: 資料庫存取的服務角色金鑰
- `TARGET_SCHEMA`: 資料庫架構名稱
- `TARGET_TABLE`: 目標資料表名稱

## 檔案處理流程

1. **上傳處理**: RAR檔案上傳後加入處理佇列
2. **自動解壓**: 系統自動解壓RAR檔案
3. **JSON處理**: 逐一處理JSON檔案，提取判決資料
4. **資料庫插入**: 將處理好的資料插入Supabase資料庫
5. **檔案清理**: 處理完的JSON檔案自動刪除
6. **目錄清理**: 全部處理完後刪除整個解壓目錄

## 排隊系統

- 支援多檔案同時上傳
- 背景處理避免阻塞API回應
- 自動處理現有extracted目錄
- 按日期優先級處理（較新的優先）
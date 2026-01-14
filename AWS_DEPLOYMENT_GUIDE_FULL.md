# AWS Lambda & Secrets Manager 部署全攻略

本文件詳細記錄如何將本專案 (`chatbot` 和 `ragserver`) 部署至 AWS Lambda，並使用 Secrets Manager 安全管理環境變數。

## 目錄
1. [架構總覽](#架構總覽)
2. [前置準備](#前置準備)
3. [Secrets Manager 設定 (UI 操作)](#secrets-manager-設定-ui-操作)
4. [IAM 權限設定](#iam-權限設定)
5. [部署 RagServer (容器化部署)](#部署-ragserver-容器化部署)
6. [部署 Chatbot (Zip 部署)](#部署-chatbot-zip-部署)
7. [API Gateway 設定](#api-gateway-設定)
8. [常見問題](#常見問題)

---

## 架構總覽

```plantuml
[前端 (Vite/S3)] --> [API Gateway (HTTP API)]
                          |
        ------------------------------------
        |                                  |
   [Lambda: Chatbot]               [Lambda: RagServer]
   (Zip 部署, 輕量級)               (Container 部署, 含 Qdrant/FastEmbed)
        |                                  |
        v                                  v
[Secrets Manager (boto3)]       [Secrets Manager (boto3)]
        |                                  |
        v                                  v
[OpenAI / Supabase]             [Qdrant / Supabase / Google AI]
```

---

## 前置準備

1.  **AWS 帳號**: 確認你有權限存取 Lambda, Secrets Manager, ECR, IAM。
2.  **AWS CLI**: 安裝並設定 (`aws configure`)。
3.  **Docker**: 用於建置 RagServer 映像檔。
4.  **Python 3.12**: 用於打包 Chatbot。

---

## Secrets Manager 設定 (UI 操作)

我們使用 AWS Secrets Manager 來儲存 API Key，且程式碼已設定為使用 `boto3` 直接讀取。

### 步驟 1: 建立 Chatbot Secret
1.  登入 AWS Console，搜尋 **Secrets Manager**。
2.  點擊 **"Store a new secret"**。
3.  **Secret type**: 選擇 **"Other type of secret"**。
4.  **Key/value pairs**:
    *   `LLM_API_KEY`: (OpenAI API Key)
    *   `SUPABASE_URL`: (Supabase 網址)
    *   `SUPABASE_KEY`: (Supabase Anon Key)
    *   `RAG_SERVER_URL`: (部署後的 RagServer API Gateway 網址，稍後回來填)
5.  點擊 **Next**。
6.  **Secret name**: 輸入 `lawschatter/chatbot/config`。
7.  點擊 **Next** -> **Store**。

### 步驟 2: 建立 RagServer Secret
1.  重複上述步驟。
2.  **Key/value pairs**:
    *   `OPENAI_API_KEY`: (OpenAI API Key)
    *   `GENAI_EMBEDDING_API_KEY`: (Google AI Key)
    *   `SUPABASE_URL`: (Supabase 網址)
    *   `SUPABASE_KEY`: (Supabase Anon Key)
    *   `QDRANT_CLIENT`: (Qdrant Cloud URL 或自建 Qdrant 網址)
    *   `COLLECTION_NAME`: (例如 embedding-seperate)
3.  **Secret name**: 輸入 `lawschatter/ragserver/config`。

---

## IAM 權限設定

Lambda 需要權限才能讀取 Secrets Manager。

1.  進入 **IAM** -> **Roles**，找到你的 Lambda Execution Role (或新建一個)。
2.  新增 **Inline Policy** (或建立 Managed Policy)：
    ```json
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "secretsmanager:GetSecretValue",
                "Resource": "arn:aws:secretsmanager:*:*:secret:lawschatter/*"
            }
        ]
    }
    ```
3.  確認該 Role 也有 `AWSLambdaBasicExecutionRole` (寫入 CloudWatch Logs 權限)。

---

## 部署 RagServer (容器化部署)

由於 RagServer 依賴龐大 (`fastembed`, `numpy`, `jieba`)，即使壓縮也超過 Lambda Zip 的 250MB 限制，因此**必須使用 Docker Container 部署**。

### 步驟 1: 建立 ECR Repository
```bash
aws ecr create-repository --repository-name lawschatter-ragserver --region ap-south-1
```

### 步驟 2: 建置並推送 Docker Image
在 `ragserver/rag-seperate/` 目錄下執行：

```powershell
# 1. 登入 ECR (替換 YOUR_ACCOUNT_ID)
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com

# 2. 建置 Docker Image (使用 Dockerfile.lambda)
docker build -t lawschatter-ragserver -f Dockerfile.lambda .

# 3. 標記 Image
docker tag lawschatter-ragserver:latest YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/lawschatter-ragserver:latest

# 4. 推送至 ECR
docker push YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/lawschatter-ragserver:latest
```

### 步驟 3: 建立 Lambda Function
1.  進入 **Lambda** -> **Create function**。
2.  選擇 **"Container image"**。
3.  **Function name**: `lawschatter-ragserver`。
4.  **Container image URI**: 選擇剛上傳的 Image。
5.  **Architecture**: x86_64。
6.  **Change default execution role**: 選擇前面設定好權限的 Role。
7.  建立後，進入 **Configuration** -> **General configuration**：
    *   **Timeout**: 設定為 `60` 秒 (防止冷啟動超時)。
    *   **Memory**: 建議 `2048 MB` (向量運算需要較多記憶體)。
8.  進入 **Configuration** -> **Environment variables**：
    *   新增 `AWS_REGION`: `ap-south-1` (確保 boto3 連到正確區域)。

---

## 部署 Chatbot (Zip 部署)

Chatbot 依賴較輕 (`fastapi`, `openai`)，可用傳統 Zip 方式部署。

### 步驟 1: 打包程式碼
在 `chatbot/` 目錄下執行：

```powershell
# 1. 建立部署資料夾
mkdir package
cd package

# 2. 安裝依賴到當前目錄
pip install -r ..\requirements.txt -t .
# 記得也要安裝 boto3 (雖然 Lambda 內建，但有些版本可能較舊，建議安裝)
pip install boto3 -t .

# 3. 複製專案程式碼
xcopy /E /I /Y ..\config config
xcopy /E /I /Y ..\controllers controllers
xcopy /E /I /Y ..\domain domain
xcopy /E /I /Y ..\entities entities
xcopy /E /I /Y ..\infrastructure infrastructure
xcopy /E /I /Y ..\services services
copy ..\main.py .

# 4. 壓縮成 Zip
powershell Compress-Archive -Path * -DestinationPath ..\chatbot-lambda.zip -Force
cd ..
```

### 步驟 2: 建立 Lambda Function
1.  進入 **Lambda** -> **Create function**。
2.  選擇 **"Author from scratch"**。
3.  **Function name**: `lawschatter-chatbot`。
4.  **Runtime**: Python 3.12。
5.  **Change default execution role**: 選擇設定好權限的 Role。
6.  建立後，點擊 **"Upload from"** -> **".zip file"** -> 上傳 `chatbot-lambda.zip`。
7.  **Handler**: 設定為 `main.handler` (因為我們在 main.py 最後加了 Mangum handler)。
8.  進入 **Configuration** -> **Environment variables**：
    *   新增 `AWS_REGION`: `ap-south-1`。

---

## API Gateway 設定

為了讓外部能存取 Lambda，我們需要設定 API Gateway。

1.  進入 **API Gateway** -> **Create API**。
2.  選擇 **HTTP API** (較便宜且效能好)。
3.  **Integrations**:
    *   新增 **Lambda**: `lawschatter-chatbot`。
    *   新增 **Lambda**: `lawschatter-ragserver`。
4.  **Configure routes**:
    *   `POST /chat/completion` -> 指向 `lawschatter-chatbot`
    *   `POST /search` -> 指向 `lawschatter-ragserver`
    *   `GET /docs` -> 指向 `lawschatter-chatbot` (如果你想看 swagger)
5.  **Deploy**: 選擇 **$default** stage (自動部署)。
6.  取得 **Invoke URL**，這就是你的 API 網址。

**最後更新**：
回到 Secrets Manager，修改 `lawschatter/chatbot/config`，將 `RAG_SERVER_URL` 更新為 API Gateway 的 Invoke URL。

---

## 常見問題

### Q: 為什麼 RagServer 會出現 "Runtime.ImportModuleError"?
A: 通常是因為 `fastembed` 或 `onnxruntime` 的 C++ 依賴在庫與 Lambda 環境不相容。這就是為什麼我們強烈建議使用 **Docker Container** 部署，因為你可以確保環境完全一致。

### Q: 如何解決 Cold Start (冷啟動) 慢的問題？
A:
1.  **增加記憶體**: Lambda 的 CPU 算力與記憶體成正比，開到 1769MB 會有 1 vCPU。
2.  **Provisioned Concurrency**: 付費讓 AWS 保持你的 Lambda 暖機 (適合生產環境)。

### Q: Secrets Manager 讀取失敗？
A:
1.  檢查 **Region**: 程式碼預設 `ap-south-1`，確認你的 Secret 也在同區域。
2.  檢查 **IAM**: 確認 Role 有 `secretsmanager:GetSecretValue`。
3.  檢查 **Secret Name**: 確認程式碼中的名稱 `lawschatter/chatbot/config` 與 Console 一致。

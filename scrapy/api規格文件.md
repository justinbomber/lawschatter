# 司法院裁判書開放 API 文件（Markdown 版本）

> 本文件僅針對「驗證權限」、「取得裁判書異動清單」與「取得裁判書內容」三支 RESTful API 進行整理。資料格式皆為 JSON。

---

## 1. 驗證權限（Auth）

| 項目            | 說明 |
| --------------- | ---- |
| 功能            | 驗證帳號／密碼並取得 `token` |
| HTTP Method     | `POST` |
| URL             | `https://data.judicial.gov.tw/jdg/api/Auth` |
| Content-Type    | `application/json` |
| Token 效期      | 6 小時（逾時需重新驗證） |

### Request Body

```json
{
  "user": "your_account",
  "password": "your_password"
}
```

### Success Response

```json
{
  "token": "ddf8bb4f32f746bdb5510c1eed76db51"
}
```

### Error Response

```json
{
  "error": "驗證失敗"
}
```

---

## 2. 取得裁判書異動清單（JList）

| 項目            | 說明 |
| --------------- | ---- |
| 功能            | 取得「最近 7 日」內的裁判書異動清單 |
| HTTP Method     | `POST` |
| URL             | `https://data.judicial.gov.tw/jdg/api/JList` |
| Content-Type    | `application/json` |
| 使用時間        | 每日 00:00–06:00 |

### Request Body

```json
{
  "token": "ddf8bb4f32f746bdb5510c1eed76db51"
}
```

### Success Response

```json
[
  {
    "DATE": "2016-12-23",
    "LIST": [
      "CDEV,105,橋司附民移調,101,20161219,1",
      "CDEV,105,橋司附民移調,95,20161219,1",
      "CDEV,105,橋司附民移調,98,20161219,1"
      // ...
    ]
  },
  {
    "DATE": "2016-12-24",
    "LIST": [
      "CYDM,105,原訴,12,20161214,1",
      "CYDM,105,朴簡,498,20161216,1",
      "CYDM,105,易,509,20161216,1"
      // ...
    ]
  }
]
```

### Error Response

```json
{
  "error": "驗證失敗"
}
```

---

## 3. 取得裁判書內容（JDoc）

| 項目            | 說明 |
| --------------- | ---- |
| 功能            | 依 `jid` 取得裁判書完整內容與附件 |
| HTTP Method     | `POST` |
| URL             | `https://data.judicial.gov.tw/jdg/api/JDoc` |
| Content-Type    | `application/json` |
| 使用時間        | 每日 00:00–06:00 |

### Request Body

```json
{
  "token": "ddf8bb4f32f746bdb5510c1eed76db51",
  "j": "CHDM,105,交訴,51,20161216,1"
}
```

### 成功範例（全文型態為 **text**）

```json
{
  "ATTACHMENTS": [
    {
      "TITLE": "附表三.pdf",
      "URL": "https://data.judicial.gov.tw/jdg/api/JFile/CHDM/100%2c%e8%a8%b4%2c1552%2c1020517%2c2%2cCHDM1025H015_003.pdf"
    },
    {
      "TITLE": "附表一.pdf",
      "URL": "https://data.judicial.gov.tw/jdg/api/JFile/CHDM/100%2c%e8%a8%b4%2c1552%2c1020517%2c2%2cCHDM1025H015_001.pdf"
    }
  ],
  "JFULLX": {
    "JFULLTYPE": "text",
    "JFULLCONTENT": "（裁判書全文文字內容……）",
    "JFULLPDF": ""
  },
  "JID": "CHDM,105,交訴,51,20161216,1",
  "JYEAR": "105",
  "JCASE": "交訴",
  "JNO": "51",
  "JDATE": "2016-12-16",
  "JTITLE": "（裁判案由）"
}
```

### 可能的 `JFULLTYPE`

| 值   | 說明                         |
| ---- | ---------------------------- |
| text | `JFULLCONTENT` 為文字內容；`JFULLPDF` 為空字串 |
| file | `JFULLCONTENT` 為空字串；`JFULLPDF` 為 PDF 下載網址 |

### 移除或異動

若回傳：

```json
{
  "error": "查無資料，本裁判可能未公開或已從系統移除，若您曾經下載過本裁判，亦請您將其移除！謝謝！"
}
```

代表該裁判書已被移除或不再公開，應將本地資料同步刪除或更新。

---

## 裁判書異動處理建議

1. 若同一 `jid` 再度出現在異動清單，表示該筆資料已更新，應以新資料覆蓋舊資料。  
2. 若 API 回傳「查無資料」訊息，須將先前下載的該筆裁判書刪除以保障當事人隱私。

---

## 注意事項

- API 僅於每日 **00:00–06:00** 提供服務。  
- 呼叫 `JList` 與 `JDoc` 前，必須先以 `Auth` 取得有效 `token`。  
- 所有 JSON 欄位皆為 UTF-8 編碼。
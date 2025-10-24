
#!/usr/bin/env python3
"""
將 json-output/ 目錄下的 JSON 檔案處理並塞入 Qdrant

使用方式：
    python main.py
"""

import sys
from pathlib import Path

# 將當前目錄加入 Python 路徑
sys.path.append(str(Path(__file__).parent))

import json
import logging
import uuid
import hashlib
import shutil
import re
import requests
from typing import List, Dict, Any
from langchain_core.documents import Document
from hybrid_embed import qdrant_hybrid_vector_store


def setup_logging():
    """設定日誌系統"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    return logging.getLogger("main")


def has_chinese_content(text: str) -> bool:
    """檢查文本是否包含中文字符
    
    Args:
        text: 要檢查的文本
        
    Returns:
        是否包含中文字符
    """
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    return bool(chinese_pattern.search(text))


def is_content_valid(content: str, max_length: int = 2000) -> tuple[bool, str]:
    """檢查內容是否符合處理條件
    
    Args:
        content: 要檢查的內容
        max_length: 最大字數限制
        
    Returns:
        (是否有效, 原因)
    """
    if not content.strip():
        return False, "內容為空"
    
    # 檢查字數
    # if len(content) > max_length:
    #     return False, f"字數超過限制 ({len(content)} > {max_length})"
    
    # 檢查是否包含中文
    if not has_chinese_content(content):
        return False, "不包含中文內容"
    
    return True, "內容有效"


def move_invalid_file(json_file_path: Path, reason: str):
    """將無效檔案移動到 json-err 目錄
    
    Args:
        json_file_path: JSON 檔案路徑
        reason: 移動原因
    """
    logger = logging.getLogger("main")
    
    # 建立 json-err 目錄
    error_dir = Path("json-err")
    error_dir.mkdir(exist_ok=True)
    
    # 移動檔案
    target_path = error_dir / json_file_path.name
    shutil.move(str(json_file_path), str(target_path))
    
    logger.info(f"檔案已移動到錯誤目錄: {json_file_path.name} -> {target_path} (原因: {reason})")


def load_extract_json_files(json_dir: str = "json-output") -> List[Dict[str, Any]]:
    """載入 json-output 目錄下的所有 JSON 檔案
    
    Args:
        json_dir: JSON 檔案目錄
        
    Returns:
        所有 JSON 檔案的內容列表
    """
    logger = logging.getLogger("main")
    json_path = Path(json_dir)
    
    if not json_path.exists():
        raise FileNotFoundError(f"找不到目錄: {json_dir}")
    
    json_files = list(json_path.glob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"在 {json_dir} 目錄中找不到 JSON 檔案")
    
    logger.info(f"找到 {len(json_files)} 個 JSON 檔案")
    
    all_data = []
    for json_file in json_files:
        logger.info(f"載入檔案: {json_file.name}")
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_data.append(data)
    
    logger.info(f"成功載入 {len(all_data)} 個檔案")
    return all_data


def convert_to_documents(extract_data_list: List[Dict[str, Any]], json_filename: str = "") -> tuple[List[Document], List[str]]:
    """將提取的資料轉換成 langchain Document 格式
    
    Args:
        extract_data_list: 提取資料列表，每個包含 file_path 和 extracted_content
        json_filename: 當前處理的 JSON 檔案名稱，用於生成唯一 ID
        
    Returns:
        (Documents 列表, ID 列表)
    """
    logger = logging.getLogger("main")
    documents = []
    ids = []
    
    for i, data in enumerate(extract_data_list):
        file_path = data.get('file_path', '')
        extracted_content = data.get('extracted_content', '')
        
        if not extracted_content.strip():
            continue
            
        # 使用當前 JSON 檔案名稱作為 ID 基礎，確保唯一性
        base_name = Path(json_filename).stem if json_filename else Path(file_path).stem if file_path else f"doc_{i}"
        
        # 生成唯一 ID：JSON檔案名 + 索引
        unique_string = f"{base_name}_{i}"
        doc_id_hash = hashlib.md5(unique_string.encode('utf-8')).hexdigest()
        doc_id = str(uuid.UUID(doc_id_hash))
        
        # 建立 metadata
        doc_metadata = {
            "file_path": file_path,
            "document_id": doc_id,
            "filename": base_name,
            "content_length": len(extracted_content)
        }
        
        # 建立 Document
        document = Document(
            page_content=extracted_content,
            metadata=doc_metadata
        )
        
        documents.append(document)
        ids.append(doc_id)
        
        logger.info(f"處理文件: {base_name}")
    
    logger.info(f"總共轉換 {len(documents)} 個文件成 Documents")
    return documents, ids


def add_documents_to_qdrant(documents: List[Document], ids: List[str]):
    """將 Documents 加入到 Qdrant 使用 hybrid 嵌入
    
    Args:
        documents: Document 列表
        ids: ID 列表
    """
    logger = logging.getLogger("main")
    
    logger.info(f"開始將 {len(documents)} 個 documents 加入到 Qdrant")
    
    # 記錄加入前的點數
    response = requests.get("http://localhost:6333/collections/REPORT_EMB")
    before_count = response.json()["result"]["points_count"]
    logger.info(f"加入前 Qdrant 點數: {before_count}")
    
    # 使用 hybrid_embed 模組中的 qdrant_hybrid_vector_store (同步處理)
    qdrant_hybrid_vector_store.add_documents(
        documents=documents, 
        ids=ids
    )
    
    # 驗證是否真的加入成功
    response = requests.get("http://localhost:6333/collections/REPORT_EMB")
    after_count = response.json()["result"]["points_count"]
    logger.info(f"加入後 Qdrant 點數: {after_count}")
    
    if after_count <= before_count:
        raise RuntimeError(f"加入失敗！點數沒有增加 (前:{before_count}, 後:{after_count})")
    
    logger.info(f"成功將 {after_count - before_count} 個 documents 加入到 Qdrant")


def process_single_file(json_file_path: Path) -> int:
    """處理單一 JSON 檔案
    
    Args:
        json_file_path: JSON 檔案路徑
        
    Returns:
        處理的文件數量
    """
    logger = logging.getLogger("main")
    
    logger.info(f"載入檔案: {json_file_path.name}")
    
    # 載入 JSON 檔案
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 檢查內容是否有效
    extracted_content = data.get('extracted_content', '')
    is_valid, reason = is_content_valid(extracted_content)
    
    if not is_valid:
        logger.info(f"{json_file_path.name} 內容無效: {reason}")
        move_invalid_file(json_file_path, reason)
        return 0
    
    # 轉換成 Documents
    documents, ids = convert_to_documents([data], json_file_path.name)
    
    doc_count = len(documents)
    
    if not documents:
        logger.info(f"{json_file_path.name} 沒有有效內容")
        move_invalid_file(json_file_path, "轉換後無有效文件")
        return 0
    
    # 加入到 Qdrant
    add_documents_to_qdrant(documents, ids)
    
    logger.info(f"{json_file_path.name} 處理完成 ({doc_count} 文件)")
    
    # 將處理完的檔案移動到 processed 資料夾
    processed_dir = Path("json-output-processed")
    processed_dir.mkdir(exist_ok=True)
    
    target_path = processed_dir / json_file_path.name
    shutil.move(str(json_file_path), str(target_path))
    logger.info(f"檔案已移動到: {target_path}")
    
    return doc_count


def main():
    """主要執行函數"""
    logger = setup_logging()
    
    logger.info("開始處理 json-output 檔案並使用 hybrid 嵌入塞入 Qdrant")
    
    # 檢查目錄
    json_dir = Path("json-output")
    if not json_dir.exists():
        raise FileNotFoundError(f"找不到目錄: {json_dir}")
    
    # 取得所有 JSON 檔案
    json_files = list(json_dir.glob("*.json"))
    
    if not json_files:
        logger.info("目錄中沒有 JSON 檔案需要處理")
        return
    
    logger.info(f"找到 {len(json_files)} 個 JSON 檔案需要處理")
    
    # 統計變數
    processed_count = 0
    valid_count = 0
    invalid_count = 0
    total_docs = 0
    
    # 處理所有檔案
    for json_file in json_files:
        processed_count += 1
        
        logger.info(f"處理第 {processed_count}/{len(json_files)} 個檔案: {json_file.name}")
        
        doc_count = process_single_file(json_file)
        
        if doc_count > 0:
            valid_count += 1
            total_docs += doc_count
        else:
            invalid_count += 1
        
        logger.info(f"已處理 {processed_count}/{len(json_files)} 個檔案")
    
    # 顯示最終統計
    logger.info("所有檔案處理完成")
    logger.info(f"總處理檔案數: {processed_count}")
    logger.info(f"有效檔案數: {valid_count}")
    logger.info(f"無效檔案數: {invalid_count}")
    logger.info(f"總文件數: {total_docs}")
    logger.info("有效檔案已移動到 json-output-processed 目錄")
    logger.info("無效檔案已移動到 json-err 目錄")


if __name__ == "__main__":
    main()
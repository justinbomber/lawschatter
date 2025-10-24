import os
import sys
import logging
from pathlib import Path

# 添加 src 目錄到 Python 路徑
current_dir = Path(__file__).parent
src_dir = current_dir.parent
sys.path.insert(0, str(src_dir))

from modules.config import Config
from modules.database import DatabaseConnection
from modules.uploader import JudgmentUploader


def process_rar_background(rar_path: str):
    """背景處理RAR檔案的獨立函數"""
    config = Config.from_env()
    config.validate()
    logger = config.setup_logging()
    
    logger.info(f"Starting background processing for: {rar_path}")
    
    db_connection = DatabaseConnection(config, logger)
    uploader = JudgmentUploader(db_connection, logger)
    
    result = uploader.process_rar_file(rar_path)
    logger.info(f"Background processing completed: {result}")
    
    # 處理完成後刪除臨時檔案
    if os.path.exists(rar_path):
        os.unlink(rar_path)
        logger.info(f"Cleaned up temporary file: {rar_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python background_processor.py <rar_path>")
        sys.exit(1)
    
    rar_path = sys.argv[1]
    process_rar_background(rar_path)

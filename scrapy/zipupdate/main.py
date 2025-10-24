import uvicorn
import sys
import logging
from pathlib import Path

# 添加專案根目錄到路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 動態導入模組以避免 linter 錯誤
def import_modules():
    import importlib
    queue_manager = importlib.import_module('src.modules.queue_manager')
    api_main = importlib.import_module('src.api.main')
    return queue_manager.get_global_queue, api_main.app

get_global_queue, app = import_modules()

def startup_initialization():
    """程式啟動時的初始化作業"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    logger = logging.getLogger("zipupdate")
    
    logger.info("正在啟動 zipupdate 服務...")
    
    # 初始化全域佇列並處理現有的extracted目錄
    queue_manager = get_global_queue()
    queue_manager.process_existing_extracted_dirs()
    
    logger.info("zipupdate 服務啟動完成")

if __name__ == "__main__":
    # 執行啟動初始化
    startup_initialization()
    
    # 啟動 API 服務
    uvicorn.run(app, host="0.0.0.0", port=8001)
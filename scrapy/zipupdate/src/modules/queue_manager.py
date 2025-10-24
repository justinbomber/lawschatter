import threading
import queue
import time
import logging
from pathlib import Path
from typing import Dict, Any
from .config import Config
from .database import DatabaseConnection
from .uploader import JudgmentUploader


class FileProcessingQueue:
    """檔案處理排隊系統"""
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self.file_queue = queue.Queue()  # 存放待處理的檔案路徑
        self.is_processing = False
        self.worker_thread = None
        self.lock = threading.Lock()
        
        # 初始化資料庫連接和上傳器
        config = Config.from_env()
        config.validate()
        db_connection = DatabaseConnection(config, self.logger)
        self.uploader = JudgmentUploader(db_connection, self.logger)
    
    def add_file_to_queue(self, file_path: str, file_type: str = "rar") -> bool:
        """將檔案加入處理佇列"""
        try:
            self.file_queue.put({
                "file_path": file_path,
                "file_type": file_type,
                "added_time": time.time()
            })
            self.logger.info(f"檔案已加入處理佇列: {file_path}")
            
            # 確保處理執行緒正在運行
            self.ensure_worker_running()
            return True
        except Exception as e:
            self.logger.error(f"加入檔案到佇列失敗: {file_path}, 錯誤: {e}")
            return False
    
    def ensure_worker_running(self):
        """確保工作執行緒正在運行"""
        with self.lock:
            if not self.is_processing or not self.worker_thread or not self.worker_thread.is_alive():
                self.is_processing = True
                self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
                self.worker_thread.start()
                self.logger.info("檔案處理工作執行緒已啟動")
    
    def _worker_loop(self):
        """工作執行緒主循環"""
        self.logger.info("檔案處理工作執行緒開始運行")
        
        while self.is_processing:
            try:
                # 嘗試從佇列中獲取檔案（等待5秒超時）
                file_info = self.file_queue.get(timeout=5)
                
                if file_info:
                    self._process_file(file_info)
                    self.file_queue.task_done()
                    
            except queue.Empty:
                # 佇列為空，繼續循環
                continue
            except Exception as e:
                self.logger.error(f"處理檔案時發生錯誤: {e}")
        
        self.logger.info("檔案處理工作執行緒已停止")
    
    def _process_file(self, file_info: Dict[str, Any]):
        """處理單個檔案"""
        file_path = file_info["file_path"]
        file_type = file_info["file_type"]
        
        self.logger.info(f"開始處理檔案: {file_path}, 類型: {file_type}")
        
        try:
            if file_type == "rar":
                result = self.uploader.process_rar_file(file_path)
                self.logger.info(f"RAR檔案處理完成: {result}")
                
                # 刪除臨時檔案
                if Path(file_path).exists():
                    Path(file_path).unlink()
                    self.logger.info(f"已刪除臨時檔案: {file_path}")
                    
            elif file_type == "extracted_dir":
                result = self.uploader.process_extracted_directory(file_path)
                self.logger.info(f"Extracted目錄處理完成: {result}")
                
        except Exception as e:
            self.logger.error(f"處理檔案失敗: {file_path}, 錯誤: {e}")
    
    def process_existing_extracted_dirs(self, extracted_base_dir: str = "./extracted"):
        """處理現有的extracted目錄"""
        self.logger.info("開始檢查並處理現有的extracted目錄")
        
        sorted_dirs = self.uploader.get_sorted_extracted_dirs(extracted_base_dir)
        
        for dir_path in sorted_dirs:
            self.add_file_to_queue(dir_path, "extracted_dir")
        
        if sorted_dirs:
            self.logger.info(f"已將 {len(sorted_dirs)} 個extracted目錄加入處理佇列")
        else:
            self.logger.info("沒有找到需要處理的extracted目錄")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """獲取佇列狀態"""
        return {
            "queue_size": self.file_queue.qsize(),
            "is_processing": self.is_processing,
            "worker_alive": self.worker_thread.is_alive() if self.worker_thread else False
        }
    
    def stop_processing(self):
        """停止處理"""
        self.logger.info("正在停止檔案處理...")
        self.is_processing = False
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=10)
        
        self.logger.info("檔案處理已停止")


# 全域佇列實例
_global_queue = None

def get_global_queue() -> FileProcessingQueue:
    """獲取全域檔案處理佇列實例"""
    global _global_queue
    if _global_queue is None:
        _global_queue = FileProcessingQueue()
    return _global_queue

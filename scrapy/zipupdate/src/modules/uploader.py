import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from .database import DatabaseConnection
from .rar_handler import RarHandler
from .json_parser import JudgmentParser


class JudgmentUploader:
    def __init__(self, db_connection: DatabaseConnection, logger: logging.Logger):
        self.db = db_connection
        self.logger = logger
        self.rar_handler = RarHandler()
        self.parser = JudgmentParser()
    
    def _process_files_individually(self, file_paths: list) -> Dict[str, int]:
        """逐檔案處理和插入，只有插入成功後才刪除檔案"""
        inserted_count = 0
        skipped_count = 0
        deleted_count = 0
        total_files = len(file_paths)
        
        self.logger.info(f"開始逐檔案處理 {total_files} 個檔案")
        
        for index, file_path in enumerate(file_paths, 1):
            try:
                # 解析單個檔案
                data = self.parser.parse_json_file(file_path)
                
                if not self.parser.validate_judgment_data(data):
                    self.logger.warning(f"[{index}/{total_files}] 檔案驗證失敗，跳過: {file_path}")
                    continue
                
                # 標準化資料
                normalized_data = self.parser.normalize_judgment_data(data)
                jid = normalized_data.get('jid', 'Unknown')
                
                # 檢查是否已存在
                if self.db.check_judgment_exists(jid):
                    self.logger.info(f"[{index}/{total_files}] 資料已存在，跳過: {jid}")
                    skipped_count += 1
                    # 即使跳過也刪除檔案，因為資料已經在資料庫中
                    self._delete_single_file(file_path)
                    deleted_count += 1
                else:
                    # 插入資料庫
                    try:
                        result = self.db.insert_judgment(normalized_data)
                        self.logger.info(f"[{index}/{total_files}] 成功插入資料庫: {jid}")
                        inserted_count += 1
                        
                        # 只有插入成功後才刪除檔案
                        if self._delete_single_file(file_path):
                            deleted_count += 1
                            
                    except Exception as db_error:
                        self.logger.error(f"[{index}/{total_files}] 資料庫插入失敗: {jid}, 錯誤: {db_error}")
                        self.logger.info(f"[{index}/{total_files}] 保留檔案: {file_path}")
                        # 不刪除檔案，保留以供重新處理
                        
            except Exception as e:
                self.logger.error(f"[{index}/{total_files}] 處理檔案失敗: {file_path}, 錯誤: {e}")
                # 處理失敗的檔案不刪除
        
        self.logger.info(f"檔案處理完成 - 總計: {total_files}, 新增: {inserted_count}, 跳過: {skipped_count}, 刪除: {deleted_count}")
        return {"inserted": inserted_count, "skipped": skipped_count, "deleted": deleted_count}
    
    def _delete_single_file(self, file_path: str) -> bool:
        """刪除單個檔案，返回是否成功"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                self.logger.info(f"已成功上傳並刪除檔案: {file_path}")
                return True
            else:
                self.logger.warning(f"檔案不存在，無法刪除: {file_path}")
                return False
        except Exception as e:
            self.logger.error(f"刪除檔案失敗: {file_path}, 錯誤: {e}")
            return False

    def process_rar_file(self, rar_path: str) -> Dict[str, int]:
        """處理RAR檔案（新上傳的檔案）"""
        self.logger.info(f"Processing RAR file: {rar_path}")

        extract_dir = self.rar_handler.extract_rar(rar_path)
        self.logger.info(f"Extracted to: {extract_dir}")

        json_files = self.rar_handler.find_json_files(extract_dir)
        self.logger.info(f"Found {len(json_files)} JSON files")

        # 不刪除檔案，因為這是新解壓的
        processed_data = self.parser.process_json_files(json_files, delete_after_process=False)
        self.logger.info(f"Successfully processed {len(processed_data)} judgment files")

        result = {"inserted": 0, "skipped": 0}
        if processed_data:
            self.logger.info(f"Starting individual insertion of {len(processed_data)} judgments")
            result = self.db.insert_judgments_individually(processed_data)
            self.logger.info(f"Database operation completed: {result['inserted']} inserted, {result['skipped']} skipped")

        self.rar_handler.cleanup_extracted()
        self.logger.info("Cleanup completed")

        return {
            "total_files": len(json_files),
            "processed_files": len(processed_data),
            "uploaded_files": result["inserted"]
        }
    
    def get_sorted_extracted_dirs(self, extracted_base_dir: str = "./extracted") -> List[str]:
        """獲取按日期排序的extracted目錄列表（最新的在前）"""
        extracted_path = Path(extracted_base_dir)
        if not extracted_path.exists():
            return []
        
        date_dirs = []
        for item in extracted_path.iterdir():
            if item.is_dir():
                try:
                    # 假設目錄名稱是日期格式，例如 202506
                    date_str = item.name
                    if len(date_str) == 6 and date_str.isdigit():  # YYYYMM格式
                        year = int(date_str[:4])
                        month = int(date_str[4:])
                        date_obj = datetime(year, month, 1)
                        date_dirs.append((str(item), date_obj))
                except ValueError:
                    # 如果無法解析日期，則跳過
                    continue
        
        # 按日期排序（最新的在前）
        date_dirs.sort(key=lambda x: x[1], reverse=True)
        return [dir_path for dir_path, _ in date_dirs]
    
    def process_extracted_directory(self, dir_path: str) -> Dict[str, int]:
        """處理extracted目錄中的單個日期目錄"""
        self.logger.info(f"Processing extracted directory: {dir_path}")
        
        json_files = self.rar_handler.find_json_files(dir_path)
        self.logger.info(f"Found {len(json_files)} JSON files in {dir_path}")
        
        if not json_files:
            self.logger.info(f"No JSON files found in {dir_path}, removing empty directory")
            try:
                shutil.rmtree(dir_path)
            except Exception as e:
                self.logger.error(f"Failed to remove empty directory {dir_path}: {e}")
            return {"total_files": 0, "processed_files": 0, "uploaded_files": 0}
        
        # 逐檔案處理和插入，確保資料安全
        result = self._process_files_individually(json_files)
        self.logger.info(f"File processing completed: {result['inserted']} inserted, {result['skipped']} skipped, {result['deleted']} files deleted")
        
        # 檢查目錄是否為空，如果是則刪除
        try:
            if not os.listdir(dir_path):
                shutil.rmtree(dir_path)
                self.logger.info(f"Removed empty directory: {dir_path}")
        except Exception as e:
            self.logger.error(f"Failed to remove directory {dir_path}: {e}")
        
        return {
            "total_files": len(json_files),
            "processed_files": result["inserted"] + result["skipped"],
            "uploaded_files": result["inserted"]
        }
    
    def process_all_extracted_directories(self, extracted_base_dir: str = "./extracted") -> Dict[str, int]:
        """處理所有extracted目錄中的檔案"""
        self.logger.info("Starting to process all extracted directories")
        
        sorted_dirs = self.get_sorted_extracted_dirs(extracted_base_dir)
        if not sorted_dirs:
            self.logger.info("No extracted directories found")
            return {"total_files": 0, "processed_files": 0, "uploaded_files": 0}
        
        total_result = {"total_files": 0, "processed_files": 0, "uploaded_files": 0}
        
        for dir_path in sorted_dirs:
            try:
                result = self.process_extracted_directory(dir_path)
                total_result["total_files"] += result["total_files"]
                total_result["processed_files"] += result["processed_files"]
                total_result["uploaded_files"] += result["uploaded_files"]
            except Exception as e:
                self.logger.error(f"Error processing directory {dir_path}: {e}")
        
        # 如果所有子目錄都被刪除了，嘗試刪除extracted根目錄
        try:
            extracted_path = Path(extracted_base_dir)
            if extracted_path.exists() and not any(extracted_path.iterdir()):
                shutil.rmtree(extracted_base_dir)
                self.logger.info(f"Removed empty extracted base directory: {extracted_base_dir}")
        except Exception as e:
            self.logger.error(f"Failed to remove extracted base directory {extracted_base_dir}: {e}")
        
        self.logger.info(f"Completed processing all extracted directories: {total_result}")
        return total_result
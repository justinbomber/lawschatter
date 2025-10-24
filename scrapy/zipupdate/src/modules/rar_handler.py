import rarfile
import os
import shutil
from pathlib import Path


class RarHandler:
    def __init__(self, extract_dir: str = "./extracted"):
        self.extract_dir = Path(extract_dir)

    def extract_rar(self, rar_path: str):
        self.extract_dir.mkdir(exist_ok=True)

        with rarfile.RarFile(rar_path, 'r') as rar_ref:
            rar_ref.extractall(self.extract_dir)

        return str(self.extract_dir)

    def cleanup_extracted(self):
        if self.extract_dir.exists():
            shutil.rmtree(self.extract_dir)

    def find_json_files(self, directory: str):
        json_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(os.path.join(root, file))
        return json_files
    
    def delete_file(self, file_path: str) -> bool:
        """刪除單個檔案"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                return True
        except Exception as e:
            print(f"刪除檔案失敗: {file_path}, 錯誤: {e}")
        return False
    
    def delete_directory_if_empty(self, directory: str) -> bool:
        """如果目錄為空則刪除該目錄"""
        try:
            if os.path.exists(directory) and not os.listdir(directory):
                os.rmdir(directory)
                return True
        except Exception as e:
            print(f"刪除目錄失敗: {directory}, 錯誤: {e}")
        return False
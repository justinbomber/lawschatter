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
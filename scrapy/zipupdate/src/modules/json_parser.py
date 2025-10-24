import json
from typing import Dict, List


class JudgmentParser:
    @staticmethod
    def parse_json_file(file_path: str) -> Dict:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data

    @staticmethod
    def validate_judgment_data(data: Dict) -> bool:
        required_fields = ['JID', 'JYEAR', 'JCASE', 'JNO', 'JDATE', 'JTITLE', 'JFULL', 'JPDF']
        return all(field in data for field in required_fields)

    @staticmethod
    def extract_jid_full(jfull: str) -> str:
        """從jfull中提取jid_full（前兩個\\r\\n之前的內容）"""
        if not jfull:
            return ""
        
        # 找到前兩個 \r\n 的位置
        first_rn = jfull.find('\r\n')
        if first_rn != -1:
            second_rn = jfull.find('\r\n', first_rn + 2)
            if second_rn != -1:
                # 提取前兩個 \r\n 之前的內容並移除換行符
                result = jfull[:second_rn].replace('\r\n', '')
            else:
                # 如果只有一個 \r\n，就取到第一個 \r\n 為止
                result = jfull[:first_rn]
        else:
            # 如果沒有 \r\n，就取整個內容
            result = jfull
        
        # 最終清洗：移除 \r\n 和多餘的空格
        result = result.replace('\r\n', '').replace('\r', '').replace('\n', '')
        # 將多個連續空格替換為單個空格，並移除首尾空格
        import re
        result = re.sub(r'\s+', '', result).strip()
        
        return result

    @staticmethod
    def normalize_judgment_data(data: Dict) -> Dict:
        jfull = data.get('JFULL', '')
        jid_full = JudgmentParser.extract_jid_full(jfull)
        
        return {
            'jid': data['JID'],
            'jid_full': jid_full,  # 新增 jid_full 欄位
            'jyear': data['JYEAR'],
            'jcase': data['JCASE'],
            'jno': data['JNO'],
            'jdate': data['JDATE'],
            'jtitle': data['JTITLE'],
            'jfull': jfull,
            'jpdf': data['JPDF']
        }

    def process_json_files(self, file_paths: List[str], delete_after_process: bool = False) -> List[Dict]:
        """處理JSON檔案，可選擇處理後刪除檔案"""
        processed_data = []

        for file_path in file_paths:
            try:
                data = self.parse_json_file(file_path)

                if self.validate_judgment_data(data):
                    normalized_data = self.normalize_judgment_data(data)
                    processed_data.append(normalized_data)
                    
                    # 處理成功後刪除檔案（如果啟用）
                    if delete_after_process:
                        import os
                        if os.path.exists(file_path):
                            os.unlink(file_path)
                            print(f"已處理並刪除檔案: {file_path}")
                else:
                    print(f"驗證失敗，跳過檔案: {file_path}")
                    
            except Exception as e:
                print(f"處理檔案失敗: {file_path}, 錯誤: {e}")

        return processed_data
#!/usr/bin/env python3
"""
批次匯入判決書JSON檔案到Supabase
讀取jan_scamp目錄下的所有JSON檔案，並將其匯入到Supabase的main_judgments表中
"""

import os
import json
import sys
import argparse
from typing import Dict, List, Any
import hashlib
import time

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ 錯誤：需要安裝supabase客戶端庫")
    print("請執行：pip install supabase")
    sys.exit(1)

# Supabase設定
SUPABASE_URL = "https://lawschatter.mooo.com/"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyAgCiAgICAicm9sZSI6ICJzZXJ2aWNlX3JvbGUiLAogICAgImlzcyI6ICJzdXBhYmFzZS1kZW1vIiwKICAgICJpYXQiOiAxNjQxNzY5MjAwLAogICAgImV4cCI6IDE3OTk1MzU2MDAKfQ.DaYlNEoUrrEn2Ig7tqibS-PHK5vgusbcbo7X36XVt4Q"

# 檔案路徑設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.join(SCRIPT_DIR, "jan_scamp")
TABLE_NAME = "main_judgments"
SCHEMA_NAME = "lawschatter"  # 使用自定義 lawschatter schema

# 設置 lawschatter schema 權限的 SQL 語句
SETUP_SCHEMA_PERMISSIONS_SQL = """
-- 創建 schema（如果不存在）
CREATE SCHEMA IF NOT EXISTS lawschatter;

-- 授予 schema 使用權限給所有角色
GRANT USAGE ON SCHEMA lawschatter TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA lawschatter TO anon, authenticated, service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA lawschatter TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA lawschatter TO anon, authenticated, service_role;

-- 設置預設權限，確保未來創建的對象也有正確權限
ALTER DEFAULT PRIVILEGES IN SCHEMA lawschatter GRANT ALL ON TABLES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA lawschatter GRANT ALL ON ROUTINES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA lawschatter GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;
"""

def create_supabase_client() -> Client:
    """建立Supabase客戶端"""
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print(f"✓ 成功建立Supabase客戶端")
        return supabase
    except Exception as e:
        print(f"❌ 建立Supabase客戶端失敗: {e}")
        sys.exit(1)

def setup_schema_permissions(supabase: Client) -> bool:
    """設置 lawschatter schema 的權限"""
    print("🔧 檢測到使用自定義 schema 'lawschatter'")
    print("\n💡 需要手動在 Supabase 中設置權限，請按照以下步驟操作:")
    print("=" * 80)
    print("步驟 1: 在 Supabase SQL Editor 中執行以下 SQL:")
    print("-" * 80)
    print(SETUP_SCHEMA_PERMISSIONS_SQL)
    print("-" * 80)
    print("\n步驟 2: 在 Supabase Dashboard 中設置 API:")
    print("  1. 進入 Settings → API")
    print("  2. 在 'Exposed schemas' 欄位中添加 'lawschatter'")
    print("  3. 點擊 Save")
    print("\n步驟 3: 確認表格存在:")
    print("  - 確認 main_judgments 表格存在於 lawschatter schema 中")
    print("=" * 80)
    
    return False  # 總是返回 False，要求用戶手動設置

def test_supabase_connection(supabase: Client) -> bool:
    """測試Supabase連接和表格存取權限"""
    try:
        print("🔍 測試Supabase連接...")
        
        # 根據schema設定查詢表格
        if SCHEMA_NAME != "public":
            # 使用自訂schema
            result = supabase.schema(SCHEMA_NAME).table(TABLE_NAME).select("*").limit(1).execute()
            print(f"✓ 成功連接到Supabase並存取表格 '{SCHEMA_NAME}.{TABLE_NAME}'")
        else:
            # 使用預設public schema
            result = supabase.table(TABLE_NAME).select("*").limit(1).execute()
            print(f"✓ 成功連接到Supabase並存取表格 '{TABLE_NAME}'")
        return True
        
    except Exception as e:
        print(f"❌ Supabase連接測試失敗: {e}")
        print("可能的原因：")
        print("  1. URL不正確或無法存取")
        print("  2. Service Key無效")
        if SCHEMA_NAME != "public":
            print(f"  3. Schema '{SCHEMA_NAME}' 或表格 '{TABLE_NAME}' 不存在或無權限存取")
        else:
            print(f"  3. 表格 '{TABLE_NAME}' 不存在或無權限存取")
        print("  4. 網路連接問題")
        print(f"  5. 請檢查schema設定：目前設為 '{SCHEMA_NAME}'")
        return False

def list_available_tables(supabase: Client) -> List[str]:
    """列出可用的表格"""
    try:
        print("📋 正在查詢可用的表格...")
        
        # 直接嘗試查詢一些常見的表格名稱模式
        common_patterns = [
            "main_judgments", "judgment", "judgement", "main_judgment", "main_judgement",
            "judgments", "legal", "court", "case", "document", "law"
        ]
        
        found_tables = []
        for pattern in common_patterns:
            try:
                result = supabase.table(pattern).select("*").limit(1).execute()
                found_tables.append(pattern)
                print(f"    ✓ 找到表格: {pattern}")
            except Exception as e:
                # 忽略找不到表格的錯誤
                if 'does not exist' not in str(e).lower():
                    print(f"    ? 測試表格 {pattern} 時發生其他錯誤: {e}")
                
        if found_tables:
            print(f"  ✓ 找到可能的表格: {found_tables}")
            return found_tables
        else:
            print("  ⚠️ 未找到任何可存取的表格")
            
    except Exception as e:
        print(f"  ❌ 查詢表格失敗: {e}")
    
    return []

def diagnose_schema_settings(supabase: Client) -> str:
    """診斷正確的schema設定"""
    print("🔧 正在診斷schema設定...")
    
    # 首先列出可用的表格
    available_tables = list_available_tables(supabase)
    
    if available_tables:
        print(f"\n💡 建議嘗試以下表格:")
        for table in available_tables:
            print(f"    TABLE_NAME = '{table}'")
        
        # 測試第一個找到的表格
        if available_tables:
            first_table = available_tables[0]
            try:
                result = supabase.table(first_table).select("*").limit(1).execute()
                print(f"\n✓ 成功！建議使用: SCHEMA_NAME='public', TABLE_NAME='{first_table}'")
                return f"public.{first_table}"
            except Exception as e:
                print(f"\n❌ 測試表格 '{first_table}' 失敗: {e}")
    
    # 如果沒有找到表格，使用舊的測試方法
    test_configs = [
        ("public", "main_judgments"),
        ("public", "judgments"),
        ("public", "judgment"),
        ("public", "lawschatter_main_judgments"),
    ]
    
    for schema, table in test_configs:
        try:
            print(f"  測試: schema='{schema}', table='{table}'")
            result = supabase.table(table).select("*").limit(1).execute()
            
            print(f"  ✓ 成功！正確的設定可能是: SCHEMA_NAME='{schema}', TABLE_NAME='{table}'")
            return f"{schema}.{table}"
            
        except Exception as e:
            print(f"  ❌ 失敗: {e}")
            
    print("  ⚠️ 所有測試配置都失敗了")
    return None

def fix_json_format(content: str) -> str:
    """嘗試修復常見的JSON格式問題"""
    # 移除多餘的空白字元
    content = content.strip()
    
    # 確保以 { 開頭和 } 結尾
    if not content.startswith('{'):
        content = '{' + content
    if not content.endswith('}'):
        content = content + '}'
    
    # 修復常見的換行問題
    content = content.replace('\r\n', '\\r\\n').replace('\n', '\\n').replace('\r', '\\r')
    
    # 修復常見的引號問題 - 但要小心不要破壞正確的JSON
    # 這裡只做最基本的修復
    
    return content

def validate_json_format(file_path: str, auto_fix: bool = False) -> bool:
    """驗證JSON檔案格式，可選擇自動修復"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        # 檢查檔案是否為空
        if not content:
            print(f"      ❌ 檔案為空")
            return False
            
        # 首先嘗試直接解析
        try:
            json.loads(content)
            print(f"      ✓ JSON格式正確")
            return True
        except json.JSONDecodeError as e:
            print(f"      ⚠️ JSON解析錯誤: {e}")
            
            if auto_fix:
                print(f"      🔧 嘗試自動修復JSON格式...")
                
                # 嘗試修復格式
                fixed_content = fix_json_format(content)
                
                try:
                    json.loads(fixed_content)
                    print(f"      ✓ JSON格式修復成功")
                    
                    # 將修復後的內容寫回檔案（可選）
                    # 這裡我們先不自動寫回，只做驗證
                    return True
                    
                except json.JSONDecodeError as fix_error:
                    print(f"      ❌ 自動修復失敗: {fix_error}")
                    return False
            else:
                print(f"      💡 提示：可以使用 --auto-fix-json 參數嘗試自動修復")
                return False
            
    except Exception as e:
        print(f"      ❌ 檔案讀取錯誤: {e}")
        return False

def read_json_file(file_path: str, auto_fix: bool = False) -> Dict[str, Any]:
    """讀取並驗證JSON檔案"""
    filename = os.path.basename(file_path)
    
    try:
        # 首先檢查檔案是否存在
        if not os.path.exists(file_path):
            print(f"      ❌ 檔案不存在: {filename}")
            return {}
            
        # 檢查檔案大小
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            print(f"      ❌ 檔案為空: {filename}")
            return {}
            
        print(f"      📋 檔案大小: {file_size:,} bytes")
        
        # 驗證JSON格式
        print(f"      🔍 驗證JSON格式...")
        if not validate_json_format(file_path, auto_fix):
            return {}
            
        # 讀取JSON內容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 如果需要修復，應用修復
        if auto_fix:
            try:
                # 先嘗試直接解析
                data = json.loads(content)
            except json.JSONDecodeError:
                # 如果失敗，嘗試修復後解析
                print(f"      🔧 應用JSON格式修復...")
                fixed_content = fix_json_format(content)
                data = json.loads(fixed_content)
        else:
            data = json.loads(content)
            
        # 檢查JSON是否為字典格式
        if not isinstance(data, dict):
            print(f"      ❌ JSON不是字典格式")
            return {}
            
        print(f"      ✓ 成功讀取JSON，包含 {len(data)} 個欄位")
        return data
        
    except json.JSONDecodeError as e:
        print(f"      ❌ JSON格式錯誤 {filename}: 第{e.lineno}行，第{e.colno}列 - {e.msg}")
        return {}
    except UnicodeDecodeError as e:
        print(f"      ❌ 編碼錯誤 {filename}: {e}")
        return {}
    except Exception as e:
        print(f"      ❌ 讀取檔案失敗 {filename}: {e}")
        return {}

def validate_data(json_data: Dict[str, Any]) -> List[str]:
    """驗證JSON資料的完整性"""
    errors = []
    
    # 檢查必要欄位
    required_fields = ["JID", "JYEAR", "JCASE", "JNO", "JDATE"]
    for field in required_fields:
        if not json_data.get(field):
            errors.append(f"缺少必要欄位: {field}")
    
    # 檢查資料長度限制
    if json_data.get("JID") and len(json_data["JID"]) > 100:
        errors.append("JID長度超過100字元")
    
    if json_data.get("JTITLE") and len(json_data["JTITLE"]) > 200:
        errors.append("JTITLE長度超過200字元")
        
    if json_data.get("JPDF") and len(json_data["JPDF"]) > 500:
        errors.append("JPDF長度超過500字元")
    
    # 檢查JFULL是否過大 (PostgreSQL文字限制)
    jfull = json_data.get("JFULL", "")
    if len(jfull) > 1000000:  # 1MB限制
        errors.append(f"JFULL內容過大: {len(jfull)}字元 (建議小於1MB)")
    
    return errors

def transform_data(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """將JSON資料轉換為Supabase表格式"""
    if not json_data:
        return {}
    
    # 清理和截斷過長的資料
    jid = str(json_data.get("JID", ""))[:100]
    jyear = str(json_data.get("JYEAR", ""))[:10]
    jcase = str(json_data.get("JCASE", ""))[:20]
    jno = str(json_data.get("JNO", ""))[:20]
    jdate = str(json_data.get("JDATE", ""))[:20]
    jtitle = str(json_data.get("JTITLE", ""))[:200]
    jfull = str(json_data.get("JFULL", ""))
    jpdf = str(json_data.get("JPDF", ""))[:500]
    
    # 生成JFULL的雜湊值
    
    transformed_data = {
        "jid": jid,
        "jyear": jyear,
        "jcase": jcase,
        "jno": jno,
        "jdate": jdate,
        "jtitle": jtitle,
        "jfull": jfull,
        "jpdf": jpdf
    }
    
    return transformed_data

def get_json_files(directory: str) -> List[str]:
    """取得目錄下所有JSON檔案"""
    json_files = []
    
    if not os.path.exists(directory):
        print(f"❌ 目錄不存在: {directory}")
        return json_files
    
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            json_files.append(file_path)
    
    json_files.sort()  # 排序檔案
    return json_files

def insert_single_record(supabase: Client, data: Dict[str, Any], file_path: str, delete_after_insert: bool = True) -> bool:
    """插入單筆記錄到Supabase，成功後可選擇刪除原始檔案
    
    Returns:
        True: 成功插入或跳過重複資料
        False: 插入失敗
    """
    filename = os.path.basename(file_path)
    jid = data.get('jid', 'Unknown')
    
    try:
        # 顯示要插入的資料大小
        jfull_length = len(data.get('jfull', ''))
        print(f"  📝 資料詳情: JID={jid}, 全文長度={jfull_length}字元")
        
        # 使用upsert避免重複插入，以jid為唯一鍵
        if SCHEMA_NAME != "public":
            # 使用自訂schema
            result = supabase.schema(SCHEMA_NAME).table(TABLE_NAME).upsert(
                data,
                on_conflict="jid"  # 如果jid相同則更新
            ).execute()
        else:
            # 使用預設public schema
            result = supabase.table(TABLE_NAME).upsert(
                data,
                on_conflict="jid"  # 如果jid相同則更新
            ).execute()
        
        # 檢查結果
        if hasattr(result, 'data') and result.data:
            print(f"  ✓ 成功插入/更新: {jid}")
            
            # 成功插入後刪除原始JSON檔案
            if delete_after_insert:
                try:
                    os.remove(file_path)
                    print(f"  🗑️ 已刪除原始檔案: {filename}")
                except Exception as delete_error:
                    print(f"  ⚠️ 刪除檔案失敗: {filename} - {delete_error}")
                    
            return True
        else:
            print(f"  ❌ 插入失敗，無回傳資料: {jid}")
            if hasattr(result, 'error') and result.error:
                print(f"      錯誤詳情: {result.error}")
            return False
            
    except Exception as e:
        error_str = str(e)
        
        # 檢查是否為重複資料錯誤 (PostgreSQL 唯一性約束違反)
        if "23505" in error_str:
            print(f"  ⚠️ 跳過重複資料: {jid}")
            print(f"      原因: 資料庫觸發器檢測到重複內容")
            
            # 如果設定為插入成功後刪除檔案，這裡也要刪除（因為資料已存在）
            if delete_after_insert:
                try:
                    os.remove(file_path)
                    print(f"  🗑️ 已刪除重複檔案: {filename}")
                except Exception as delete_error:
                    print(f"  ⚠️ 刪除檔案失敗: {filename} - {delete_error}")
            
            return True  # 返回 True 表示處理成功（跳過重複資料）
            
        # 其他錯誤的處理
        print(f"  ❌ 插入失敗: {jid}")
        print(f"      錯誤詳情: {error_str}")
        
        # 嘗試解析錯誤類型
        error_str_lower = error_str.lower()
        if '404' in error_str_lower:
            print("      可能原因: 表格不存在或URL不正確")
        elif '401' in error_str_lower or '403' in error_str_lower:
            print("      可能原因: 認證失敗或權限不足")
        elif 'connection' in error_str_lower or 'timeout' in error_str_lower:
            print("      可能原因: 網路連接問題")
        elif 'json' in error_str_lower:
            print("      可能原因: 資料格式錯誤")
        elif '23505' in error_str:
            print("      可能原因: 違反唯一性約束（重複資料）")
            
        return False

def process_files_individually(supabase: Client, json_files: List[str], delete_after_insert: bool = True, stop_on_error: bool = True, auto_fix_json: bool = False) -> Dict[str, int]:
    """逐檔案處理並插入資料"""
    total_files = len(json_files)
    successful_inserts = 0
    failed_inserts = 0
    skipped_files = 0
    
    print(f"開始逐檔案處理 {total_files} 個JSON檔案...")
    print(f"插入成功後{'會' if delete_after_insert else '不會'}刪除原始檔案")
    print(f"{'遇到錯誤會立即停止' if stop_on_error else '會繼續處理所有檔案'}")
    print("-" * 50)
    
    for i, file_path in enumerate(json_files, 1):
        filename = os.path.basename(file_path)
        print(f"📖 處理檔案 {i}/{total_files}: {filename}")
        
        # 讀取JSON檔案
        json_data = read_json_file(file_path, auto_fix_json)
        if not json_data:
            print(f"  ⚠️ 跳過空檔案或格式錯誤檔案: {filename}")
            skipped_files += 1
            continue
        
        # 驗證資料
        validation_errors = validate_data(json_data)
        if validation_errors:
            print(f"  ❌ 資料驗證失敗: {filename}")
            for error in validation_errors:
                print(f"      - {error}")
            failed_inserts += 1
            if stop_on_error:
                print(f"\n🛑 在檔案 {filename} 遇到錯誤，停止處理")
                break
            continue
            
        # 轉換資料格式
        transformed_data = transform_data(json_data)
        if not transformed_data.get("jid"):
            print(f"  ⚠️ 跳過無效資料: {filename}")
            skipped_files += 1
            continue
        
        # 插入資料並可選擇刪除檔案
        if insert_single_record(supabase, transformed_data, file_path, delete_after_insert):
            successful_inserts += 1
        else:
            failed_inserts += 1
            if stop_on_error:
                print(f"\n🛑 在檔案 {filename} 插入失敗，停止處理")
                break
        
        # 稍微延遲避免請求過於頻繁
        if i < total_files:
            time.sleep(0.3)
    
    # 返回統計結果
    stats = {
        'total': total_files,
        'successful': successful_inserts,
        'failed': failed_inserts,
        'skipped': skipped_files,
        'processed': successful_inserts + failed_inserts + skipped_files
    }
    
    print(f"\n📊 處理結果統計:")
    print(f"  總檔案數: {stats['total']}")
    print(f"  已處理檔案: {stats['processed']}")
    print(f"  成功處理: {stats['successful']}")
    print(f"  處理失敗: {stats['failed']}")
    print(f"  跳過檔案: {stats['skipped']}")
    if stats['processed'] > 0:
        print(f"  成功率: {(stats['successful']/stats['processed']*100):.1f}%")
    
    if stop_on_error and stats['failed'] > 0:
        print(f"⚠️ 因遇到錯誤提前停止，剩餘 {stats['total'] - stats['processed']} 個檔案未處理")
    
    return stats

def parse_arguments():
    """解析命令行參數"""
    parser = argparse.ArgumentParser(
        description="批次匯入判決書JSON檔案到Supabase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  python batch_import_to_supabase.py                      # 互動模式，會詢問是否刪除檔案
  python batch_import_to_supabase.py --delete            # 自動刪除成功處理的檔案
  python batch_import_to_supabase.py --no-delete         # 保留所有檔案
  python batch_import_to_supabase.py --continue-on-error # 遇到錯誤時繼續處理其他檔案
  python batch_import_to_supabase.py --auto-fix-json     # 自動修復JSON格式錯誤
        """
    )
    
    delete_group = parser.add_mutually_exclusive_group()
    delete_group.add_argument(
        '--delete', 
        action='store_true',
        help='成功插入後自動刪除原始JSON檔案'
    )
    delete_group.add_argument(
        '--no-delete', 
        action='store_true',
        help='保留所有JSON檔案，不刪除'
    )
    
    error_group = parser.add_mutually_exclusive_group()
    error_group.add_argument(
        '--stop-on-error',
        action='store_true',
        default=True,
        help='遇到錯誤時立即停止處理（預設行為）'
    )
    error_group.add_argument(
        '--continue-on-error',
        action='store_true',
        help='遇到錯誤時繼續處理其他檔案'
    )
    
    parser.add_argument(
        '--auto-fix-json',
        action='store_true',
        help='自動嘗試修復JSON格式錯誤'
    )
    
    return parser.parse_args()

def main():
    """主要執行函數"""
    args = parse_arguments()
    
    print("🚀 開始逐檔案匯入判決書資料到Supabase")
    print(f"來源目錄: {JSON_DIR}")
    if SCHEMA_NAME != "public":
        print(f"目標表格: {SCHEMA_NAME}.{TABLE_NAME}")
    else:
        print(f"目標表格: {TABLE_NAME}")
    print(f"Schema: {SCHEMA_NAME}")
    print(f"Supabase URL: {SUPABASE_URL}")
    print(f"Service Key: {SUPABASE_SERVICE_KEY[:20]}...{SUPABASE_SERVICE_KEY[-10:]} (已遮蔽)")
    
    # 決定是否刪除檔案
    if args.delete:
        delete_after_insert = True
        print("🗑️ 模式：成功插入後會自動刪除原始JSON檔案")
    elif args.no_delete:
        delete_after_insert = False
        print("📁 模式：保留所有JSON檔案")
    else:
        # 互動模式
        print("⚠️ 注意：可選擇在成功插入後刪除原始JSON檔案")
        while True:
            confirm = input("確認要在插入成功後刪除原始JSON檔案嗎？(y/n): ").lower().strip()
            if confirm in ['y', 'yes', '是']:
                delete_after_insert = True
                break
            elif confirm in ['n', 'no', '否']:
                delete_after_insert = False
                break
            else:
                print("請輸入 y(是) 或 n(否)")
    
    # 決定錯誤處理方式
    stop_on_error = not args.continue_on_error
    if args.continue_on_error:
        print("🔄 模式：遇到錯誤時會繼續處理其他檔案")
    else:
        print("🛑 模式：遇到錯誤時會立即停止（預設）")
        
    # 決定是否自動修復JSON
    auto_fix_json = args.auto_fix_json
    if auto_fix_json:
        print("🔧 模式：自動嘗試修復JSON格式錯誤")
    
    print("-" * 50)
    
    # 建立Supabase連接
    supabase = create_supabase_client()
    
    # 測試連接
    if not test_supabase_connection(supabase):
        print("❌ 無法連接到Supabase")
        
        if SCHEMA_NAME == "lawschatter":
            print("🔧 由於使用自定義 schema 'lawschatter'，嘗試自動設置權限...")
            if setup_schema_permissions(supabase):
                print("✓ 權限設置成功，重新測試連接...")
                if test_supabase_connection(supabase):
                    print("✅ 連接測試成功！繼續執行匯入...")
                else:
                    print("❌ 權限設置後仍無法連接，請檢查以下設定:")
                    print("  1. 確認 main_judgments 表格存在於 lawschatter schema 中")
                    print("  2. 確認 Supabase Dashboard API Settings 中已將 'lawschatter' 加入 Exposed schemas")
                    return
            else:
                print("❌ 無法自動設置權限，請按照上方指示手動設置後重新執行")
                return
        else:
            print("🔧 嘗試診斷正確的schema設定...")
            correct_config = diagnose_schema_settings(supabase)
            if correct_config:
                print(f"\n💡 建議修改代碼中的設定:")
                schema, table = correct_config.split('.')
                print(f"    SCHEMA_NAME = '{schema}'")
                print(f"    TABLE_NAME = '{table}'")
            else:
                print("\n💡 建議操作:")
                print("  1. 檢查 Supabase 中是否已建立相關表格")
                print("  2. 確認表格名稱是否正確")
                print("  3. 檢查 Service Key 是否有正確的權限")
            print("\n❌ 請修正設定後重新執行")
            return
    
    # 取得所有JSON檔案
    json_files = get_json_files(JSON_DIR)
    
    if not json_files:
        print("❌ 沒有找到JSON檔案")
        return
    
    print(f"📁 找到 {len(json_files)} 個JSON檔案")
    
    # 逐檔案處理並插入資料
    stats = process_files_individually(supabase, json_files, delete_after_insert, stop_on_error, auto_fix_json)
    
    # 最終結果報告
    if stats['failed'] == 0:
        print("🎉 所有資料匯入完成！")
    elif stop_on_error and stats['failed'] > 0:
        print("❌ 匯入過程中遇到錯誤並停止")
    else:
        print("⚠️ 部分資料匯入失敗，請檢查錯誤訊息")
        
    if delete_after_insert and stats['successful'] > 0:
        print(f"🗑️ 已刪除 {stats['successful']} 個成功處理的JSON檔案")
        
    # 提供建議
    if stats['failed'] > 0:
        print("\n💡 建議:")
        if stop_on_error:
            print("  - 解決當前錯誤後重新執行腳本")
            print("  - 或使用 --continue-on-error 參數跳過錯誤檔案")
        print("  - 檢查Supabase連接設定和表格權限")
        print("  - 確認JSON檔案格式正確")

if __name__ == "__main__":
    main()

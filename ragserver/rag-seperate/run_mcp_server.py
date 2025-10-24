#!/usr/bin/env python3
"""
啟動 FastMCP Qdrant 搜尋伺服器
"""
import sys
import os

# 添加當前目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server_fastmcp import mcp

def main():
    """啟動 MCP 伺服器"""
    print("🚀 啟動 FastMCP Qdrant 搜尋伺服器...")
    print("=" * 50)
    print("可用工具:")
    print("- qdrant_search: 在 Qdrant 中搜尋文件")
    print("- build_filter_help: 建構篩選條件幫助")
    print("- collection_schema: 取得集合結構")
    print("- list_collections: 列出所有集合")
    print("- collection_info: 取得集合詳細資訊")
    print("=" * 50)
    print("按 Ctrl+C 停止伺服器")
    print()
    
    try:
        # 啟動 FastMCP 伺服器
        mcp.run()
    except KeyboardInterrupt:
        print("\n👋 伺服器已停止")
    except Exception as e:
        print(f"❌ 伺服器錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

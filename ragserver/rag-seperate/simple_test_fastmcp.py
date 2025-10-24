#!/usr/bin/env python3
"""
簡單測試 FastMCP 伺服器
"""
import asyncio
from mcp_server_fastmcp import mcp

async def simple_test():
    """簡單測試 FastMCP 工具"""
    print("🧪 簡單測試 FastMCP 工具")
    print("=" * 30)
    
    # 測試篩選幫助工具（不需要 Qdrant 連線）
    print("\n📖 測試篩選條件幫助...")
    try:
        result = await mcp.call_tool("build_filter_help", {"filter_type": "simple"})
        print("✅ 篩選幫助工具運行成功")
        print(f"返回類型: {type(result)}")
        if isinstance(result, tuple):
            print(f"結果內容: {result[1].get('result', 'No result')[:200]}...")
        else:
            print(f"結果內容: {str(result)[:200]}...")
    except Exception as e:
        print(f"❌ 錯誤: {e}")
    
    print("\n🎉 測試完成！")

if __name__ == "__main__":
    asyncio.run(simple_test())

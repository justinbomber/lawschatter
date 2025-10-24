#!/usr/bin/env python3
"""
測試 FastMCP 伺服器的功能
"""
import asyncio
import json
from mcp_server_fastmcp import mcp

async def test_tools():
    """測試所有工具功能"""
    print("🧪 測試 FastMCP Qdrant 搜尋工具")
    print("=" * 50)
    
    # 測試列出集合
    print("\n📋 測試列出集合...")
    try:
        result = await mcp.call_tool("list_collections", {})
        print(f"結果: {result}")
    except Exception as e:
        print(f"錯誤: {e}")
    
    # 測試篩選幫助
    print("\n📖 測試篩選條件幫助...")
    try:
        result = await mcp.call_tool("build_filter_help", {"filter_type": "examples"})
        print(f"結果: {result}")
    except Exception as e:
        print(f"錯誤: {e}")
    
    # 測試集合結構（如果有集合的話）
    print("\n🔍 測試集合結構分析...")
    try:
        collections_result = await mcp.call_tool("list_collections", {})
        # 從 FastMCP 的返回結果中提取 JSON 字串
        if isinstance(collections_result, tuple) and len(collections_result) > 1:
            result_data = collections_result[1].get('result', '{}')
            collections_data = json.loads(result_data)
        else:
            collections_data = json.loads(collections_result)
        
        if collections_data.get("collections"):
            collection_name = collections_data["collections"][0]
            print(f"分析集合: {collection_name}")
            result = await mcp.call_tool("collection_schema", {"collection": collection_name})
            print(f"結果: {result}")
        else:
            print("沒有可用的集合")
    except Exception as e:
        print(f"錯誤: {e}")

if __name__ == "__main__":
    asyncio.run(test_tools())

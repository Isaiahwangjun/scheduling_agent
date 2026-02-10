"""
MCP Client - 使用 langchain-mcp-adapters 連接 MCP Server
"""

import sys
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient

# MCP Server 路徑
MCP_SERVER_PATH = Path(__file__).parent.parent / "mcp_server.py"

# Tools cache
_tools_cache = None


async def get_mcp_tools():
    """取得 MCP Tools（從 Server 動態取得）"""
    global _tools_cache

    if _tools_cache is not None:
        return _tools_cache

    client = MultiServerMCPClient({
        "calendar": {
            "command": sys.executable,
            "args": [str(MCP_SERVER_PATH)],
            "transport": "stdio",
        }
    })
    _tools_cache = await client.get_tools()
    return _tools_cache

import os
import json
import asyncio
import httpx
from typing import Any, Dict, List
from crewai.tools import BaseTool
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp import ClientSession

class DeepWikiTool(BaseTool):
    name: str = "DeepWiki Tool"
    description: str = "Search DeepWiki for technical analysis, token fundamentals, and trend data. Requires DEEPWIKI_API_KEY."
    api_key: str = None
    endpoint: str = "https://mcp.deepwiki.com/mcp"

    def _run(self, query: str) -> str:
        """
        Execute a search on DeepWiki using the MCP protocol.
        """
        if not self.api_key:
            self.api_key = os.environ.get("DEEPWIKI_API_KEY")
        
        try:
            return asyncio.run(self._execute_mcp_search(query))
        except Exception as e:
            return f"DeepWiki Tool Error: {str(e)}"

    async def _execute_mcp_search(self, query: str) -> str:
        """
        Connect to DeepWiki MCP server and execute search.
        """
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-API-Key"] = self.api_key
        
        async with sse_client(self.endpoint, headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                tools = await session.list_tools()
                search_tool_name = None
                for tool in tools.tools:
                    if "search" in tool.name.lower():
                        search_tool_name = tool.name
                        break
                
                if not search_tool_name:
                    return "DeepWiki Error: Search tool not found on server."
                
                # 実際の検索実行
                result = await session.call_tool(search_tool_name, arguments={"query": query})
                
                # 結果の解析と返却
                if hasattr(result, 'content'):
                    return str(result.content)
                return str(result)

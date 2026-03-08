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
        # Load API key from env if not set
        if not self.api_key:
            self.api_key = os.environ.get("DEEPWIKI_API_KEY")
        
        # Proceed even without API key (Public Mode)
        try:
            # Run the async MCP client in a sync context
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
        
        # Use the SSE client (even though the endpoint says /mcp, it might be SSE-compatible or streamable)
        # The error message said "Streamable HTTP". Let's assume standard MCP over HTTP.
        # But wait, mcp library's sse_client might support it.
        # Let's try the sse_client on the new endpoint.
        
        async with sse_client(self.endpoint, headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # List tools to find the search tool name
                tools = await session.list_tools()
                search_tool_name = None
                for tool in tools.tools:
                    if "search" in tool.name.lower():
                        search_tool_name = tool.name
                        break
                
                if not search_tool_name:
                    return f"Error: No search tool found in DeepWiki MCP. Available tools: {[t.name for t in tools.tools]}"
                
                # Call the search tool
                result = await session.call_tool(search_tool_name, {"query": query})
                
                # Parse result
                if result.is_error:
                    return f"DeepWiki Search Failed: {result.content}"
                
                # Extract text content
                content = ""
                for item in result.content:
                    if item.type == "text":
                        content += item.text + "\n"
                
                return content

if __name__ == "__main__":
    # Simple test if run directly
    tool = DeepWikiTool()
    print(tool._run("test query"))

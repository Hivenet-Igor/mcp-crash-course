import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

llm = ChatOpenAI()

class MCPServerManager:
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path) if base_path else Path(__file__).parent
        self.servers = {}
    
    def add_server(self, name: str, script_path: str, command: str = "python"):
        """Add a server configuration."""
        full_path = self.base_path / script_path
        self.servers[name] = {
            "command": command,
            "args": [str(full_path)]
        }
        return self
    
    async def load_server_tools(self, server_name: str, server_config: dict) -> list:
        """Load tools from a single MCP server."""
        server_params = StdioServerParameters(**server_config)
        
        async with stdio_client(server_params) as (read, write):    
            async with ClientSession(read_stream=read, write_stream=write) as session:
                await session.initialize()
                print(f"{server_name.title()} server initialized")
                tools = await load_mcp_tools(session)
                return tools
    
    async def load_all_tools(self) -> list:
        """Load tools from all configured servers concurrently."""
        tasks = [
            self.load_server_tools(name, config) 
            for name, config in self.servers.items()
        ]
        
        # Load all servers concurrently
        tool_lists = await asyncio.gather(*tasks)
        
        # Flatten the list of tool lists
        all_tools = []
        for tools in tool_lists:
            all_tools.extend(tools)
        
        return all_tools

async def main():
    # Configure servers in a clean, chainable way
    manager = MCPServerManager()
    manager.add_server("math", "servers/math_server.py") \
           .add_server("weather", "servers/weather_server.py")
    
    # Load all tools
    tools = await manager.load_all_tools()
    
    print(f"Total tools loaded: {len(tools)}")
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")
    
    # Example usage with agent
    # agent = create_react_agent(llm, tools)
    # result = await agent.ainvoke({"messages": [HumanMessage(content="What is 54 + 2 * 3?")]})
    # print(result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())

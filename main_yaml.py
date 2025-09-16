import asyncio
import yaml
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

async def load_server_tools(server_name: str, server_config: dict, base_path: Path) -> list:
    """Load tools from a single MCP server."""
    script_path = base_path / server_config['script']
    server_params = StdioServerParameters(
        command=server_config['command'],
        args=[str(script_path)]
    )
    
    async with stdio_client(server_params) as (read, write):    
        async with ClientSession(read_stream=read, write_stream=write) as session:
            await session.initialize()
            print(f"{server_name.title()} server initialized")
            tools = await load_mcp_tools(session)
            return tools

async def main():
    base_path = Path(__file__).parent
    
    # Load server configuration from YAML
    with open(base_path / "servers.yaml", 'r') as file:
        config = yaml.safe_load(file)
    
    # Load tools from all configured servers
    tasks = [
        load_server_tools(name, server_config, base_path)
        for name, server_config in config['servers'].items()
    ]
    
    tool_lists = await asyncio.gather(*tasks)
    all_tools = [tool for tools in tool_lists for tool in tools]
    
    print(f"Total tools loaded: {len(all_tools)}")
    for tool in all_tools:
        print(f"- {tool.name}: {tool.description}")

if __name__ == "__main__":
    asyncio.run(main())

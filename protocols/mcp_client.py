import asyncio
import json
import nest_asyncio 
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from utils.logger import get_logger

# Apply the patch immediately
nest_asyncio.apply()

logger = get_logger("MCP_CLIENT")

async def call_remote_mcp(port: int, tool_name: str, arguments: dict):
    """
    Connects to a FastMCP server via SSE and calls a tool.
    """
    url = f"http://127.0.0.1:{port}/sse"
    logger.debug(f"Attempting connection to {url} for tool '{tool_name}'")
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                logger.info(f"Calling Tool: {tool_name}")
                result = await session.call_tool(tool_name, arguments)
                
                # Extract Text Content
                if result.content and len(result.content) > 0:
                    response = result.content[0].text
                    return response
                
                logger.warning(f"Port {port} returned Empty Content")
                return None
                
    except Exception as e:
        logger.error(f"CONNECTION ERROR (Port {port}): {str(e)}")
        # Return a JSON error string so the caller can parse it gracefully
        return json.dumps({"status": "error", "message": f"Connection Failed: {str(e)}"})

def sync_mcp_call(port, tool_name, args):
    """Wrapper to run async MCP calls in sync agents"""
    try:
        # Check if a loop is already running (FastAPI case)
        loop = asyncio.get_running_loop()
        if loop.is_running():
            # Use the existing loop
            return loop.run_until_complete(call_remote_mcp(port, tool_name, args))
    except RuntimeError:
        pass # No running loop, proceed to create new one

    # Fallback for scripts/Streamlit where no loop exists
    return asyncio.run(call_remote_mcp(port, tool_name, args))
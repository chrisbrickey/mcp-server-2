"""FastMCP server providing example tools and resources."""

from dotenv import load_dotenv
from fastmcp import FastMCP

from greenroom.tools import register_all_tools

# Load environment variables
load_dotenv()

# Create FastMCP instance
mcp = FastMCP("greenroom")

@mcp.resource("config://version")
def get_version() -> str:
    """Get MCP server version."""
    return "0.1.0"

# Register all tools
register_all_tools(mcp)

def main() -> None:
    """Run the MCP server."""
    mcp.run()

if __name__ == "__main__":
    main()

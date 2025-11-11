"""FastMCP server providing example tools and resources."""

from fastmcp import FastMCP

# Create FastMCP instance
mcp = FastMCP("mcp-server-2")

@mcp.tool()
def speak() -> str:
    """Return a test message to verify the MCP server is responding."""
    return "I'm inside the server."

@mcp.resource("config://version")
def get_version() -> str:
    """Get MCP server version."""
    return "0.1.0"

def main() -> None:
    """Run the MCP server."""
    mcp.run()

if __name__ == "__main__":
    main()

"""MCP tools for the greenroom server."""

from fastmcp import FastMCP

from greenroom.tools.fetching_tools import register_fetching_tools
from greenroom.tools.operations_tools import register_operations_tools


def register_all_tools(mcp: FastMCP) -> None:
    """Register all tools with the MCP server."""
    register_fetching_tools(mcp)
    register_operations_tools(mcp)


__all__ = ["register_all_tools"]

# mcp-server-2

A simple python package containing a Model Context Protocol (MCP) server that provides utilities to agents.
I'm using this repo to learn about MCP server implementation.

## Dependencies
- **Python 3.12** 
- **FastMCP >=2.13.0** - MCP server framework; requires Python 3.10+
- **uv** -  package manager; [installation instructions](https://github.com/astral-sh/uv#installation)
- **Hatchling** - build system

_This project uses the **FastMCP** framework, which requires less boilerplate than other frameworks (e.g., MCP Python SDK)._
_See [mcp-server-1](https://github.com/chrisbrickey/mcp-server-1) for examples where functionality is more explicit._

## Features

### Tools
These tools are callable actions, analogous to POST requests. An agent executes these operations which may have side effects.
Tools are annotated with `@mcp.tool()` in the FastMCP framework.
- Tools will be added in the future.

### Resources
These resources provide read-only data, analogous to GET requests. An agent reads the information but does not performa actions. 
Resources are annotated with `@mcp.resource()` in the FastMCP framework.
- **config://version** - Get server version

## Project Structure
This project follows the modern Python src/ layout to support convenient packaging and testing.

```
mcp-server-2/
├── src/
│   └── mcp_server_2/          # python package
│       ├── __init__.py
│       └── server.py          # primary entry point to server
├── pyproject.toml             # configuration and dependencies
├── uv.lock                    # dependency lock file (auto-generated)
├── .python-version            
├── .gitignore
└── README.md
```

### Growing This Project
As the server becomes more complex, new files will be added to the package (`src/mcp_server_2/`).

```
src/mcp_server_2/          # python package
├── __init__.py
├── server.py              # primary entry point to server
├── tools/                 # tools organized into modules
│   ├── __init__.py
│   ├── math_tools.py
│   └── data_tools.py
└── utils.py               # shared utilities
```


## Setup

```bash
# Clone the repository
git clone <repository-url>
cd mcp-server-2

# Install dependencies (uv will create a virtual environment automatically)
uv sync
```

## Development

### Run the MCP Server Locally
The server will start and communicate via stdio (standard input/output), which is the standard transport for local MCP servers.

```
# best approach uses the MCP entry point
uv run mcp-server-2
```

```
# alternative: via python
uv run python src/mcp_server_2/server.py
```

_NB: You should not run the server directly (e.g. `uv run <path to server.py>`) because the server is part of a python package.
Running it directly would break the module resolution._

### Inspect using MCP Inspector (web ui)
```
  npx @modelcontextprotocol/inspector uv --directory /ABSOLUTE/PATH/TO/PROJECT run python src/mcp_server_2/server.py
```

## Interacting with the MCP Server
This project does not yet include a frontend with which to exercise the server, but you can use anthropic tooling to interact with the server.

### via Claude Code
Claude Code has native MCP client support so it can connect to your MCP server using the stdio transport, which the 
FastMCP server already uses. 

1. Run the setup command
```
  claude mcp add --transport stdio mcp-server-2 uv -- --directory /ABSOLUTE/PATH/TO/PROJECT run python src/mcp_server_2/server.py
```

2. Open claude code
- Enter `/mcp` to view available MCP servers. Confirm that mcp-server-2 is one of them.

3. Exercise the server
- Resources can be referenced with @ mentions
- Tools will automatically be used during the conversation
- Prompts show up as / slash commands 
- To explicitly test a tool, ask claude to call the tool. e.g. `Call the <name-of-tool> tool from the MCP server called mcp-server-2.`

_When you update the methods on the MCP server, you must rerun all of these steps in order for the updates to be available to the claude session._


### Alternative: via Claude Desktop 

1. Download [Claude Desktop](https://www.claude.com/download)
_Make sure you download the actual native desktop client - not the wrapper on the web client._

2. Add the server to the Claude Desktop configuration file (`claude_desktop_config.json`).
_If this file does not already exist, create it here: *macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`._

```json
{
  "mcpServers": {
    "mcp-server-2": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/PROJECT",
        "run",
        "python",
        "src/mcp_server_2/server.py"
      ]
    }
  }
}
```
_Replace `/ABSOLUTE/PATH/TO/PROJECT` with the actual path to the project directory (not the package directory)._

3. Restart Claude Desktop.

## How It Works

1. The `pyproject.toml` file declares the `fastmcp` dependency managed by uv
2. When an agent (e.g. claude code) starts, it launches this MCP server as a subprocess using the configured command
3. `uv` automatically manages the virtual environment and dependencies
4. The server advertises its available resources and tools (e.g. the `tools/list` JSON-RPC method)
5. During conversations, the agent can automatically call these tools when relevant
6. The server executes the requested tool and returns results to the agent
7. The agent incorporates the results into its response to you

## Future Development

- Add testing infrastructure
- Add more useful resources and tools
- Add helper agents and coordinate their activity
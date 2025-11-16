# greenroom

A simple python package containing an MCP (Model Context Protocol) server that provides entertainment recommender utilities to agents. 
This server integrates with [TMDB](www.themoviedb.org), a free and community-driven database of entertainment content.

## Features

### Tools
These tools are callable actions, analogous to POST requests. An agent executes these operations which may have side effects.
Tools are annotated with `@mcp.tool()` in the FastMCP framework.
- **list_genres** - Fetches all entertainment genres from TMDB API for movies and TV shows, returning a unified map showing which media types support each genre

_NB: The `@mcp.tool()` decorator wraps the function into a FunctionTool object, which prevents it from being called directly including by tests. The logic of tool methods is extracted to helpers methods, which are covered by unit tests._

### Resources
These resources provide read-only data, analogous to GET requests. An agent reads the information but does not performa actions. 
Resources are annotated with `@mcp.resource()` in the FastMCP framework.
- **config://version** - Get server version

### Contexts
Context-aware tools use FastMCP's `Context` parameter to access advanced MCP features like LLM sampling.

- **list_genres_simplified** - Returns a simplified list of genre names by using `ctx.sample()` to leverage the agent's LLM capabilities for data transformation - it asks the current client's LLM to reformat the data. If sampling is not supported by the current client, then the method falls back to direct extraction of genres using python code.

#### How It Works

```
Agent → list_genres_simplified(ctx)
      → fetch_genres() [gets full structured data]
      → ctx.sample() [asks agent to simplify it]
      → Returns clean, sorted list to agent
```

#### Client Support

Sampling requires the MCP client to support callbacks to its LLM, which is a security-sensitive feature:
- **Claude Desktop**: Does NOT currently support sampling
- **Claude Code**: Also unlikely to support it currently

#### Use Cases

While using a context to simplify the format of `list_genres` is overkill, the pattern demonstrates agent-to-agent communication useful for:
- Summarizing large documents
- Analyzing sentiment
- Making recommendations based on data
- Multi-step workflows with decision points



## Project Structure
This project follows the modern Python src/ layout to support convenient packaging and testing.

```
greenroom/                  # project root
├── src/
│   └── greenroom/          # python package
│       ├── __init__.py
│       └── server.py       # primary entry point to server
├── pyproject.toml          # configuration and dependencies
├── uv.lock                 # dependency lock file (auto-generated)
├── .python-version            
├── .gitignore
└── README.md
```

### Growing This Project
As the server becomes more complex, new files will be added to the package (`src/greenroom/`).

```
src/greenroom/          # python package
├── __init__.py
├── server.py           # primary entry point to server
├── tools/              # tools organized into modules
│   ├── __init__.py
│   ├── math_tools.py
│   └── data_tools.py
└── utils.py            # shared utilities
```

## Dependencies

- **Python 3.12** 
- **FastMCP >=2.13.0** - MCP server framework; requires Python 3.10+
- **uv** -  package manager; [installation instructions](https://github.com/astral-sh/uv#installation)
- **Hatchling** - build system
- **httpx** - for API calls to TMDB
- **python-dotenv** - for API key management

_This project uses the **FastMCP** framework, which requires less boilerplate than other frameworks (e.g., MCP Python SDK)._
_See [mcp-server-1](https://github.com/chrisbrickey/mcp-server-1) for examples where functionality is more explicit._

## Setup

1. Create local development environment
```
# Clone the repository
git clone <repository-url>
cd greenroom

# Install dependencies (uv will create a virtual environment automatically)
uv sync
```

2. Add TMDB api key as environment variable
- Get a free API key at [TMDB](www.themoviedb.org) by creating an account, going to account settings, and navigating to the API section.
- Create a file called `.env` at the top level of the project. (This file is gitignored to prevent committing secrets.)
- Copy the content of `.env.example` to your new file.
- Replace `your_tmdb_api_key_here` in .env with the actual TMDB API key.


## Development

### Run the MCP Server Locally
The server will start and communicate via stdio (standard input/output), which is the standard transport for local MCP servers.

```
# best approach uses the MCP entry point
uv run greenroom
```

```
# alternative: via python
uv run python src/greenroom/server.py
```

_NB: You should not run the server directly (e.g. `uv run <path to server.py>`) because the server is part of a python package.
Running it directly would break the module resolution._

### Inspect using MCP Inspector (web ui)
```
  npx @modelcontextprotocol/inspector uv --directory /ABSOLUTE/PATH/TO/PROJECT run python src/greenroom/server.py
```

### Run tests
```
uv run python -m pytest

# alternative to printout test names for quicker debugging
uv run python -m pytest -v
```

## Interacting with the MCP Server
This project does not yet include a frontend with which to exercise the server, but you can use anthropic tooling to interact with the server.

### via Claude Code
Claude Code has native MCP client support so it can connect to your MCP server using the stdio transport, which the 
FastMCP server already uses. 

1. Run the setup command
```
  # Updates local claude settings and runs the MCP server
  claude mcp add --transport stdio greenroom uv -- --directory /ABSOLUTE/PATH/TO/PROJECT run python src/greenroom/server.py
```

2. Open claude code
- Enter `/mcp` to view available MCP servers. Confirm that greenroom is one of them.

3. Exercise the server
- Resources can be referenced with @ mentions
- Tools will automatically be used during the conversation
- Prompts show up as / slash commands
- To explicitly test a tool, ask claude to call the tool. e.g. `Call the <name-of-tool> tool from the MCP server called greenroom.`

When you update the methods on the MCP server, you must rerun all of the above steps in order for the updates to be available to the claude session.

#### Claude code troubleshooting
When you run the set up command (`claude mcp add`), a configuration for that MCP server is added to your local claude settings. 
On my local machine, mcp configurations are stored at `/Users/$USER_NAME/.claude.json`.

Manual configuration of the MCP server in claude settings:
```json
# Replace /ABSOLUTE/PATH/TO/PROJECT with the actual path to the project directory (not the package directory).
{
  "mcpServers": {
    "greenroom": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/PROJECT",
        "run",
        "python",
        "src/greenroom/server.py"
      ]
    }
  }
}
```

Remove the server from claude settings on local machine.
This might be useful if the configuration is not correct. Removing the server and then re-adding the server might be good way to resolve configuration issues.
```
  claude mcp remove greenroom
```

## How It Works

1. The `pyproject.toml` file declares the `fastmcp` dependency managed by uv
2. When an agent (e.g. claude code) starts, it launches this MCP server as a subprocess using the configured command
3. `uv` automatically manages the virtual environment and dependencies
4. The server advertises its available resources and tools (e.g. the `tools/list` JSON-RPC method)
5. During conversations, the agent can automatically call these tools when relevant
6. The server executes the requested tool and returns results to the agent
7. The agent incorporates the results into its response to you

## Future Development
- Add alternative media types (e.g. podcasts)
- Add helper agents using local LLMs or an additional LLM integration and coordinate the activity of those agents
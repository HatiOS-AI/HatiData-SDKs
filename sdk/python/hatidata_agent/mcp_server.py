"""MCP server for HatiData agent access.

Exposes HatiData as an MCP (Model Context Protocol) server, allowing
Claude and other MCP-compatible agents to query the data warehouse
directly. Tools provided:

- `query` — Execute SQL and return results
- `list_tables` — List available tables
- `describe_table` — Get schema for a table
- `get_context` — RAG context retrieval via full-text search

Usage::

    # Start the MCP server (stdio transport)
    hatidata-mcp-server --host localhost --port 5439

    # Or in Python
    from hatidata_agent.mcp_server import create_server
    server = create_server(host="localhost", port=5439)
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from hatidata_agent.client import HatiDataAgent


def create_tools(agent: HatiDataAgent) -> list[dict[str, Any]]:
    """Create MCP tool definitions."""
    return [
        {
            "name": "query",
            "description": (
                "Execute a SQL query against the HatiData warehouse. "
                "Returns results as a JSON array of objects. "
                "Supports Snowflake-compatible SQL syntax."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "The SQL query to execute",
                    },
                },
                "required": ["sql"],
            },
        },
        {
            "name": "list_tables",
            "description": "List all available tables in the database.",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "describe_table",
            "description": "Get the schema (columns, types) for a specific table.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to describe",
                    },
                },
                "required": ["table_name"],
            },
        },
        {
            "name": "get_context",
            "description": (
                "Retrieve relevant rows from a table using full-text search. "
                "Useful for RAG context retrieval."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Table to search",
                    },
                    "search_query": {
                        "type": "string",
                        "description": "Natural language search query",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Maximum results (default 10)",
                        "default": 10,
                    },
                },
                "required": ["table", "search_query"],
            },
        },
    ]


def handle_tool_call(
    agent: HatiDataAgent, tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Handle an MCP tool call and return the result."""
    try:
        if tool_name == "query":
            rows = agent.query(arguments["sql"])
            return {
                "content": [
                    {"type": "text", "text": json.dumps(rows, default=str)},
                ],
            }

        elif tool_name == "list_tables":
            rows = agent.query(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main' ORDER BY table_name"
            )
            tables = [row["table_name"] for row in rows]
            return {
                "content": [
                    {"type": "text", "text": json.dumps(tables)},
                ],
            }

        elif tool_name == "describe_table":
            table = arguments["table_name"]
            rows = agent.query(
                f"SELECT column_name, data_type, is_nullable "
                f"FROM information_schema.columns "
                f"WHERE table_name = '{table}' ORDER BY ordinal_position"
            )
            return {
                "content": [
                    {"type": "text", "text": json.dumps(rows, default=str)},
                ],
            }

        elif tool_name == "get_context":
            rows = agent.get_context(
                table=arguments["table"],
                search_query=arguments["search_query"],
                top_k=arguments.get("top_k", 10),
            )
            return {
                "content": [
                    {"type": "text", "text": json.dumps(rows, default=str)},
                ],
            }

        else:
            return {
                "content": [
                    {"type": "text", "text": f"Unknown tool: {tool_name}"},
                ],
                "isError": True,
            }

    except Exception as e:
        return {
            "content": [
                {"type": "text", "text": f"Error: {e}"},
            ],
            "isError": True,
        }


def run_stdio_server(agent: HatiDataAgent) -> None:
    """Run MCP server over stdio transport (JSON-RPC)."""
    tools = create_tools(agent)

    # Server info
    server_info = {
        "name": "hatidata",
        "version": "0.1.0",
        "capabilities": {
            "tools": {},
        },
    }

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = request.get("method", "")
        req_id = request.get("id")

        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": server_info,
                    "capabilities": server_info["capabilities"],
                },
            }

        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": tools},
            }

        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = handle_tool_call(agent, tool_name, arguments)
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result,
            }

        elif method == "notifications/initialized":
            continue  # No response needed for notifications.

        else:
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


def main() -> None:
    """Entry point for the MCP server CLI."""
    parser = argparse.ArgumentParser(description="HatiData MCP Server")
    parser.add_argument("--host", default="localhost", help="Proxy host")
    parser.add_argument("--port", type=int, default=5439, help="Proxy port")
    parser.add_argument("--agent-id", default="mcp-agent", help="Agent ID")
    parser.add_argument("--database", default="hatidata", help="Database")
    parser.add_argument("--user", default="agent", help="Username")
    parser.add_argument("--password", default="", help="Password")
    args = parser.parse_args()

    agent = HatiDataAgent(
        host=args.host,
        port=args.port,
        agent_id=args.agent_id,
        framework="anthropic",
        database=args.database,
        user=args.user,
        password=args.password,
    )

    run_stdio_server(agent)


if __name__ == "__main__":
    main()

"""HatiData MCP Server — Programmatic Start

Prerequisites:
    pip install hatidata-agent[mcp]

Usage:
    # Start the server:
    python mcp_server.py

    # Or use the CLI directly:
    hatidata-mcp-server --host localhost --port 5439
"""

import sys


def main():
    print("Starting HatiData MCP Server...")
    print("This exposes HatiData as tools for Claude, Cursor, and other MCP clients.")
    print()
    print("Tools available:")
    print("  - query: Execute SQL queries")
    print("  - list_tables: List available tables")
    print("  - describe_table: Get table schema")
    print("  - get_context: RAG context retrieval")
    print()

    # Start the MCP server (stdio transport)
    from hatidata_agent.mcp_server import main as mcp_main

    sys.argv = [
        "hatidata-mcp-server",
        "--host", "localhost",
        "--port", "5439",
        "--agent-id", "mcp-example",
    ]
    mcp_main()


if __name__ == "__main__":
    main()

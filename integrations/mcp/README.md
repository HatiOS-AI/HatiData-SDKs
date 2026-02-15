# HatiData MCP Server Configuration

Ready-made configuration files for connecting HatiData's MCP server to your preferred AI client.

## Supported Clients

| Client | Config File | Status |
|--------|------------|--------|
| Claude Desktop | [`claude-desktop.json`](./claude-desktop.json) | Ready |
| Claude Code | [`claude-code.json`](./claude-code.json) | Ready |
| Cursor | [`cursor.json`](./cursor.json) | Ready |

## Quick Setup

### Claude Desktop

Copy `claude-desktop.json` to your Claude Desktop config directory:

```bash
# macOS
cp claude-desktop.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Linux
cp claude-desktop.json ~/.config/claude/claude_desktop_config.json
```

### Cursor

Copy `cursor.json` to your Cursor MCP config:

```bash
cp cursor.json ~/.cursor/mcp.json
```

### Claude Code

Copy `claude-code.json` to your project's `.claude/` directory:

```bash
cp claude-code.json .claude/mcp.json
```

## Available Tools (23)

| Category | Tools |
|----------|-------|
| **SQL** | `run_sql`, `run_sql_readonly`, `list_schemas`, `list_tables`, `describe_table`, `get_usage_stats` |
| **Memory** | `store_memory`, `search_memory`, `get_agent_state`, `set_agent_state`, `delete_memory` |
| **Chain-of-Thought** | `log_reasoning_step`, `replay_decision`, `get_session_history` |
| **Triggers** | `register_trigger`, `list_triggers`, `delete_trigger`, `test_trigger` |
| **Branching** | `branch_create`, `branch_query`, `branch_merge`, `branch_discard`, `branch_list` |

## Directory Listings

See [DIRECTORY_SUBMISSION.md](./DIRECTORY_SUBMISSION.md) for submission status across MCP directories.

| Directory | Status |
|-----------|--------|
| Smithery.ai | Pending (manifest ready: [`smithery.yaml`](./smithery.yaml)) |
| Glama | Pending |
| mcp.run | Pending |

## Prerequisites

```bash
pip install hatidata-agent
```

Or initialize a local warehouse with the CLI:

```bash
cargo install hatidata-cli
hati init my-warehouse
```

The MCP server connects to HatiData on port 5439.

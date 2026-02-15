# MCP Directory Submission Tracker

## Overview

HatiData MCP Server provides 23 tools across 5 categories: SQL, Memory, Chain-of-Thought, Triggers, and Branching.

## Directory Submissions

| Directory | URL | Status | Submission Date | Notes |
|-----------|-----|--------|----------------|-------|
| **Smithery.ai** | https://smithery.ai | Pending | — | Primary directory. Submit via GitHub PR to smithery-ai/registry |
| **Glama** | https://glama.ai/mcp | Pending | — | Submit via https://glama.ai/mcp/submit |
| **mcp.run** | https://mcp.run | Pending | — | Submit via their GitHub repo |
| **MCP Hub** | https://mcphub.io | Pending | — | Community directory |

## Submission Checklist

### Smithery.ai (Primary)

- [ ] `smithery.yaml` manifest created (see `smithery.yaml` in this directory)
- [ ] All 23 tools documented with descriptions and scopes
- [ ] Install command specified (`pip install hatidata-agent`)
- [ ] Repository URL and homepage set
- [ ] Fork https://github.com/smithery-ai/registry
- [ ] Add entry to registry
- [ ] Open PR with manifest

### Glama

- [ ] Visit https://glama.ai/mcp/submit
- [ ] Fill in server details:
  - Name: `hatidata-mcp-server`
  - Description: MCP server for HatiData data warehouse
  - Repository: https://github.com/HatiOS-AI/HatiData-Core
  - Install: `pip install hatidata-agent`
- [ ] Submit for review

### mcp.run

- [ ] Fork their registry repo
- [ ] Add server entry
- [ ] Open PR

## Tool Summary (for directory descriptions)

**23 tools in 5 categories:**

| Category | Tools | Description |
|----------|-------|-------------|
| SQL (6) | `run_sql`, `run_sql_readonly`, `list_schemas`, `list_tables`, `describe_table`, `get_usage_stats` | Query execution and schema exploration |
| Memory (5) | `store_memory`, `search_memory`, `get_agent_state`, `set_agent_state`, `delete_memory` | Persistent agent memory and state |
| Chain-of-Thought (3) | `log_reasoning_step`, `replay_decision`, `get_session_history` | Decision logging and replay |
| Triggers (4) | `register_trigger`, `list_triggers`, `delete_trigger`, `test_trigger` | Event-driven automation |
| Branching (5) | `branch_create`, `branch_query`, `branch_merge`, `branch_discard`, `branch_list` | Isolated query experimentation |

## Short Description (for directory listings)

> HatiData MCP Server — Query your data warehouse, manage agent memory, and branch queries from Claude, Cursor, and Cline. 23 tools across SQL, memory, chain-of-thought, triggers, and branching.

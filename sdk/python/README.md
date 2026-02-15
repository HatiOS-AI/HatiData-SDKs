# HatiData Agent SDK

[![PyPI version](https://img.shields.io/pypi/v/hatidata-agent.svg)](https://pypi.org/project/hatidata-agent/)
[![Python versions](https://img.shields.io/pypi/pyversions/hatidata-agent.svg)](https://pypi.org/project/hatidata-agent/)
[![License](https://img.shields.io/pypi/l/hatidata-agent.svg)](https://github.com/HatiOS-AI/hatidata-core/blob/main/LICENSE)

**RAM for Agents** — Python SDK for AI agents to query HatiData's in-VPC data warehouse with sub-10ms latency via Postgres wire protocol.

## Installation

```bash
pip install hatidata-agent

# With async support
pip install hatidata-agent[async]

# With LangChain support
pip install hatidata-agent[langchain]

# With MCP server
pip install hatidata-agent[mcp]

# Everything
pip install hatidata-agent[all]
```

## Quick Start

```python
from hatidata_agent import HatiDataAgent

agent = HatiDataAgent(
    host="proxy.internal",
    port=5439,
    agent_id="my-agent",
    framework="langchain",
)

# Simple query
rows = agent.query("SELECT * FROM customers WHERE status = 'active' LIMIT 10")
print(rows)  # [{"id": 1, "name": "Acme Corp", ...}, ...]
```

## Features

- **Sub-10ms query latency** -- In-VPC execution, no data leaves your network
- **Postgres wire protocol** -- Works with any Postgres client library
- **Reasoning chain tracking** -- Multi-step audit trails for agent workflows
- **RAG context retrieval** -- Full-text and vector similarity search
- **LangChain integration** -- Drop-in `SQLDatabase` replacement for LangChain agents
- **MCP server** -- Expose HatiData as tools for Claude and other MCP-compatible agents
- **Agent identification** -- Per-agent billing, priority scheduling, and audit via Postgres startup parameters
- **Snowflake SQL compatible** -- Bring existing queries without rewrites

## Reasoning Chain Tracking

Track multi-step reasoning chains for audit and debugging:

```python
with agent.reasoning_chain("req-001") as chain:
    # Step 0: Discover tables
    tables = chain.query("SELECT table_name FROM information_schema.tables")

    # Step 1: Get relevant data
    customers = chain.query("SELECT * FROM customers WHERE tier = 'enterprise'", step=1)

    # Step 2: Aggregate
    revenue = chain.query("SELECT SUM(revenue) FROM orders WHERE customer_id IN (...)", step=2)
```

## RAG Context Retrieval

```python
# Full-text search
context = agent.get_context("customers", "enterprise accounts in US", top_k=5)

# Vector similarity search
context = agent.get_rag_context("docs", "embedding", query_vector, top_k=10)
```

## LangChain Integration

```python
from hatidata_agent.langchain import HatiDataSQLDatabase
from langchain.agents import create_sql_agent

db = HatiDataSQLDatabase(
    host="proxy.internal",
    port=5439,
    agent_id="sql-agent-1",
)

agent = create_sql_agent(llm=llm, db=db, verbose=True)
result = agent.run("How many enterprise customers do we have?")
```

## MCP Server

Run as an MCP server for Claude and other MCP-compatible agents:

```bash
# Start the MCP server
hatidata-mcp-server --host proxy.internal --port 5439

# Or add to Claude Code's MCP config:
# ~/.claude/mcp.json
{
  "mcpServers": {
    "hatidata": {
      "command": "hatidata-mcp-server",
      "args": ["--host", "proxy.internal", "--port", "5439"]
    }
  }
}
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `query` | Execute SQL and return JSON results |
| `list_tables` | List available tables |
| `describe_table` | Get table schema |
| `get_context` | RAG context retrieval via full-text search |

## Agent Identification

The SDK automatically identifies agents via Postgres startup parameters:

| Parameter | Purpose |
|-----------|---------|
| `hatidata_agent_id` | Unique agent identifier |
| `hatidata_framework` | AI framework (langchain, crewai, autogen, etc.) |
| `hatidata_priority` | Scheduling priority (low, normal, high, critical) |
| `hatidata_request_id` | Request/reasoning chain ID |
| `hatidata_reasoning_step` | Step number within a chain |

These enable per-agent billing, priority scheduling, audit trails, and the Agent Tax Report showing savings vs legacy cloud warehouses.

## Documentation

Full documentation is available at [docs.hatiosai.com/hatidata](https://docs.hatiosai.com/hatidata).

## License

Apache License 2.0. Copyright (c) Marviy Pte Ltd. See [LICENSE](https://github.com/HatiOS-AI/hatidata-core/blob/main/LICENSE) for details.

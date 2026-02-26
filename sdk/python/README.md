# HatiData Python SDK

[![PyPI version](https://img.shields.io/pypi/v/hatidata-agent.svg)](https://pypi.org/project/hatidata-agent/)
[![Python versions](https://img.shields.io/pypi/pyversions/hatidata-agent.svg)](https://pypi.org/project/hatidata-agent/)
[![License](https://img.shields.io/pypi/l/hatidata-agent.svg)](https://github.com/HatiOS-AI/HatiData-SDKs/blob/main/LICENSE)

**Every Agent Deserves a Brain.** Python SDK for HatiData -- the agent-native data platform. Sub-10ms SQL queries via Postgres wire protocol, plus a full Control Plane client for agent memory, semantic triggers, state branching, chain-of-thought audit trails, and JIT access.

## Installation

```bash
pip install hatidata-agent
```

## Two Clients, One SDK

| Client | Purpose | Protocol |
|--------|---------|----------|
| `HatiDataAgent` | SQL queries via proxy (data plane) | Postgres wire protocol |
| `ControlPlaneClient` | Agent-native features (memory, triggers, branches, CoT) | REST API |

## Quick Start -- Data Plane

```python
from hatidata_agent import HatiDataAgent

agent = HatiDataAgent(
    host="proxy.internal",
    port=5439,
    agent_id="my-agent",
    framework="langchain",
)

rows = agent.query("SELECT * FROM customers WHERE status = 'active' LIMIT 10")
```

## Quick Start -- Control Plane

```python
from hatidata_agent import ControlPlaneClient

cp = ControlPlaneClient(
    base_url="https://api.hatidata.com",
    email="you@company.com",
    password="...",
)
cp.login()

# Agent memory
cp.create_memory(agent_id="my-agent", content="User prefers dark mode")
results = cp.search_memory(query="user preferences", top_k=5)

# Semantic triggers
trigger = cp.create_trigger(name="PII detected", concept="personal data exposure")
result = cp.test_trigger(trigger["id"], "User SSN is 123-45-6789")

# State branching
branch = cp.create_branch(agent_id="analyst", tables=["portfolio"])
cp.merge_branch(branch["id"], strategy="branch_wins")

# Chain-of-thought audit trail
session_id, traces = cp.build_cot_session(
    agent_id="my-agent",
    org_id=cp.org_id,
    steps=[
        {"type": "Thought", "content": {"text": "Analyzing customer data"}},
        {"type": "ToolCall", "content": {"tool": "sql_query", "query": "SELECT ..."}},
        {"type": "LlmResponse", "content": {"answer": "Found 42 enterprise accounts"}},
    ],
)
cp.ingest_cot(traces)
verification = cp.verify_cot(session_id)  # SHA-256 hash chain verification
```

## Features

### Data Plane (`HatiDataAgent`)

- **Sub-10ms query latency** -- in-VPC execution, no data leaves your network
- **Postgres wire protocol** -- works with any Postgres client library
- **Reasoning chain tracking** -- multi-step audit trails for agent workflows
- **RAG context retrieval** -- full-text and vector similarity search
- **Snowflake SQL compatible** -- bring existing queries without rewrites
- **Agent identification** -- per-agent billing, scheduling, and audit via startup parameters

### Control Plane (`ControlPlaneClient`)

- **Agent memory** -- store, search, and manage long-term agent memories with vector embeddings
- **Semantic triggers** -- register concept-based triggers that fire on semantic similarity
- **State branching** -- create isolated data branches for experimentation, merge winners, discard losers
- **Chain-of-thought** -- SHA-256 hash-chained audit trails for tamper-evident reasoning logs
- **JIT access** -- request time-bounded privilege escalation for agents and humans
- **JWT and API key auth** -- auto-login on first request, org-scoped endpoints

## Control Plane API Reference

### Authentication

```python
cp = ControlPlaneClient(base_url="...", email="...", password="...")
cp.login()  # JWT auth -- auto-called on first request

# Or use API key auth (no login needed)
cp = ControlPlaneClient(base_url="...", api_key="hd_live_...", org_id="org-...")
```

### Agent Memory

```python
# Create
mem = cp.create_memory(agent_id="agent-1", content="...", memory_type="observation")

# List with filters
memories = cp.list_memories(agent_id="agent-1", memory_type="observation", limit=20)

# Semantic search
results = cp.search_memory(query="user preferences", agent_id="agent-1", top_k=5)

# Delete
cp.delete_memory(mem["id"])

# Embedding stats
stats = cp.embedding_stats()
```

### Semantic Triggers

```python
# Register
trigger = cp.create_trigger(
    name="PII Detected",
    concept="personal data exposure",
    threshold=0.85,
    actions=["webhook"],
    cooldown_secs=60,
)

# List all
triggers = cp.list_triggers()

# Test against text
result = cp.test_trigger(trigger["id"], "Customer SSN is 123-45-6789")
print(result["would_fire"], result["similarity"])

# Delete
cp.delete_trigger(trigger["id"])
```

### State Branching

```python
# Create isolated branches
branch = cp.create_branch(agent_id="analyst", tables=["portfolio"], description="Conservative rebalance")

# Inspect
branches = cp.list_branches()
diff = cp.branch_diff(branch["id"])
conflicts = cp.branch_conflicts(branch["id"])
cost = cp.branch_cost(branch["id"])
analytics = cp.branch_analytics()

# Merge or discard
cp.merge_branch(branch["id"], strategy="branch_wins")
cp.discard_branch(other_branch_id)
```

### Chain-of-Thought

```python
# Build hash-chained session
session_id, traces = cp.build_cot_session(
    agent_id="my-agent",
    org_id=cp.org_id,
    steps=[
        {"type": "Thought", "content": {"text": "..."}},
        {"type": "ToolCall", "content": {"tool": "search", "query": "..."}},
        {"type": "ToolResult", "content": {"count": 42}},
        {"type": "LlmResponse", "content": {"answer": "..."}},
    ],
)

# Ingest
result = cp.ingest_cot(traces)

# Verify hash chain integrity
verification = cp.verify_cot(session_id)
assert verification["chain_valid"] is True

# Replay for audit
replay = cp.replay_cot(session_id)

# List sessions
sessions = cp.list_cot_sessions()
```

### JIT Access

```python
grant = cp.request_jit(target_role="admin", reason="deploy fix", duration_hours=2)
grants = cp.list_jit_grants()
```

## Reasoning Chain Tracking (Data Plane)

Track multi-step reasoning chains via the proxy:

```python
with agent.reasoning_chain("req-001") as chain:
    tables = chain.query("SELECT table_name FROM information_schema.tables")
    data = chain.query("SELECT * FROM customers WHERE tier = 'enterprise'", step=1)
    revenue = chain.query("SELECT SUM(revenue) FROM orders", step=2)
```

## LangChain Integration

```python
from hatidata_agent.langchain import HatiDataSQLDatabase
from langchain.agents import create_sql_agent

db = HatiDataSQLDatabase(host="proxy.internal", port=5439, agent_id="sql-agent-1")
agent = create_sql_agent(llm=llm, db=db, verbose=True)
result = agent.run("How many enterprise customers do we have?")
```

## MCP Server

```bash
hatidata-mcp-server --host proxy.internal --port 5439
```

| Tool | Description |
|------|-------------|
| `query` | Execute SQL and return JSON results |
| `list_tables` | List available tables |
| `describe_table` | Get table schema |
| `get_context` | RAG context retrieval via full-text search |

## Documentation

- [Getting Started](https://docs.hatidata.com/getting-started)
- [Python SDK Reference](https://docs.hatidata.com/sdks/python)
- [Control Plane API](https://docs.hatidata.com/api-reference)
- [Agent Memory](https://docs.hatidata.com/features/agent-memory)
- [Semantic Triggers](https://docs.hatidata.com/features/semantic-triggers)
- [State Branching](https://docs.hatidata.com/features/branching)
- [Chain-of-Thought](https://docs.hatidata.com/features/chain-of-thought)

## License

Apache License 2.0. Copyright (c) Marviy Pte Ltd. See [LICENSE](https://github.com/HatiOS-AI/HatiData-SDKs/blob/main/LICENSE) for details.

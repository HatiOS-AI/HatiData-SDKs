# HatiData

**Local-first data warehouse for AI agents.**

Install in 30 seconds. Query in 60.

[![CI](https://github.com/HatiOS-AI/HatiData-Core/actions/workflows/ci.yml/badge.svg)](https://github.com/HatiOS-AI/HatiData-Core/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/hatidata-agent)](https://pypi.org/project/hatidata-agent/)
[![npm](https://img.shields.io/npm/v/@hatidata/sdk)](https://www.npmjs.com/package/@hatidata/sdk)
[![crates.io](https://img.shields.io/crates/v/hatidata-cli)](https://crates.io/crates/hatidata-cli)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

---

## 30-Second Install

```bash
# Python
pip install hatidata-agent

# Rust CLI
cargo install hatidata-cli

# TypeScript / Node.js
npm install @hatidata/sdk
```

## 60-Second First Query

```bash
# Initialize a local warehouse
hati init my-warehouse && cd my-warehouse

# Create a table and insert data
hati query "CREATE TABLE users (id INT, name VARCHAR, email VARCHAR)"
hati query "INSERT INTO users VALUES (1, 'Alice', 'alice@example.com'), (2, 'Bob', NULL)"

# Write Snowflake-compatible SQL — it just works
hati query "SELECT NVL(email, 'unknown') AS email, IFF(id > 1, 'new', 'old') AS cohort FROM users"
```

NVL, IFF, DATEDIFF, FLATTEN, QUALIFY, LISTAGG — write Snowflake-compatible SQL, run it locally on DuckDB.

## Sign Up and Authenticate

Cloud features (push, pull, sync) require a free HatiData account. Sign up directly from the CLI:

```bash
# Interactive signup — creates account + saves API key
hati auth signup

# Or log in with an existing account
hati auth login

# Check auth status
hati auth status
```

You can also sign up during `hati init` — the interactive wizard offers signup, login, or local-only mode.

Get a free account at [hatidata.com/signup](https://hatidata.com/signup).

## For AI Agents

### Python

```python
from hatidata_agent import HatiDataAgent

agent = HatiDataAgent(
    host="localhost", port=5439,
    agent_id="my-agent", framework="langchain"
)
rows = agent.query("SELECT * FROM customers WHERE region = 'US'")
```

### TypeScript

```typescript
import { HatiDataClient } from '@hatidata/sdk';

const client = new HatiDataClient({ host: 'localhost', port: 5439 });
await client.connect();
const result = await client.query('SELECT * FROM customers');
```

### MCP (Claude, Cursor, Cline)

23 tools across 5 categories: SQL, Memory, Chain-of-Thought, Triggers, and Branches.

```json
{
  "mcpServers": {
    "hatidata": {
      "command": "hatidata-mcp-server",
      "args": ["--host", "localhost", "--port", "5439", "--agent-id", "my-agent", "--database", "hatidata"]
    }
  }
}
```

## Hybrid SQL

Combine structured queries with semantic search. Standard SQL runs locally — hybrid SQL transparently transpiles via the HatiData cloud API (50 free queries/day).

```python
from hatidata_agent import HatiDataAgent

agent = HatiDataAgent(
    host="localhost", port=5439,
    cloud_key="hd_live_..."  # free at hatidata.com/signup
)

# Semantic search — find similar tickets
rows = agent.query("""
    SELECT ticket_id, subject, body
    FROM support_tickets
    WHERE semantic_match(embedding, 'billing dispute')
    ORDER BY semantic_rank(embedding, 'billing dispute') DESC
    LIMIT 10
""")

# Hybrid join — enrich with knowledge base
rows = agent.query("""
    SELECT t.ticket_id, k.article_title, k.solution
    FROM support_tickets t
    JOIN_VECTOR knowledge_base k ON semantic_match(k.embedding, t.subject)
    WHERE t.status = 'open'
""")
```

| Function | Returns | Use In |
|----------|---------|--------|
| `semantic_match(col, 'text')` | boolean | WHERE, JOIN ON |
| `semantic_match(col, 'text', 0.8)` | boolean | WHERE (custom threshold) |
| `semantic_rank(col, 'text')` | float | ORDER BY, SELECT |
| `vector_match(col, 'text')` | boolean | Alias for semantic_match |
| `JOIN_VECTOR table ON ...` | — | Semantic joins |

Get a free cloud key: [hatidata.com/signup](https://hatidata.com/signup). Full reference: [docs.hatidata.com/sql-reference/hybrid-search](https://docs.hatidata.com/sql-reference/hybrid-search).

## Packages

| Package | Install | Description |
|---------|---------|-------------|
| [`hatidata-cli`](cli/) | `cargo install hatidata-cli` | CLI (`hati` binary): local warehouse, auth, push/pull with tier enforcement |
| [`hatidata-agent`](sdk/python/) | `pip install hatidata-agent` | Python SDK with MCP server |
| [`@hatidata/sdk`](sdk/typescript/) | `npm install @hatidata/sdk` | TypeScript / Node.js SDK |
| [`dbt-hatidata`](integrations/dbt/) | `pip install dbt-hatidata` | dbt adapter |
| [`langchain-hatidata`](integrations/langchain/) | `pip install langchain-hatidata` | LangChain integration |
| [`crewai-hatidata`](integrations/crewai/) | `pip install crewai-hatidata` | CrewAI integration |
| [MCP configs](integrations/mcp/) | See README | Claude Desktop, Claude Code, Cursor |

## Tier Model

```
Local (Free)              Cloud ($29/mo)            Enterprise (Custom)
DuckDB on your            Managed cloud             In your VPC
machine                   warehouse                 via PrivateLink

          hati push --target cloud -->
                          hati push --target vpc -->
```

All tiers require a free HatiData account for cloud features. [Sign up here](https://hatidata.com/signup).

| | Free | Cloud | Growth | Enterprise |
|---|---|---|---|---|
| **Price** | $0 | $29/mo | Custom | Custom |
| **Tables per push** | 5 | 50 | 500 | Unlimited |
| **Rows per table** | 10,000 | 1,000,000 | 100,000,000 | Unlimited |
| **Push size per table** | 10 MB | 100 MB | 1 GB | Unlimited |
| **Pull data** | -- | Yes | Yes | Yes |
| **VPC push** | -- | -- | Yes | Yes |
| **Local queries** | Unlimited | Unlimited | Unlimited | Unlimited |

**Free** — Local DuckDB with cloud push for up to 5 tables. Data stays in `.hati/local.duckdb`. Free forever.

**Cloud** — `hati push --target cloud` syncs your local warehouse to a managed endpoint. $29/month.

**Growth** — Higher limits plus `hati push --target vpc` for VPC deployment. Custom pricing.

**Enterprise** — Unlimited everything, VPC via PrivateLink, SSO, RBAC, CMEK. Custom pricing.

## Examples

See the [`examples/`](examples/) directory for runnable scripts in Python, TypeScript, dbt, and SQL.

## Documentation

Full documentation at [docs.hatidata.com](https://docs.hatidata.com).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR guidelines.

## License

Apache-2.0. See [LICENSE](LICENSE).

Copyright 2024-2026 Marviy Pte Ltd.

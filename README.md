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

## For AI Agents

### Python

```python
from hatidata_agent import HatiDataAgent

agent = HatiDataAgent(
    host="localhost", port=5439,
    agent_id="my-agent", agent_framework="langchain"
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

```json
{
  "mcpServers": {
    "hatidata": {
      "command": "hatidata-mcp-server",
      "args": ["--host", "localhost", "--port", "5439"]
    }
  }
}
```

## Packages

| Package | Install | Description |
|---------|---------|-------------|
| [`hatidata-cli`](cli/) | `cargo install hatidata-cli` | CLI (`hati` binary): local warehouse + push to cloud |
| [`hatidata-agent`](sdk/python/) | `pip install hatidata-agent` | Python SDK with MCP server |
| [`@hatidata/sdk`](sdk/typescript/) | `npm install @hatidata/sdk` | TypeScript / Node.js SDK |
| [`dbt-hatidata`](integrations/dbt/) | `pip install dbt-hatidata` | dbt adapter |
| [`langchain-hatidata`](integrations/langchain/) | `pip install langchain-hatidata` | LangChain integration |
| [`crewai-hatidata`](integrations/crewai/) | `pip install crewai-hatidata` | CrewAI integration |
| [MCP configs](integrations/mcp/) | See README | Claude Desktop, Claude Code, Cursor |

## Three-Tier Model

```
Local (Free)              Cloud ($29/mo)            Enterprise (Custom)
DuckDB on your            Managed cloud             In your VPC
machine                   warehouse                 via PrivateLink

          hati push --target cloud -->
                          hati push --target vpc -->
```

**Local** — Zero cloud dependency. Data stays in `.hati/local.duckdb`. Free forever.

**Cloud** — `hati push --target cloud` syncs your local warehouse to a managed endpoint. $29/month.

**Enterprise** — `hati push --target vpc` deploys into your AWS VPC via PrivateLink. Custom pricing.

## Examples

See the [`examples/`](examples/) directory for runnable scripts in Python, TypeScript, dbt, and SQL.

## Documentation

Full documentation at [docs.hatiosai.com/hatidata](https://docs.hatiosai.com/hatidata).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR guidelines.

## License

Apache-2.0. See [LICENSE](LICENSE).

Copyright 2024 Marviy Pte Ltd.

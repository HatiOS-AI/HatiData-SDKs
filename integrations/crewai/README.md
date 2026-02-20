# crewai-hatidata

[![PyPI version](https://img.shields.io/pypi/v/crewai-hatidata.svg)](https://pypi.org/project/crewai-hatidata/)
[![Python versions](https://img.shields.io/pypi/pyversions/crewai-hatidata.svg)](https://pypi.org/project/crewai-hatidata/)
[![License](https://img.shields.io/pypi/l/crewai-hatidata.svg)](https://github.com/HatiOS-AI/HatiData-Core/blob/main/LICENSE)

CrewAI integration for [HatiData](https://hatidata.com) -- Memory and Tools that let CrewAI agents query, explore, and persist data in HatiData's in-VPC warehouse.

## Installation

```bash
pip install crewai-hatidata
```

## Quick Start

```python
from crewai import Agent, Task, Crew
from crewai_hatidata import HatiDataQueryTool, HatiDataMemory

query_tool = HatiDataQueryTool(host="proxy.internal", agent_id="analyst")
memory = HatiDataMemory(host="proxy.internal", agent_id="analyst")

agent = Agent(
    role="Data Analyst",
    tools=[query_tool],
    memory=memory,
)
```

## Features

- **HatiDataQueryTool** -- Execute SQL queries against HatiData from CrewAI agents
- **HatiDataListTablesTool** -- Discover available tables in the warehouse
- **HatiDataDescribeTableTool** -- Inspect table schemas and column types
- **HatiDataContextSearchTool** -- Full-text context search for RAG workflows
- **HatiDataMemory** -- Persistent agent memory backed by HatiData
- **Agent-aware billing** -- Every query is tagged with agent ID for per-agent cost tracking
- **Sub-10ms latency** -- Queries execute in-VPC with no data leaving your network

## Components

| Class | Description |
|-------|-------------|
| `HatiDataQueryTool` | Execute SQL queries and return results |
| `HatiDataListTablesTool` | List available tables |
| `HatiDataDescribeTableTool` | Get table schema details |
| `HatiDataContextSearchTool` | Full-text search for RAG context |
| `HatiDataMemory` | Persistent conversation memory |

## Documentation

Full documentation is available at [docs.hatidata.com](https://docs.hatidata.com).

## License

Apache License 2.0. Copyright (c) Marviy Pte Ltd. See [LICENSE](https://github.com/HatiOS-AI/HatiData-Core/blob/main/LICENSE) for details.

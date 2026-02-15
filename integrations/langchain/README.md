# langchain-hatidata

[![PyPI version](https://img.shields.io/pypi/v/langchain-hatidata.svg)](https://pypi.org/project/langchain-hatidata/)
[![Python versions](https://img.shields.io/pypi/pyversions/langchain-hatidata.svg)](https://pypi.org/project/langchain-hatidata/)
[![License](https://img.shields.io/pypi/l/langchain-hatidata.svg)](https://github.com/HatiOS-AI/HatiData-Core/blob/main/LICENSE)

LangChain integration for [HatiData](https://hatidata.com) -- Memory, VectorStore, and Tools backed by HatiData's in-VPC data warehouse with agent-aware billing and audit.

## Installation

```bash
pip install langchain-hatidata
```

## Quick Start

```python
from langchain_hatidata import HatiDataMemory, HatiDataVectorStore, HatiDataToolkit

# Conversation memory persisted to HatiData
memory = HatiDataMemory(host="proxy.internal", agent_id="my-agent")

# Vector store for RAG
vectorstore = HatiDataVectorStore(
    host="proxy.internal",
    agent_id="my-agent",
    table="embeddings",
)

# SQL tools for agents
toolkit = HatiDataToolkit(host="proxy.internal", agent_id="my-agent")
```

## Features

- **HatiDataMemory** -- Persistent conversation memory backed by HatiData, with full audit trails
- **HatiDataVectorStore** -- Vector similarity search for RAG pipelines, stored in-VPC
- **HatiDataToolkit** -- SQL query, table listing, schema inspection, and context search tools for LangChain agents
- **Agent-aware billing** -- Every query is tagged with agent ID and framework for per-agent cost tracking
- **Sub-10ms latency** -- Queries execute in-VPC with no data leaving your network

## Components

| Class | LangChain Base | Description |
|-------|---------------|-------------|
| `HatiDataMemory` | `BaseMemory` | Conversation history persisted to HatiData |
| `HatiDataVectorStore` | `VectorStore` | Vector similarity search backed by HatiData |
| `HatiDataToolkit` | `BaseToolkit` | SQL and context search tools for agents |

## Documentation

Full documentation is available at [docs.hatiosai.com/hatidata](https://docs.hatiosai.com/hatidata).

## License

Apache License 2.0. Copyright (c) Marviy Pte Ltd. See [LICENSE](https://github.com/HatiOS-AI/HatiData-Core/blob/main/LICENSE) for details.

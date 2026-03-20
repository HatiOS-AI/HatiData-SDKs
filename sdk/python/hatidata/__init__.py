"""HatiData Python SDK -- async-first agent-native data warehouse client.

Provides async access to HatiData's in-VPC data warehouse via the Postgres
wire protocol (asyncpg) with built-in agent memory, chain-of-thought,
and semantic trigger support via MCP.

Quick start::

    from hatidata import HatiData

    db = HatiData(
        host="preprod.hatidata.com",
        port=5439,
        api_key="hd_live_xxx",
    )

    rows = await db.query("SELECT * FROM trade_log WHERE ticker = $1", ["NVDA"])
    await db.memory.store(content="NVDA is trending", agent_id="trader-1")
    await db.close()
"""

from hatidata.client import ConnectionError, HatiData, HatiDataError, QueryError
from hatidata._mcp import McpError, McpTransportError

__version__ = "0.5.0"
__all__ = [
    "HatiData",
    "HatiDataError",
    "ConnectionError",
    "QueryError",
    "McpError",
    "McpTransportError",
]

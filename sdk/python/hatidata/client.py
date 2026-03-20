"""Core async HatiData client -- query, execute, and agent-native features.

Uses ``asyncpg`` for Postgres wire protocol (supports $1 parameterized
queries natively, async, binary protocol) and ``httpx`` for MCP endpoint
communication.

Usage::

    from hatidata import HatiData

    db = HatiData(
        host="preprod.hatidata.com",
        port=5439,
        api_key="hd_live_xxx",
        database="main",
    )

    rows = await db.query("SELECT * FROM trade_log WHERE ticker = $1", ["NVDA"])
    await db.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER, name TEXT)")
    await db.insert("products", {"id": 1, "name": "Widget"})
    await db.close()
"""

from __future__ import annotations

import json
from typing import Any, Optional, Sequence

import asyncpg

from hatidata._mcp import McpTransport
from hatidata.cot import CotClient
from hatidata.memory import MemoryClient
from hatidata.triggers import TriggerClient


class HatiDataError(Exception):
    """Base exception for HatiData SDK errors."""


class ConnectionError(HatiDataError):
    """Raised when a database connection cannot be established."""


class QueryError(HatiDataError):
    """Raised when a query fails."""


class HatiData:
    """Async HatiData client with agent-native features.

    Connects to the HatiData proxy via Postgres wire protocol (asyncpg)
    and provides access to agent memory, chain-of-thought, and semantic
    triggers via the MCP endpoint.

    Args:
        host: Proxy hostname.
        port: Proxy port (default 5439).
        api_key: HatiData API key (``hd_live_*`` or ``hd_agent_*``).
            Used for both proxy auth (as password) and MCP auth.
        database: Database name (default ``main``).
        user: Username (default ``agent``).
        agent_id: Agent identifier for billing and audit.
        framework: AI framework name (langchain, crewai, custom, etc.).
        mcp_port: MCP server port (default 5440). Set to None to disable
            MCP features.
        mcp_url: Full MCP URL override. If not set, derived from host
            and mcp_port.
        connect_timeout: Connection timeout in seconds.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5439,
        api_key: str = "",
        database: str = "main",
        user: str = "agent",
        agent_id: str = "",
        framework: str = "custom",
        mcp_port: Optional[int] = 5440,
        mcp_url: Optional[str] = None,
        connect_timeout: float = 10.0,
    ) -> None:
        self.host = host
        self.port = port
        self.api_key = api_key
        self.database = database
        self.user = user
        self.agent_id = agent_id
        self.framework = framework
        self.connect_timeout = connect_timeout

        self._pool: Optional[asyncpg.Pool] = None

        # MCP transport for agent-native features
        if mcp_url:
            effective_mcp_url = mcp_url
        elif mcp_port is not None:
            scheme = "https" if port == 443 else "http"
            effective_mcp_url = f"{scheme}://{host}:{mcp_port}/mcp"
        else:
            effective_mcp_url = None

        if effective_mcp_url and api_key:
            self._mcp = McpTransport(
                mcp_url=effective_mcp_url,
                api_key=api_key,
            )
        else:
            self._mcp = None

        # Agent-native sub-clients (lazy, backed by MCP)
        self._memory: Optional[MemoryClient] = None
        self._cot: Optional[CotClient] = None
        self._triggers: Optional[TriggerClient] = None

    # -- Agent-native feature accessors -----------------------------------

    @property
    def memory(self) -> MemoryClient:
        """Access agent memory operations (store, search, delete)."""
        if self._memory is None:
            if self._mcp is None:
                raise HatiDataError(
                    "Memory features require an api_key and MCP endpoint. "
                    "Pass api_key= to HatiData() to enable agent-native features."
                )
            self._memory = MemoryClient(self._mcp)
        return self._memory

    @property
    def cot(self) -> CotClient:
        """Access chain-of-thought operations (log_step, replay)."""
        if self._cot is None:
            if self._mcp is None:
                raise HatiDataError(
                    "CoT features require an api_key and MCP endpoint. "
                    "Pass api_key= to HatiData() to enable agent-native features."
                )
            self._cot = CotClient(self._mcp)
        return self._cot

    @property
    def triggers(self) -> TriggerClient:
        """Access semantic trigger operations (register, list, delete)."""
        if self._triggers is None:
            if self._mcp is None:
                raise HatiDataError(
                    "Trigger features require an api_key and MCP endpoint. "
                    "Pass api_key= to HatiData() to enable agent-native features."
                )
            self._triggers = TriggerClient(self._mcp)
        return self._triggers

    # -- Connection management --------------------------------------------

    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create the connection pool."""
        if self._pool is None or self._pool._closed:
            server_settings = {}
            if self.agent_id:
                server_settings["hatidata_agent_id"] = self.agent_id
            if self.framework:
                server_settings["hatidata_framework"] = self.framework

            try:
                self._pool = await asyncpg.create_pool(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.api_key or None,
                    min_size=1,
                    max_size=10,
                    timeout=self.connect_timeout,
                    server_settings=server_settings,
                )
            except (OSError, asyncpg.PostgresError) as exc:
                raise ConnectionError(
                    f"Failed to connect to {self.host}:{self.port}: {exc}"
                ) from exc

        return self._pool

    # -- Query interface --------------------------------------------------

    async def query(
        self,
        sql: str,
        params: Optional[Sequence[Any]] = None,
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as a list of dicts.

        Uses asyncpg's native $1, $2 parameterized queries for injection
        safety and binary protocol efficiency.

        Args:
            sql: SQL query string with $1, $2 parameter placeholders.
            params: Optional list of parameter values.

        Returns:
            List of row dicts with column names as keys.

        Raises:
            QueryError: If the query fails.
        """
        pool = await self._get_pool()
        try:
            if params:
                rows = await pool.fetch(sql, *params)
            else:
                rows = await pool.fetch(sql)
            return [dict(row) for row in rows]
        except asyncpg.PostgresError as exc:
            raise QueryError(f"Query failed: {exc}") from exc

    async def execute(
        self,
        sql: str,
        params: Optional[Sequence[Any]] = None,
    ) -> str:
        """Execute a SQL statement (DDL, INSERT, UPDATE, DELETE).

        Args:
            sql: SQL statement with optional $1, $2 parameter placeholders.
            params: Optional list of parameter values.

        Returns:
            Status string from asyncpg (e.g., ``INSERT 0 1``).

        Raises:
            QueryError: If the statement fails.
        """
        pool = await self._get_pool()
        try:
            if params:
                return await pool.execute(sql, *params)
            else:
                return await pool.execute(sql)
        except asyncpg.PostgresError as exc:
            raise QueryError(f"Execute failed: {exc}") from exc

    async def insert(
        self,
        table: str,
        data: dict[str, Any],
    ) -> str:
        """Insert a single row into a table.

        Convenience method that builds a parameterized INSERT from a dict.

        Args:
            table: Target table name.
            data: Column-value mapping for the row.

        Returns:
            Status string from asyncpg.

        Raises:
            QueryError: If the insert fails.
            ValueError: If data is empty.
        """
        if not data:
            raise ValueError("data dict must not be empty")

        columns = list(data.keys())
        placeholders = [f"${i + 1}" for i in range(len(columns))]
        values = list(data.values())

        # Serialize any dict/list values to JSON strings
        for i, v in enumerate(values):
            if isinstance(v, (dict, list)):
                values[i] = json.dumps(v)

        sql = (
            f'INSERT INTO {table} ({", ".join(columns)}) '
            f'VALUES ({", ".join(placeholders)})'
        )
        return await self.execute(sql, values)

    # -- Lifecycle --------------------------------------------------------

    async def close(self) -> None:
        """Close database pool and MCP transport."""
        if self._pool and not self._pool._closed:
            await self._pool.close()
            self._pool = None
        if self._mcp:
            await self._mcp.close()

    async def __aenter__(self) -> HatiData:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

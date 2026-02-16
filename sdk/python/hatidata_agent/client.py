"""HatiData agent client — Postgres wire protocol with agent startup params.

Usage::

    from hatidata_agent import HatiDataAgent

    agent = HatiDataAgent(
        host="proxy.internal",
        port=5439,
        agent_id="data-analyst-agent",
        framework="langchain",
        database="analytics",
    )

    # Simple query
    rows = agent.query("SELECT COUNT(*) FROM orders")

    # With reasoning chain tracking
    with agent.reasoning_chain("req-001") as chain:
        tables = chain.query("SELECT table_name FROM information_schema.tables")
        data = chain.query("SELECT * FROM customers LIMIT 10", step=1)
        summary = chain.query("SELECT AVG(revenue) FROM orders", step=2)

    # RAG context retrieval
    context = agent.get_context("customers", "enterprise accounts", top_k=5)
"""

from __future__ import annotations

import json
import os
import re
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Optional

import psycopg2
import psycopg2.extras

# Keywords that indicate hybrid SQL requiring cloud transpilation.
_HYBRID_SQL_KEYWORDS = re.compile(
    r"\bJOIN_VECTOR\b|\bsemantic_match\b|\bvector_match\b|\bsemantic_rank\b",
    re.IGNORECASE,
)


class HatiDataError(Exception):
    """Base exception for HatiData SDK errors."""


class HybridSQLError(HatiDataError):
    """Raised when hybrid SQL is used without a cloud key."""


class TranspileQuotaError(HatiDataError):
    """Raised when the daily hybrid SQL quota is exceeded."""


class HatiDataAgent:
    """Agent-aware HatiData client using psycopg2.

    Connects via Postgres wire protocol and identifies itself through
    startup parameters that the proxy reads for billing, scheduling,
    and audit.

    Args:
        host: Proxy hostname.
        port: Proxy port (default 5439).
        agent_id: Unique identifier for this agent instance.
        framework: AI framework name (langchain, crewai, autogen, etc.).
        database: Database name (default "hatidata").
        user: Username (default "agent").
        password: Password (default empty for dev mode).
        priority: Query priority (low, normal, high, critical).
        connect_timeout: Connection timeout in seconds.
        cloud_key: API key for hybrid SQL transpilation (from hatidata.com/signup).
        cloud_endpoint: HatiData cloud API URL (default: https://api.hatidata.com).
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5439,
        agent_id: str = "",
        framework: str = "custom",
        database: str = "hatidata",
        user: str = "agent",
        password: str = "",
        priority: str = "normal",
        connect_timeout: int = 10,
        cloud_key: Optional[str] = None,
        cloud_endpoint: str = "https://api.hatidata.com",
    ):
        self.host = host
        self.port = port
        self.agent_id = agent_id or f"agent-{uuid.uuid4().hex[:8]}"
        self.framework = framework
        self.database = database
        self.user = user
        self.password = password
        self.priority = priority
        self.connect_timeout = connect_timeout
        self._conn: Optional[psycopg2.extensions.connection] = None

        # Hybrid SQL cloud transpilation
        self.cloud_endpoint = cloud_endpoint.rstrip("/")
        self.cloud_key = cloud_key or os.environ.get("HATIDATA_CLOUD_KEY") or _load_config_key()

    def _get_connection(self) -> psycopg2.extensions.connection:
        """Get or create a connection with agent startup params."""
        if self._conn is None or self._conn.closed:
            # Agent identification via startup parameters.
            # These are read by the HatiData proxy during connection setup.
            options = (
                f"-c hatidata_agent_id={self.agent_id} "
                f"-c hatidata_framework={self.framework} "
                f"-c hatidata_priority={self.priority}"
            )

            self._conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.database,
                user=self.user,
                password=self.password,
                options=options,
                connect_timeout=self.connect_timeout,
                application_name=f"hatidata-agent/{self.framework}",
            )
            self._conn.autocommit = True

        return self._conn

    def query(
        self,
        sql: str,
        params: Optional[tuple[Any, ...]] = None,
        request_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as a list of dicts.

        If the query contains hybrid SQL syntax (JOIN_VECTOR, semantic_match,
        etc.), it is transparently transpiled via the HatiData cloud API before
        local execution. Standard SQL queries run directly without any cloud call.

        Args:
            sql: SQL query string.
            params: Optional query parameters (for parameterized queries).
            request_id: Optional request ID for tracing.

        Returns:
            List of row dicts with column names as keys.

        Raises:
            HybridSQLError: If hybrid SQL is used without a cloud_key.
            TranspileQuotaError: If the daily hybrid SQL quota is exceeded.
        """
        # Transparently transpile hybrid SQL if needed
        effective_sql = self._maybe_transpile(sql)

        conn = self._get_connection()

        # Set request_id for this query if provided.
        if request_id:
            with conn.cursor() as cur:
                cur.execute(f"SET hatidata_request_id = '{request_id}'")

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(effective_sql, params)
            if cur.description:
                return [dict(row) for row in cur.fetchall()]
            return []

    def execute(self, sql: str, params: Optional[tuple[Any, ...]] = None) -> int:
        """Execute a SQL statement (INSERT, UPDATE, DELETE) and return row count.

        Args:
            sql: SQL statement.
            params: Optional query parameters.

        Returns:
            Number of affected rows.
        """
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount

    def get_context(
        self,
        table: str,
        search_query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Retrieve RAG context using HatiData's built-in context function.

        This uses the `hatidata_context()` UDF which the proxy rewrites
        to an efficient full-text search subquery.

        Args:
            table: Table name to search.
            search_query: Natural language search query.
            top_k: Maximum number of results.

        Returns:
            List of matching rows as dicts.
        """
        sql = f"SELECT * FROM hatidata_context('{table}', '{search_query}', {top_k})"
        return self.query(sql)

    def get_rag_context(
        self,
        table: str,
        embedding_col: str,
        vector: list[float],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Retrieve RAG context via vector similarity search.

        Args:
            table: Table name containing embeddings.
            embedding_col: Column name with embedding vectors.
            vector: Query embedding vector.
            top_k: Maximum number of results.

        Returns:
            List of matching rows ordered by similarity.
        """
        vector_str = f"[{', '.join(str(v) for v in vector)}]"
        sql = (
            f"SELECT * FROM hatidata_rag_context('{table}', '{embedding_col}', "
            f"{vector_str}, {top_k})"
        )
        return self.query(sql)

    @contextmanager
    def reasoning_chain(
        self,
        request_id: Optional[str] = None,
        parent_request_id: Optional[str] = None,
    ) -> Generator[ReasoningChain, None, None]:
        """Context manager for tracking a multi-step reasoning chain.

        Usage::

            with agent.reasoning_chain("req-001") as chain:
                tables = chain.query("SELECT table_name FROM information_schema.tables")
                data = chain.query("SELECT * FROM orders LIMIT 10", step=1)

        Args:
            request_id: Unique ID for this reasoning chain.
            parent_request_id: Parent chain ID for nested reasoning.
        """
        rid = request_id or f"req-{uuid.uuid4().hex[:12]}"
        chain = ReasoningChain(self, rid, parent_request_id)
        try:
            yield chain
        finally:
            chain._finalize()

    # ── Memory convenience methods ────────────────────────────────────

    _MEMORY_SCHEMA = "_hatidata_memory_local"

    def _ensure_memory_schema(self) -> None:
        """Create the memory schema and tables if they don't exist."""
        schema = self._MEMORY_SCHEMA
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS \"{schema}\"")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS "{schema}".agent_memories (
                    memory_id   VARCHAR PRIMARY KEY,
                    agent_id    VARCHAR NOT NULL,
                    content     TEXT NOT NULL,
                    memory_type VARCHAR NOT NULL DEFAULT 'fact',
                    importance  DOUBLE DEFAULT 0.5,
                    metadata    VARCHAR,
                    created_at  VARCHAR DEFAULT (strftime(now(), '%Y-%m-%dT%H:%M:%SZ')),
                    last_accessed_at VARCHAR DEFAULT (strftime(now(), '%Y-%m-%dT%H:%M:%SZ'))
                )
            """)
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS "{schema}".agent_state (
                    agent_id   VARCHAR NOT NULL,
                    key        VARCHAR NOT NULL,
                    value      VARCHAR NOT NULL,
                    version    BIGINT DEFAULT 1,
                    updated_at VARCHAR DEFAULT (strftime(now(), '%Y-%m-%dT%H:%M:%SZ')),
                    PRIMARY KEY (agent_id, key)
                )
            """)

    def store_memory(
        self,
        content: str,
        memory_type: str = "fact",
        metadata: Optional[dict[str, Any]] = None,
        importance: float = 0.5,
    ) -> str:
        """Store a memory in the agent memory table.

        Args:
            content: The memory content text.
            memory_type: Type of memory (fact, observation, instruction, etc.).
            metadata: Optional JSON metadata dict.
            importance: Importance score 0.0-1.0 (default 0.5).

        Returns:
            The generated memory_id (UUID string).
        """
        self._ensure_memory_schema()
        memory_id = uuid.uuid4().hex
        meta_json = json.dumps(metadata) if metadata else None
        schema = self._MEMORY_SCHEMA
        self.execute(
            f'INSERT INTO "{schema}".agent_memories '
            f"(memory_id, agent_id, content, memory_type, importance, metadata) "
            f"VALUES (%s, %s, %s, %s, %s, %s)",
            (memory_id, self.agent_id, content, memory_type, importance, meta_json),
        )
        return memory_id

    def search_memory(
        self,
        query: str,
        top_k: int = 10,
        memory_type: Optional[str] = None,
        min_importance: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """Search stored memories by text similarity.

        Uses ILIKE text matching with ordering by importance and recency.
        For full vector similarity search, use the MCP server connected to
        a running proxy with Qdrant enabled.

        Args:
            query: Search query text.
            top_k: Maximum results to return.
            memory_type: Optional filter by memory type.
            min_importance: Optional minimum importance threshold.

        Returns:
            List of matching memory dicts.
        """
        self._ensure_memory_schema()
        schema = self._MEMORY_SCHEMA
        conditions = [f"agent_id = '{self.agent_id}'"]
        # Build search condition using keywords from the query
        words = [w.strip() for w in query.split() if len(w.strip()) > 2]
        if words:
            like_clauses = " OR ".join(f"content ILIKE '%{w}%'" for w in words)
            conditions.append(f"({like_clauses})")
        if memory_type:
            conditions.append(f"memory_type = '{memory_type}'")
        if min_importance is not None:
            conditions.append(f"importance >= {min_importance}")

        where = " AND ".join(conditions)
        sql = (
            f'SELECT * FROM "{schema}".agent_memories '
            f"WHERE {where} "
            f"ORDER BY importance DESC, created_at DESC "
            f"LIMIT {top_k}"
        )
        return self.query(sql)

    def get_state(self, key: str) -> Optional[Any]:
        """Get an agent state value by key.

        Args:
            key: The state key.

        Returns:
            The JSON-decoded value, or None if the key doesn't exist.
        """
        self._ensure_memory_schema()
        schema = self._MEMORY_SCHEMA
        rows = self.query(
            f'SELECT value FROM "{schema}".agent_state '
            f"WHERE agent_id = %s AND key = %s",
            (self.agent_id, key),
        )
        if rows:
            try:
                return json.loads(rows[0]["value"])
            except (json.JSONDecodeError, KeyError):
                return rows[0].get("value")
        return None

    def set_state(self, key: str, value: Any) -> None:
        """Set an agent state value.

        Args:
            key: The state key.
            value: The value (will be JSON-encoded).
        """
        self._ensure_memory_schema()
        schema = self._MEMORY_SCHEMA
        json_val = json.dumps(value)
        self.execute(
            f'INSERT INTO "{schema}".agent_state (agent_id, key, value) '
            f"VALUES (%s, %s, %s) "
            f"ON CONFLICT (agent_id, key) DO UPDATE "
            f"SET value = EXCLUDED.value, version = \"{schema}\".agent_state.version + 1, "
            f"updated_at = strftime(now(), '%Y-%m-%dT%H:%M:%SZ')",
            (self.agent_id, key, json_val),
        )

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID.

        Args:
            memory_id: The memory UUID to delete.

        Returns:
            True if a row was deleted, False if not found.
        """
        self._ensure_memory_schema()
        schema = self._MEMORY_SCHEMA
        count = self.execute(
            f'DELETE FROM "{schema}".agent_memories WHERE memory_id = %s',
            (memory_id,),
        )
        return count > 0

    # ── End memory methods ──────────────────────────────────────────

    def _maybe_transpile(self, sql: str) -> str:
        """Transpile hybrid SQL via cloud API if the query uses hybrid syntax.

        Standard SQL is returned unchanged. Hybrid SQL (JOIN_VECTOR,
        semantic_match, vector_match, semantic_rank) is sent to the HatiData
        cloud transpilation endpoint which rewrites it and resolves embeddings.
        """
        if not _HYBRID_SQL_KEYWORDS.search(sql):
            return sql

        if not self.cloud_key:
            raise HybridSQLError(
                "Hybrid SQL (JOIN_VECTOR, semantic_match, etc.) requires a cloud key. "
                "Get a free key at https://hatidata.com/signup, then pass cloud_key= "
                "to HatiDataAgent() or set HATIDATA_CLOUD_KEY env var."
            )

        import requests

        resp = requests.post(
            f"{self.cloud_endpoint}/v1/transpile",
            json={"sql": sql},
            headers={"Authorization": f"ApiKey {self.cloud_key}"},
            timeout=30,
        )

        if resp.status_code == 429:
            body = resp.json()
            raise TranspileQuotaError(
                body.get("error", "Daily hybrid SQL quota exceeded. "
                          "Upgrade at https://hatidata.com/pricing")
            )

        if not resp.ok:
            raise HatiDataError(
                f"Transpilation failed ({resp.status_code}): {resp.text}"
            )

        result = resp.json()
        return result["sql"]

    def close(self) -> None:
        """Close the underlying database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> HatiDataAgent:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class ReasoningChain:
    """Tracks a multi-step reasoning chain with auto-incrementing steps."""

    def __init__(
        self,
        agent: HatiDataAgent,
        request_id: str,
        parent_request_id: Optional[str] = None,
    ):
        self._agent = agent
        self.request_id = request_id
        self.parent_request_id = parent_request_id
        self._step = 0

    def query(
        self,
        sql: str,
        params: Optional[tuple[Any, ...]] = None,
        step: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Execute a query as part of this reasoning chain.

        Args:
            sql: SQL query.
            params: Optional query parameters.
            step: Explicit step number (auto-increments if not provided).
        """
        current_step = step if step is not None else self._step
        self._step = current_step + 1

        conn = self._agent._get_connection()
        with conn.cursor() as cur:
            cur.execute(f"SET hatidata_request_id = '{self.request_id}'")
            cur.execute(f"SET hatidata_reasoning_step = '{current_step}'")
            if self.parent_request_id:
                cur.execute(
                    f"SET hatidata_parent_request_id = '{self.parent_request_id}'"
                )

        return self._agent.query(sql, params)

    def _finalize(self) -> None:
        """Reset session vars after chain completes."""
        try:
            conn = self._agent._get_connection()
            with conn.cursor() as cur:
                cur.execute("SET hatidata_request_id = ''")
                cur.execute("SET hatidata_reasoning_step = ''")
        except Exception:
            pass


def _load_config_key() -> Optional[str]:
    """Load cloud_key from ~/.hatidata/config.json if it exists."""
    config_path = Path.home() / ".hatidata" / "config.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text())
            return data.get("cloud_key")
        except (json.JSONDecodeError, OSError):
            pass
    return None

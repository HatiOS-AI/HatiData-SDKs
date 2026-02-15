"""CrewAI Memory backed by HatiData.

Persists agent memory (short-term and long-term) to HatiData's SQL
engine for durable cross-session state with full audit trail.

Usage::

    from crewai_hatidata import HatiDataMemory

    memory = HatiDataMemory(
        host="proxy.internal",
        agent_id="research-agent",
    )

    # Store a memory
    memory.save("The customer prefers monthly billing", metadata={"topic": "billing"})

    # Search memories
    results = memory.search("billing preferences")
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from hatidata_agent import HatiDataAgent


class HatiDataMemory:
    """CrewAI-compatible memory backed by HatiData.

    Stores memories in a SQL table with agent identification,
    enabling per-agent billing and audit. Supports both key-value
    storage and full-text search retrieval.

    The memory table is auto-created on first use::

        CREATE TABLE IF NOT EXISTS _crewai_memory (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            importance REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5439,
        agent_id: str = "crewai-agent",
        database: str = "hatidata",
        user: str = "agent",
        password: str = "",
    ):
        self._agent = HatiDataAgent(
            host=host,
            port=port,
            agent_id=agent_id,
            framework="crewai",
            database=database,
            user=user,
            password=password,
        )
        self._agent_id = agent_id
        self._table_created = False

    def _ensure_table(self) -> None:
        """Create the memory table if it doesn't exist."""
        if self._table_created:
            return
        self._agent.execute(
            "CREATE TABLE IF NOT EXISTS _crewai_memory ("
            "  id TEXT PRIMARY KEY,"
            "  agent_id TEXT NOT NULL,"
            "  content TEXT NOT NULL,"
            "  metadata TEXT,"
            "  importance REAL DEFAULT 0.5,"
            "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
        self._table_created = True

    def save(
        self,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        importance: float = 0.5,
    ) -> str:
        """Store a memory entry.

        Args:
            content: The memory content to store.
            metadata: Optional metadata dict.
            importance: Importance score (0.0 to 1.0).

        Returns:
            The ID of the stored memory.
        """
        self._ensure_table()
        mem_id = uuid.uuid4().hex
        meta_str = json.dumps(metadata) if metadata else "{}"
        self._agent.execute(
            f"INSERT INTO _crewai_memory (id, agent_id, content, metadata, importance) "
            f"VALUES ('{mem_id}', '{self._agent_id}', '{_escape(content)}', "
            f"'{_escape(meta_str)}', {importance})"
        )
        return mem_id

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search memories by content.

        Args:
            query: Search query (matched against content).
            limit: Maximum results to return.

        Returns:
            List of matching memory entries.
        """
        self._ensure_table()
        rows = self._agent.query(
            f"SELECT id, content, metadata, importance, created_at "
            f"FROM _crewai_memory "
            f"WHERE agent_id = '{self._agent_id}' "
            f"AND content ILIKE '%{_escape(query)}%' "
            f"ORDER BY created_at DESC LIMIT {limit}"
        )
        results = []
        for row in rows:
            entry = {
                "id": row["id"],
                "content": row["content"],
                "importance": row.get("importance", 0.5),
                "created_at": str(row.get("created_at", "")),
            }
            try:
                entry["metadata"] = json.loads(row.get("metadata", "{}"))
            except (json.JSONDecodeError, TypeError):
                entry["metadata"] = {}
            results.append(entry)
        return results

    def get_all(self, limit: int = 100) -> list[dict[str, Any]]:
        """Retrieve all memories for this agent.

        Args:
            limit: Maximum results to return.

        Returns:
            List of memory entries.
        """
        self._ensure_table()
        rows = self._agent.query(
            f"SELECT id, content, metadata, importance, created_at "
            f"FROM _crewai_memory "
            f"WHERE agent_id = '{self._agent_id}' "
            f"ORDER BY created_at DESC LIMIT {limit}"
        )
        results = []
        for row in rows:
            entry = {
                "id": row["id"],
                "content": row["content"],
                "importance": row.get("importance", 0.5),
                "created_at": str(row.get("created_at", "")),
            }
            try:
                entry["metadata"] = json.loads(row.get("metadata", "{}"))
            except (json.JSONDecodeError, TypeError):
                entry["metadata"] = {}
            results.append(entry)
        return results

    def clear(self) -> None:
        """Clear all memories for this agent."""
        self._ensure_table()
        self._agent.execute(
            f"DELETE FROM _crewai_memory WHERE agent_id = '{self._agent_id}'"
        )


def _escape(s: str) -> str:
    """Escape single quotes for SQL insertion."""
    return s.replace("'", "''")

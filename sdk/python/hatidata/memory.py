"""Agent memory module -- store, search, and manage agent memories.

Uses the MCP endpoint for vector-backed memory operations (store, search,
delete) which leverage Qdrant for semantic similarity search.

Usage::

    db = HatiData(host="preprod.hatidata.com", port=5439, api_key="hd_live_xxx")

    await db.memory.store(
        content="Customer prefers organic products",
        agent_id="catalog-agent",
        memory_type="preference",
        importance=0.8,
    )

    results = await db.memory.search(
        query="organic coffee preferences",
        agent_id="catalog-agent",
        top_k=5,
    )
"""

from __future__ import annotations

from typing import Any, Optional

from hatidata._mcp import McpTransport


class MemoryClient:
    """Client for agent memory operations via MCP tools.

    Args:
        transport: The MCP transport instance for JSON-RPC calls.
    """

    def __init__(self, transport: McpTransport) -> None:
        self._transport = transport

    async def store(
        self,
        content: str,
        agent_id: str = "",
        memory_type: str = "fact",
        importance: float = 0.5,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Store a memory in the agent's persistent memory.

        Args:
            content: The memory content text.
            agent_id: Agent identifier (used for scoping).
            memory_type: Type of memory (fact, observation, instruction,
                preference, episode).
            importance: Importance score 0.0-1.0.
            metadata: Optional key-value metadata dict.

        Returns:
            Dict with ``memory_id`` of the stored memory.
        """
        arguments: dict[str, Any] = {
            "content": content,
            "memory_type": memory_type,
            "importance": importance,
        }
        if metadata:
            arguments["metadata"] = metadata
        return await self._transport.call_tool("store_memory", arguments)

    async def search(
        self,
        query: str,
        agent_id: str = "",
        top_k: int = 10,
        memory_type: Optional[str] = None,
        min_importance: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """Search agent memories by semantic similarity.

        Uses vector search (Qdrant) when available, falling back to
        text-based matching.

        Args:
            query: Natural language search query.
            agent_id: Agent identifier to scope results.
            top_k: Maximum number of results to return.
            memory_type: Optional filter by memory type.
            min_importance: Optional minimum importance threshold.

        Returns:
            List of matching memory dicts, ranked by relevance.
        """
        arguments: dict[str, Any] = {
            "query": query,
            "top_k": top_k,
        }
        if memory_type:
            arguments["memory_type"] = memory_type
        if min_importance is not None:
            arguments["min_importance"] = min_importance

        result = await self._transport.call_tool("search_memory", arguments)
        if isinstance(result, list):
            return result
        return []

    async def delete(self, memory_id: str) -> dict[str, Any]:
        """Delete a specific memory by its ID.

        Args:
            memory_id: The memory UUID to delete.

        Returns:
            Dict with ``deleted`` status and ``memory_id``.
        """
        return await self._transport.call_tool(
            "delete_memory", {"memory_id": memory_id}
        )

    async def get_state(self, key: str) -> Any:
        """Get a persistent agent state value by key.

        Args:
            key: The state key.

        Returns:
            The stored value (any JSON type), or None if not found.
        """
        result = await self._transport.call_tool(
            "get_agent_state", {"key": key}
        )
        return result.get("value") if isinstance(result, dict) else None

    async def set_state(self, key: str, value: Any) -> dict[str, Any]:
        """Set a persistent agent state value.

        Args:
            key: The state key.
            value: The value to store (any JSON-serializable type).

        Returns:
            Dict with ``key`` and ``status``.
        """
        return await self._transport.call_tool(
            "set_agent_state", {"key": key, "value": value}
        )

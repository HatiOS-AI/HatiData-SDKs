"""Tests for the memory module."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from hatidata._mcp import McpTransport
from hatidata.memory import MemoryClient


@pytest.fixture
def memory_client() -> MemoryClient:
    """Create a MemoryClient with mocked MCP transport."""
    transport = McpTransport(
        mcp_url="http://localhost:5440/mcp",
        api_key="hd_live_test123",
    )
    transport.call_tool = AsyncMock()
    return MemoryClient(transport)


class TestMemoryStore:
    @pytest.mark.asyncio
    async def test_store_basic(self, memory_client: MemoryClient) -> None:
        memory_client._transport.call_tool.return_value = {
            "memory_id": "mem-abc123"
        }

        result = await memory_client.store(
            content="Customer prefers organic products",
            agent_id="catalog-agent",
            memory_type="preference",
            importance=0.8,
        )

        assert result["memory_id"] == "mem-abc123"
        memory_client._transport.call_tool.assert_called_once_with(
            "store_memory",
            {
                "content": "Customer prefers organic products",
                "memory_type": "preference",
                "importance": 0.8,
            },
        )

    @pytest.mark.asyncio
    async def test_store_with_metadata(self, memory_client: MemoryClient) -> None:
        memory_client._transport.call_tool.return_value = {
            "memory_id": "mem-xyz"
        }

        await memory_client.store(
            content="test",
            metadata={"category": "food"},
        )

        call_args = memory_client._transport.call_tool.call_args
        assert call_args[0][1]["metadata"] == {"category": "food"}

    @pytest.mark.asyncio
    async def test_store_defaults(self, memory_client: MemoryClient) -> None:
        memory_client._transport.call_tool.return_value = {"memory_id": "m1"}

        await memory_client.store(content="hello")

        call_args = memory_client._transport.call_tool.call_args
        args = call_args[0][1]
        assert args["memory_type"] == "fact"
        assert args["importance"] == 0.5
        assert "metadata" not in args


class TestMemorySearch:
    @pytest.mark.asyncio
    async def test_search_basic(self, memory_client: MemoryClient) -> None:
        memory_client._transport.call_tool.return_value = [
            {"memory_id": "m1", "content": "organic preference", "score": 0.95},
            {"memory_id": "m2", "content": "coffee order", "score": 0.82},
        ]

        results = await memory_client.search(
            query="organic coffee preferences",
            agent_id="catalog-agent",
            top_k=5,
        )

        assert len(results) == 2
        assert results[0]["score"] == 0.95
        memory_client._transport.call_tool.assert_called_once_with(
            "search_memory",
            {"query": "organic coffee preferences", "top_k": 5},
        )

    @pytest.mark.asyncio
    async def test_search_with_filters(self, memory_client: MemoryClient) -> None:
        memory_client._transport.call_tool.return_value = []

        await memory_client.search(
            query="test",
            memory_type="preference",
            min_importance=0.7,
        )

        call_args = memory_client._transport.call_tool.call_args
        args = call_args[0][1]
        assert args["memory_type"] == "preference"
        assert args["min_importance"] == 0.7

    @pytest.mark.asyncio
    async def test_search_returns_empty_for_non_list(
        self, memory_client: MemoryClient
    ) -> None:
        memory_client._transport.call_tool.return_value = {"error": "not found"}
        results = await memory_client.search(query="test")
        assert results == []


class TestMemoryDelete:
    @pytest.mark.asyncio
    async def test_delete(self, memory_client: MemoryClient) -> None:
        memory_client._transport.call_tool.return_value = {
            "deleted": True,
            "memory_id": "mem-123",
        }

        result = await memory_client.delete(memory_id="mem-123")

        assert result["deleted"] is True
        memory_client._transport.call_tool.assert_called_once_with(
            "delete_memory", {"memory_id": "mem-123"}
        )


class TestMemoryState:
    @pytest.mark.asyncio
    async def test_get_state(self, memory_client: MemoryClient) -> None:
        memory_client._transport.call_tool.return_value = {
            "key": "last_run",
            "value": "2026-03-20T00:00:00Z",
        }

        result = await memory_client.get_state("last_run")
        assert result == "2026-03-20T00:00:00Z"

    @pytest.mark.asyncio
    async def test_get_state_not_found(self, memory_client: MemoryClient) -> None:
        memory_client._transport.call_tool.return_value = {
            "key": "missing",
            "value": None,
        }

        result = await memory_client.get_state("missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_state(self, memory_client: MemoryClient) -> None:
        memory_client._transport.call_tool.return_value = {
            "key": "counter",
            "status": "ok",
        }

        result = await memory_client.set_state("counter", 42)
        assert result["status"] == "ok"
        memory_client._transport.call_tool.assert_called_once_with(
            "set_agent_state", {"key": "counter", "value": 42}
        )

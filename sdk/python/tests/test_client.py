"""Tests for the core HatiData async client."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hatidata import HatiData, HatiDataError, ConnectionError, QueryError


class TestHatiDataInit:
    """Test client initialization and configuration."""

    def test_default_config(self) -> None:
        db = HatiData()
        assert db.host == "localhost"
        assert db.port == 5439
        assert db.database == "main"
        assert db.user == "agent"
        assert db.api_key == ""
        assert db._pool is None

    def test_custom_config(self) -> None:
        db = HatiData(
            host="preprod.hatidata.com",
            port=5439,
            api_key="hd_live_xxx",
            database="analytics",
            agent_id="my-agent",
            framework="langchain",
        )
        assert db.host == "preprod.hatidata.com"
        assert db.api_key == "hd_live_xxx"
        assert db.database == "analytics"
        assert db.agent_id == "my-agent"
        assert db.framework == "langchain"

    def test_mcp_transport_created_with_api_key(self) -> None:
        db = HatiData(
            host="localhost",
            api_key="hd_live_xxx",
            mcp_port=5440,
        )
        assert db._mcp is not None
        assert db._mcp._api_key == "hd_live_xxx"
        assert db._mcp._url == "http://localhost:5440/mcp"

    def test_mcp_transport_not_created_without_api_key(self) -> None:
        db = HatiData(host="localhost")
        assert db._mcp is None

    def test_mcp_disabled_with_none_port(self) -> None:
        db = HatiData(host="localhost", api_key="hd_live_xxx", mcp_port=None)
        assert db._mcp is None

    def test_custom_mcp_url(self) -> None:
        db = HatiData(
            host="localhost",
            api_key="hd_live_xxx",
            mcp_url="https://custom.mcp.endpoint/mcp",
        )
        assert db._mcp is not None
        assert db._mcp._url == "https://custom.mcp.endpoint/mcp"


class TestAgentNativeAccessors:
    """Test that agent-native feature properties work correctly."""

    def test_memory_requires_api_key(self) -> None:
        db = HatiData(host="localhost")
        with pytest.raises(HatiDataError, match="api_key"):
            _ = db.memory

    def test_cot_requires_api_key(self) -> None:
        db = HatiData(host="localhost")
        with pytest.raises(HatiDataError, match="api_key"):
            _ = db.cot

    def test_triggers_requires_api_key(self) -> None:
        db = HatiData(host="localhost")
        with pytest.raises(HatiDataError, match="api_key"):
            _ = db.triggers

    def test_memory_accessor_with_api_key(self) -> None:
        db = HatiData(host="localhost", api_key="hd_live_xxx")
        mem = db.memory
        assert mem is not None
        # Accessing again returns same instance
        assert db.memory is mem

    def test_cot_accessor_with_api_key(self) -> None:
        db = HatiData(host="localhost", api_key="hd_live_xxx")
        cot = db.cot
        assert cot is not None
        assert db.cot is cot

    def test_triggers_accessor_with_api_key(self) -> None:
        db = HatiData(host="localhost", api_key="hd_live_xxx")
        triggers = db.triggers
        assert triggers is not None
        assert db.triggers is triggers


class TestInsert:
    """Test the insert helper."""

    @pytest.mark.asyncio
    async def test_insert_builds_correct_sql(self) -> None:
        db = HatiData(host="localhost", api_key="hd_live_xxx")
        # Mock _get_pool to avoid real connections
        mock_pool = AsyncMock()
        mock_pool.execute = AsyncMock(return_value="INSERT 0 1")
        mock_pool._closed = False
        db._pool = mock_pool

        result = await db.insert("products", {"id": 1, "name": "Widget"})
        assert result == "INSERT 0 1"

        call_args = mock_pool.execute.call_args
        sql = call_args[0][0]
        assert "INSERT INTO products" in sql
        assert "$1" in sql
        assert "$2" in sql
        # Values should be passed as positional args
        assert call_args[0][1] == 1
        assert call_args[0][2] == "Widget"

    @pytest.mark.asyncio
    async def test_insert_serializes_dict_values(self) -> None:
        db = HatiData(host="localhost", api_key="hd_live_xxx")
        mock_pool = AsyncMock()
        mock_pool.execute = AsyncMock(return_value="INSERT 0 1")
        mock_pool._closed = False
        db._pool = mock_pool

        metadata = {"category": "food", "organic": True}
        await db.insert("products", {"id": 1, "metadata": metadata})

        call_args = mock_pool.execute.call_args
        # Dict value should be JSON-serialized
        assert call_args[0][2] == json.dumps(metadata)

    @pytest.mark.asyncio
    async def test_insert_empty_data_raises(self) -> None:
        db = HatiData(host="localhost", api_key="hd_live_xxx")
        with pytest.raises(ValueError, match="must not be empty"):
            await db.insert("products", {})


class TestClose:
    """Test lifecycle management."""

    @pytest.mark.asyncio
    async def test_close_without_connection(self) -> None:
        db = HatiData(host="localhost")
        # Should not raise
        await db.close()

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        async with HatiData(host="localhost") as db:
            assert db is not None
        # After exiting, pool should be None
        assert db._pool is None

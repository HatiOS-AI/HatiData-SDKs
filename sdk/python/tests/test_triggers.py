"""Tests for the semantic triggers module."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from hatidata._mcp import McpTransport
from hatidata.triggers import TriggerClient


@pytest.fixture
def trigger_client() -> TriggerClient:
    """Create a TriggerClient with mocked MCP transport."""
    transport = McpTransport(
        mcp_url="http://localhost:5440/mcp",
        api_key="hd_live_test123",
    )
    transport.call_tool = AsyncMock()
    return TriggerClient(transport)


class TestTriggerRegister:
    @pytest.mark.asyncio
    async def test_register_basic(self, trigger_client: TriggerClient) -> None:
        trigger_client._transport.call_tool.return_value = {
            "trigger_id": "tr-001",
            "name": "low_stock_alert",
        }

        result = await trigger_client.register(
            name="low_stock_alert",
            concept="inventory below threshold",
            threshold=0.85,
            action="webhook",
            webhook_url="https://myapp.com/webhooks/stock",
        )

        assert result["trigger_id"] == "tr-001"
        call_args = trigger_client._transport.call_tool.call_args
        args = call_args[0][1]
        assert args["name"] == "low_stock_alert"
        assert args["concept"] == "inventory below threshold"
        assert args["threshold"] == 0.85
        assert args["action_type"] == "webhook"
        assert args["action_config"]["webhook_url"] == "https://myapp.com/webhooks/stock"

    @pytest.mark.asyncio
    async def test_register_defaults(self, trigger_client: TriggerClient) -> None:
        trigger_client._transport.call_tool.return_value = {
            "trigger_id": "tr-002",
            "name": "pii_detect",
        }

        await trigger_client.register(
            name="pii_detect",
            concept="personal data exposure",
        )

        call_args = trigger_client._transport.call_tool.call_args
        args = call_args[0][1]
        assert args["threshold"] == 0.7
        assert args["action_type"] == "flag_for_review"
        assert "action_config" not in args

    @pytest.mark.asyncio
    async def test_register_with_action_config(
        self, trigger_client: TriggerClient
    ) -> None:
        trigger_client._transport.call_tool.return_value = {
            "trigger_id": "tr-003",
            "name": "notify",
        }

        await trigger_client.register(
            name="notify",
            concept="urgent issue",
            action="agent_notify",
            action_config={"priority": "high"},
        )

        call_args = trigger_client._transport.call_tool.call_args
        args = call_args[0][1]
        assert args["action_config"]["priority"] == "high"


class TestTriggerList:
    @pytest.mark.asyncio
    async def test_list_all(self, trigger_client: TriggerClient) -> None:
        trigger_client._transport.call_tool.return_value = [
            {"trigger_id": "tr-1", "name": "alert1"},
            {"trigger_id": "tr-2", "name": "alert2"},
        ]

        results = await trigger_client.list()

        assert len(results) == 2
        trigger_client._transport.call_tool.assert_called_once_with(
            "list_triggers", {}
        )

    @pytest.mark.asyncio
    async def test_list_active_only(self, trigger_client: TriggerClient) -> None:
        trigger_client._transport.call_tool.return_value = []

        await trigger_client.list(status="active")

        call_args = trigger_client._transport.call_tool.call_args
        assert call_args[0][1]["status"] == "active"

    @pytest.mark.asyncio
    async def test_list_non_list_response(
        self, trigger_client: TriggerClient
    ) -> None:
        trigger_client._transport.call_tool.return_value = {"error": "oops"}
        results = await trigger_client.list()
        assert results == []


class TestTriggerDelete:
    @pytest.mark.asyncio
    async def test_delete(self, trigger_client: TriggerClient) -> None:
        trigger_client._transport.call_tool.return_value = {
            "deleted": True,
            "trigger_id": "tr-123",
        }

        result = await trigger_client.delete(trigger_id="tr-123")

        assert result["deleted"] is True
        trigger_client._transport.call_tool.assert_called_once_with(
            "delete_trigger", {"trigger_id": "tr-123"}
        )


class TestTriggerTest:
    @pytest.mark.asyncio
    async def test_trigger_match(self, trigger_client: TriggerClient) -> None:
        trigger_client._transport.call_tool.return_value = {
            "matched": True,
            "score": 0.92,
            "threshold": 0.85,
            "trigger_name": "low_stock",
        }

        result = await trigger_client.test(
            trigger_id="tr-001",
            content="Warehouse stock is critically low at 5 units",
        )

        assert result["matched"] is True
        assert result["score"] == 0.92
        trigger_client._transport.call_tool.assert_called_once_with(
            "test_trigger",
            {
                "trigger_id": "tr-001",
                "content": "Warehouse stock is critically low at 5 units",
            },
        )

    @pytest.mark.asyncio
    async def test_trigger_no_match(self, trigger_client: TriggerClient) -> None:
        trigger_client._transport.call_tool.return_value = {
            "matched": False,
            "score": 0.12,
            "threshold": 0.85,
            "trigger_name": "low_stock",
        }

        result = await trigger_client.test(
            trigger_id="tr-001",
            content="The weather is nice today",
        )

        assert result["matched"] is False
        assert result["score"] == 0.12

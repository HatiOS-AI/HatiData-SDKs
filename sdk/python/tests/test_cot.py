"""Tests for the chain-of-thought module."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from hatidata._mcp import McpTransport
from hatidata.cot import CotClient


@pytest.fixture
def cot_client() -> CotClient:
    """Create a CotClient with mocked MCP transport."""
    transport = McpTransport(
        mcp_url="http://localhost:5440/mcp",
        api_key="hd_live_test123",
    )
    transport.call_tool = AsyncMock()
    return CotClient(transport)


class TestCotLogStep:
    @pytest.mark.asyncio
    async def test_log_step_with_content(self, cot_client: CotClient) -> None:
        cot_client._transport.call_tool.return_value = {
            "trace_id": "tr-abc",
            "session_id": "session-123",
        }

        result = await cot_client.log_step(
            session_id="session-123",
            step_type="memory_retrieval",
            content="Searching for similar setups",
        )

        assert result["trace_id"] == "tr-abc"
        call_args = cot_client._transport.call_tool.call_args
        assert call_args[0][0] == "log_reasoning_step"
        args = call_args[0][1]
        assert args["session_id"] == "session-123"
        assert args["step_type"] == "memory_retrieval"
        assert args["content"] == "Searching for similar setups"

    @pytest.mark.asyncio
    async def test_log_step_with_input_output(self, cot_client: CotClient) -> None:
        cot_client._transport.call_tool.return_value = {
            "trace_id": "tr-xyz",
            "session_id": "s1",
        }

        await cot_client.log_step(
            session_id="s1",
            step_type="analysis",
            input_data={"query": "similar setups"},
            output_data={"results": [1, 2, 3]},
        )

        call_args = cot_client._transport.call_tool.call_args
        args = call_args[0][1]
        # Content should be auto-generated from input/output
        assert "input:" in args["content"]
        assert "output:" in args["content"]
        # Metadata should include input/output data
        assert args["metadata"]["input_data"] == {"query": "similar setups"}
        assert args["metadata"]["output_data"] == {"results": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_log_step_defaults(self, cot_client: CotClient) -> None:
        cot_client._transport.call_tool.return_value = {
            "trace_id": "tr-1",
            "session_id": "s1",
        }

        await cot_client.log_step(session_id="s1", content="test")

        call_args = cot_client._transport.call_tool.call_args
        args = call_args[0][1]
        assert args["step_type"] == "observation"
        assert args["importance"] == 0.5


class TestCotReplay:
    @pytest.mark.asyncio
    async def test_replay_session(self, cot_client: CotClient) -> None:
        cot_client._transport.call_tool.return_value = {
            "session_id": "session-123",
            "steps": [
                {"step_number": 0, "step_type": "observation", "content": "start"},
                {"step_number": 1, "step_type": "decision", "content": "done"},
            ],
            "step_count": 2,
            "chain_valid": None,
        }

        result = await cot_client.replay(session_id="session-123")

        assert result["step_count"] == 2
        assert len(result["steps"]) == 2
        cot_client._transport.call_tool.assert_called_once_with(
            "replay_decision",
            {"session_id": "session-123", "verify_chain": False},
        )

    @pytest.mark.asyncio
    async def test_replay_with_verification(self, cot_client: CotClient) -> None:
        cot_client._transport.call_tool.return_value = {
            "session_id": "s1",
            "steps": [],
            "step_count": 0,
            "chain_valid": True,
        }

        result = await cot_client.replay(session_id="s1", verify_chain=True)

        assert result["chain_valid"] is True
        call_args = cot_client._transport.call_tool.call_args
        assert call_args[0][1]["verify_chain"] is True


class TestCotListSessions:
    @pytest.mark.asyncio
    async def test_list_sessions(self, cot_client: CotClient) -> None:
        cot_client._transport.call_tool.return_value = [
            {"session_id": "s1", "step_count": 5},
            {"session_id": "s2", "step_count": 3},
        ]

        results = await cot_client.list_sessions(limit=10)

        assert len(results) == 2
        call_args = cot_client._transport.call_tool.call_args
        assert call_args[0][1]["limit"] == 10

    @pytest.mark.asyncio
    async def test_list_sessions_with_filters(self, cot_client: CotClient) -> None:
        cot_client._transport.call_tool.return_value = []

        await cot_client.list_sessions(
            agent_id="my-agent",
            since="2026-01-01T00:00:00Z",
        )

        call_args = cot_client._transport.call_tool.call_args
        args = call_args[0][1]
        assert args["agent_id"] == "my-agent"
        assert args["since"] == "2026-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_list_sessions_non_list_response(
        self, cot_client: CotClient
    ) -> None:
        cot_client._transport.call_tool.return_value = {"error": "something"}
        results = await cot_client.list_sessions()
        assert results == []

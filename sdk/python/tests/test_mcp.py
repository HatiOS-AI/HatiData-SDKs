"""Tests for the MCP JSON-RPC transport."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from hatidata._mcp import McpError, McpTransport, McpTransportError
from tests.conftest import make_jsonrpc_response, make_jsonrpc_error, make_httpx_response


class TestMcpTransportInit:
    def test_default_config(self) -> None:
        t = McpTransport(mcp_url="http://localhost:5440/mcp", api_key="key")
        assert t._url == "http://localhost:5440/mcp"
        assert t._api_key == "key"
        assert t._timeout == 30.0
        assert t._client is None

    def test_trailing_slash_stripped(self) -> None:
        t = McpTransport(mcp_url="http://localhost:5440/mcp/", api_key="key")
        assert t._url == "http://localhost:5440/mcp"


class TestMcpTransportCallTool:
    @pytest.mark.asyncio
    async def test_successful_call(self) -> None:
        transport = McpTransport(
            mcp_url="http://localhost:5440/mcp",
            api_key="hd_live_test",
        )
        mock_response = make_httpx_response(
            make_jsonrpc_response({"memory_id": "m1"})
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        transport._client = mock_client

        result = await transport.call_tool("store_memory", {"content": "test"})

        assert result == {"memory_id": "m1"}
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        payload = call_kwargs.kwargs["json"]
        assert payload["method"] == "tools/call"
        assert payload["params"]["name"] == "store_memory"

    @pytest.mark.asyncio
    async def test_jsonrpc_error(self) -> None:
        transport = McpTransport(
            mcp_url="http://localhost:5440/mcp",
            api_key="hd_live_test",
        )
        mock_response = make_httpx_response(
            make_jsonrpc_error(-32601, "Method not found")
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        transport._client = mock_client

        with pytest.raises(McpError, match="Method not found"):
            await transport.call_tool("bad_tool", {})

    @pytest.mark.asyncio
    async def test_auth_failure_401(self) -> None:
        transport = McpTransport(
            mcp_url="http://localhost:5440/mcp",
            api_key="bad_key",
        )
        mock_response = make_httpx_response({"error": "unauthorized"}, status_code=401)
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        transport._client = mock_client

        with pytest.raises(McpTransportError, match="Authentication failed"):
            await transport.call_tool("store_memory", {"content": "test"})

    @pytest.mark.asyncio
    async def test_forbidden_403(self) -> None:
        transport = McpTransport(
            mcp_url="http://localhost:5440/mcp",
            api_key="limited_key",
        )
        mock_response = make_httpx_response({"error": "forbidden"}, status_code=403)
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        transport._client = mock_client

        with pytest.raises(McpTransportError, match="Access denied"):
            await transport.call_tool("store_memory", {"content": "test"})

    @pytest.mark.asyncio
    async def test_http_error(self) -> None:
        transport = McpTransport(
            mcp_url="http://localhost:5440/mcp",
            api_key="hd_live_test",
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client.is_closed = False
        transport._client = mock_client

        with pytest.raises(McpTransportError, match="HTTP request failed"):
            await transport.call_tool("store_memory", {"content": "test"})

    @pytest.mark.asyncio
    async def test_tool_error_response(self) -> None:
        transport = McpTransport(
            mcp_url="http://localhost:5440/mcp",
            api_key="hd_live_test",
        )
        error_result = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [{"type": "text", "text": "Error: table not found"}],
                "isError": True,
            },
        }
        mock_response = make_httpx_response(error_result)
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        transport._client = mock_client

        with pytest.raises(McpError, match="table not found"):
            await transport.call_tool("query", {"sql": "SELECT * FROM missing"})

    @pytest.mark.asyncio
    async def test_request_id_increments(self) -> None:
        transport = McpTransport(
            mcp_url="http://localhost:5440/mcp",
            api_key="hd_live_test",
        )
        mock_response = make_httpx_response(
            make_jsonrpc_response({"ok": True})
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        transport._client = mock_client

        await transport.call_tool("test1", {})
        await transport.call_tool("test2", {})

        calls = mock_client.post.call_args_list
        id1 = calls[0].kwargs["json"]["id"]
        id2 = calls[1].kwargs["json"]["id"]
        assert id2 == id1 + 1


class TestMcpTransportClose:
    @pytest.mark.asyncio
    async def test_close_without_client(self) -> None:
        transport = McpTransport(
            mcp_url="http://localhost:5440/mcp",
            api_key="key",
        )
        await transport.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_with_client(self) -> None:
        transport = McpTransport(
            mcp_url="http://localhost:5440/mcp",
            api_key="key",
        )
        mock_client = AsyncMock()
        mock_client.is_closed = False
        transport._client = mock_client

        await transport.close()
        mock_client.aclose.assert_called_once()
        assert transport._client is None

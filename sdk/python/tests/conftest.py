"""Shared test fixtures for the HatiData async SDK."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from hatidata import HatiData
from hatidata._mcp import McpTransport


@pytest.fixture
def mcp_transport() -> McpTransport:
    """Create an McpTransport instance (not connected)."""
    return McpTransport(
        mcp_url="http://localhost:5440/mcp",
        api_key="hd_live_test123",
    )


@pytest.fixture
def mock_mcp_transport() -> McpTransport:
    """Create an McpTransport with a mocked call_tool method."""
    transport = McpTransport(
        mcp_url="http://localhost:5440/mcp",
        api_key="hd_live_test123",
    )
    transport.call_tool = AsyncMock()
    return transport


def make_jsonrpc_response(result: Any, request_id: int = 1) -> dict[str, Any]:
    """Build a JSON-RPC 2.0 success response wrapping MCP tool output."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, default=str),
                }
            ]
        },
    }


def make_jsonrpc_error(
    code: int, message: str, request_id: int = 1
) -> dict[str, Any]:
    """Build a JSON-RPC 2.0 error response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


def make_httpx_response(
    json_data: Any, status_code: int = 200
) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = json.dumps(json_data)
    return resp

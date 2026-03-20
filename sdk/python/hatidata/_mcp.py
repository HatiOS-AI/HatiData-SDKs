"""Internal MCP JSON-RPC 2.0 transport for HatiData agent-native features.

Handles communication with the HatiData MCP endpoint for memory, CoT,
triggers, and other agent-native operations that are exposed as MCP tools.

This module is not part of the public API.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import httpx


class McpError(Exception):
    """Raised when an MCP JSON-RPC call returns an error."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"MCP error {code}: {message}")


class McpTransportError(Exception):
    """Raised when the HTTP transport fails (network, auth, etc.)."""


class McpTransport:
    """Async JSON-RPC 2.0 client for the HatiData MCP endpoint.

    The MCP endpoint accepts tool calls as JSON-RPC requests. Each tool
    invocation is a ``tools/call`` method with the tool name and arguments.

    Args:
        mcp_url: Full URL to the MCP endpoint (e.g., ``http://localhost:5440/mcp``).
        api_key: HatiData API key (``hd_live_*`` or ``hd_agent_*``).
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        mcp_url: str,
        api_key: str,
        timeout: float = 30.0,
    ) -> None:
        self._url = mcp_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._request_id = 0
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"ApiKey {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self._timeout,
            )
        return self._client

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Invoke an MCP tool and return the parsed result.

        Args:
            tool_name: The MCP tool name (e.g., ``store_memory``).
            arguments: Tool arguments as a dict.

        Returns:
            The parsed result from the tool's response content.

        Raises:
            McpError: If the JSON-RPC response contains an error.
            McpTransportError: If the HTTP request fails.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        client = await self._get_client()

        try:
            response = await client.post(self._url, json=payload)
        except httpx.HTTPError as exc:
            raise McpTransportError(f"HTTP request failed: {exc}") from exc

        if response.status_code == 401:
            raise McpTransportError(
                "Authentication failed. Check your API key."
            )

        if response.status_code == 403:
            raise McpTransportError(
                "Access denied. Your API key may lack the required scope."
            )

        if response.status_code >= 400:
            raise McpTransportError(
                f"MCP endpoint returned HTTP {response.status_code}: {response.text}"
            )

        try:
            result = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise McpTransportError(
                f"Invalid JSON response: {response.text}"
            ) from exc

        # Handle JSON-RPC error
        if "error" in result:
            err = result["error"]
            raise McpError(
                code=err.get("code", -1),
                message=err.get("message", "Unknown error"),
                data=err.get("data"),
            )

        # Extract content from MCP tool result
        rpc_result = result.get("result", {})
        if rpc_result.get("isError"):
            content = rpc_result.get("content", [{}])
            error_text = content[0].get("text", "Unknown tool error") if content else "Unknown tool error"
            raise McpError(code=-1, message=error_text)

        # Parse the text content (JSON-encoded tool output)
        content = rpc_result.get("content", [])
        if content and content[0].get("type") == "text":
            try:
                return json.loads(content[0]["text"])
            except (json.JSONDecodeError, ValueError):
                return content[0]["text"]

        return rpc_result

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

"""Semantic triggers module -- register, list, and manage triggers.

Triggers fire when agent content semantically matches a concept above
a configurable threshold. Actions include webhook, agent notification,
event logging, and flagging for human review.

Usage::

    db = HatiData(host="preprod.hatidata.com", port=5439, api_key="hd_live_xxx")

    await db.triggers.register(
        name="low_stock_alert",
        concept="inventory below threshold",
        threshold=0.85,
        action="webhook",
        webhook_url="https://myapp.com/webhooks/stock",
    )

    triggers = await db.triggers.list()
    await db.triggers.delete(trigger_id="tr-123")
"""

from __future__ import annotations

from typing import Any, Optional

from hatidata._mcp import McpTransport


class TriggerClient:
    """Client for semantic trigger operations via MCP tools.

    Args:
        transport: The MCP transport instance for JSON-RPC calls.
    """

    def __init__(self, transport: McpTransport) -> None:
        self._transport = transport

    async def register(
        self,
        name: str,
        concept: str,
        threshold: float = 0.7,
        action: str = "flag_for_review",
        webhook_url: Optional[str] = None,
        action_config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Register a new semantic trigger.

        Args:
            name: Human-readable trigger name.
            concept: The concept/topic to watch for.
            threshold: Match threshold 0.0-1.0 (default 0.7).
            action: Action type -- one of ``flag_for_review``, ``webhook``,
                ``agent_notify``, ``write_event``.
            webhook_url: URL for webhook action (required if action is
                ``webhook``).
            action_config: Additional action configuration dict.

        Returns:
            Dict with ``trigger_id`` and ``name``.
        """
        arguments: dict[str, Any] = {
            "name": name,
            "concept": concept,
            "threshold": threshold,
            "action_type": action,
        }

        config = dict(action_config or {})
        if webhook_url:
            config["webhook_url"] = webhook_url
        if config:
            arguments["action_config"] = config

        return await self._transport.call_tool("register_trigger", arguments)

    async def list(
        self,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List registered semantic triggers.

        Args:
            status: Optional filter -- ``active``, ``inactive``, or ``all``.

        Returns:
            List of trigger dicts.
        """
        arguments: dict[str, Any] = {}
        if status:
            arguments["status"] = status

        result = await self._transport.call_tool("list_triggers", arguments)
        if isinstance(result, list):
            return result
        return []

    async def delete(self, trigger_id: str) -> dict[str, Any]:
        """Delete (soft-disable) a semantic trigger.

        Args:
            trigger_id: The trigger UUID to disable.

        Returns:
            Dict with ``deleted`` status and ``trigger_id``.
        """
        return await self._transport.call_tool(
            "delete_trigger", {"trigger_id": trigger_id}
        )

    async def test(
        self,
        trigger_id: str,
        content: str,
    ) -> dict[str, Any]:
        """Test if content would match a trigger's concept.

        Args:
            trigger_id: The trigger ID to test against.
            content: Content text to evaluate.

        Returns:
            Dict with ``matched`` (bool), ``score``, ``threshold``,
            and ``trigger_name``.
        """
        return await self._transport.call_tool(
            "test_trigger",
            {"trigger_id": trigger_id, "content": content},
        )

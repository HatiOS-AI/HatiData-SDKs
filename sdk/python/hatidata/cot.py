"""Chain-of-Thought (CoT) module -- log and replay agent reasoning traces.

Provides SHA-256 hash-chained reasoning step logging and session replay
via MCP tools. Each step is appended to an immutable, tamper-evident chain.

Usage::

    db = HatiData(host="preprod.hatidata.com", port=5439, api_key="hd_live_xxx")

    receipt = await db.cot.log_step(
        session_id="session-123",
        step_type="memory_retrieval",
        input_data={"query": "similar setups"},
        output_data={"results": [...]},
    )

    trace = await db.cot.replay(session_id="session-123")
"""

from __future__ import annotations

from typing import Any, Optional

from hatidata._mcp import McpTransport


class CotClient:
    """Client for chain-of-thought operations via MCP tools.

    Args:
        transport: The MCP transport instance for JSON-RPC calls.
    """

    def __init__(self, transport: McpTransport) -> None:
        self._transport = transport

    async def log_step(
        self,
        session_id: str,
        step_type: str = "observation",
        content: Optional[str] = None,
        input_data: Optional[dict[str, Any]] = None,
        output_data: Optional[dict[str, Any]] = None,
        importance: float = 0.5,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Log a reasoning step in a chain-of-thought session.

        Steps are appended to an immutable SHA-256 hash chain for
        tamper-evidence. Step types include: observation, hypothesis,
        analysis, decision, action, reflection, planning, evaluation,
        retrieval, synthesis, delegation, error.

        Args:
            session_id: Reasoning session identifier.
            step_type: Type of reasoning step.
            content: The reasoning step content text. If not provided,
                a JSON representation of input_data and output_data is used.
            input_data: Optional input data for this step.
            output_data: Optional output/result data for this step.
            importance: Importance score 0.0-1.0.
            metadata: Optional metadata dict.

        Returns:
            Dict with ``trace_id`` and ``session_id``.
        """
        # Build content from input/output if not provided directly
        if content is None:
            parts = []
            if input_data:
                parts.append(f"input: {input_data}")
            if output_data:
                parts.append(f"output: {output_data}")
            content = "; ".join(parts) if parts else step_type

        arguments: dict[str, Any] = {
            "session_id": session_id,
            "step_type": step_type,
            "content": content,
            "importance": importance,
        }
        if metadata:
            arguments["metadata"] = metadata
        # Include input/output in metadata if provided
        if input_data or output_data:
            extra_meta = arguments.get("metadata", {}) or {}
            if input_data:
                extra_meta["input_data"] = input_data
            if output_data:
                extra_meta["output_data"] = output_data
            arguments["metadata"] = extra_meta

        return await self._transport.call_tool("log_reasoning_step", arguments)

    async def replay(
        self,
        session_id: str,
        verify_chain: bool = False,
    ) -> dict[str, Any]:
        """Replay all reasoning steps for a session in order.

        Args:
            session_id: The session ID to replay.
            verify_chain: If True, verify the SHA-256 hash chain integrity.

        Returns:
            Dict with ``session_id``, ``steps`` list, ``step_count``,
            and optionally ``chain_valid`` (bool).
        """
        return await self._transport.call_tool(
            "replay_decision",
            {
                "session_id": session_id,
                "verify_chain": verify_chain,
            },
        )

    async def list_sessions(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
        since: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List recent chain-of-thought sessions.

        Args:
            agent_id: Optional filter by agent ID.
            limit: Maximum sessions to return.
            since: ISO timestamp to filter from.

        Returns:
            List of session summary dicts.
        """
        arguments: dict[str, Any] = {"limit": limit}
        if agent_id:
            arguments["agent_id"] = agent_id
        if since:
            arguments["since"] = since

        result = await self._transport.call_tool(
            "get_session_history", arguments
        )
        if isinstance(result, list):
            return result
        return []

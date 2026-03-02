"""HatiData Control Plane client — REST API for agent-native features.

Wraps the Control Plane HTTP API for agent memory, semantic triggers,
branches, chain-of-thought, and JIT access.

Usage::

    from hatidata_agent import ControlPlaneClient

    cp = ControlPlaneClient(
        base_url="https://staging-api.hatidata.com",
        email="sarah@acme.demo.hatidata.dev",
        password="DemoDay2026!",
    )

    # Agent memory
    mem = cp.create_memory(agent_id="my-agent", content="User prefers dark mode")
    results = cp.search_memory(query="user preferences", top_k=5)

    # Semantic triggers
    trigger = cp.create_trigger(name="PII detected", concept="personal data exposure")

    # Branches
    branch = cp.create_branch(agent_id="analyst", tables=["portfolio"])
    cp.merge_branch(branch["id"])

    # Chain-of-thought
    cp.ingest_cot(traces=[...])
    replay = cp.replay_cot(session_id="sess-001")
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import requests


class ControlPlaneClient:
    """Authenticated client for HatiData Control Plane REST API.

    Supports JWT auth (email/password login) and API key auth.

    Args:
        base_url: Control plane URL (e.g., "https://staging-api.hatidata.com").
        email: User email for JWT login.
        password: User password for JWT login.
        api_key: API key (alternative to email/password). Use ``ApiKey <key>`` format.
        org_id: Organization ID. Auto-detected from login if not provided.
        timeout: Request timeout in seconds.
        include_meta: When True, preserve ``_meta`` response metadata in API responses.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        email: str = "",
        password: str = "",
        api_key: str = "",
        org_id: str = "",
        timeout: int = 15,
        include_meta: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.api_key = api_key
        self.org_id = org_id
        self.timeout = timeout
        self.include_meta = include_meta
        self._token: Optional[str] = None
        self._user_context: Optional[dict[str, Any]] = None
        self._org_context: Optional[dict[str, Any]] = None

    # ── Authentication ─────────────────────────────────────────────────────

    def login(self) -> dict[str, Any]:
        """Authenticate with email/password and store JWT token.

        Returns the full login response (token, user, org).
        """
        resp = requests.post(
            f"{self.base_url}/v1/auth/login",
            json={"email": self.email, "password": self.password},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["token"]
        self._user_context = data.get("user")
        self._org_context = data.get("org")
        if not self.org_id and self._org_context:
            self.org_id = self._org_context.get("id", "")
        return data

    def _headers(self) -> dict[str, str]:
        """Build auth headers. Auto-login if needed."""
        if self.api_key:
            return {"Authorization": f"ApiKey {self.api_key}"}
        if not self._token:
            self.login()
        return {"Authorization": f"Bearer {self._token}"}

    def _url(self, path: str) -> str:
        """Build org-scoped URL."""
        return f"{self.base_url}/v1/organizations/{self.org_id}{path}"

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        resp = requests.get(
            self._url(path),
            headers=self._headers(),
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json: Optional[dict] = None) -> Any:
        resp = requests.post(
            self._url(path),
            headers=self._headers(),
            json=json or {},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _put(self, path: str, json: Optional[dict] = None) -> Any:
        resp = requests.put(
            self._url(path),
            headers=self._headers(),
            json=json or {},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path: str) -> Any:
        resp = requests.delete(
            self._url(path),
            headers=self._headers(),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        if resp.content:
            return resp.json()
        return {}

    def _abs_get(self, path: str, params: Optional[dict] = None) -> Any:
        """GET with absolute path (not org-scoped)."""
        resp = requests.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _abs_post(self, path: str, json: Optional[dict] = None) -> Any:
        """POST with absolute path (not org-scoped)."""
        resp = requests.post(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=json or {},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _request_with_meta(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Make a request and return full JSON including _meta if present.

        When ``include_meta`` is True, returns the raw response JSON
        (preserving ``_meta`` wrapper). Otherwise returns just the data.
        """
        url = self._url(path)
        resp = requests.request(
            method, url, headers=self._headers(), timeout=self.timeout, **kwargs
        )
        resp.raise_for_status()
        data = resp.json()
        if self.include_meta:
            return data
        # Strip _meta wrapper if present
        if isinstance(data, dict) and "data" in data and "_meta" in data:
            return data["data"]
        return data

    # ── Health ─────────────────────────────────────────────────────────────

    def health_check(self) -> bool:
        """Check if the control plane is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    # ── Agent Memory ───────────────────────────────────────────────────────

    def create_memory(
        self,
        agent_id: str,
        content: str,
        memory_type: str = "observation",
    ) -> dict[str, Any]:
        """Store a new agent memory."""
        return self._post("/agent-memory", {
            "agent_id": agent_id,
            "content": content,
            "memory_type": memory_type,
        })

    def list_memories(
        self,
        agent_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List agent memories with optional filters."""
        params: dict[str, Any] = {"limit": limit}
        if agent_id:
            params["agent_id"] = agent_id
        if memory_type:
            params["memory_type"] = memory_type
        return self._get("/agent-memory", params)

    def search_memory(
        self,
        query: str,
        agent_id: Optional[str] = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Semantic search over agent memories."""
        params: dict[str, Any] = {"query": query, "top_k": top_k}
        if agent_id:
            params["agent_id"] = agent_id
        return self._get("/agent-memory/search", params)

    def delete_memory(self, memory_id: str) -> dict[str, Any]:
        """Delete a specific memory."""
        return self._delete(f"/agent-memory/{memory_id}")

    def embedding_stats(self) -> dict[str, Any]:
        """Get embedding statistics for the org."""
        return self._get("/agent-memory/embedding-stats")

    # ── Semantic Triggers ──────────────────────────────────────────────────

    def create_trigger(
        self,
        name: str,
        concept: str,
        threshold: float = 0.85,
        actions: Optional[list[str]] = None,
        cooldown_secs: int = 60,
    ) -> dict[str, Any]:
        """Register a new semantic trigger."""
        return self._post("/triggers", {
            "name": name,
            "concept": concept,
            "threshold": threshold,
            "actions": actions or ["webhook"],
            "cooldown_secs": cooldown_secs,
        })

    def list_triggers(self) -> list[dict[str, Any]]:
        """List all semantic triggers for the org."""
        return self._get("/triggers")

    def test_trigger(self, trigger_id: str, text: str) -> dict[str, Any]:
        """Test a trigger against sample text."""
        return self._post(f"/triggers/{trigger_id}/test", {"text": text})

    def delete_trigger(self, trigger_id: str) -> dict[str, Any]:
        """Delete a semantic trigger."""
        return self._delete(f"/triggers/{trigger_id}")

    # ── Branches ───────────────────────────────────────────────────────────

    def create_branch(
        self,
        agent_id: str,
        tables: list[str],
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a new data branch for isolated experimentation."""
        payload: dict[str, Any] = {"agent_id": agent_id, "tables": tables}
        if description:
            payload["description"] = description
        return self._post("/branches", payload)

    def list_branches(self) -> list[dict[str, Any]]:
        """List all branches for the org."""
        return self._get("/branches")

    def get_branch(self, branch_id: str) -> dict[str, Any]:
        """Get details of a specific branch."""
        return self._get(f"/branches/{branch_id}")

    def merge_branch(
        self,
        branch_id: str,
        strategy: str = "branch_wins",
    ) -> dict[str, Any]:
        """Merge a branch back to main."""
        return self._post(f"/branches/{branch_id}/merge", {"strategy": strategy})

    def discard_branch(self, branch_id: str) -> dict[str, Any]:
        """Discard a branch and free resources."""
        return self._delete(f"/branches/{branch_id}")

    def branch_diff(self, branch_id: str) -> dict[str, Any]:
        """Get diff between branch and main."""
        return self._get(f"/branches/{branch_id}/diff")

    def branch_conflicts(self, branch_id: str) -> dict[str, Any]:
        """Check for merge conflicts."""
        return self._get(f"/branches/{branch_id}/conflicts")

    def branch_cost(self, branch_id: str) -> dict[str, Any]:
        """Get storage/compute cost for a branch."""
        return self._get(f"/branches/{branch_id}/cost")

    def branch_analytics(self) -> dict[str, Any]:
        """Get aggregate branch analytics for the org."""
        return self._get("/branches/analytics")

    # ── Chain-of-Thought ───────────────────────────────────────────────────

    def ingest_cot(self, traces: list[dict[str, Any]]) -> dict[str, Any]:
        """Ingest chain-of-thought trace entries."""
        return self._abs_post("/v1/cot/ingest", {"traces": traces})

    def list_cot_sessions(self) -> list[dict[str, Any]]:
        """List all CoT sessions."""
        return self._abs_get("/v1/cot/sessions")

    def replay_cot(self, session_id: str) -> dict[str, Any]:
        """Replay a CoT session step-by-step."""
        return self._abs_get(f"/v1/cot/sessions/{session_id}/replay")

    def verify_cot(self, session_id: str) -> dict[str, Any]:
        """Verify the hash chain integrity of a CoT session."""
        return self._abs_get(f"/v1/cot/sessions/{session_id}/verify")

    # ── JIT Access ─────────────────────────────────────────────────────────

    def request_jit(
        self,
        target_role: str,
        reason: str,
        duration_hours: int = 1,
    ) -> dict[str, Any]:
        """Request just-in-time privilege escalation."""
        return self._post("/jit/request", {
            "target_role": target_role,
            "reason": reason,
            "duration_hours": duration_hours,
        })

    def list_jit_grants(self) -> list[dict[str, Any]]:
        """List all JIT access grants for the org."""
        return self._get("/jit")

    # ── CoT Hash Chain Helpers ─────────────────────────────────────────────

    @staticmethod
    def build_cot_trace(
        session_id: str,
        agent_id: str,
        org_id: str,
        step_index: int,
        step_type: str,
        content: dict[str, Any],
        prev_hash: str = "",
    ) -> dict[str, Any]:
        """Build a single CoT trace entry with SHA-256 hash chain."""
        trace_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        hash_input = f"{prev_hash}{step_type}{str(content)}{timestamp}"
        content_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        return {
            "trace_id": trace_id,
            "session_id": session_id,
            "agent_id": agent_id,
            "org_id": org_id,
            "step_index": step_index,
            "trace_type": step_type,
            "content": content,
            "content_hash": content_hash,
            "timestamp": timestamp,
        }

    @staticmethod
    def build_cot_session(
        agent_id: str,
        org_id: str,
        steps: list[dict[str, Any]],
    ) -> tuple[str, list[dict[str, Any]]]:
        """Build a complete CoT session with hash-chained steps.

        Args:
            agent_id: Agent identifier.
            org_id: Organization ID.
            steps: List of dicts with ``type`` and ``content`` keys.

        Returns:
            Tuple of (session_id, list_of_trace_dicts).
        """
        session_id = str(uuid.uuid4())
        traces: list[dict[str, Any]] = []
        prev_hash = ""
        for i, step in enumerate(steps):
            trace = ControlPlaneClient.build_cot_trace(
                session_id=session_id,
                agent_id=agent_id,
                org_id=org_id,
                step_index=i,
                step_type=step["type"],
                content=step["content"],
                prev_hash=prev_hash,
            )
            prev_hash = trace["content_hash"]
            traces.append(trace)
        return session_id, traces

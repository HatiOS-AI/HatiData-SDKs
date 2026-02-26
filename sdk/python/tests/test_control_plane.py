"""Unit tests for ControlPlaneClient — mock HTTP, no live server needed."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from hatidata_agent.control_plane import ControlPlaneClient


@pytest.fixture
def client() -> ControlPlaneClient:
    """Pre-authenticated client with org_id set."""
    cp = ControlPlaneClient(
        base_url="http://localhost:8080",
        email="test@example.com",
        password="pass",
        org_id="org-001",
    )
    cp._token = "fake-jwt"
    return cp


def _mock_response(data: dict | list, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = data
    resp.content = json.dumps(data).encode()
    resp.raise_for_status = MagicMock()
    return resp


# ── Auth ───────────────────────────────────────────────────────────────────


class TestAuth:
    @patch("hatidata_agent.control_plane.requests.post")
    def test_login_stores_token(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response({
            "token": "jwt-123",
            "user": {"id": "u1", "email": "test@example.com"},
            "org": {"id": "org-001", "name": "Test Org"},
        })
        cp = ControlPlaneClient(
            base_url="http://localhost:8080",
            email="test@example.com",
            password="pass",
        )
        result = cp.login()
        assert cp._token == "jwt-123"
        assert cp.org_id == "org-001"
        assert result["user"]["email"] == "test@example.com"

    @patch("hatidata_agent.control_plane.requests.post")
    def test_auto_login_on_first_request(self, mock_post: MagicMock) -> None:
        login_resp = _mock_response({
            "token": "jwt-auto",
            "user": {"id": "u1"},
            "org": {"id": "org-auto"},
        })
        mock_post.return_value = login_resp

        cp = ControlPlaneClient(
            base_url="http://localhost:8080",
            email="test@example.com",
            password="pass",
        )
        headers = cp._headers()
        assert headers["Authorization"] == "Bearer jwt-auto"
        assert cp.org_id == "org-auto"

    def test_api_key_auth_skips_login(self) -> None:
        cp = ControlPlaneClient(
            base_url="http://localhost:8080",
            api_key="hd_live_testkey123",
            org_id="org-key",
        )
        headers = cp._headers()
        assert headers["Authorization"] == "ApiKey hd_live_testkey123"


# ── Health ─────────────────────────────────────────────────────────────────


class TestHealth:
    @patch("hatidata_agent.control_plane.requests.get")
    def test_health_check_ok(self, mock_get: MagicMock) -> None:
        mock_get.return_value = MagicMock(status_code=200)
        cp = ControlPlaneClient(base_url="http://localhost:8080")
        assert cp.health_check() is True

    @patch("hatidata_agent.control_plane.requests.get")
    def test_health_check_fail(self, mock_get: MagicMock) -> None:
        mock_get.return_value = MagicMock(status_code=503)
        cp = ControlPlaneClient(base_url="http://localhost:8080")
        assert cp.health_check() is False


# ── Agent Memory ───────────────────────────────────────────────────────────


class TestAgentMemory:
    @patch("hatidata_agent.control_plane.requests.post")
    def test_create_memory(self, mock_post: MagicMock, client: ControlPlaneClient) -> None:
        mock_post.return_value = _mock_response({"id": "mem-1", "content": "test"})
        result = client.create_memory(agent_id="agent-1", content="test")
        assert result["id"] == "mem-1"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["json"]["agent_id"] == "agent-1"

    @patch("hatidata_agent.control_plane.requests.get")
    def test_list_memories(self, mock_get: MagicMock, client: ControlPlaneClient) -> None:
        mock_get.return_value = _mock_response([
            {"id": "mem-1", "content": "a"},
            {"id": "mem-2", "content": "b"},
        ])
        result = client.list_memories(agent_id="agent-1")
        assert len(result) == 2
        params = mock_get.call_args.kwargs["params"]
        assert params["agent_id"] == "agent-1"

    @patch("hatidata_agent.control_plane.requests.get")
    def test_search_memory(self, mock_get: MagicMock, client: ControlPlaneClient) -> None:
        mock_get.return_value = _mock_response([{"id": "mem-1", "score": 0.95}])
        result = client.search_memory(query="user preferences", top_k=3)
        assert len(result) == 1
        params = mock_get.call_args.kwargs["params"]
        assert params["query"] == "user preferences"
        assert params["top_k"] == 3

    @patch("hatidata_agent.control_plane.requests.delete")
    def test_delete_memory(self, mock_delete: MagicMock, client: ControlPlaneClient) -> None:
        mock_delete.return_value = _mock_response({"memory_id": "mem-1", "status": "deleted"})
        result = client.delete_memory("mem-1")
        assert result["status"] == "deleted"


# ── Semantic Triggers ──────────────────────────────────────────────────────


class TestTriggers:
    @patch("hatidata_agent.control_plane.requests.post")
    def test_create_trigger(self, mock_post: MagicMock, client: ControlPlaneClient) -> None:
        mock_post.return_value = _mock_response({"id": "t-1", "name": "PII"})
        result = client.create_trigger(name="PII", concept="personal data")
        assert result["name"] == "PII"
        body = mock_post.call_args.kwargs["json"]
        assert body["concept"] == "personal data"
        assert body["threshold"] == 0.85

    @patch("hatidata_agent.control_plane.requests.get")
    def test_list_triggers(self, mock_get: MagicMock, client: ControlPlaneClient) -> None:
        mock_get.return_value = _mock_response([{"id": "t-1"}, {"id": "t-2"}])
        result = client.list_triggers()
        assert len(result) == 2

    @patch("hatidata_agent.control_plane.requests.post")
    def test_test_trigger(self, mock_post: MagicMock, client: ControlPlaneClient) -> None:
        mock_post.return_value = _mock_response({
            "trigger_id": "t-1",
            "similarity": 0.92,
            "would_fire": True,
        })
        result = client.test_trigger("t-1", "contains SSN 123-45-6789")
        assert result["would_fire"] is True
        assert result["similarity"] == 0.92

    @patch("hatidata_agent.control_plane.requests.delete")
    def test_delete_trigger(self, mock_delete: MagicMock, client: ControlPlaneClient) -> None:
        mock_delete.return_value = _mock_response({"trigger_id": "t-1", "status": "deleted"})
        result = client.delete_trigger("t-1")
        assert result["status"] == "deleted"


# ── Branches ───────────────────────────────────────────────────────────────


class TestBranches:
    @patch("hatidata_agent.control_plane.requests.post")
    def test_create_branch(self, mock_post: MagicMock, client: ControlPlaneClient) -> None:
        mock_post.return_value = _mock_response({"id": "br-1", "status": "active"})
        result = client.create_branch(
            agent_id="analyst",
            tables=["portfolio"],
            description="Test rebalancing",
        )
        assert result["status"] == "active"
        body = mock_post.call_args.kwargs["json"]
        assert body["tables"] == ["portfolio"]
        assert body["description"] == "Test rebalancing"

    @patch("hatidata_agent.control_plane.requests.get")
    def test_list_branches(self, mock_get: MagicMock, client: ControlPlaneClient) -> None:
        mock_get.return_value = _mock_response([{"id": "br-1"}, {"id": "br-2"}])
        assert len(client.list_branches()) == 2

    @patch("hatidata_agent.control_plane.requests.post")
    def test_merge_branch(self, mock_post: MagicMock, client: ControlPlaneClient) -> None:
        mock_post.return_value = _mock_response({"branch_id": "br-1", "status": "merged"})
        result = client.merge_branch("br-1")
        assert result["status"] == "merged"

    @patch("hatidata_agent.control_plane.requests.delete")
    def test_discard_branch(self, mock_delete: MagicMock, client: ControlPlaneClient) -> None:
        mock_delete.return_value = _mock_response({"branch_id": "br-1", "status": "discarded"})
        result = client.discard_branch("br-1")
        assert result["status"] == "discarded"

    @patch("hatidata_agent.control_plane.requests.get")
    def test_branch_diff(self, mock_get: MagicMock, client: ControlPlaneClient) -> None:
        mock_get.return_value = _mock_response({
            "branch_id": "br-1",
            "total_rows_added": 5,
            "tables": [],
        })
        result = client.branch_diff("br-1")
        assert result["total_rows_added"] == 5


# ── Chain-of-Thought ───────────────────────────────────────────────────────


class TestCoT:
    @patch("hatidata_agent.control_plane.requests.post")
    def test_ingest_cot(self, mock_post: MagicMock, client: ControlPlaneClient) -> None:
        mock_post.return_value = _mock_response({"ingested": 3, "trace_ids": ["a", "b", "c"]})
        result = client.ingest_cot(traces=[{"trace_id": "a"}, {"trace_id": "b"}, {"trace_id": "c"}])
        assert result["ingested"] == 3

    @patch("hatidata_agent.control_plane.requests.get")
    def test_replay_cot(self, mock_get: MagicMock, client: ControlPlaneClient) -> None:
        mock_get.return_value = _mock_response({
            "session_id": "s-1",
            "total_steps": 5,
            "chain_valid": True,
            "steps": [],
        })
        result = client.replay_cot("s-1")
        assert result["chain_valid"] is True

    @patch("hatidata_agent.control_plane.requests.get")
    def test_verify_cot(self, mock_get: MagicMock, client: ControlPlaneClient) -> None:
        mock_get.return_value = _mock_response({
            "session_id": "s-1",
            "chain_valid": True,
            "invalid_hashes": [],
        })
        result = client.verify_cot("s-1")
        assert result["chain_valid"] is True
        assert result["invalid_hashes"] == []

    def test_build_cot_session(self) -> None:
        session_id, traces = ControlPlaneClient.build_cot_session(
            agent_id="test-agent",
            org_id="org-001",
            steps=[
                {"type": "Thought", "content": {"text": "analyzing data"}},
                {"type": "ToolCall", "content": {"tool": "sql", "query": "SELECT 1"}},
                {"type": "ToolResult", "content": {"result": [{"1": 1}]}},
            ],
        )
        assert len(traces) == 3
        assert traces[0]["session_id"] == session_id
        assert traces[0]["trace_type"] == "Thought"
        assert traces[1]["trace_type"] == "ToolCall"
        assert traces[2]["trace_type"] == "ToolResult"
        # Verify hash chain: each trace has a content_hash
        for trace in traces:
            assert len(trace["content_hash"]) == 64  # SHA-256 hex

    def test_build_cot_trace(self) -> None:
        trace = ControlPlaneClient.build_cot_trace(
            session_id="s-1",
            agent_id="agent-1",
            org_id="org-001",
            step_index=0,
            step_type="Thought",
            content={"text": "test"},
        )
        assert trace["session_id"] == "s-1"
        assert trace["step_index"] == 0
        assert len(trace["content_hash"]) == 64


# ── JIT Access ─────────────────────────────────────────────────────────────


class TestJitAccess:
    @patch("hatidata_agent.control_plane.requests.post")
    def test_request_jit(self, mock_post: MagicMock, client: ControlPlaneClient) -> None:
        mock_post.return_value = _mock_response({"id": "jit-1", "status": "pending"})
        result = client.request_jit(
            target_role="admin",
            reason="emergency investigation",
        )
        assert result["status"] == "pending"

    @patch("hatidata_agent.control_plane.requests.get")
    def test_list_jit_grants(self, mock_get: MagicMock, client: ControlPlaneClient) -> None:
        mock_get.return_value = _mock_response({"grants": [{"id": "jit-1"}]})
        result = client.list_jit_grants()
        assert result["grants"][0]["id"] == "jit-1"


# ── URL Building ───────────────────────────────────────────────────────────


class TestUrlBuilding:
    def test_org_scoped_url(self, client: ControlPlaneClient) -> None:
        assert client._url("/agent-memory") == "http://localhost:8080/v1/organizations/org-001/agent-memory"

    def test_trailing_slash_stripped(self) -> None:
        cp = ControlPlaneClient(base_url="http://localhost:8080/", org_id="o1")
        assert cp._url("/test") == "http://localhost:8080/v1/organizations/o1/test"

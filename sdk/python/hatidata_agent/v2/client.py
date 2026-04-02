"""HatiData V2 Runtime Client — thin wrapper over the V2 REST API."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx


@dataclass
class V2Config:
    """Configuration for the V2 client."""
    base_url: str
    token: str
    auth_scheme: str = "ApiKey"  # "ApiKey" or "Bearer"
    timeout: float = 30.0


class HatiDataV2Client:
    """
    HatiData V2 Runtime Client.

    Usage::

        from hatidata_agent.v2 import HatiDataV2Client

        client = HatiDataV2Client(
            base_url="https://preprod-api.hatidata.com",
            token="hd_live_your_api_key",
        )

        # Create a task
        task = client.runtime.create_task(kind="code_generation")

        # Create and claim an attempt
        attempt = client.runtime.create_attempt(task["id"])
        claimed = client.runtime.claim(attempt["id"], attempt["lease_token"])

        # Complete
        client.runtime.complete(attempt["id"], attempt["lease_token"], succeeded=True)

        # Explain the result
        bundle = client.lineage.explain(artifact_id)
    """

    def __init__(
        self,
        base_url: str = "https://api.hatidata.com",
        token: str = "",
        auth_scheme: str = "ApiKey",
        timeout: float = 30.0,
    ):
        self._base = base_url.rstrip("/")
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"{auth_scheme} {token}",
        }
        self._timeout = timeout
        self._http = httpx.Client(base_url=self._base, headers=self._headers, timeout=timeout)

        self.runtime = _RuntimeClient(self)
        self.lineage = _LineageClient(self)
        self.reviews = _ReviewClient(self)
        self.views = _ViewsClient(self)

    def _request(self, method: str, path: str, **kwargs) -> Any:
        resp = self._http.request(method, path, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class _RuntimeClient:
    def __init__(self, client: HatiDataV2Client):
        self._c = client

    def create_task(self, kind: str, **kwargs) -> Dict:
        return self._c._request("POST", "/v2/runtime/tasks", json={"kind": kind, **kwargs})

    def get_task(self, task_id: str) -> Dict:
        return self._c._request("GET", f"/v2/runtime/tasks/{task_id}")

    def list_tasks(self, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        params = {"limit": limit}
        if status:
            params["status"] = status
        return self._c._request("GET", "/v2/runtime/tasks", params=params)

    def create_attempt(self, task_id: str, agent_id: Optional[str] = None) -> Dict:
        body = {"agent_id": agent_id} if agent_id else {}
        return self._c._request("POST", f"/v2/runtime/tasks/{task_id}/attempts", json=body)

    def claim(self, attempt_id: str, lease_token: str, agent_id: Optional[str] = None) -> Dict:
        return self._c._request("PUT", f"/v2/runtime/attempts/{attempt_id}/claim", json={
            "lease_token": lease_token,
            "agent_id": agent_id,
        })

    def heartbeat(self, attempt_id: str, lease_token: str) -> Dict:
        return self._c._request("PUT", f"/v2/runtime/attempts/{attempt_id}/heartbeat", json={
            "lease_token": lease_token,
        })

    def complete(self, attempt_id: str, lease_token: str, succeeded: bool = True, failure_reason: Optional[str] = None) -> Dict:
        if succeeded:
            outcome = {"outcome": "succeeded"}
        else:
            outcome = {"outcome": "failed", "failure_reason": failure_reason or "unknown"}
        return self._c._request("PUT", f"/v2/runtime/attempts/{attempt_id}/complete", json={
            "lease_token": lease_token,
            **outcome,
        })

    def record_decision(self, attempt_id: str, model_id: str, **kwargs) -> Dict:
        return self._c._request("POST", "/v2/runtime/decisions", json={
            "attempt_id": attempt_id,
            "model_id": model_id,
            **kwargs,
        })

    def record_invocation(self, decision_id: str, model_id: str, prompt_hash: str,
                          input_tokens: int, output_tokens: int, cost_usd: float,
                          latency_ms: int, **kwargs) -> Dict:
        return self._c._request("POST", "/v2/runtime/invocations", json={
            "decision_id": decision_id,
            "model_id": model_id,
            "prompt_hash": prompt_hash,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            **kwargs,
        })

    def publish_artifact(self, attempt_id: str, kind: str, content_hash: str,
                         confidence: float, **kwargs) -> Dict:
        return self._c._request("POST", "/v2/runtime/artifacts", json={
            "attempt_id": attempt_id,
            "kind": kind,
            "content_hash": content_hash,
            "confidence": confidence,
            **kwargs,
        })

    def record_validation(self, artifact_id: str, validator_kind: str, result: str, **kwargs) -> Dict:
        return self._c._request("POST", f"/v2/runtime/artifacts/{artifact_id}/validations", json={
            "validator_kind": validator_kind,
            "result": result,
            **kwargs,
        })

    def ingest_event(self, attempt_id: str, kind: str, payload: Optional[Dict] = None) -> Dict:
        return self._c._request("POST", "/v2/runtime/events", json={
            "attempt_id": attempt_id,
            "kind": kind,
            "payload": payload or {},
        })


class _LineageClient:
    def __init__(self, client: HatiDataV2Client):
        self._c = client

    def upstream(self, entity_id: str, depth: int = 10, entity_type: str = "artifact") -> Dict:
        return self._c._request("GET", f"/v2/lineage/{entity_id}/upstream",
                                params={"depth": depth, "entity_type": entity_type})

    def downstream(self, entity_id: str, depth: int = 10, entity_type: str = "task") -> Dict:
        return self._c._request("GET", f"/v2/lineage/{entity_id}/downstream",
                                params={"depth": depth, "entity_type": entity_type})

    def explain(self, artifact_id: str, max_events: int = 100) -> Dict:
        return self._c._request("GET", f"/v2/explain/{artifact_id}",
                                params={"max_events": max_events})


class _ReviewClient:
    def __init__(self, client: HatiDataV2Client):
        self._c = client

    def request_review(self, requested_by: str, **kwargs) -> Dict:
        return self._c._request("POST", "/v2/reviews", json={
            "requested_by": requested_by,
            **kwargs,
        })

    def approve(self, review_id: str, decided_by: str, expected_version: int,
                reason: Optional[str] = None) -> Dict:
        return self._c._request("PUT", f"/v2/reviews/{review_id}/resolve", json={
            "outcome": "approved",
            "decided_by": decided_by,
            "expected_version": expected_version,
            "resolution_reason": reason,
        })

    def reject(self, review_id: str, decided_by: str, expected_version: int,
               reason: str = "Rejected") -> Dict:
        return self._c._request("PUT", f"/v2/reviews/{review_id}/resolve", json={
            "outcome": "blocked",
            "decided_by": decided_by,
            "expected_version": expected_version,
            "resolution_reason": reason,
        })

    def list_pending(self, limit: int = 50) -> List[Dict]:
        return self._c._request("GET", "/v2/reviews/pending", params={"limit": limit})


class _ViewsClient:
    def __init__(self, client: HatiDataV2Client):
        self._c = client

    def active_attempts(self) -> Dict:
        return self._c._request("GET", "/v2/runtime/views/active-attempts")

    def invocation_costs(self) -> Dict:
        return self._c._request("GET", "/v2/runtime/views/invocation-costs")

    def confidence_distribution(self) -> Dict:
        return self._c._request("GET", "/v2/runtime/views/confidence-distribution")

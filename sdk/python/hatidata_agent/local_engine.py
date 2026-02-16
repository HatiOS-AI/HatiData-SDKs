"""Local DuckDB engine for MCP server --local mode.

Provides the same query()/execute() interface as HatiDataAgent but backed
by a local DuckDB file instead of a remote proxy connection.  All memory,
chain-of-thought, trigger, and branch schemas are auto-created on first use.

Usage::

    from hatidata_agent.local_engine import LocalDuckDBEngine

    engine = LocalDuckDBEngine(".hati/local.duckdb")
    engine.query("SELECT 42 AS answer")
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class LocalDuckDBEngine:
    """DuckDB-backed engine for fully local (offline) agent workflows.

    Mirrors the internal schemas that the Rust proxy creates so MCP tools
    work identically in local and cloud modes.

    Args:
        db_path: Path to the DuckDB database file. Parent directories are
            created automatically.  Defaults to ``.hati/local.duckdb``.
    """

    # Schema names matching the Rust proxy internals
    MEMORY_SCHEMA = "_hatidata_memory_local"
    COT_SCHEMA = "_hatidata_cot_local"
    TRIGGER_SCHEMA = "_hatidata_triggers_local"

    def __init__(self, db_path: str = ".hati/local.duckdb") -> None:
        try:
            import duckdb
        except ImportError as exc:
            raise ImportError(
                "duckdb is required for local mode. "
                "Install it with: pip install 'hatidata-agent[mcp]'"
            ) from exc

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(db_path)
        self._initialized_schemas: set[str] = set()

    # ── Schema initialisation ────────────────────────────────────────

    def ensure_memory_schema(self) -> None:
        """Create the memory schema with agent_memories and agent_state tables."""
        if self.MEMORY_SCHEMA in self._initialized_schemas:
            return
        s = self.MEMORY_SCHEMA
        self.conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{s}"')
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{s}".agent_memories (
                memory_id        VARCHAR PRIMARY KEY,
                agent_id         VARCHAR NOT NULL,
                org_id           VARCHAR DEFAULT 'local',
                content          TEXT NOT NULL,
                memory_type      VARCHAR NOT NULL DEFAULT 'fact',
                importance       DOUBLE DEFAULT 0.5,
                access_count     BIGINT DEFAULT 0,
                has_embedding    BOOLEAN DEFAULT FALSE,
                metadata         VARCHAR,
                tags             VARCHAR,
                source           VARCHAR DEFAULT 'mcp',
                source_event_id  VARCHAR,
                expires_at       VARCHAR,
                created_at       VARCHAR DEFAULT (strftime(now(), '%Y-%m-%dT%H:%M:%SZ')),
                updated_at       VARCHAR DEFAULT (strftime(now(), '%Y-%m-%dT%H:%M:%SZ')),
                last_accessed_at VARCHAR DEFAULT (strftime(now(), '%Y-%m-%dT%H:%M:%SZ'))
            )
        """)
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{s}".agent_state (
                agent_id   VARCHAR NOT NULL,
                key        VARCHAR NOT NULL,
                value      VARCHAR NOT NULL,
                version    BIGINT DEFAULT 1,
                updated_at VARCHAR DEFAULT (strftime(now(), '%Y-%m-%dT%H:%M:%SZ')),
                PRIMARY KEY (agent_id, key)
            )
        """)
        self._initialized_schemas.add(self.MEMORY_SCHEMA)

    def ensure_cot_schema(self) -> None:
        """Create the chain-of-thought schema with agent_traces table."""
        if self.COT_SCHEMA in self._initialized_schemas:
            return
        s = self.COT_SCHEMA
        self.conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{s}"')
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{s}".agent_traces (
                trace_id         VARCHAR PRIMARY KEY,
                session_id       VARCHAR NOT NULL,
                agent_id         VARCHAR NOT NULL,
                org_id           VARCHAR DEFAULT 'local',
                step_number      INTEGER NOT NULL,
                step_type        VARCHAR NOT NULL DEFAULT 'observation',
                content          TEXT NOT NULL,
                input_data       VARCHAR,
                output_data      VARCHAR,
                model_name       VARCHAR,
                token_count      INTEGER DEFAULT 0,
                latency_ms       INTEGER DEFAULT 0,
                importance       DOUBLE DEFAULT 0.5,
                metadata         VARCHAR,
                prev_hash        VARCHAR NOT NULL DEFAULT '',
                hash             VARCHAR NOT NULL,
                has_embedding    BOOLEAN DEFAULT FALSE,
                created_at       VARCHAR DEFAULT (strftime(now(), '%Y-%m-%dT%H:%M:%SZ'))
            )
        """)
        self._initialized_schemas.add(self.COT_SCHEMA)

    def ensure_trigger_schema(self) -> None:
        """Create the trigger schema with trigger_registry table."""
        if self.TRIGGER_SCHEMA in self._initialized_schemas:
            return
        s = self.TRIGGER_SCHEMA
        self.conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{s}"')
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{s}".trigger_registry (
                trigger_id    VARCHAR PRIMARY KEY,
                org_id        VARCHAR DEFAULT 'local',
                name          VARCHAR NOT NULL,
                concept       VARCHAR NOT NULL,
                threshold     DOUBLE DEFAULT 0.7,
                action_type   VARCHAR NOT NULL DEFAULT 'flag_for_review',
                action_config VARCHAR DEFAULT '{{}}',
                enabled       BOOLEAN DEFAULT TRUE,
                cooldown_ms   BIGINT DEFAULT 60000,
                last_fired_at VARCHAR,
                fire_count    BIGINT DEFAULT 0,
                created_at    VARCHAR DEFAULT (strftime(now(), '%Y-%m-%dT%H:%M:%SZ')),
                updated_at    VARCHAR DEFAULT (strftime(now(), '%Y-%m-%dT%H:%M:%SZ'))
            )
        """)
        self._initialized_schemas.add(self.TRIGGER_SCHEMA)

    # ── Query interface (matches HatiDataAgent) ──────────────────────

    def query(self, sql: str, params: Optional[tuple[Any, ...]] = None) -> list[dict[str, Any]]:
        """Execute SQL and return results as a list of dicts.

        Args:
            sql: SQL query string.
            params: Optional positional parameters ($1, $2, ...).

        Returns:
            List of row dicts with column names as keys.
        """
        if params:
            result = self.conn.execute(sql, list(params))
        else:
            result = self.conn.execute(sql)

        if result.description:
            columns = [desc[0] for desc in result.description]
            return [dict(zip(columns, row)) for row in result.fetchall()]
        return []

    def execute(self, sql: str, params: Optional[tuple[Any, ...]] = None) -> int:
        """Execute a SQL statement and return affected row count.

        Args:
            sql: SQL statement.
            params: Optional positional parameters.

        Returns:
            Number of affected rows (best-effort, DuckDB may return -1).
        """
        if params:
            result = self.conn.execute(sql, list(params))
        else:
            result = self.conn.execute(sql)

        try:
            return result.fetchone()[0] if result.description else 0
        except Exception:
            return 0

    # ── Memory helpers ───────────────────────────────────────────────

    def store_memory(
        self,
        agent_id: str,
        content: str,
        memory_type: str = "fact",
        metadata: Optional[dict[str, Any]] = None,
        importance: float = 0.5,
    ) -> str:
        """Store a memory and return its UUID."""
        self.ensure_memory_schema()
        memory_id = uuid.uuid4().hex
        meta_json = json.dumps(metadata) if metadata else None
        s = self.MEMORY_SCHEMA
        self.conn.execute(
            f'INSERT INTO "{s}".agent_memories '
            f"(memory_id, agent_id, content, memory_type, importance, metadata) "
            f"VALUES ($1, $2, $3, $4, $5, $6)",
            [memory_id, agent_id, content, memory_type, importance, meta_json],
        )
        return memory_id

    def search_memory(
        self,
        agent_id: str,
        query_text: str,
        top_k: int = 10,
        memory_type: Optional[str] = None,
        min_importance: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """Search memories by ILIKE text matching."""
        self.ensure_memory_schema()
        s = self.MEMORY_SCHEMA
        conditions = [f"agent_id = '{agent_id}'"]
        words = [w.strip() for w in query_text.split() if len(w.strip()) > 2]
        if words:
            like_clauses = " OR ".join(f"content ILIKE '%{w}%'" for w in words)
            conditions.append(f"({like_clauses})")
        if memory_type:
            conditions.append(f"memory_type = '{memory_type}'")
        if min_importance is not None:
            conditions.append(f"importance >= {min_importance}")

        where = " AND ".join(conditions)
        sql = (
            f'SELECT * FROM "{s}".agent_memories '
            f"WHERE {where} "
            f"ORDER BY importance DESC, created_at DESC "
            f"LIMIT {top_k}"
        )
        return self.query(sql)

    def get_state(self, agent_id: str, key: str) -> Optional[Any]:
        """Get an agent state value by key."""
        self.ensure_memory_schema()
        s = self.MEMORY_SCHEMA
        rows = self.query(
            f'SELECT value FROM "{s}".agent_state '
            f"WHERE agent_id = $1 AND key = $2",
            (agent_id, key),
        )
        if rows:
            try:
                return json.loads(rows[0]["value"])
            except (json.JSONDecodeError, KeyError):
                return rows[0].get("value")
        return None

    def set_state(self, agent_id: str, key: str, value: Any) -> None:
        """Set an agent state value (upsert)."""
        self.ensure_memory_schema()
        s = self.MEMORY_SCHEMA
        json_val = json.dumps(value)
        self.conn.execute(
            f'INSERT INTO "{s}".agent_state (agent_id, key, value) '
            f"VALUES ($1, $2, $3) "
            f"ON CONFLICT (agent_id, key) DO UPDATE "
            f"SET value = EXCLUDED.value, "
            f'version = "{s}".agent_state.version + 1, '
            f"updated_at = strftime(now(), '%Y-%m-%dT%H:%M:%SZ')",
            [agent_id, key, json_val],
        )

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID. Returns True if deleted."""
        self.ensure_memory_schema()
        s = self.MEMORY_SCHEMA
        before = self.query(
            f'SELECT COUNT(*) AS c FROM "{s}".agent_memories WHERE memory_id = $1',
            (memory_id,),
        )
        if before and before[0]["c"] > 0:
            self.conn.execute(
                f'DELETE FROM "{s}".agent_memories WHERE memory_id = $1',
                [memory_id],
            )
            return True
        return False

    # ── Chain-of-Thought helpers ─────────────────────────────────────

    def log_reasoning_step(
        self,
        agent_id: str,
        session_id: str,
        step_type: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        importance: float = 0.5,
    ) -> str:
        """Append a reasoning step with SHA-256 hash chain."""
        self.ensure_cot_schema()
        s = self.COT_SCHEMA
        trace_id = uuid.uuid4().hex

        # Get the last hash in this session for chain integrity
        rows = self.query(
            f'SELECT hash, step_number FROM "{s}".agent_traces '
            f"WHERE session_id = $1 ORDER BY step_number DESC LIMIT 1",
            (session_id,),
        )
        prev_hash = rows[0]["hash"] if rows else ""
        step_number = (rows[0]["step_number"] + 1) if rows else 0

        # Compute SHA-256 hash: prev_hash + session_id + step_type + content
        chain_input = f"{prev_hash}{session_id}{step_type}{content}"
        new_hash = hashlib.sha256(chain_input.encode()).hexdigest()

        meta_json = json.dumps(metadata) if metadata else None
        self.conn.execute(
            f'INSERT INTO "{s}".agent_traces '
            f"(trace_id, session_id, agent_id, step_number, step_type, content, "
            f"importance, metadata, prev_hash, hash) "
            f"VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
            [trace_id, session_id, agent_id, step_number, step_type, content,
             importance, meta_json, prev_hash, new_hash],
        )
        return trace_id

    def replay_session(
        self,
        session_id: str,
        verify_chain: bool = False,
    ) -> dict[str, Any]:
        """Replay all reasoning traces for a session."""
        self.ensure_cot_schema()
        s = self.COT_SCHEMA
        rows = self.query(
            f'SELECT * FROM "{s}".agent_traces '
            f"WHERE session_id = $1 ORDER BY step_number ASC",
            (session_id,),
        )

        chain_valid = None
        if verify_chain and rows:
            chain_valid = True
            for i, row in enumerate(rows):
                expected_prev = rows[i - 1]["hash"] if i > 0 else ""
                if row["prev_hash"] != expected_prev:
                    chain_valid = False
                    break
                chain_input = (
                    f"{row['prev_hash']}{row['session_id']}"
                    f"{row['step_type']}{row['content']}"
                )
                expected_hash = hashlib.sha256(chain_input.encode()).hexdigest()
                if row["hash"] != expected_hash:
                    chain_valid = False
                    break

        return {
            "session_id": session_id,
            "steps": rows,
            "step_count": len(rows),
            "chain_valid": chain_valid,
        }

    def list_sessions(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
        since: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List distinct CoT sessions with metadata."""
        self.ensure_cot_schema()
        s = self.COT_SCHEMA
        conditions = []
        if agent_id:
            conditions.append(f"agent_id = '{agent_id}'")
        if since:
            conditions.append(f"created_at >= '{since}'")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        return self.query(
            f'SELECT session_id, agent_id, MIN(created_at) AS started_at, '
            f"MAX(created_at) AS last_step_at, COUNT(*) AS step_count "
            f'FROM "{s}".agent_traces {where} '
            f"GROUP BY session_id, agent_id "
            f"ORDER BY started_at DESC LIMIT {limit}"
        )

    # ── Trigger helpers ──────────────────────────────────────────────

    def register_trigger(
        self,
        name: str,
        concept: str,
        threshold: float = 0.7,
        action_type: str = "flag_for_review",
        action_config: Optional[dict[str, Any]] = None,
    ) -> str:
        """Register a new semantic trigger."""
        self.ensure_trigger_schema()
        trigger_id = uuid.uuid4().hex
        s = self.TRIGGER_SCHEMA
        config_json = json.dumps(action_config) if action_config else "{}"
        self.conn.execute(
            f'INSERT INTO "{s}".trigger_registry '
            f"(trigger_id, name, concept, threshold, action_type, action_config) "
            f"VALUES ($1, $2, $3, $4, $5, $6)",
            [trigger_id, name, concept, threshold, action_type, config_json],
        )
        return trigger_id

    def list_triggers(self, status: Optional[str] = None) -> list[dict[str, Any]]:
        """List registered triggers."""
        self.ensure_trigger_schema()
        s = self.TRIGGER_SCHEMA
        where = ""
        if status == "active":
            where = "WHERE enabled = TRUE"
        elif status == "inactive":
            where = "WHERE enabled = FALSE"
        return self.query(
            f'SELECT * FROM "{s}".trigger_registry {where} ORDER BY created_at DESC'
        )

    def delete_trigger(self, trigger_id: str) -> bool:
        """Soft-delete a trigger (set enabled=false)."""
        self.ensure_trigger_schema()
        s = self.TRIGGER_SCHEMA
        rows = self.query(
            f'SELECT trigger_id FROM "{s}".trigger_registry WHERE trigger_id = $1',
            (trigger_id,),
        )
        if rows:
            self.conn.execute(
                f'UPDATE "{s}".trigger_registry SET enabled = FALSE, '
                f"updated_at = strftime(now(), '%Y-%m-%dT%H:%M:%SZ') "
                f"WHERE trigger_id = $1",
                [trigger_id],
            )
            return True
        return False

    def test_trigger(self, trigger_id: str, content: str) -> dict[str, Any]:
        """Test if content matches a trigger's concept (simplified text match)."""
        self.ensure_trigger_schema()
        s = self.TRIGGER_SCHEMA
        rows = self.query(
            f'SELECT * FROM "{s}".trigger_registry WHERE trigger_id = $1',
            (trigger_id,),
        )
        if not rows:
            return {"matched": False, "error": "Trigger not found"}

        trigger = rows[0]
        concept = trigger["concept"].lower()
        content_lower = content.lower()

        # Simplified matching: check if concept keywords appear in content
        concept_words = [w for w in concept.split() if len(w) > 2]
        matched_words = [w for w in concept_words if w in content_lower]
        score = len(matched_words) / max(len(concept_words), 1)

        return {
            "matched": score >= trigger["threshold"],
            "score": round(score, 4),
            "threshold": trigger["threshold"],
            "trigger_name": trigger["name"],
            "concept": trigger["concept"],
        }

    # ── Branch helpers ───────────────────────────────────────────────

    def branch_create(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        ttl_seconds: int = 3600,
    ) -> dict[str, Any]:
        """Create an isolated branch schema with views of all main tables."""
        branch_id = uuid.uuid4().hex[:12]
        schema_name = f"branch_{branch_id}"
        display_name = name or schema_name
        self.conn.execute(f'CREATE SCHEMA "{schema_name}"')

        # Create views for all tables in the main schema
        tables = self.query(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' AND table_type = 'BASE TABLE'"
        )
        for t in tables:
            tbl = t["table_name"]
            self.conn.execute(
                f'CREATE VIEW "{schema_name}"."{tbl}" AS SELECT * FROM main."{tbl}"'
            )

        return {
            "branch_id": branch_id,
            "schema_name": schema_name,
            "name": display_name,
            "description": description or "",
            "table_count": len(tables),
            "ttl_seconds": ttl_seconds,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def branch_query(self, branch_id: str, sql: str) -> list[dict[str, Any]]:
        """Execute SQL within a branch's schema context."""
        schema_name = f"branch_{branch_id}"
        # Verify the branch exists
        schemas = self.query(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name = $1",
            (schema_name,),
        )
        if not schemas:
            return [{"error": f"Branch {branch_id} not found"}]

        self.conn.execute(f"SET search_path = '{schema_name},main'")
        try:
            return self.query(sql)
        finally:
            self.conn.execute("SET search_path = 'main'")

    def branch_merge(
        self,
        branch_id: str,
        strategy: str = "branch_wins",
    ) -> dict[str, Any]:
        """Merge materialized branch tables back to main."""
        schema_name = f"branch_{branch_id}"
        schemas = self.query(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name = $1",
            (schema_name,),
        )
        if not schemas:
            return {"error": f"Branch {branch_id} not found", "merged": 0}

        # Find tables (not views) in the branch schema — these were materialized
        tables = self.query(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = $1 AND table_type = 'BASE TABLE'",
            (schema_name,),
        )

        merged = 0
        for t in tables:
            tbl = t["table_name"]
            if strategy == "branch_wins":
                self.conn.execute(f'DROP TABLE IF EXISTS main."{tbl}"')
                self.conn.execute(
                    f'CREATE TABLE main."{tbl}" AS SELECT * FROM "{schema_name}"."{tbl}"'
                )
                merged += 1
            elif strategy == "main_wins":
                # Skip — main keeps its version
                continue

        # Clean up the branch
        self.conn.execute(f'DROP SCHEMA "{schema_name}" CASCADE')

        return {
            "branch_id": branch_id,
            "strategy": strategy,
            "merged": merged,
            "status": "completed",
        }

    def branch_discard(self, branch_id: str) -> bool:
        """Drop a branch schema entirely."""
        schema_name = f"branch_{branch_id}"
        schemas = self.query(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name = $1",
            (schema_name,),
        )
        if not schemas:
            return False
        self.conn.execute(f'DROP SCHEMA "{schema_name}" CASCADE')
        return True

    def branch_list(self, status: Optional[str] = None) -> list[dict[str, Any]]:
        """List all branch schemas."""
        rows = self.query(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name LIKE 'branch_%'"
        )
        branches = []
        for r in rows:
            schema_name = r["schema_name"]
            branch_id = schema_name.replace("branch_", "", 1)

            # Count tables vs views in the branch
            table_info = self.query(
                "SELECT table_type, COUNT(*) AS cnt "
                "FROM information_schema.tables "
                "WHERE table_schema = $1 GROUP BY table_type",
                (schema_name,),
            )
            views = 0
            tables = 0
            for ti in table_info:
                if ti["table_type"] == "VIEW":
                    views += ti["cnt"]
                else:
                    tables += ti["cnt"]

            branches.append({
                "branch_id": branch_id,
                "schema_name": schema_name,
                "materialized_tables": tables,
                "views": views,
                "status": "active",
            })
        return branches

    # ── Lifecycle ────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the DuckDB connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self) -> LocalDuckDBEngine:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

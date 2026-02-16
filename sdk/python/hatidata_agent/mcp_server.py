"""MCP server for HatiData agent access — 23 tools across 5 categories.

Exposes HatiData as an MCP (Model Context Protocol) server, allowing
Claude and other MCP-compatible agents to query the data warehouse
directly.

**SQL tools** (6): query, read_query, list_schemas, list_tables,
describe_table, get_usage_stats

**Memory tools** (5): store_memory, search_memory, get_agent_state,
set_agent_state, delete_memory

**Chain-of-Thought tools** (3): log_reasoning_step, replay_decision,
get_session_history

**Trigger tools** (4): register_trigger, list_triggers, delete_trigger,
test_trigger

**Branch tools** (5): branch_create, branch_query, branch_merge,
branch_discard, branch_list

Usage::

    # Cloud mode — connects to running HatiData proxy
    hatidata-mcp-server --host localhost --port 5439

    # Local mode — embedded DuckDB, no proxy required
    hatidata-mcp-server --local

    # With API key for cloud auth
    HATIDATA_API_KEY=hd_live_xxx hatidata-mcp-server --host proxy.internal
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Optional, Protocol


# ── Backend protocol ─────────────────────────────────────────────────
# Both HatiDataAgent and LocalDuckDBEngine conform to this duck-typed
# interface, so tool handlers work identically in cloud and local modes.


class _Backend(Protocol):
    agent_id: str

    def query(self, sql: str, params: Optional[tuple[Any, ...]] = None) -> list[dict[str, Any]]: ...
    def execute(self, sql: str, params: Optional[tuple[Any, ...]] = None) -> int: ...


# ── Tool definitions ─────────────────────────────────────────────────


def _sql_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "query",
            "description": (
                "Execute a SQL query against the HatiData warehouse. "
                "Returns results as a JSON array of objects. "
                "Supports Snowflake-compatible SQL syntax."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "The SQL query to execute"},
                },
                "required": ["sql"],
            },
        },
        {
            "name": "read_query",
            "description": (
                "Execute a read-only SQL query. The query is wrapped to prevent "
                "mutations. Use this for SELECT statements when you want extra safety."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "A SELECT SQL query"},
                },
                "required": ["sql"],
            },
        },
        {
            "name": "list_schemas",
            "description": "List all schemas (namespaces) in the database.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "list_tables",
            "description": "List all tables, optionally filtered by schema.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "schema": {
                        "type": "string",
                        "description": "Schema to filter by (default: all schemas)",
                    },
                },
            },
        },
        {
            "name": "describe_table",
            "description": "Get the column names, types, and nullability for a table.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to describe",
                    },
                },
                "required": ["table_name"],
            },
        },
        {
            "name": "get_usage_stats",
            "description": (
                "Get row counts and estimated sizes for all tables. "
                "Useful for understanding the data landscape."
            ),
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]


def _memory_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "store_memory",
            "description": (
                "Store a memory (fact, observation, instruction) in the agent's "
                "persistent memory. Returns the memory_id for later retrieval."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The memory content text"},
                    "memory_type": {
                        "type": "string",
                        "description": "Type: fact, observation, instruction, preference, episode",
                        "default": "fact",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional key-value metadata",
                    },
                    "importance": {
                        "type": "number",
                        "description": "Importance score 0.0-1.0 (default 0.5)",
                        "default": 0.5,
                    },
                },
                "required": ["content"],
            },
        },
        {
            "name": "search_memory",
            "description": (
                "Search the agent's stored memories by text similarity. "
                "Returns matches ranked by importance and recency."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "top_k": {
                        "type": "integer",
                        "description": "Maximum results (default 10)",
                        "default": 10,
                    },
                    "memory_type": {
                        "type": "string",
                        "description": "Filter by memory type",
                    },
                    "min_importance": {
                        "type": "number",
                        "description": "Minimum importance threshold",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_agent_state",
            "description": "Get a persistent state value by key for this agent.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "The state key"},
                },
                "required": ["key"],
            },
        },
        {
            "name": "set_agent_state",
            "description": "Set a persistent state value for this agent. Value is JSON-encoded.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "The state key"},
                    "value": {"description": "The value to store (any JSON type)"},
                },
                "required": ["key", "value"],
            },
        },
        {
            "name": "delete_memory",
            "description": "Delete a specific memory by its ID.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "description": "The memory UUID to delete"},
                },
                "required": ["memory_id"],
            },
        },
    ]


def _cot_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "log_reasoning_step",
            "description": (
                "Log a reasoning step in a chain-of-thought session. "
                "Steps are hash-chained (SHA-256) for tamper-evidence. "
                "Step types: observation, hypothesis, analysis, decision, "
                "action, reflection, planning, evaluation, retrieval, "
                "synthesis, delegation, error."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Reasoning session ID"},
                    "step_type": {
                        "type": "string",
                        "description": "Step type (observation, hypothesis, decision, etc.)",
                        "default": "observation",
                    },
                    "content": {"type": "string", "description": "The reasoning step content"},
                    "metadata": {"type": "object", "description": "Optional metadata"},
                    "importance": {
                        "type": "number",
                        "description": "Importance 0.0-1.0",
                        "default": 0.5,
                    },
                },
                "required": ["session_id", "content"],
            },
        },
        {
            "name": "replay_decision",
            "description": (
                "Replay all reasoning steps for a session in order. "
                "Optionally verifies the SHA-256 hash chain integrity."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID to replay"},
                    "verify_chain": {
                        "type": "boolean",
                        "description": "Verify hash chain integrity (default false)",
                        "default": False,
                    },
                },
                "required": ["session_id"],
            },
        },
        {
            "name": "get_session_history",
            "description": "List recent chain-of-thought sessions with metadata.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max sessions to return (default 50)",
                        "default": 50,
                    },
                    "agent_id": {"type": "string", "description": "Filter by agent ID"},
                    "since": {
                        "type": "string",
                        "description": "ISO timestamp to filter from",
                    },
                },
            },
        },
    ]


def _trigger_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "register_trigger",
            "description": (
                "Register a semantic trigger that fires when content matches a concept. "
                "Actions: flag_for_review, webhook, agent_notify, write_event."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Human-readable trigger name"},
                    "concept": {
                        "type": "string",
                        "description": "The concept/topic to watch for",
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Match threshold 0.0-1.0 (default 0.7)",
                        "default": 0.7,
                    },
                    "action_type": {
                        "type": "string",
                        "description": "Action: flag_for_review, webhook, agent_notify, write_event",
                        "default": "flag_for_review",
                    },
                    "action_config": {
                        "type": "object",
                        "description": "Action configuration (e.g. webhook URL)",
                    },
                },
                "required": ["name", "concept"],
            },
        },
        {
            "name": "list_triggers",
            "description": "List registered semantic triggers.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter: active, inactive, or all (default all)",
                    },
                },
            },
        },
        {
            "name": "delete_trigger",
            "description": "Disable (soft-delete) a semantic trigger by ID.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "trigger_id": {"type": "string", "description": "Trigger UUID to disable"},
                },
                "required": ["trigger_id"],
            },
        },
        {
            "name": "test_trigger",
            "description": "Test if content would match a trigger's concept.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "trigger_id": {"type": "string", "description": "Trigger ID to test against"},
                    "content": {"type": "string", "description": "Content to evaluate"},
                },
                "required": ["trigger_id", "content"],
            },
        },
    ]


def _branch_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "branch_create",
            "description": (
                "Create an isolated data branch. All main tables are visible as "
                "views; writes are copy-on-write materialized. Use for safe "
                "experimentation without affecting production data."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Branch display name"},
                    "description": {"type": "string", "description": "Branch description"},
                    "ttl_seconds": {
                        "type": "integer",
                        "description": "Auto-expire after N seconds (default 3600)",
                        "default": 3600,
                    },
                },
            },
        },
        {
            "name": "branch_query",
            "description": "Execute SQL within a branch's isolated context.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "branch_id": {"type": "string", "description": "Branch ID"},
                    "sql": {"type": "string", "description": "SQL to execute in the branch"},
                },
                "required": ["branch_id", "sql"],
            },
        },
        {
            "name": "branch_merge",
            "description": (
                "Merge materialized branch tables back to main. "
                "Strategies: branch_wins (default), main_wins."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "branch_id": {"type": "string", "description": "Branch ID to merge"},
                    "strategy": {
                        "type": "string",
                        "description": "Merge strategy: branch_wins or main_wins",
                        "default": "branch_wins",
                    },
                },
                "required": ["branch_id"],
            },
        },
        {
            "name": "branch_discard",
            "description": "Discard a branch and all its data.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "branch_id": {"type": "string", "description": "Branch ID to discard"},
                },
                "required": ["branch_id"],
            },
        },
        {
            "name": "branch_list",
            "description": "List all active branches with their table counts.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by status"},
                },
            },
        },
    ]


def create_tools() -> list[dict[str, Any]]:
    """Return all 23 MCP tool definitions."""
    return _sql_tools() + _memory_tools() + _cot_tools() + _trigger_tools() + _branch_tools()


# ── Tool handlers ────────────────────────────────────────────────────


def _ok(data: Any) -> dict[str, Any]:
    """Wrap a result in MCP content format."""
    return {"content": [{"type": "text", "text": json.dumps(data, default=str)}]}


def _err(msg: str) -> dict[str, Any]:
    """Wrap an error in MCP content format."""
    return {"content": [{"type": "text", "text": msg}], "isError": True}


def handle_tool_call(
    backend: Any,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    is_local: bool = False,
) -> dict[str, Any]:
    """Handle an MCP tool call and return the result."""
    try:
        # ── SQL tools ────────────────────────────────────────────────
        if tool_name == "query":
            rows = backend.query(arguments["sql"])
            return _ok(rows)

        elif tool_name == "read_query":
            sql = arguments["sql"].strip().rstrip(";")
            rows = backend.query(f"SELECT * FROM ({sql}) AS _readonly")
            return _ok(rows)

        elif tool_name == "list_schemas":
            rows = backend.query(
                "SELECT schema_name FROM information_schema.schemata ORDER BY schema_name"
            )
            return _ok([r["schema_name"] for r in rows])

        elif tool_name == "list_tables":
            schema = arguments.get("schema")
            if schema:
                rows = backend.query(
                    "SELECT table_schema, table_name, table_type "
                    "FROM information_schema.tables "
                    f"WHERE table_schema = '{schema}' ORDER BY table_name"
                )
            else:
                rows = backend.query(
                    "SELECT table_schema, table_name, table_type "
                    "FROM information_schema.tables "
                    "WHERE table_schema NOT IN ('information_schema', 'pg_catalog') "
                    "ORDER BY table_schema, table_name"
                )
            return _ok(rows)

        elif tool_name == "describe_table":
            table = arguments["table_name"]
            rows = backend.query(
                f"SELECT column_name, data_type, is_nullable "
                f"FROM information_schema.columns "
                f"WHERE table_name = '{table}' ORDER BY ordinal_position"
            )
            return _ok(rows)

        elif tool_name == "get_usage_stats":
            rows = backend.query(
                "SELECT table_schema, table_name, "
                "estimated_size, column_count "
                "FROM duckdb_tables() "
                "ORDER BY estimated_size DESC"
            )
            return _ok(rows)

        # ── Memory tools ─────────────────────────────────────────────
        elif tool_name == "store_memory":
            if is_local:
                mid = backend.store_memory(
                    agent_id=backend.agent_id,
                    content=arguments["content"],
                    memory_type=arguments.get("memory_type", "fact"),
                    metadata=arguments.get("metadata"),
                    importance=arguments.get("importance", 0.5),
                )
            else:
                mid = backend.store_memory(
                    content=arguments["content"],
                    memory_type=arguments.get("memory_type", "fact"),
                    metadata=arguments.get("metadata"),
                    importance=arguments.get("importance", 0.5),
                )
            return _ok({"memory_id": mid})

        elif tool_name == "search_memory":
            if is_local:
                rows = backend.search_memory(
                    agent_id=backend.agent_id,
                    query_text=arguments["query"],
                    top_k=arguments.get("top_k", 10),
                    memory_type=arguments.get("memory_type"),
                    min_importance=arguments.get("min_importance"),
                )
            else:
                rows = backend.search_memory(
                    query=arguments["query"],
                    top_k=arguments.get("top_k", 10),
                    memory_type=arguments.get("memory_type"),
                    min_importance=arguments.get("min_importance"),
                )
            return _ok(rows)

        elif tool_name == "get_agent_state":
            if is_local:
                val = backend.get_state(backend.agent_id, arguments["key"])
            else:
                val = backend.get_state(arguments["key"])
            return _ok({"key": arguments["key"], "value": val})

        elif tool_name == "set_agent_state":
            if is_local:
                backend.set_state(backend.agent_id, arguments["key"], arguments["value"])
            else:
                backend.set_state(arguments["key"], arguments["value"])
            return _ok({"key": arguments["key"], "status": "ok"})

        elif tool_name == "delete_memory":
            if is_local:
                deleted = backend.delete_memory(arguments["memory_id"])
            else:
                deleted = backend.delete_memory(arguments["memory_id"])
            return _ok({"deleted": deleted, "memory_id": arguments["memory_id"]})

        # ── Chain-of-Thought tools ───────────────────────────────────
        elif tool_name == "log_reasoning_step":
            if is_local:
                tid = backend.log_reasoning_step(
                    agent_id=backend.agent_id,
                    session_id=arguments["session_id"],
                    step_type=arguments.get("step_type", "observation"),
                    content=arguments["content"],
                    metadata=arguments.get("metadata"),
                    importance=arguments.get("importance", 0.5),
                )
            else:
                # Cloud mode: insert via SQL
                import hashlib
                import uuid
                schema = "_hatidata_cot_local"
                backend.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
                backend.execute(f"""
                    CREATE TABLE IF NOT EXISTS "{schema}".agent_traces (
                        trace_id VARCHAR PRIMARY KEY, session_id VARCHAR NOT NULL,
                        agent_id VARCHAR NOT NULL, org_id VARCHAR DEFAULT 'local',
                        step_number INTEGER NOT NULL, step_type VARCHAR NOT NULL,
                        content TEXT NOT NULL, input_data VARCHAR, output_data VARCHAR,
                        model_name VARCHAR, token_count INTEGER DEFAULT 0,
                        latency_ms INTEGER DEFAULT 0, importance DOUBLE DEFAULT 0.5,
                        metadata VARCHAR, prev_hash VARCHAR NOT NULL DEFAULT '',
                        hash VARCHAR NOT NULL, has_embedding BOOLEAN DEFAULT FALSE,
                        created_at VARCHAR DEFAULT (strftime(now(), '%Y-%m-%dT%H:%M:%SZ'))
                    )
                """)
                session_id = arguments["session_id"]
                step_type = arguments.get("step_type", "observation")
                content = arguments["content"]
                rows = backend.query(
                    f'SELECT hash, step_number FROM "{schema}".agent_traces '
                    f"WHERE session_id = '{session_id}' ORDER BY step_number DESC LIMIT 1"
                )
                prev_hash = rows[0]["hash"] if rows else ""
                step_number = (rows[0]["step_number"] + 1) if rows else 0
                chain_input = f"{prev_hash}{session_id}{step_type}{content}"
                new_hash = hashlib.sha256(chain_input.encode()).hexdigest()
                tid = uuid.uuid4().hex
                meta_json = json.dumps(arguments.get("metadata")) if arguments.get("metadata") else None
                backend.execute(
                    f'INSERT INTO "{schema}".agent_traces '
                    f"(trace_id, session_id, agent_id, step_number, step_type, "
                    f"content, importance, metadata, prev_hash, hash) "
                    f"VALUES ('{tid}', '{session_id}', '{backend.agent_id}', "
                    f"{step_number}, '{step_type}', '{content.replace(chr(39), chr(39)+chr(39))}', "
                    f"{arguments.get('importance', 0.5)}, "
                    f"{'NULL' if meta_json is None else chr(39) + meta_json + chr(39)}, "
                    f"'{prev_hash}', '{new_hash}')"
                )
            return _ok({"trace_id": tid, "session_id": arguments["session_id"]})

        elif tool_name == "replay_decision":
            if is_local:
                result = backend.replay_session(
                    session_id=arguments["session_id"],
                    verify_chain=arguments.get("verify_chain", False),
                )
            else:
                schema = "_hatidata_cot_local"
                rows = backend.query(
                    f'SELECT * FROM "{schema}".agent_traces '
                    f"WHERE session_id = '{arguments['session_id']}' "
                    f"ORDER BY step_number ASC"
                )
                chain_valid = None
                if arguments.get("verify_chain") and rows:
                    import hashlib
                    chain_valid = True
                    for i, row in enumerate(rows):
                        expected_prev = rows[i - 1]["hash"] if i > 0 else ""
                        if row["prev_hash"] != expected_prev:
                            chain_valid = False
                            break
                        ci = f"{row['prev_hash']}{row['session_id']}{row['step_type']}{row['content']}"
                        if row["hash"] != hashlib.sha256(ci.encode()).hexdigest():
                            chain_valid = False
                            break
                result = {
                    "session_id": arguments["session_id"],
                    "steps": rows,
                    "step_count": len(rows),
                    "chain_valid": chain_valid,
                }
            return _ok(result)

        elif tool_name == "get_session_history":
            if is_local:
                result = backend.list_sessions(
                    agent_id=arguments.get("agent_id"),
                    limit=arguments.get("limit", 50),
                    since=arguments.get("since"),
                )
            else:
                schema = "_hatidata_cot_local"
                conditions = []
                if arguments.get("agent_id"):
                    conditions.append(f"agent_id = '{arguments['agent_id']}'")
                if arguments.get("since"):
                    conditions.append(f"created_at >= '{arguments['since']}'")
                where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
                limit = arguments.get("limit", 50)
                result = backend.query(
                    f'SELECT session_id, agent_id, MIN(created_at) AS started_at, '
                    f"MAX(created_at) AS last_step_at, COUNT(*) AS step_count "
                    f'FROM "{schema}".agent_traces {where} '
                    f"GROUP BY session_id, agent_id "
                    f"ORDER BY started_at DESC LIMIT {limit}"
                )
            return _ok(result)

        # ── Trigger tools ────────────────────────────────────────────
        elif tool_name == "register_trigger":
            if is_local:
                tid = backend.register_trigger(
                    name=arguments["name"],
                    concept=arguments["concept"],
                    threshold=arguments.get("threshold", 0.7),
                    action_type=arguments.get("action_type", "flag_for_review"),
                    action_config=arguments.get("action_config"),
                )
            else:
                import uuid
                schema = "_hatidata_triggers_local"
                backend.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
                backend.execute(f"""
                    CREATE TABLE IF NOT EXISTS "{schema}".trigger_registry (
                        trigger_id VARCHAR PRIMARY KEY, org_id VARCHAR DEFAULT 'local',
                        name VARCHAR NOT NULL, concept VARCHAR NOT NULL,
                        threshold DOUBLE DEFAULT 0.7, action_type VARCHAR NOT NULL,
                        action_config VARCHAR DEFAULT '{{}}', enabled BOOLEAN DEFAULT TRUE,
                        cooldown_ms BIGINT DEFAULT 60000, last_fired_at VARCHAR,
                        fire_count BIGINT DEFAULT 0,
                        created_at VARCHAR DEFAULT (strftime(now(), '%Y-%m-%dT%H:%M:%SZ')),
                        updated_at VARCHAR DEFAULT (strftime(now(), '%Y-%m-%dT%H:%M:%SZ'))
                    )
                """)
                tid = uuid.uuid4().hex
                config = json.dumps(arguments.get("action_config") or {})
                backend.execute(
                    f'INSERT INTO "{schema}".trigger_registry '
                    f"(trigger_id, name, concept, threshold, action_type, action_config) "
                    f"VALUES ('{tid}', '{arguments['name']}', '{arguments['concept']}', "
                    f"{arguments.get('threshold', 0.7)}, "
                    f"'{arguments.get('action_type', 'flag_for_review')}', '{config}')"
                )
            return _ok({"trigger_id": tid, "name": arguments["name"]})

        elif tool_name == "list_triggers":
            if is_local:
                result = backend.list_triggers(status=arguments.get("status"))
            else:
                schema = "_hatidata_triggers_local"
                where = ""
                if arguments.get("status") == "active":
                    where = "WHERE enabled = TRUE"
                elif arguments.get("status") == "inactive":
                    where = "WHERE enabled = FALSE"
                result = backend.query(
                    f'SELECT * FROM "{schema}".trigger_registry {where} ORDER BY created_at DESC'
                )
            return _ok(result)

        elif tool_name == "delete_trigger":
            if is_local:
                deleted = backend.delete_trigger(arguments["trigger_id"])
            else:
                schema = "_hatidata_triggers_local"
                backend.execute(
                    f'UPDATE "{schema}".trigger_registry SET enabled = FALSE, '
                    f"updated_at = strftime(now(), '%Y-%m-%dT%H:%M:%SZ') "
                    f"WHERE trigger_id = '{arguments['trigger_id']}'"
                )
                deleted = True
            return _ok({"deleted": deleted, "trigger_id": arguments["trigger_id"]})

        elif tool_name == "test_trigger":
            if is_local:
                result = backend.test_trigger(arguments["trigger_id"], arguments["content"])
            else:
                schema = "_hatidata_triggers_local"
                rows = backend.query(
                    f'SELECT * FROM "{schema}".trigger_registry '
                    f"WHERE trigger_id = '{arguments['trigger_id']}'"
                )
                if not rows:
                    return _ok({"matched": False, "error": "Trigger not found"})
                trigger = rows[0]
                concept = trigger["concept"].lower()
                content_lower = arguments["content"].lower()
                concept_words = [w for w in concept.split() if len(w) > 2]
                matched_words = [w for w in concept_words if w in content_lower]
                score = len(matched_words) / max(len(concept_words), 1)
                result = {
                    "matched": score >= trigger["threshold"],
                    "score": round(score, 4),
                    "threshold": trigger["threshold"],
                    "trigger_name": trigger["name"],
                }
            return _ok(result)

        # ── Branch tools ─────────────────────────────────────────────
        elif tool_name == "branch_create":
            if is_local:
                result = backend.branch_create(
                    name=arguments.get("name"),
                    description=arguments.get("description"),
                    ttl_seconds=arguments.get("ttl_seconds", 3600),
                )
            else:
                import uuid
                branch_id = uuid.uuid4().hex[:12]
                schema_name = f"branch_{branch_id}"
                backend.execute(f'CREATE SCHEMA "{schema_name}"')
                tables = backend.query(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'main' AND table_type = 'BASE TABLE'"
                )
                for t in tables:
                    tbl = t["table_name"]
                    backend.execute(
                        f'CREATE VIEW "{schema_name}"."{tbl}" AS SELECT * FROM main."{tbl}"'
                    )
                result = {
                    "branch_id": branch_id,
                    "schema_name": schema_name,
                    "name": arguments.get("name", schema_name),
                    "table_count": len(tables),
                }
            return _ok(result)

        elif tool_name == "branch_query":
            if is_local:
                result = backend.branch_query(arguments["branch_id"], arguments["sql"])
            else:
                schema_name = f"branch_{arguments['branch_id']}"
                backend.execute(f"SET search_path = '{schema_name},main'")
                try:
                    result = backend.query(arguments["sql"])
                finally:
                    backend.execute("SET search_path = 'main'")
            return _ok(result)

        elif tool_name == "branch_merge":
            if is_local:
                result = backend.branch_merge(
                    arguments["branch_id"],
                    strategy=arguments.get("strategy", "branch_wins"),
                )
            else:
                schema_name = f"branch_{arguments['branch_id']}"
                tables = backend.query(
                    "SELECT table_name FROM information_schema.tables "
                    f"WHERE table_schema = '{schema_name}' AND table_type = 'BASE TABLE'"
                )
                strategy = arguments.get("strategy", "branch_wins")
                merged = 0
                for t in tables:
                    tbl = t["table_name"]
                    if strategy == "branch_wins":
                        backend.execute(f'DROP TABLE IF EXISTS main."{tbl}"')
                        backend.execute(
                            f'CREATE TABLE main."{tbl}" AS '
                            f'SELECT * FROM "{schema_name}"."{tbl}"'
                        )
                        merged += 1
                backend.execute(f'DROP SCHEMA "{schema_name}" CASCADE')
                result = {"branch_id": arguments["branch_id"], "merged": merged, "status": "completed"}
            return _ok(result)

        elif tool_name == "branch_discard":
            if is_local:
                ok = backend.branch_discard(arguments["branch_id"])
            else:
                schema_name = f"branch_{arguments['branch_id']}"
                backend.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
                ok = True
            return _ok({"discarded": ok, "branch_id": arguments["branch_id"]})

        elif tool_name == "branch_list":
            if is_local:
                result = backend.branch_list(status=arguments.get("status"))
            else:
                rows = backend.query(
                    "SELECT schema_name FROM information_schema.schemata "
                    "WHERE schema_name LIKE 'branch_%'"
                )
                result = []
                for r in rows:
                    sn = r["schema_name"]
                    bid = sn.replace("branch_", "", 1)
                    ti = backend.query(
                        "SELECT table_type, COUNT(*) AS cnt "
                        "FROM information_schema.tables "
                        f"WHERE table_schema = '{sn}' GROUP BY table_type"
                    )
                    views = sum(x["cnt"] for x in ti if x["table_type"] == "VIEW")
                    tables = sum(x["cnt"] for x in ti if x["table_type"] != "VIEW")
                    result.append({
                        "branch_id": bid,
                        "schema_name": sn,
                        "materialized_tables": tables,
                        "views": views,
                    })
            return _ok(result)

        else:
            return _err(f"Unknown tool: {tool_name}")

    except Exception as e:
        return _err(f"Error: {e}")


# ── Stdio JSON-RPC transport ────────────────────────────────────────


def run_stdio_server(backend: Any, *, is_local: bool = False) -> None:
    """Run MCP server over stdio transport (JSON-RPC 2.0)."""
    tools = create_tools()

    server_info = {
        "name": "hatidata",
        "version": "0.2.0",
        "capabilities": {"tools": {}},
    }

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = request.get("method", "")
        req_id = request.get("id")

        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": server_info,
                    "capabilities": server_info["capabilities"],
                },
            }

        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": tools},
            }

        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = handle_tool_call(backend, tool_name, arguments, is_local=is_local)
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result,
            }

        elif method == "notifications/initialized":
            continue

        else:
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


# ── CLI entry point ──────────────────────────────────────────────────


def main() -> None:
    """Entry point for the ``hatidata-mcp-server`` CLI."""
    parser = argparse.ArgumentParser(
        description="HatiData MCP Server — 23 tools for agent data access"
    )
    parser.add_argument("--host", default="localhost", help="Proxy host (default: localhost)")
    parser.add_argument("--port", type=int, default=5439, help="Proxy port (default: 5439)")
    parser.add_argument("--agent-id", default="mcp-agent", help="Agent identifier")
    parser.add_argument("--database", default="hatidata", help="Database name")
    parser.add_argument("--user", default="agent", help="Username")
    parser.add_argument("--password", default="", help="Password (or use HATIDATA_API_KEY env)")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Run in local mode with embedded DuckDB (no proxy required)",
    )
    parser.add_argument(
        "--db-path",
        default=".hati/local.duckdb",
        help="DuckDB file path for local mode (default: .hati/local.duckdb)",
    )
    args = parser.parse_args()

    if args.local:
        from hatidata_agent.local_engine import LocalDuckDBEngine

        backend = LocalDuckDBEngine(db_path=args.db_path)
        backend.agent_id = args.agent_id  # type: ignore[attr-defined]
        _log(f"Local mode: {args.db_path} (agent: {args.agent_id})")
        run_stdio_server(backend, is_local=True)
    else:
        from hatidata_agent.client import HatiDataAgent

        # API key: explicit password > env var > empty (dev mode)
        password = args.password or os.environ.get("HATIDATA_API_KEY", "")

        agent = HatiDataAgent(
            host=args.host,
            port=args.port,
            agent_id=args.agent_id,
            framework="mcp",
            database=args.database,
            user=args.user,
            password=password,
            cloud_key=os.environ.get("HATIDATA_CLOUD_KEY"),
        )
        _log(f"Cloud mode: {args.host}:{args.port} (agent: {args.agent_id})")
        run_stdio_server(agent, is_local=False)


def _log(msg: str) -> None:
    """Log to stderr (stdout is reserved for JSON-RPC)."""
    print(f"[hatidata-mcp] {msg}", file=sys.stderr)


if __name__ == "__main__":
    main()

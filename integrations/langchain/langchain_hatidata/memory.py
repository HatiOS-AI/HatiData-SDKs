"""LangChain Memory backed by HatiData.

Persists conversation history to HatiData's SQL engine, enabling
cross-session memory for agents with full audit trail.

Usage::

    from langchain_hatidata import HatiDataMemory
    from langchain.chains import ConversationChain

    memory = HatiDataMemory(
        host="proxy.internal",
        agent_id="chat-agent",
        session_id="session-001",
    )

    chain = ConversationChain(llm=llm, memory=memory)
    chain.run("What is HatiData?")
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from langchain_core.memory import BaseMemory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from hatidata_agent import HatiDataAgent


class HatiDataMemory(BaseMemory):
    """LangChain memory that persists conversation history to HatiData.

    Stores messages in a SQL table with agent identification for
    per-agent billing and audit. Supports both buffer-style and
    summary-style retrieval.

    The memory table is auto-created on first use::

        CREATE TABLE IF NOT EXISTS _hatidata_memory (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """

    memory_key: str = "history"
    input_key: str = "input"
    output_key: str = "output"
    return_messages: bool = False
    _agent: Optional[HatiDataAgent] = None
    _session_id: str = ""
    _table_created: bool = False
    _host: str = "localhost"
    _port: int = 5439
    _agent_id: str = "langchain-agent"
    _database: str = "hatidata"
    _user: str = "agent"
    _password: str = ""

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5439,
        agent_id: str = "langchain-agent",
        session_id: Optional[str] = None,
        database: str = "hatidata",
        user: str = "agent",
        password: str = "",
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._host = host
        self._port = port
        self._agent_id = agent_id
        self._database = database
        self._user = user
        self._password = password
        self._session_id = session_id or f"sess-{uuid.uuid4().hex[:12]}"
        self._agent = HatiDataAgent(
            host=host,
            port=port,
            agent_id=agent_id,
            framework="langchain",
            database=database,
            user=user,
            password=password,
        )
        self._table_created = False

    def _ensure_table(self) -> None:
        """Create the memory table if it doesn't exist."""
        if self._table_created or self._agent is None:
            return
        self._agent.execute(
            "CREATE TABLE IF NOT EXISTS _hatidata_memory ("
            "  id TEXT PRIMARY KEY,"
            "  session_id TEXT NOT NULL,"
            "  agent_id TEXT NOT NULL,"
            "  role TEXT NOT NULL,"
            "  content TEXT NOT NULL,"
            "  metadata TEXT,"
            "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
        self._table_created = True

    @property
    def memory_variables(self) -> list[str]:
        return [self.memory_key]

    def load_memory_variables(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Load conversation history from HatiData."""
        self._ensure_table()
        assert self._agent is not None

        rows = self._agent.query(
            f"SELECT role, content FROM _hatidata_memory "
            f"WHERE session_id = '{self._session_id}' "
            f"ORDER BY created_at"
        )

        if self.return_messages:
            messages: list[BaseMessage] = []
            for row in rows:
                if row["role"] == "human":
                    messages.append(HumanMessage(content=row["content"]))
                else:
                    messages.append(AIMessage(content=row["content"]))
            return {self.memory_key: messages}

        # Return as formatted string
        lines = []
        for row in rows:
            prefix = "Human" if row["role"] == "human" else "AI"
            lines.append(f"{prefix}: {row['content']}")
        return {self.memory_key: "\n".join(lines)}

    def save_context(
        self, inputs: dict[str, Any], outputs: dict[str, str]
    ) -> None:
        """Save a conversation turn to HatiData."""
        self._ensure_table()
        assert self._agent is not None

        human_input = inputs.get(self.input_key, "")
        ai_output = outputs.get(self.output_key, "")

        # Store human message
        human_id = uuid.uuid4().hex
        self._agent.execute(
            f"INSERT INTO _hatidata_memory (id, session_id, agent_id, role, content) "
            f"VALUES ('{human_id}', '{self._session_id}', '{self._agent_id}', "
            f"'human', '{_escape(human_input)}')"
        )

        # Store AI message
        ai_id = uuid.uuid4().hex
        self._agent.execute(
            f"INSERT INTO _hatidata_memory (id, session_id, agent_id, role, content) "
            f"VALUES ('{ai_id}', '{self._session_id}', '{self._agent_id}', "
            f"'ai', '{_escape(ai_output)}')"
        )

    def clear(self) -> None:
        """Clear conversation history for this session."""
        self._ensure_table()
        assert self._agent is not None
        self._agent.execute(
            f"DELETE FROM _hatidata_memory WHERE session_id = '{self._session_id}'"
        )


def _escape(s: str) -> str:
    """Escape single quotes for SQL insertion."""
    return s.replace("'", "''")

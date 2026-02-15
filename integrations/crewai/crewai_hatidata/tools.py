"""CrewAI Tools backed by HatiData.

Provides tools that allow CrewAI agents to query, explore, and
search data in HatiData's in-VPC data warehouse.

Usage::

    from crewai import Agent
    from crewai_hatidata import HatiDataQueryTool, HatiDataListTablesTool

    agent = Agent(
        role="Data Analyst",
        tools=[
            HatiDataQueryTool(host="proxy.internal", agent_id="analyst"),
            HatiDataListTablesTool(host="proxy.internal", agent_id="analyst"),
        ],
    )
"""

from __future__ import annotations

from typing import Any, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from hatidata_agent import HatiDataAgent


class _QueryInput(BaseModel):
    """Input for SQL query execution."""
    sql: str = Field(description="The SQL query to execute")


class _DescribeInput(BaseModel):
    """Input for table description."""
    table_name: str = Field(description="Name of the table to describe")


class _ContextSearchInput(BaseModel):
    """Input for context search."""
    table: str = Field(description="Table to search")
    search_query: str = Field(description="Natural language search query")
    top_k: int = Field(default=10, description="Maximum number of results")


def _make_agent(
    host: str, port: int, agent_id: str, database: str, user: str, password: str
) -> HatiDataAgent:
    """Create a HatiDataAgent with CrewAI framework identification."""
    return HatiDataAgent(
        host=host,
        port=port,
        agent_id=agent_id,
        framework="crewai",
        database=database,
        user=user,
        password=password,
    )


class HatiDataQueryTool(BaseTool):
    """Execute SQL queries against HatiData."""

    name: str = "hatidata_query"
    description: str = (
        "Execute a SQL query against HatiData and return results as a list of rows. "
        "Use this for SELECT queries to retrieve and analyze data."
    )
    args_schema: Type[BaseModel] = _QueryInput
    _agent: HatiDataAgent

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5439,
        agent_id: str = "crewai-agent",
        database: str = "hatidata",
        user: str = "agent",
        password: str = "",
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._agent = _make_agent(host, port, agent_id, database, user, password)

    def _run(self, sql: str) -> str:
        try:
            rows = self._agent.query(sql)
            if not rows:
                return "Query returned no results."
            return str(rows)
        except Exception as e:
            return f"Error executing query: {e}"


class HatiDataListTablesTool(BaseTool):
    """List available tables in HatiData."""

    name: str = "hatidata_list_tables"
    description: str = (
        "List all available tables in the HatiData database. "
        "Use this to discover what data is available before writing queries."
    )
    _agent: HatiDataAgent

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5439,
        agent_id: str = "crewai-agent",
        database: str = "hatidata",
        user: str = "agent",
        password: str = "",
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._agent = _make_agent(host, port, agent_id, database, user, password)

    def _run(self) -> str:
        try:
            rows = self._agent.query(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main' ORDER BY table_name"
            )
            tables = [row["table_name"] for row in rows]
            return f"Available tables: {', '.join(tables)}" if tables else "No tables found."
        except Exception as e:
            return f"Error listing tables: {e}"


class HatiDataDescribeTableTool(BaseTool):
    """Describe a table's schema in HatiData."""

    name: str = "hatidata_describe_table"
    description: str = (
        "Get column names and data types for a specific table. "
        "Use this to understand table structure before writing SQL queries."
    )
    args_schema: Type[BaseModel] = _DescribeInput
    _agent: HatiDataAgent

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5439,
        agent_id: str = "crewai-agent",
        database: str = "hatidata",
        user: str = "agent",
        password: str = "",
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._agent = _make_agent(host, port, agent_id, database, user, password)

    def _run(self, table_name: str) -> str:
        try:
            rows = self._agent.query(
                f"SELECT column_name, data_type, is_nullable "
                f"FROM information_schema.columns "
                f"WHERE table_name = '{table_name}' ORDER BY ordinal_position"
            )
            if not rows:
                return f"Table '{table_name}' not found."
            lines = [
                f"  {r['column_name']}: {r['data_type']}"
                + (" (nullable)" if r.get("is_nullable") == "YES" else "")
                for r in rows
            ]
            return f"Table: {table_name}\nColumns:\n" + "\n".join(lines)
        except Exception as e:
            return f"Error describing table: {e}"


class HatiDataContextSearchTool(BaseTool):
    """Search for context using HatiData's full-text search."""

    name: str = "hatidata_context_search"
    description: str = (
        "Search for relevant data using natural language. "
        "Uses HatiData's built-in full-text search for RAG context retrieval."
    )
    args_schema: Type[BaseModel] = _ContextSearchInput
    _agent: HatiDataAgent

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5439,
        agent_id: str = "crewai-agent",
        database: str = "hatidata",
        user: str = "agent",
        password: str = "",
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._agent = _make_agent(host, port, agent_id, database, user, password)

    def _run(self, table: str, search_query: str, top_k: int = 10) -> str:
        try:
            rows = self._agent.get_context(table, search_query, top_k=top_k)
            if not rows:
                return "No matching results found."
            return str(rows)
        except Exception as e:
            return f"Error searching context: {e}"

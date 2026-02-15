"""LangChain Tools backed by HatiData.

Provides a toolkit of SQL tools that agents can use to query,
explore, and retrieve data from HatiData.

Usage::

    from langchain_hatidata import HatiDataToolkit
    from langchain.agents import AgentExecutor, create_react_agent

    toolkit = HatiDataToolkit(host="proxy.internal", agent_id="sql-agent")
    tools = toolkit.get_tools()

    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
    executor = AgentExecutor(agent=agent, tools=tools)
"""

from __future__ import annotations

from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from hatidata_agent import HatiDataAgent


class QueryInput(BaseModel):
    """Input for the SQL query tool."""
    sql: str = Field(description="SQL query to execute")


class DescribeTableInput(BaseModel):
    """Input for the describe table tool."""
    table_name: str = Field(description="Name of the table to describe")


class ContextSearchInput(BaseModel):
    """Input for the context search tool."""
    table: str = Field(description="Table to search")
    search_query: str = Field(description="Natural language search query")
    top_k: int = Field(default=10, description="Maximum number of results")


class HatiDataQueryTool(BaseTool):
    """Execute SQL queries against HatiData."""

    name: str = "hatidata_query"
    description: str = (
        "Execute a SQL query against HatiData and return results. "
        "Use this for SELECT queries to retrieve data. "
        "Input should be a valid SQL query string."
    )
    args_schema: Type[BaseModel] = QueryInput
    _agent: HatiDataAgent

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, agent: HatiDataAgent, **kwargs: Any):
        super().__init__(**kwargs)
        self._agent = agent

    def _run(self, sql: str) -> str:
        """Execute the SQL query."""
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
        "Use this to discover what tables exist before querying."
    )
    _agent: HatiDataAgent

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, agent: HatiDataAgent, **kwargs: Any):
        super().__init__(**kwargs)
        self._agent = agent

    def _run(self) -> str:
        """List tables."""
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
        "Get the column names and types for a specific table. "
        "Use this to understand table structure before writing queries."
    )
    args_schema: Type[BaseModel] = DescribeTableInput
    _agent: HatiDataAgent

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, agent: HatiDataAgent, **kwargs: Any):
        super().__init__(**kwargs)
        self._agent = agent

    def _run(self, table_name: str) -> str:
        """Describe the table."""
        try:
            rows = self._agent.query(
                f"SELECT column_name, data_type, is_nullable "
                f"FROM information_schema.columns "
                f"WHERE table_name = '{table_name}' ORDER BY ordinal_position"
            )
            if not rows:
                return f"Table '{table_name}' not found."
            lines = [f"  {r['column_name']}: {r['data_type']}"
                     + (" (nullable)" if r.get("is_nullable") == "YES" else "")
                     for r in rows]
            return f"Table: {table_name}\nColumns:\n" + "\n".join(lines)
        except Exception as e:
            return f"Error describing table: {e}"


class HatiDataContextSearchTool(BaseTool):
    """Search for context using HatiData's full-text search."""

    name: str = "hatidata_context_search"
    description: str = (
        "Search for relevant data using natural language. "
        "Uses HatiData's built-in full-text search for RAG context retrieval. "
        "Provide a table name and a search query."
    )
    args_schema: Type[BaseModel] = ContextSearchInput
    _agent: HatiDataAgent

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, agent: HatiDataAgent, **kwargs: Any):
        super().__init__(**kwargs)
        self._agent = agent

    def _run(self, table: str, search_query: str, top_k: int = 10) -> str:
        """Search for context."""
        try:
            rows = self._agent.get_context(table, search_query, top_k=top_k)
            if not rows:
                return "No matching results found."
            return str(rows)
        except Exception as e:
            return f"Error searching context: {e}"


class HatiDataToolkit:
    """Toolkit providing HatiData SQL tools for LangChain agents.

    Creates a set of tools that allow LangChain agents to query,
    explore, and search data in HatiData.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5439,
        agent_id: str = "langchain-agent",
        database: str = "hatidata",
        user: str = "agent",
        password: str = "",
    ):
        self._agent = HatiDataAgent(
            host=host,
            port=port,
            agent_id=agent_id,
            framework="langchain",
            database=database,
            user=user,
            password=password,
        )

    def get_tools(self) -> list[BaseTool]:
        """Return a list of HatiData tools for use by a LangChain agent."""
        return [
            HatiDataQueryTool(agent=self._agent),
            HatiDataListTablesTool(agent=self._agent),
            HatiDataDescribeTableTool(agent=self._agent),
            HatiDataContextSearchTool(agent=self._agent),
        ]

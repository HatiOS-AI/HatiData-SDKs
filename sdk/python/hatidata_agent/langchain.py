"""LangChain integration for HatiData agent queries.

Provides a LangChain-compatible SQLDatabase wrapper that automatically
identifies itself as a LangChain agent, enabling per-agent billing,
scheduling, and audit in HatiData.

Usage::

    from hatidata_agent.langchain import HatiDataSQLDatabase
    from langchain.agents import create_sql_agent

    db = HatiDataSQLDatabase(
        host="proxy.internal",
        port=5439,
        agent_id="sql-agent-1",
    )

    agent = create_sql_agent(llm=llm, db=db, verbose=True)
    result = agent.run("How many active enterprise customers do we have?")
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from hatidata_agent.client import HatiDataAgent


class HatiDataSQLDatabase:
    """LangChain-compatible SQL database wrapper for HatiData.

    Implements the interface expected by LangChain's SQL agent tools:
    - `run(command)` — Execute SQL and return string result
    - `get_usable_table_names()` — List available tables
    - `get_table_info(table_names)` — Get DDL/schema for tables
    - `dialect` — Database dialect identifier

    This wrapper automatically sets `framework="langchain"` for
    agent identification in HatiData's billing and audit systems.
    """

    dialect = "postgresql"

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5439,
        agent_id: str = "langchain-agent",
        database: str = "hatidata",
        user: str = "agent",
        password: str = "",
        priority: str = "normal",
        include_tables: Optional[Sequence[str]] = None,
        sample_rows_in_table_info: int = 3,
    ):
        self._agent = HatiDataAgent(
            host=host,
            port=port,
            agent_id=agent_id,
            framework="langchain",
            database=database,
            user=user,
            password=password,
            priority=priority,
        )
        self._include_tables = set(include_tables) if include_tables else None
        self._sample_rows = sample_rows_in_table_info

    def run(self, command: str, fetch: str = "all") -> str:
        """Execute SQL and return results as a string.

        Args:
            command: SQL query or statement.
            fetch: "all" to fetch all rows, "one" for single row.

        Returns:
            String representation of the results.
        """
        rows = self._agent.query(command)
        if not rows:
            return ""
        if fetch == "one" and rows:
            return str(rows[0])
        return str(rows)

    def run_no_throw(self, command: str, fetch: str = "all") -> str:
        """Execute SQL, returning error message on failure instead of raising."""
        try:
            return self.run(command, fetch)
        except Exception as e:
            return f"Error: {e}"

    def get_usable_table_names(self) -> list[str]:
        """Return list of table names available for querying."""
        rows = self._agent.query(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' ORDER BY table_name"
        )
        tables = [row["table_name"] for row in rows]

        if self._include_tables:
            tables = [t for t in tables if t in self._include_tables]

        return tables

    def get_table_info(self, table_names: Optional[list[str]] = None) -> str:
        """Get CREATE TABLE DDL and sample rows for the given tables.

        Args:
            table_names: Tables to describe. If None, describes all usable tables.

        Returns:
            Multi-line string with DDL and sample rows for each table.
        """
        if table_names is None:
            table_names = self.get_usable_table_names()

        info_parts = []
        for table in table_names:
            # Get column info.
            cols = self._agent.query(
                f"SELECT column_name, data_type, is_nullable "
                f"FROM information_schema.columns "
                f"WHERE table_name = '{table}' ORDER BY ordinal_position"
            )

            # Build CREATE TABLE statement.
            col_defs = []
            for col in cols:
                nullable = "" if col.get("is_nullable") == "YES" else " NOT NULL"
                col_defs.append(
                    f"  {col['column_name']} {col['data_type']}{nullable}"
                )

            ddl = f"CREATE TABLE {table} (\n" + ",\n".join(col_defs) + "\n);"

            # Sample rows.
            sample = ""
            if self._sample_rows > 0:
                rows = self._agent.query(
                    f"SELECT * FROM {table} LIMIT {self._sample_rows}"
                )
                if rows:
                    sample = (
                        f"\n\n/*\n{self._sample_rows} rows from {table} table:\n"
                        + "\t".join(rows[0].keys())
                        + "\n"
                    )
                    for row in rows:
                        sample += "\t".join(str(v) for v in row.values()) + "\n"
                    sample += "*/"

            info_parts.append(f"{ddl}{sample}")

        return "\n\n".join(info_parts)

    def get_table_info_no_throw(
        self, table_names: Optional[list[str]] = None
    ) -> str:
        """Get table info, returning error message on failure."""
        try:
            return self.get_table_info(table_names)
        except Exception as e:
            return f"Error: {e}"

    @property
    def table_info(self) -> str:
        """Property for LangChain compatibility."""
        return self.get_table_info()

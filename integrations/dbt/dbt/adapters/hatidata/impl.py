"""HatiData dbt adapter — extends PostgresAdapter for Snowflake SQL compatibility."""

from typing import List, Optional

from dbt.adapters.postgres import PostgresAdapter
from dbt.adapters.hatidata.connections import HatiDataConnectionManager
from dbt.adapters.hatidata.relation import HatiDataRelation
from dbt.adapters.hatidata.column import HatiDataColumn


class HatiDataAdapter(PostgresAdapter):
    """
    HatiData dbt adapter.

    Extends PostgresAdapter since HatiData speaks Postgres wire protocol.
    Overrides Snowflake-specific behaviors where needed. The proxy's
    built-in transpiler handles most Snowflake SQL → DuckDB translation.
    """

    ConnectionManager = HatiDataConnectionManager
    Relation = HatiDataRelation
    Column = HatiDataColumn

    @classmethod
    def type(cls) -> str:
        return "hatidata"

    @classmethod
    def date_function(cls) -> str:
        return "current_timestamp"

    def list_schemas(self, database: str) -> List[str]:
        """List schemas via Iceberg catalog."""
        results = self.execute_macro(
            "hatidata__list_schemas", kwargs={"database": database}
        )
        return [row[0] for row in results]

    def list_relations_without_caching(self, schema_relation):
        """Query Iceberg catalog for tables in a schema."""
        kwargs = {"schema_relation": schema_relation}
        results = self.execute_macro(
            "hatidata__list_relations_without_caching", kwargs=kwargs
        )
        relations = []
        for row in results:
            relations.append(
                self.Relation.create(
                    database=row[0],
                    schema=row[1],
                    identifier=row[2],
                    type=row[3],
                )
            )
        return relations

    def get_columns_in_relation(self, relation) -> List[HatiDataColumn]:
        """Get column metadata from Iceberg schema."""
        kwargs = {"relation": relation}
        results = self.execute_macro(
            "hatidata__get_columns_in_relation", kwargs=kwargs
        )
        return [
            self.Column(
                column=row[0],
                dtype=row[1],
                char_size=row[2] if len(row) > 2 else None,
                numeric_precision=row[3] if len(row) > 3 else None,
                numeric_scale=row[4] if len(row) > 4 else None,
            )
            for row in results
        ]

    def valid_incremental_strategies(self) -> List[str]:
        """Support Snowflake-compatible incremental strategies."""
        return ["append", "delete+insert", "merge"]

    def standardize_grants_dict(self, grants_table):
        """HatiData RBAC grant handling."""
        return grants_table

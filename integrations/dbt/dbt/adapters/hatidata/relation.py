"""HatiData relation (table/view) representation."""

from dataclasses import dataclass
from dbt.adapters.postgres.relation import PostgresRelation
from dbt.adapters.contracts.relation import RelationType


@dataclass(frozen=True, eq=False, repr=False)
class HatiDataRelation(PostgresRelation):
    """
    Represents a relation (table or view) in HatiData.

    Extends PostgresRelation since HatiData uses Postgres wire protocol
    with Iceberg-backed storage.
    """

    @classmethod
    def get_relation_type(cls) -> RelationType:
        return RelationType.Table

    def __post_init__(self):
        # HatiData uses Iceberg tables; views are materialized as DuckDB views
        pass

    @classmethod
    def create(cls, database=None, schema=None, identifier=None, type=None, **kwargs):
        """Create a HatiDataRelation from catalog metadata."""
        if isinstance(type, str):
            type = RelationType(type)
        return cls.from_dict(
            {
                "database": database,
                "schema": schema,
                "identifier": identifier,
                "type": type,
            }
        )

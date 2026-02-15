"""HatiData column type mapping — Snowflake types to DuckDB types."""

from dbt.adapters.postgres.column import PostgresColumn


# Snowflake type → DuckDB type mapping
SNOWFLAKE_TO_DUCKDB_TYPES = {
    "VARIANT": "JSON",
    "OBJECT": "JSON",
    "ARRAY": "JSON",
    "NUMBER": "DECIMAL",
    "FLOAT": "DOUBLE",
    "FLOAT4": "FLOAT",
    "FLOAT8": "DOUBLE",
    "STRING": "VARCHAR",
    "TEXT": "VARCHAR",
    "BINARY": "BLOB",
    "VARBINARY": "BLOB",
    "TIMESTAMP_LTZ": "TIMESTAMPTZ",
    "TIMESTAMP_NTZ": "TIMESTAMP",
    "TIMESTAMP_TZ": "TIMESTAMPTZ",
    "DATETIME": "TIMESTAMP",
    "BOOLEAN": "BOOLEAN",
    "INT": "INTEGER",
    "INTEGER": "INTEGER",
    "BIGINT": "BIGINT",
    "SMALLINT": "SMALLINT",
    "TINYINT": "TINYINT",
}


class HatiDataColumn(PostgresColumn):
    """
    Column representation with Snowflake → DuckDB type mapping.

    When dbt models use Snowflake type names, this class maps them
    to DuckDB-compatible types that HatiData's proxy understands.
    """

    @classmethod
    def translate_type(cls, dtype: str) -> str:
        """Map Snowflake type names to DuckDB-compatible types."""
        upper = dtype.upper().strip()
        return SNOWFLAKE_TO_DUCKDB_TYPES.get(upper, upper)

    def data_type(self) -> str:
        """Return the DuckDB-compatible data type."""
        return self.translate_type(self.dtype)

    @classmethod
    def numeric_type(cls, dtype: str, precision, scale) -> str:
        """Handle numeric type with precision and scale."""
        if precision is not None and scale is not None:
            return f"DECIMAL({precision},{scale})"
        if precision is not None:
            return f"DECIMAL({precision})"
        return "DECIMAL"

    def is_string(self) -> bool:
        """Check if column is a string type."""
        return self.translate_type(self.dtype) in ("VARCHAR", "TEXT", "STRING")

    def is_number(self) -> bool:
        """Check if column is a numeric type."""
        translated = self.translate_type(self.dtype)
        return translated in (
            "INTEGER",
            "BIGINT",
            "SMALLINT",
            "TINYINT",
            "DECIMAL",
            "DOUBLE",
            "FLOAT",
        )

    def is_json(self) -> bool:
        """Check if column is a JSON/semi-structured type."""
        return self.translate_type(self.dtype) == "JSON"

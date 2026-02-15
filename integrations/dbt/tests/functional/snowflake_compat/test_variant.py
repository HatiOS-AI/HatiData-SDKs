"""Functional tests for Snowflake VARIANT -> DuckDB JSON compatibility."""

import pytest


@pytest.mark.functional
class TestVariant:
    """Test VARIANT/JSON type handling."""

    def test_json_type_creation(self, cursor):
        """Test creating a table with JSON (VARIANT equivalent) column."""
        cursor.execute("DROP TABLE IF EXISTS test_variant")
        cursor.execute("CREATE TABLE test_variant (id INTEGER, data JSON)")
        cursor.execute(
            """INSERT INTO test_variant VALUES
            (1, '{"name": "alice", "age": 30}'),
            (2, '{"name": "bob", "age": 25}')
            """
        )
        cursor.execute("SELECT COUNT(*) FROM test_variant")
        assert cursor.fetchone()[0] == 2
        cursor.execute("DROP TABLE test_variant")

    def test_json_extract(self, cursor):
        """Test extracting fields from JSON (Snowflake col:field notation)."""
        cursor.execute(
            """
            SELECT json_extract_string('{"name": "alice"}'::JSON, 'name')
            """
        )
        assert cursor.fetchone()[0] == "alice"

    def test_json_nested_extract(self, cursor):
        """Test extracting nested JSON fields."""
        cursor.execute(
            """
            SELECT json_extract_string(
                '{"user": {"name": "alice"}}'::JSON,
                '$.user.name'
            )
            """
        )
        assert cursor.fetchone()[0] == "alice"

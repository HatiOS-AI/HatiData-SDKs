"""Functional tests for Snowflake QUALIFY clause support."""

import pytest


@pytest.mark.functional
class TestQualify:
    """Test QUALIFY clause handling (via transpilation)."""

    def test_qualify_row_number(self, cursor):
        """Test QUALIFY with ROW_NUMBER (deduplication pattern)."""
        cursor.execute("DROP TABLE IF EXISTS test_qualify")
        cursor.execute(
            """
            CREATE TABLE test_qualify AS
            SELECT * FROM (VALUES
                (1, 'a', '2024-01-01'),
                (1, 'b', '2024-01-02'),
                (2, 'c', '2024-01-01'),
                (2, 'd', '2024-01-02')
            ) AS t(id, value, updated_at)
            """
        )

        # DuckDB supports QUALIFY natively
        cursor.execute(
            """
            SELECT id, value FROM test_qualify
            QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) = 1
            ORDER BY id
            """
        )
        rows = cursor.fetchall()
        assert len(rows) == 2
        assert rows[0] == (1, "b")
        assert rows[1] == (2, "d")
        cursor.execute("DROP TABLE test_qualify")

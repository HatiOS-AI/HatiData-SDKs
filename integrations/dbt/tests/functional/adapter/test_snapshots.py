"""Functional tests for dbt snapshot support."""

import pytest


@pytest.mark.functional
class TestSnapshots:
    """Test snapshot-related SQL patterns."""

    def test_timestamp_based_snapshot_columns(self, cursor):
        """Verify that timestamp-based snapshot queries work."""
        cursor.execute("DROP TABLE IF EXISTS test_snapshot_src")
        cursor.execute(
            """
            CREATE TABLE test_snapshot_src (
                id INTEGER,
                name VARCHAR,
                updated_at TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            INSERT INTO test_snapshot_src VALUES
            (1, 'alice', '2024-01-01 00:00:00'),
            (2, 'bob', '2024-01-01 00:00:00')
            """
        )

        # Snapshot query pattern: select with dbt_scd columns
        cursor.execute(
            """
            SELECT
                id, name, updated_at,
                updated_at AS dbt_valid_from,
                NULL::TIMESTAMP AS dbt_valid_to,
                md5(CAST(id AS VARCHAR)) AS dbt_scd_id
            FROM test_snapshot_src
            """
        )
        rows = cursor.fetchall()
        assert len(rows) == 2
        assert rows[0][3] is not None  # dbt_valid_from
        assert rows[0][4] is None  # dbt_valid_to
        cursor.execute("DROP TABLE test_snapshot_src")

    def test_md5_hash_function(self, cursor):
        """Verify MD5 function works for snapshot hashing."""
        cursor.execute("SELECT md5('test')")
        row = cursor.fetchone()
        assert len(row[0]) == 32  # MD5 hex string

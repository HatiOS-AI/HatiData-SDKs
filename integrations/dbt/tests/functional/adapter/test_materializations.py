"""Functional tests for dbt materializations."""

import pytest


@pytest.mark.functional
class TestMaterializations:
    """Test table and view materializations."""

    def test_table_materialization(self, cursor):
        """Test creating a table from a SELECT."""
        cursor.execute("DROP TABLE IF EXISTS test_mat_table")
        cursor.execute(
            "CREATE TABLE test_mat_table AS SELECT 1 AS id, 'test' AS name"
        )
        cursor.execute("SELECT * FROM test_mat_table")
        row = cursor.fetchone()
        assert row[0] == 1
        assert row[1] == "test"
        cursor.execute("DROP TABLE test_mat_table")

    def test_view_materialization(self, cursor):
        """Test creating a view from a SELECT."""
        cursor.execute("DROP TABLE IF EXISTS test_mat_src")
        cursor.execute("CREATE TABLE test_mat_src AS SELECT generate_series AS id FROM generate_series(1, 10)")
        cursor.execute("CREATE OR REPLACE VIEW test_mat_view AS SELECT * FROM test_mat_src WHERE id > 5")
        cursor.execute("SELECT COUNT(*) FROM test_mat_view")
        row = cursor.fetchone()
        assert row[0] == 5
        cursor.execute("DROP VIEW test_mat_view")
        cursor.execute("DROP TABLE test_mat_src")

    def test_table_replace(self, cursor):
        """Test replacing an existing table."""
        cursor.execute("DROP TABLE IF EXISTS test_mat_replace")
        cursor.execute("CREATE TABLE test_mat_replace AS SELECT 1 AS id")
        cursor.execute("DROP TABLE test_mat_replace")
        cursor.execute("CREATE TABLE test_mat_replace AS SELECT 2 AS id")
        cursor.execute("SELECT id FROM test_mat_replace")
        row = cursor.fetchone()
        assert row[0] == 2
        cursor.execute("DROP TABLE test_mat_replace")

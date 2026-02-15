"""Functional tests for incremental materialization strategies."""

import pytest


@pytest.mark.functional
class TestIncrementalStrategies:
    """Test incremental materialization strategies."""

    def test_append_strategy(self, cursor):
        """Test append-only incremental strategy."""
        cursor.execute("DROP TABLE IF EXISTS test_inc_append")
        cursor.execute("CREATE TABLE test_inc_append (id INTEGER, name VARCHAR)")
        cursor.execute("INSERT INTO test_inc_append VALUES (1, 'first')")
        cursor.execute("INSERT INTO test_inc_append VALUES (2, 'second')")
        cursor.execute("SELECT COUNT(*) FROM test_inc_append")
        assert cursor.fetchone()[0] == 2
        cursor.execute("DROP TABLE test_inc_append")

    def test_delete_insert_strategy(self, cursor):
        """Test delete+insert incremental strategy."""
        cursor.execute("DROP TABLE IF EXISTS test_inc_di")
        cursor.execute("CREATE TABLE test_inc_di (id INTEGER PRIMARY KEY, name VARCHAR)")
        cursor.execute("INSERT INTO test_inc_di VALUES (1, 'first'), (2, 'second')")

        # Delete matching then insert updated
        cursor.execute("DELETE FROM test_inc_di WHERE id IN (SELECT 1)")
        cursor.execute("INSERT INTO test_inc_di VALUES (1, 'updated_first')")

        cursor.execute("SELECT name FROM test_inc_di WHERE id = 1")
        assert cursor.fetchone()[0] == "updated_first"
        cursor.execute("SELECT COUNT(*) FROM test_inc_di")
        assert cursor.fetchone()[0] == 2
        cursor.execute("DROP TABLE test_inc_di")

    def test_merge_strategy_via_on_conflict(self, cursor):
        """Test merge strategy using INSERT ... ON CONFLICT (DuckDB upsert)."""
        cursor.execute("DROP TABLE IF EXISTS test_inc_merge")
        cursor.execute(
            "CREATE TABLE test_inc_merge (id INTEGER PRIMARY KEY, name VARCHAR, updated_at TIMESTAMP)"
        )
        cursor.execute(
            "INSERT INTO test_inc_merge VALUES (1, 'original', '2024-01-01')"
        )

        # Upsert via ON CONFLICT
        cursor.execute(
            """
            INSERT INTO test_inc_merge (id, name, updated_at)
            VALUES (1, 'updated', '2024-06-01'), (2, 'new', '2024-06-01')
            ON CONFLICT (id)
            DO UPDATE SET name = EXCLUDED.name, updated_at = EXCLUDED.updated_at
            """
        )

        cursor.execute("SELECT name FROM test_inc_merge WHERE id = 1")
        assert cursor.fetchone()[0] == "updated"
        cursor.execute("SELECT COUNT(*) FROM test_inc_merge")
        assert cursor.fetchone()[0] == 2
        cursor.execute("DROP TABLE test_inc_merge")

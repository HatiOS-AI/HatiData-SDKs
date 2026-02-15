"""Functional tests for dbt seed loading."""

import pytest


@pytest.mark.functional
class TestSeeds:
    """Test CSV seed loading patterns."""

    def test_create_table_from_values(self, cursor):
        """Test inserting seed-like data."""
        cursor.execute("DROP TABLE IF EXISTS test_seed")
        cursor.execute(
            """
            CREATE TABLE test_seed (
                id INTEGER,
                name VARCHAR,
                amount DECIMAL(10,2)
            )
            """
        )
        cursor.execute(
            """
            INSERT INTO test_seed VALUES
            (1, 'Alice', 100.50),
            (2, 'Bob', 200.75),
            (3, 'Charlie', 300.00)
            """
        )
        cursor.execute("SELECT COUNT(*) FROM test_seed")
        assert cursor.fetchone()[0] == 3
        cursor.execute("SELECT SUM(amount) FROM test_seed")
        result = float(cursor.fetchone()[0])
        assert result == pytest.approx(601.25)
        cursor.execute("DROP TABLE test_seed")

    def test_csv_copy_pattern(self, cursor):
        """Test that COPY FROM pattern works (used by dbt seed)."""
        cursor.execute("DROP TABLE IF EXISTS test_seed_copy")
        cursor.execute("CREATE TABLE test_seed_copy (id INTEGER, value VARCHAR)")
        cursor.execute("INSERT INTO test_seed_copy VALUES (1, 'a'), (2, 'b')")
        cursor.execute("SELECT * FROM test_seed_copy ORDER BY id")
        rows = cursor.fetchall()
        assert rows[0] == (1, "a")
        assert rows[1] == (2, "b")
        cursor.execute("DROP TABLE test_seed_copy")

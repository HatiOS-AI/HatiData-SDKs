"""Functional tests for basic dbt adapter operations."""

import pytest


@pytest.mark.functional
class TestBasicConnection:
    """Test basic connection and query execution."""

    def test_select_one(self, cursor):
        cursor.execute("SELECT 1 AS n")
        row = cursor.fetchone()
        assert row[0] == 1

    def test_select_string(self, cursor):
        cursor.execute("SELECT 'hello' AS greeting")
        row = cursor.fetchone()
        assert row[0] == "hello"

    def test_select_multiple_columns(self, cursor):
        cursor.execute("SELECT 1 AS a, 'two' AS b, 3.14 AS c")
        row = cursor.fetchone()
        assert row[0] == 1
        assert row[1] == "two"
        assert float(row[2]) == pytest.approx(3.14)

    def test_create_and_query_table(self, cursor):
        cursor.execute("CREATE TABLE IF NOT EXISTS test_dbt_basic (id INTEGER, name VARCHAR)")
        cursor.execute("INSERT INTO test_dbt_basic VALUES (1, 'alice'), (2, 'bob')")
        cursor.execute("SELECT COUNT(*) FROM test_dbt_basic")
        row = cursor.fetchone()
        assert row[0] == 2
        cursor.execute("DROP TABLE IF EXISTS test_dbt_basic")

    def test_create_and_query_view(self, cursor):
        cursor.execute("CREATE TABLE IF NOT EXISTS test_dbt_view_src (id INTEGER)")
        cursor.execute("INSERT INTO test_dbt_view_src VALUES (1), (2), (3)")
        cursor.execute("CREATE OR REPLACE VIEW test_dbt_view AS SELECT * FROM test_dbt_view_src WHERE id > 1")
        cursor.execute("SELECT COUNT(*) FROM test_dbt_view")
        row = cursor.fetchone()
        assert row[0] == 2
        cursor.execute("DROP VIEW IF EXISTS test_dbt_view")
        cursor.execute("DROP TABLE IF EXISTS test_dbt_view_src")

    def test_information_schema(self, cursor):
        cursor.execute("SELECT table_name FROM information_schema.tables LIMIT 5")
        rows = cursor.fetchall()
        assert isinstance(rows, list)

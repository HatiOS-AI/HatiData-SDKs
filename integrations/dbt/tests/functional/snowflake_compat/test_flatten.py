"""Functional tests for Snowflake FLATTEN -> DuckDB UNNEST compatibility."""

import pytest


@pytest.mark.functional
class TestFlatten:
    """Test FLATTEN transpilation to UNNEST."""

    def test_unnest_array(self, cursor):
        """Test unnesting a JSON array (DuckDB equivalent of FLATTEN)."""
        cursor.execute(
            """
            SELECT unnest FROM unnest([1, 2, 3]) AS t(unnest)
            """
        )
        rows = cursor.fetchall()
        assert len(rows) == 3
        values = [r[0] for r in rows]
        assert sorted(values) == [1, 2, 3]

    def test_unnest_json_array(self, cursor):
        """Test unnesting a JSON array column."""
        cursor.execute(
            """
            SELECT value
            FROM (SELECT '[1,2,3]'::JSON AS arr),
                 unnest(json_extract(arr, '$[*]')::INT[]) AS t(value)
            """
        )
        rows = cursor.fetchall()
        assert len(rows) == 3

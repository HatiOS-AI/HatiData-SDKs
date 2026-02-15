"""Functional tests for Snowflake semi-structured data access patterns."""

import pytest


@pytest.mark.functional
class TestSemiStructured:
    """Test semi-structured data access (Snowflake col:field::type pattern)."""

    def test_json_extract_string_function(self, cursor):
        """Test json_extract_string (transpiled from col:field)."""
        cursor.execute(
            """
            SELECT json_extract_string('{"key": "value"}'::JSON, 'key')
            """
        )
        assert cursor.fetchone()[0] == "value"

    def test_json_extract_numeric(self, cursor):
        """Test extracting numeric values from JSON."""
        cursor.execute(
            """
            SELECT CAST(json_extract('{"count": 42}'::JSON, 'count') AS INTEGER)
            """
        )
        assert cursor.fetchone()[0] == 42

    def test_json_array_length(self, cursor):
        """Test getting JSON array length."""
        cursor.execute(
            """
            SELECT json_array_length('[1, 2, 3, 4, 5]'::JSON)
            """
        )
        assert cursor.fetchone()[0] == 5

    def test_json_type_check(self, cursor):
        """Test JSON type detection."""
        cursor.execute(
            """
            SELECT json_type('{"a": 1}'::JSON)
            """
        )
        result = cursor.fetchone()[0]
        assert result.upper() == "OBJECT"

"""Unit tests for HatiData column type mapping."""

import pytest
from dbt.adapters.hatidata.column import HatiDataColumn, SNOWFLAKE_TO_DUCKDB_TYPES


class TestColumnTypeMapping:
    """Test Snowflake -> DuckDB type translation."""

    @pytest.mark.parametrize(
        "snowflake_type,expected_duckdb_type",
        [
            ("VARIANT", "JSON"),
            ("OBJECT", "JSON"),
            ("ARRAY", "JSON"),
            ("NUMBER", "DECIMAL"),
            ("FLOAT", "DOUBLE"),
            ("FLOAT4", "FLOAT"),
            ("FLOAT8", "DOUBLE"),
            ("STRING", "VARCHAR"),
            ("TEXT", "VARCHAR"),
            ("BINARY", "BLOB"),
            ("VARBINARY", "BLOB"),
            ("TIMESTAMP_LTZ", "TIMESTAMPTZ"),
            ("TIMESTAMP_NTZ", "TIMESTAMP"),
            ("TIMESTAMP_TZ", "TIMESTAMPTZ"),
            ("DATETIME", "TIMESTAMP"),
            ("BOOLEAN", "BOOLEAN"),
            ("INT", "INTEGER"),
            ("INTEGER", "INTEGER"),
            ("BIGINT", "BIGINT"),
            ("SMALLINT", "SMALLINT"),
            ("TINYINT", "TINYINT"),
        ],
    )
    def test_type_translation(self, snowflake_type, expected_duckdb_type):
        result = HatiDataColumn.translate_type(snowflake_type)
        assert result == expected_duckdb_type

    def test_case_insensitive_translation(self):
        assert HatiDataColumn.translate_type("variant") == "JSON"
        assert HatiDataColumn.translate_type("Variant") == "JSON"
        assert HatiDataColumn.translate_type("VARIANT") == "JSON"

    def test_unknown_type_passthrough(self):
        assert HatiDataColumn.translate_type("CUSTOM_TYPE") == "CUSTOM_TYPE"
        assert HatiDataColumn.translate_type("VARCHAR") == "VARCHAR"
        assert HatiDataColumn.translate_type("DECIMAL") == "DECIMAL"

    def test_whitespace_handling(self):
        assert HatiDataColumn.translate_type("  VARIANT  ") == "JSON"
        assert HatiDataColumn.translate_type(" STRING ") == "VARCHAR"

    def test_numeric_type_with_precision_and_scale(self):
        result = HatiDataColumn.numeric_type("NUMBER", 10, 2)
        assert result == "DECIMAL(10,2)"

    def test_numeric_type_with_precision_only(self):
        result = HatiDataColumn.numeric_type("NUMBER", 10, None)
        assert result == "DECIMAL(10)"

    def test_numeric_type_no_precision(self):
        result = HatiDataColumn.numeric_type("NUMBER", None, None)
        assert result == "DECIMAL"


class TestColumnTypeChecks:
    """Test column type classification methods."""

    def test_is_string_varchar(self):
        col = HatiDataColumn(column="name", dtype="VARCHAR")
        assert col.is_string() is True

    def test_is_string_snowflake_string(self):
        col = HatiDataColumn(column="name", dtype="STRING")
        assert col.is_string() is True

    def test_is_string_integer(self):
        col = HatiDataColumn(column="id", dtype="INTEGER")
        assert col.is_string() is False

    def test_is_number_integer(self):
        col = HatiDataColumn(column="id", dtype="INTEGER")
        assert col.is_number() is True

    def test_is_number_snowflake_number(self):
        col = HatiDataColumn(column="amount", dtype="NUMBER")
        assert col.is_number() is True

    def test_is_number_string(self):
        col = HatiDataColumn(column="name", dtype="VARCHAR")
        assert col.is_number() is False

    def test_is_json_variant(self):
        col = HatiDataColumn(column="data", dtype="VARIANT")
        assert col.is_json() is True

    def test_is_json_object(self):
        col = HatiDataColumn(column="meta", dtype="OBJECT")
        assert col.is_json() is True

    def test_is_json_array(self):
        col = HatiDataColumn(column="tags", dtype="ARRAY")
        assert col.is_json() is True

    def test_is_json_string(self):
        col = HatiDataColumn(column="name", dtype="VARCHAR")
        assert col.is_json() is False

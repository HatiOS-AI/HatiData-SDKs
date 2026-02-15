{# Snowflake → DuckDB type mapping macros #}

{% macro hatidata__type_string() %} VARCHAR {% endmacro %}
{% macro hatidata__type_timestamp() %} TIMESTAMP {% endmacro %}
{% macro hatidata__type_float() %} DOUBLE {% endmacro %}
{% macro hatidata__type_numeric() %} DECIMAL {% endmacro %}
{% macro hatidata__type_bigint() %} BIGINT {% endmacro %}
{% macro hatidata__type_int() %} INTEGER {% endmacro %}
{% macro hatidata__type_boolean() %} BOOLEAN {% endmacro %}

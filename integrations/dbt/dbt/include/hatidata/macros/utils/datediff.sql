{# Snowflake DATEDIFF → DuckDB DATE_DIFF #}

{% macro hatidata__datediff(first_date, second_date, datepart) %}
    DATE_DIFF('{{ datepart }}', {{ first_date }}, {{ second_date }})
{% endmacro %}

{# Snowflake DATEADD → DuckDB interval addition #}

{% macro hatidata__dateadd(datepart, interval, from_date_or_timestamp) %}
    {{ from_date_or_timestamp }} + INTERVAL '{{ interval }}' {{ datepart }}
{% endmacro %}

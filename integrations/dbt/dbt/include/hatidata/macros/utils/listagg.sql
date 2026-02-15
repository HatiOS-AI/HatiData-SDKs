{# Snowflake LISTAGG → DuckDB STRING_AGG #}

{% macro hatidata__listagg(measure, delimiter_text, order_by_clause, limit_num) %}
    STRING_AGG(
        {{ measure }},
        {{ delimiter_text }}
        {% if order_by_clause %} {{ order_by_clause }} {% endif %}
    )
    {% if limit_num %}[1:{{ limit_num }}]{% endif %}
{% endmacro %}

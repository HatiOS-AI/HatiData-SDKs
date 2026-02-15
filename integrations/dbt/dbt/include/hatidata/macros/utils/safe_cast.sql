{# Snowflake TRY_CAST wrapper #}

{% macro hatidata__safe_cast(field, type) %}
    TRY_CAST({{ field }} AS {{ type }})
{% endmacro %}

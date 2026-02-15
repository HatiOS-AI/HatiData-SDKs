{# Timestamp handling macros for Snowflake compatibility #}

{% macro hatidata__snapshot_string_as_time(timestamp) -%}
    CAST({{ timestamp }} AS TIMESTAMP)
{%- endmacro %}

{% macro hatidata__snapshot_get_time() -%}
    current_timestamp
{%- endmacro %}

{% macro hatidata__current_timestamp_backcompat() -%}
    current_timestamp
{%- endmacro %}

{% macro hatidata__current_timestamp_in_utc_backcompat() -%}
    current_timestamp AT TIME ZONE 'UTC'
{%- endmacro %}

{# Relation management macros #}

{% macro hatidata__get_relation(database, schema, identifier) -%}
    {%- call statement('get_relation', fetch_result=True) -%}
        SELECT
            table_catalog AS database,
            table_schema AS schema,
            table_name AS name,
            CASE table_type
                WHEN 'BASE TABLE' THEN 'table'
                WHEN 'VIEW' THEN 'view'
                ELSE 'table'
            END AS type
        FROM information_schema.tables
        WHERE table_name = '{{ identifier }}'
        {% if schema %}
            AND table_schema = '{{ schema }}'
        {% endif %}
        {% if database %}
            AND table_catalog = '{{ database }}'
        {% endif %}
    {%- endcall -%}
    {{ return(load_result('get_relation').table) }}
{%- endmacro %}

{% macro hatidata__get_or_create_relation(database, schema, identifier, type) -%}
    {%- set target_relation = adapter.get_relation(
        database=database,
        schema=schema,
        identifier=identifier
    ) -%}

    {% if target_relation %}
        {{ return(target_relation) }}
    {% else %}
        {{ return(api.Relation.create(
            database=database,
            schema=schema,
            identifier=identifier,
            type=type
        )) }}
    {% endif %}
{%- endmacro %}

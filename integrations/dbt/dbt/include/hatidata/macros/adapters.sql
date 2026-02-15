{# HatiData core adapter macros #}

{% macro hatidata__list_schemas(database) %}
    SELECT schema_name
    FROM information_schema.schemata
    WHERE catalog_name = '{{ database }}'
    ORDER BY schema_name
{% endmacro %}

{% macro hatidata__list_relations_without_caching(schema_relation) %}
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
    WHERE table_schema = '{{ schema_relation.schema }}'
    {% if schema_relation.database %}
        AND table_catalog = '{{ schema_relation.database }}'
    {% endif %}
    ORDER BY table_name
{% endmacro %}

{% macro hatidata__create_table_as(temporary, relation, sql) -%}
    CREATE {% if temporary %}TEMPORARY {% endif %}TABLE {{ relation }}
    AS (
        {{ sql }}
    )
{%- endmacro %}

{% macro hatidata__create_view_as(relation, sql) -%}
    CREATE OR REPLACE VIEW {{ relation }}
    AS (
        {{ sql }}
    )
{%- endmacro %}

{% macro hatidata__drop_relation(relation) -%}
    DROP {% if relation.type == 'view' %}VIEW{% else %}TABLE{% endif %} IF EXISTS {{ relation }}
{%- endmacro %}

{% macro hatidata__truncate_relation(relation) -%}
    DELETE FROM {{ relation }}
{%- endmacro %}

{% macro hatidata__rename_relation(from_relation, to_relation) -%}
    ALTER TABLE {{ from_relation }} RENAME TO {{ to_relation.identifier }}
{%- endmacro %}

{% macro hatidata__check_schema_exists(information_schema, schema) -%}
    SELECT COUNT(*) AS schema_count
    FROM information_schema.schemata
    WHERE schema_name = '{{ schema }}'
{%- endmacro %}

{% macro hatidata__create_schema(relation) -%}
    CREATE SCHEMA IF NOT EXISTS {{ relation.without_identifier() }}
{%- endmacro %}

{% macro hatidata__drop_schema(relation) -%}
    DROP SCHEMA IF EXISTS {{ relation.without_identifier() }} CASCADE
{%- endmacro %}

{% macro hatidata__current_timestamp() -%}
    current_timestamp
{%- endmacro %}

{% macro hatidata__make_temp_relation(base_relation, suffix) %}
    {% set tmp_identifier = base_relation.identifier ~ suffix %}
    {% do return(base_relation.incorporate(
        path={"identifier": tmp_identifier},
        type="table"
    )) %}
{% endmacro %}

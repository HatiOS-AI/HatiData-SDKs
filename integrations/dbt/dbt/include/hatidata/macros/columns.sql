{# Column metadata macros #}

{% macro hatidata__get_columns_in_relation(relation) -%}
    SELECT
        column_name,
        data_type,
        character_maximum_length,
        numeric_precision,
        numeric_scale
    FROM information_schema.columns
    WHERE table_name = '{{ relation.identifier }}'
    {% if relation.schema %}
        AND table_schema = '{{ relation.schema }}'
    {% endif %}
    ORDER BY ordinal_position
{%- endmacro %}

{% macro hatidata__alter_column_type(relation, column_name, new_column_type) -%}
    ALTER TABLE {{ relation }} ALTER COLUMN {{ column_name }} TYPE {{ new_column_type }}
{%- endmacro %}

{% macro hatidata__alter_relation_add_remove_columns(relation, add_columns, remove_columns) -%}
    {% if add_columns %}
        {% for column in add_columns %}
            ALTER TABLE {{ relation }} ADD COLUMN {{ column.name }} {{ column.data_type }};
        {% endfor %}
    {% endif %}
    {% if remove_columns %}
        {% for column in remove_columns %}
            ALTER TABLE {{ relation }} DROP COLUMN {{ column.name }};
        {% endfor %}
    {% endif %}
{%- endmacro %}

{# Incremental materialization for HatiData — Snowflake-compatible strategies #}

{% materialization incremental, adapter="hatidata" %}

    {%- set unique_key = config.get('unique_key') -%}
    {%- set strategy = config.get('strategy', 'append') -%}
    {%- set full_refresh_mode = (should_full_refresh()) -%}

    {% set target_relation = this.incorporate(type='table') %}
    {% set existing_relation = load_relation(this) %}
    {% set tmp_relation = make_temp_relation(this) %}

    {{ run_hooks(pre_hooks, inside_transaction=False) }}

    {% if existing_relation is none or full_refresh_mode %}
        {# Full refresh: create table from scratch #}
        {% call statement('main') %}
            {{ create_table_as(False, target_relation, sql) }}
        {% endcall %}

    {% elif strategy == 'append' %}
        {# Append: just insert new rows #}
        {% call statement('main') %}
            INSERT INTO {{ target_relation }}
            ({{ sql }})
        {% endcall %}

    {% elif strategy == 'delete+insert' %}
        {# Delete matching rows then insert #}
        {% if unique_key %}
            {% call statement('main') %}
                DELETE FROM {{ target_relation }}
                WHERE {{ unique_key }} IN (
                    SELECT {{ unique_key }} FROM ({{ sql }}) AS __dbt_tmp
                );
                INSERT INTO {{ target_relation }}
                ({{ sql }})
            {% endcall %}
        {% else %}
            {% do exceptions.raise_compiler_error("delete+insert strategy requires a unique_key") %}
        {% endif %}

    {% elif strategy == 'merge' %}
        {# Merge: DuckDB uses INSERT ... ON CONFLICT for upserts #}
        {% if unique_key %}
            {% set dest_columns = adapter.get_columns_in_relation(target_relation) %}
            {% set dest_cols_csv = dest_columns | map(attribute='name') | join(', ') %}
            {% set update_cols = dest_columns | rejectattr('name', 'equalto', unique_key) %}
            {% set update_set = [] %}
            {% for col in update_cols %}
                {% do update_set.append(col.name ~ ' = EXCLUDED.' ~ col.name) %}
            {% endfor %}

            {% call statement('main') %}
                INSERT INTO {{ target_relation }} ({{ dest_cols_csv }})
                {{ sql }}
                ON CONFLICT ({{ unique_key }})
                DO UPDATE SET {{ update_set | join(', ') }}
            {% endcall %}
        {% else %}
            {% do exceptions.raise_compiler_error("merge strategy requires a unique_key") %}
        {% endif %}
    {% else %}
        {% do exceptions.raise_compiler_error("Invalid incremental strategy: " ~ strategy) %}
    {% endif %}

    {{ run_hooks(post_hooks, inside_transaction=False) }}

    {% do persist_docs(target_relation, model) %}

    {{ return({'relations': [target_relation]}) }}

{% endmaterialization %}

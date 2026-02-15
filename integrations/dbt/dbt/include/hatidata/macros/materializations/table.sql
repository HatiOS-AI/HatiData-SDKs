{# Table materialization for HatiData #}

{% materialization table, adapter="hatidata" %}

    {%- set existing_relation = load_relation(this) -%}
    {%- set target_relation = this.incorporate(type='table') -%}
    {%- set tmp_relation = make_temp_relation(this) -%}

    {{ run_hooks(pre_hooks, inside_transaction=False) }}

    {# Drop existing if type changed #}
    {% if existing_relation is not none and existing_relation.type != 'table' %}
        {{ adapter.drop_relation(existing_relation) }}
    {% endif %}

    {# Build as temp, then swap #}
    {% call statement('main') %}
        {{ create_table_as(False, target_relation, sql) }}
    {% endcall %}

    {% do persist_docs(target_relation, model) %}

    {{ run_hooks(post_hooks, inside_transaction=False) }}

    {{ return({'relations': [target_relation]}) }}

{% endmaterialization %}

{# View materialization for HatiData #}

{% materialization view, adapter="hatidata" %}

    {%- set existing_relation = load_relation(this) -%}
    {%- set target_relation = this.incorporate(type='view') -%}

    {{ run_hooks(pre_hooks, inside_transaction=False) }}

    {# Drop existing if type changed #}
    {% if existing_relation is not none and existing_relation.type != 'view' %}
        {{ adapter.drop_relation(existing_relation) }}
    {% endif %}

    {% call statement('main') %}
        {{ hatidata__create_view_as(target_relation, sql) }}
    {% endcall %}

    {% do persist_docs(target_relation, model) %}

    {{ run_hooks(post_hooks, inside_transaction=False) }}

    {{ return({'relations': [target_relation]}) }}

{% endmaterialization %}

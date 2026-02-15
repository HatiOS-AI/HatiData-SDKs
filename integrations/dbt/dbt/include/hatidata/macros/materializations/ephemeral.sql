{# Ephemeral materialization — compiled as CTE, never persisted #}

{% materialization ephemeral, adapter="hatidata" %}
    {# Ephemeral models are handled by dbt core as CTEs, nothing to do here #}
    {% set target_relation = this.incorporate(type='cte') %}
    {{ return({'relations': [target_relation]}) }}
{% endmaterialization %}

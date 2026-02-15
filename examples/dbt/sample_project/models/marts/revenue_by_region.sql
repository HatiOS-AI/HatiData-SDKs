-- Mart model: revenue summary by region
-- Demonstrates DATEDIFF and LISTAGG transpilation

SELECT
    region,
    COUNT(*) AS customer_count,
    LISTAGG(name, ', ') WITHIN GROUP (ORDER BY name) AS customer_names,
    MAX(created_at) AS latest_signup
FROM {{ ref('stg_customers') }}
GROUP BY region
ORDER BY customer_count DESC

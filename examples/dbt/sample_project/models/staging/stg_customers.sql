-- Staging model: clean up raw customer data
-- Uses Snowflake-compatible SQL (NVL, IFF) — transpiled automatically by HatiData

SELECT
    id,
    name,
    NVL(email, 'unknown@example.com') AS email,
    IFF(region IS NULL, 'Unassigned', region) AS region,
    department,
    created_at
FROM {{ ref('customers') }}

-- 001: Basic SELECT with WHERE, ORDER BY, LIMIT
-- Tests: Standard SQL passthrough, no transpilation rewrites needed
SELECT "id", "name", "email", "region"
FROM sample_db.customers
WHERE region = 'APAC'
ORDER BY created_at DESC
LIMIT 100;

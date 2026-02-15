-- 003: QUALIFY with ROW_NUMBER window function
-- Tests: QUALIFY → subquery rewrite (DuckDB supports QUALIFY natively, but
--        this verifies the transpiler handles it correctly either way)
SELECT customer_id,
       order_date,
       amount,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY amount DESC) AS rn
FROM sample_db.orders
QUALIFY rn = 1;

-- 005: LISTAGG with WITHIN GROUP aggregation
-- Tests: LISTAGG(DISTINCT col, sep) WITHIN GROUP (ORDER BY col)
--        → string_agg(DISTINCT col, sep ORDER BY col)
SELECT region,
       LISTAGG(DISTINCT department, ', ') WITHIN GROUP (ORDER BY department) AS departments
FROM sample_db.customers
GROUP BY region;

-- 002: LATERAL FLATTEN on JSON metadata column
-- Tests: FLATTEN → unnest, PARSE_JSON → json, colon notation → json_extract_string
SELECT o.id AS order_id,
       o.customer_id,
       f.value::STRING AS tag
FROM sample_db.orders o,
     LATERAL FLATTEN(input => PARSE_JSON(o.metadata):tags) f
WHERE o.status = 'completed';

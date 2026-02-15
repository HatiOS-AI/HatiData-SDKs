-- 004: DATEADD and DATEDIFF Snowflake date functions
-- Tests: DATEADD('day', n, date) → date + INTERVAL 'n days'
--        DATEDIFF('day', d1, d2) → date_diff('day', d1, d2)
--        CURRENT_DATE() → CURRENT_DATE
SELECT id,
       order_date,
       DATEADD('day', 30, order_date::DATE) AS due_date,
       DATEDIFF('day', order_date::DATE, CURRENT_DATE()) AS days_since
FROM sample_db.orders
WHERE DATEDIFF('day', order_date::DATE, CURRENT_DATE()) < 90;

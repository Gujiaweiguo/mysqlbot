SELECT date(register_time) AS reg_day, COUNT(*) AS new_members
FROM em_members
WHERE id BETWEEN 1001001 AND 1001012
GROUP BY 1
ORDER BY 1;

SELECT source, COUNT(*) AS member_count
FROM em_members
WHERE id BETWEEN 1001001 AND 1001012
GROUP BY source
ORDER BY source;

SELECT COALESCE(sex, 'unknown') AS sex, grade_id, COUNT(*) AS member_count
FROM em_members
WHERE id BETWEEN 1001001 AND 1001012
GROUP BY 1, 2
ORDER BY 1, 2;

SELECT member_id, COUNT(*) AS active_days
FROM em_member_actives
WHERE id BETWEEN 500001 AND 500028
GROUP BY member_id
ORDER BY active_days DESC, member_id;

SELECT a.name, COUNT(ap.id) AS apply_count
FROM em_activities a
LEFT JOIN em_activity_applies ap ON ap.activity_id = a.id
WHERE a.id BETWEEN 9001 AND 9003
GROUP BY a.id, a.name
ORDER BY apply_count DESC, a.id;

SELECT p.plan_name, COUNT(l.id) AS trigger_count, SUM(l.amount) AS trigger_amount, SUM(l.integral) AS send_integral
FROM em_marketing_plans p
LEFT JOIN em_market_plan_logs l ON l.plan_id = p.id
WHERE p.id BETWEEN 9001 AND 9003
GROUP BY p.id, p.plan_name
ORDER BY trigger_amount DESC, p.id;

SELECT s.shop_name,
       COUNT(t.id) AS order_count,
       COUNT(DISTINCT t.member_id) AS member_count,
       ROUND(SUM(t.amount)::numeric, 2) AS total_amount,
       ROUND(AVG(t.amount)::numeric, 2) AS avg_order_value
FROM em_trades t
JOIN em_order_write_off_records w ON w.tid = t.tid
JOIN em_shops s ON s.id = w.write_off_shop
WHERE t.id BETWEEN 200001 AND 200020
GROUP BY s.id, s.shop_name
ORDER BY total_amount DESC, s.id;

SELECT t.member_id, COUNT(*) AS order_count, ROUND(SUM(t.amount)::numeric, 2) AS total_amount
FROM em_trades t
WHERE t.id BETWEEN 200001 AND 200020
GROUP BY t.member_id
ORDER BY order_count DESC, total_amount DESC, t.member_id;

SELECT 'seeded_members' AS check_name, COUNT(*) AS actual_count, 12 AS expected_count
FROM em_members
WHERE id BETWEEN 1001001 AND 1001012
UNION ALL
SELECT 'seeded_activities', COUNT(*), 3
FROM em_activities
WHERE id BETWEEN 9001 AND 9003
UNION ALL
SELECT 'seeded_applies', COUNT(*), 18
FROM em_activity_applies
WHERE id BETWEEN 91001 AND 91018
UNION ALL
SELECT 'seeded_plan_logs', COUNT(*), 9
FROM em_market_plan_logs
WHERE id BETWEEN 91001 AND 91009
UNION ALL
SELECT 'seeded_trades', COUNT(*), 20
FROM em_trades
WHERE id BETWEEN 200001 AND 200020
UNION ALL
SELECT 'seeded_writeoffs', COUNT(*), 20
FROM em_order_write_off_records
WHERE id BETWEEN 400001 AND 400020
UNION ALL
SELECT 'seeded_actives', COUNT(*), 28
FROM em_member_actives
WHERE id BETWEEN 500001 AND 500028;

SELECT 'plan_log_trade_join' AS check_name, COUNT(*) AS actual_count, 9 AS expected_count
FROM em_market_plan_logs l
JOIN em_trades t ON t.tid = l.order_no
WHERE l.id BETWEEN 91001 AND 91009
  AND t.id BETWEEN 200001 AND 200020;

SELECT 'writeoff_trade_join' AS check_name, COUNT(*) AS actual_count, 20 AS expected_count
FROM em_order_write_off_records w
JOIN em_trades t ON t.tid = w.tid
WHERE w.id BETWEEN 400001 AND 400020
  AND t.id BETWEEN 200001 AND 200020;

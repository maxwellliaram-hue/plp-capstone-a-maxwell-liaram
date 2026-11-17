-- =====================================================================
-- Duka Electronics H1 2026 - analytical SQL (SQLite dialect)
-- Database : data/duka.db  (built in notebooks/01_cleaning.ipynb)
-- Tables   : orders (grain = one order line), customers, products
-- Revenue  : net_revenue = quantity * unit_price * (1 - discount_pct/100)
--            counted for is_completed = 1 only (excludes Returned/Cancelled)
-- Each query starts with a "-- Qn:" header so notebook 03 can run them.
-- =====================================================================

-- Q1: Which branches are growing or shrinking? Quarter-on-quarter revenue by branch.
-- Technique: CTE + window function LAG() over each branch's quarters.
WITH q AS (
    SELECT branch, quarter, ROUND(SUM(net_revenue)) AS revenue
    FROM orders
    WHERE is_completed = 1
    GROUP BY branch, quarter
)
SELECT branch,
       quarter,
       revenue,
       LAG(revenue) OVER (PARTITION BY branch ORDER BY quarter) AS prev_quarter_revenue,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (PARTITION BY branch ORDER BY quarter))
             / LAG(revenue) OVER (PARTITION BY branch ORDER BY quarter), 1) AS qoq_growth_pct
FROM q
ORDER BY branch, quarter;

-- Q2: Which product categories drive revenue versus order volume?
-- Technique: JOIN orders to products; SUM() OVER () turns group totals into shares.
SELECT p.category,
       COUNT(*)                                   AS order_lines,
       ROUND(SUM(o.net_revenue))                  AS revenue,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                         AS pct_of_orders,
       ROUND(100.0 * SUM(o.net_revenue) / SUM(SUM(o.net_revenue)) OVER (), 1)     AS pct_of_revenue
FROM orders o
JOIN products p ON p.product_id = o.product_id
WHERE o.is_completed = 1
GROUP BY p.category
ORDER BY revenue DESC;

-- Q3: Which individual products are proven, high-volume revenue earners?
-- Technique: GROUP BY with HAVING (filters AFTER aggregation).
SELECT p.product_name,
       p.category,
       COUNT(*)                          AS order_lines,
       ROUND(SUM(o.net_revenue))         AS revenue,
       ROUND(AVG(o.discount_pct), 1)     AS avg_discount_pct
FROM orders o
JOIN products p ON p.product_id = o.product_id
WHERE o.is_completed = 1
GROUP BY p.product_id, p.product_name, p.category
HAVING COUNT(*) >= 150 AND SUM(o.net_revenue) >= 10000000
ORDER BY revenue DESC;

-- Q4: What is each branch's month-on-month trend?
-- Technique: window function LAG() partitioned by branch.
WITH m AS (
    SELECT branch, month, ROUND(SUM(net_revenue)) AS revenue
    FROM orders
    WHERE is_completed = 1
    GROUP BY branch, month
)
SELECT branch,
       month,
       revenue,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (PARTITION BY branch ORDER BY month))
             / LAG(revenue) OVER (PARTITION BY branch ORDER BY month), 1) AS mom_growth_pct
FROM m
ORDER BY branch, month;

-- Q5: What are the top two products by revenue inside each category?
-- Technique: RANK() window function, PARTITION BY category, filtered in an outer query.
WITH ranked AS (
    SELECT p.category,
           p.product_name,
           ROUND(SUM(o.net_revenue)) AS revenue,
           RANK() OVER (PARTITION BY p.category ORDER BY SUM(o.net_revenue) DESC) AS rank_in_category
    FROM orders o
    JOIN products p ON p.product_id = o.product_id
    WHERE o.is_completed = 1
    GROUP BY p.category, p.product_name
)
SELECT category, rank_in_category, product_name, revenue
FROM ranked
WHERE rank_in_category <= 2
ORDER BY category, rank_in_category;

-- Q6: Do returns or cancellations differ by branch (a possible cause of the Q2 drop)?
-- Technique: conditional aggregation over ALL order statuses.
SELECT branch,
       COUNT(*)                                                        AS order_lines,
       ROUND(100.0 * SUM(order_status = 'Returned')  / COUNT(*), 2)    AS return_rate_pct,
       ROUND(100.0 * SUM(order_status = 'Cancelled') / COUNT(*), 2)    AS cancel_rate_pct
FROM orders
GROUP BY branch
ORDER BY return_rate_pct DESC;

-- Q7: Who are the customers? Revenue by age band for identified customers.
-- Technique: JOIN on the pseudonymised customer_key (no personal data used).
SELECT c.age_band,
       COUNT(DISTINCT o.customer_key)                                   AS customers,
       ROUND(SUM(o.net_revenue))                                        AS revenue,
       ROUND(SUM(o.net_revenue) / COUNT(DISTINCT o.customer_key))       AS revenue_per_customer
FROM orders o
JOIN customers c ON c.customer_key = o.customer_key
WHERE o.is_completed = 1
GROUP BY c.age_band
ORDER BY revenue DESC;

-- Q8: How do customers pay, by sales channel?
-- Technique: GROUP BY two columns with a window total per channel for the % share.
SELECT channel,
       payment_method,
       COUNT(*) AS order_lines,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY channel), 1) AS pct_within_channel
FROM orders
WHERE is_completed = 1 AND channel <> 'Unknown'
GROUP BY channel, payment_method
ORDER BY channel, order_lines DESC;

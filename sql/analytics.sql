-- Use integer cents for exact reconciliation. Convert only for presentation.
SELECT country, COUNT(*) AS purchases, SUM(purchase_cents)/100.0 AS revenue_cad
FROM analytics_purchases GROUP BY country ORDER BY revenue_cad DESC;
SELECT year_month, SUM(purchase_cents)/100.0 AS revenue_cad
FROM analytics_purchases GROUP BY year_month ORDER BY year_month;
SELECT age_group, COUNT(*) AS purchases, AVG(purchase_amount) AS average_purchase_cad
FROM analytics_purchases GROUP BY age_group;

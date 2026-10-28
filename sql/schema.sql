PRAGMA foreign_keys=ON;
CREATE TABLE dim_country (
 country_code TEXT PRIMARY KEY, country TEXT NOT NULL UNIQUE, region TEXT NOT NULL
);
CREATE TABLE dim_customer (
 customer_id INTEGER PRIMARY KEY CHECK(customer_id>0), name TEXT NOT NULL,
 age INTEGER NOT NULL CHECK(age BETWEEN 0 AND 120), age_group TEXT NOT NULL
);
CREATE TABLE dim_date (
 date_key TEXT PRIMARY KEY, year INTEGER NOT NULL, month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
 year_month TEXT NOT NULL
);
CREATE TABLE fact_purchase (
 purchase_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES dim_customer(customer_id),
 country_code TEXT NOT NULL REFERENCES dim_country(country_code), date_key TEXT NOT NULL REFERENCES dim_date(date_key),
 purchase_cents INTEGER NOT NULL CHECK(purchase_cents BETWEEN 1 AND 500000),
 purchase_category TEXT NOT NULL CHECK(purchase_category IN ('Low','Medium','High','VIP')),
 currency TEXT NOT NULL CHECK(currency='CAD')
);
CREATE INDEX ix_purchase_country ON fact_purchase(country_code);
CREATE INDEX ix_purchase_date ON fact_purchase(date_key);
CREATE VIEW analytics_purchases AS
 SELECT p.purchase_id,c.customer_id,c.name,c.age,c.age_group,k.country,k.country_code,k.region,
 d.date_key AS date,d.year_month,p.purchase_cents,p.purchase_cents/100.0 AS purchase_amount,
 p.purchase_category,p.currency
 FROM fact_purchase p JOIN dim_customer c USING(customer_id)
 JOIN dim_country k USING(country_code) JOIN dim_date d ON p.date_key=d.date_key;

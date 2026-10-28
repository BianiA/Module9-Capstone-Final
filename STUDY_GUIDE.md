# Explain your project

This project turns 10,000 simulated customer purchases into validated data, a SQLite database and an Excel dashboard.

- **Ingestion:** reading the original CSV. The profiles came from a public fake-user API; purchase values and dates were generated with a fixed random seed.
- **Cleaning:** checking types, dates, blank values and duplicates, and standardizing whitespace.
- **Integration:** joining a country lookup to add country codes and regions.
- **Enrichment:** deriving age groups, spending categories and month.
- **Validation:** requiring complete valid rows, real lookup matches, unique IDs and matching database totals. Bad input stops publication and is logged.
- **Data model:** a purchase fact table linked to customer, country and date dimension tables. The ERD shows those relationships.
- **SQLite:** a database stored in one file. Keys and constraints help keep the data consistent.
- **Orchestration:** scheduling the same pipeline to run automatically. The GitHub workflow is prepared; it needs publishing and a verified hosted run.
- **Monitoring:** run statuses, timestamps, durations, validation results and failures saved in logs.
- **Dashboard:** Excel formulas and charts summarize the 10,000 validated rows. The file must be refreshed after changing the underlying dataset.

## A short explanation you can practice
“The pipeline reads synthetic purchase records, cleans them and enriches them with a country lookup. It checks the records, loads a SQLite star schema and reconciles the row count and purchase total. It records run status and errors in logs. The Excel dashboard summarizes purchases by country, month, spending category and age group. All amounts are simulated CAD values, so the charts do not describe real customers.”

## Likely questions
- Why integer cents? To compare money totals exactly rather than accumulating floating-point rounding errors.
- Why preserve raw data? To trace processed records back to the original snapshot and rerun the same analysis.
- Why reject bad input? To avoid publishing incomplete or misleading analytical data.
- Is this a predictive model? No. The supplied instructions require an analytical data model and ERD, not a machine-learning prediction model.
- What is left to deploy? Publish the repository, enable/run the schedule, and check real hosted-run evidence.
- Why use a public API instead of Mockaroo? The rubric explicitly permits public APIs.
- Why Excel? The Windows visualization step explicitly permits Power BI or Excel.

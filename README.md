# Duka Electronics Sales Performance Analysis (H1 2026)

## Business Problem
The Commercial Director of Duka Electronics must decide **where to focus marketing spend and management attention in H2 2026**. The dataset has never been analysed properly: this project answers which branches and products drive growth, whether the Q2 changes are real, and what to do next.

## Key Findings
- Total revenue is flat (**−1.3%** Q2 vs Q1; 350.9M KES), but this hides a split: **Eldoret +74%**, **Mombasa −27%**, **Nakuru −29%**; Nairobi (+3%) and Kisumu (+10%) are stable.
- Mann-Whitney tests (Bonferroni α = 0.01) confirm the Eldoret, Mombasa and Nakuru changes are real (medium effect sizes); Nairobi and Kisumu are not significant.
- **Smartphones + laptops are 22% of order lines but 73% of revenue**; ~85% of the Mombasa/Nakuru decline is in these two categories.
- Returns, product mix and discounting do **not** explain the decline (Cramér's V = 0.02).

## Tools
Python (pandas, NumPy, Matplotlib, Seaborn, SciPy) · SQLite · openpyxl · ReportLab · Looker Studio

## Repository Structure
```
data/
  generate_data.py      synthetic data generator (seeded)
  raw/                  messy raw CSVs
  clean/                cleaned CSVs + cleaning_log.csv
  README.md             source, licence, ethics & privacy statement
src/
  cleaning.py           audit_quality() and clean_data() -> (tables, log)
  build_reports.py      builds Excel workbook, dashboard.png, slides.pdf
notebooks/
  01_cleaning.ipynb     six-dimension audit, cleaning log, load to SQLite
  02_eda.ipynb          univariate, bivariate, segmentation
  03_analysis.ipynb     SQL via pd.read_sql, KPI scorecard, statistical tests
sql/queries.sql         8 commented queries (JOIN, GROUP BY + HAVING, window functions)
reports/
  executive_summary.md  1-2 page summary
  dashboard.png         dashboard screenshot (live link below)
  slides.pdf            9 slides
  stakeholder_summary.xlsx   filterable summary with live formulas
  looker_studio_guide.md     steps to rebuild the live dashboard
  looker_studio_data.csv     flat, de-identified data source for the dashboard
  figures/, tables/          charts and result tables
requirements.txt
```

## How to Run
```bash
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute --inplace notebooks/01_cleaning.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/02_eda.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/03_analysis.ipynb
python src/build_reports.py
```
Or open the notebooks in order with `jupyter notebook notebooks/`. Run order matters: 01 → 02 → 03 → `build_reports.py`.

## Dashboard
[Link to live Looker Studio dashboard](PASTE-YOUR-LINK-HERE) · Screenshot: `reports/dashboard.png`

## Author
Maxwell Liaram · [LinkedIn](https://www.linkedin.com/in/maxwell-liaram-6227a3382) · maxwellliaram@gmail.com

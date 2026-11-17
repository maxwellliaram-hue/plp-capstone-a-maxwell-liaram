# Executive Summary — Duka Electronics H1 2026 Sales Performance

**To:** Commercial Director  **From:** Maxwell Liaram, Junior Data Analyst (maxwellliaram@gmail.com)  **Decision:** where to focus H2 2026 marketing spend and management attention

## The Big Idea
Total revenue looks flat (**−1.3%** Q2 vs Q1, 350.9M KES net for H1), but that stability is an illusion: **Eldoret grew +74% while Mombasa (−27%) and Nakuru (−29%) shrank**, and the shrinkage is concentrated in smartphones and laptops. H2 spend should follow that split, not the company average.

## Key findings
1. **The branch split is real, not noise.** Mann-Whitney tests on daily revenue (Bonferroni α = 0.01) show Mombasa −28% (95% CI −38% to −16%), Nakuru −30% (CI −41% to −17%) and Eldoret +73% (CI +45% to +106%) are statistically significant, with medium effect sizes (|r| = 0.32–0.46). Nairobi (+2%) and Kisumu (+9%) are statistically flat.
2. **Revenue is concentrated.** Smartphones and laptops are 22% of order lines but **73% of revenue**; four SKUs (iPhone-style 15, Galaxy-style S24, UltraSlim 13, ProBook 15) deliver 58%. About **85%** of the Mombasa/Nakuru fall (16.8M of 19.8M KES) is in these two categories.
3. **Nairobi is the anchor.** 37.8% of revenue, stable across both quarters.
4. **It is not returns, mix or discounting.** Return rates are 4.3–5.7% (Cramér's V = 0.02, negligible); category mix is near-identical across branches; discounts cost 3.2% of gross sales and show no link to basket size.

## Recommendations
| # | Action | Quantified target |
|---|---|---|
| 1 | Run a recovery review in **Mombasa and Nakuru** now: smartphone/laptop stock levels, local competitor pricing and promotions, staffing. | Restoring Q1 run-rate is worth **~19.8M KES per quarter**. |
| 2 | Weight H2 marketing toward **Eldoret** and protect its stock. | Sustaining the Q2 run-rate = **~31M KES per quarter** (+13.4M vs Q1). |
| 3 | Guarantee availability of the **top four SKUs** in every branch. | These four earn **58%** of revenue. |
| 4 | **A/B test** reduced discounts on accessories before any permanent change. | Accessories discounts cost **0.8M KES** in H1; a pilot limits risk. |
| 5 | Make payment method and customer ID mandatory at point of sale. | Currently **2.8%** and **1.7%** of sales are unknown. |

## Business impact
If Mombasa and Nakuru return to their Q1 level and Eldoret holds its Q2 level, H2 revenue would be roughly **20M KES per quarter higher** than a "Q2 repeats" baseline for the two declining branches, while protecting ~13M KES per quarter already gained in Eldoret.

## Limitations (please read)
- **Simulated data:** this capstone uses a generated dataset; real conclusions require real data.
- **Short window:** six months, so no seasonality baseline. A Q2 dip could partly be seasonal.
- **No cost or margin data:** revenue is not profit; recommendations should be re-checked against margin.
- **The tests show *that*, not *why*:** the cause of the Mombasa/Nakuru fall (competition, stock, staffing, local economy) needs a field check. Daily values are treated as independent, ignoring weekday seasonality.
- **Data quality:** 449 of 15,816 raw order lines (2.8%) were removed, and 275 sales have unknown customers. Imputed prices used the product list price (branch prices differ by about 1.5%).
- **Customer metrics** (e.g. repeat rate) are indicative only because the customer base is small and simulated.

*Full workings: `notebooks/01_cleaning.ipynb`, `02_eda.ipynb`, `03_analysis.ipynb`, `sql/queries.sql`.*

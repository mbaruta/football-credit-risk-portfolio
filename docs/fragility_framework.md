# Financial Fragility Framework — final full-history reference

## Purpose

Descriptive comparison of financial fragility within the project's documented
Brazilian football club-year sample. This **is not a credit rating, probability
of default, lending decision, or forward-looking prediction**.

## Reference population

The final published snapshot contains the complete financial CORE: **339
club-years, 35 clubs, fiscal years 2016–2025**. All documented rows belong to
one retrospective percentile reference population. Eleven unsupported
club-years remain gaps; they are not imputed.

This replaces the superseded 27-club, 135-row historical framework. The method
retains its three indicators, rank-percentile transformation and equal weights,
but the change in reference population **requires all scores to be recalculated**.
Old and new scores are not directly interchangeable.

## Indicators and components

- `current_liquidity = current_assets / current_liabilities`;
  `liquidity_risk = (1 - rank_pct(current_liquidity)) × 100`.
- `liability_ratio = total_liabilities / total_assets`;
  `solvency_risk = rank_pct(liability_ratio) × 100`.
- `return_on_assets = net_result / total_assets`;
  `profitability_risk = (1 - rank_pct(return_on_assets)) × 100`.

`rank_pct` uses pandas' ascending percentage rank over **all 339 documented
club-years together**, with average ranks for ties. The descriptive score is
the arithmetic mean of the three risk components. Higher values correspond to
greater relative fragility in this particular retrospective sample.

`negative_equity` and `previous_loss_rate` are supplementary context and are
**not part of the composite score**. The previous-loss rate is the share of
preceding **observed** years with negative `net_result`; the current year is
excluded. It may use older observations across a documentary gap, whereas
annual changes explicitly require consecutive fiscal years.

## Interpretation and caveats

Because percentile ranks use the entire 2016–2025 dataset, scores for earlier
years incorporate the distribution of later observations. This is appropriate
for the **retrospective descriptive dashboard**, but these scores must **not**
be interpreted or used as real-time historical predictions or as inputs to the
project's separate t→t+1 experiments.

Scores are comparable *within this fixed published snapshot*. Adding years or
clubs in a future data release requires regenerating all ranks and documenting
a new reference snapshot; comparing scores from different releases without
recalibration context is misleading. Reporting-perimeter changes, differing
statement lengths, and accounting semantics still constrain comparison.

## Calculation and verification

1. `src/build_financial_fragility.py` reads `data/processed/core_financials.csv`.
2. It validates uniqueness, complete numeric CORE, nonzero denominators, and
   the accepted accounting-identity tolerance of 1 BRL thousand.
3. It recalculates every ratio, pooled percentile, component, composite score,
   and historical-loss descriptor from the expanded CORE.
4. It creates `data/processed/financial_fragility_scores.csv` and
   `data/processed/fragility_reference.csv`.
5. Notebook 03 rechecks the outputs and repeats association, weight, and
   normalization sensitivity analyses **using the new full-history sample**.
6. SQL Server stores the full-score data, and Power BI reads a gap-aware
   year-over-year comparison view.

The final dashboard can filter 2016–2025 and all 35 clubs. Individual years may
contain fewer than 35 clubs where a documentary gap exists (e.g. 2025).

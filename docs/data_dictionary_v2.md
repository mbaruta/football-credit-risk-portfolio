# Data Dictionary v2.1

## 1. Purpose and status

This document defines the canonical financial data rules used in the final Football Credit Risk project.

It supersedes `data_dictionary_v1.md` as the current specification. Version 1 is retained as a historical record of the feasibility stage.

**Version:** 2.1

**Status:** FINAL / FROZEN

The final financial CORE covers 35 Brazilian football clubs over fiscal years 2016-2025.

- Potential club-years: 350
- Usable financial club-years: 339
- Definitive documentary gaps: 11
- Coverage: 96.9%

The objective is comparability, provenance and auditability. A documentary gap is preferable to an unsupported reconstruction.

---

## 2. Unit of analysis

The analytical unit is:

`football club x fiscal_year`

The financial perimeter follows the official entity or consolidated presentation selected for the professional football operation in each fiscal year.

Association/SAF transitions and other perimeter decisions are documented in staging and in the project collection history.

Financial statements from different entities are never manually combined unless the official source itself provides the consolidated presentation used by the project.

---

## 3. Financial staging schema

The canonical staging worksheet is `financial_data`, with exactly nine fields:

- `club`
- `fiscal_year`
- `statement`
- `account_original`
- `value_original`
- `unit`
- `standard_variable`
- `source_file`
- `notes`

`account_original` preserves source terminology.

`standard_variable` stores the harmonized accounting concept.

Multiple staging rows may map to the same `standard_variable` when a documented accounting variable is composed of multiple published components.

---

## 4. CORE variables

The final CORE contains exactly seven variables.

### 4.1 `cash`

Cash and immediately available financial resources.

Preferred source: Balance Sheet.

Rules:

- Prefer an explicitly published subtotal.
- Components may be summed only when the aggregation is unambiguous.
- Receivables and non-immediate financial assets are excluded.

Expected sign: non-negative.

### 4.2 `current_assets`

Total assets classified as current.

Preferred source: Balance Sheet.

Rules:

- Prefer the published current-assets subtotal.
- When absent, an accounting-identical derivation is allowed only when all components are explicitly documented.
- No discretionary allocation or approximation is permitted.

Expected sign: non-negative.

### 4.3 `total_assets`

Total assets recognized at fiscal year-end.

Preferred source: Balance Sheet.

Use the published total whenever available.

Expected sign: non-negative.

### 4.4 `current_liabilities`

Total obligations classified as current liabilities at fiscal year-end.

Preferred source: Balance Sheet.

Use the published subtotal or an economically equivalent official presentation.

Expected sign: non-negative.

### 4.5 `total_liabilities`

Total obligations excluding equity.

Preferred source: Balance Sheet.

Rules:

1. Prefer a published liabilities subtotal that clearly excludes equity.
2. Otherwise use an accounting-identical derivation from documented components.
3. `current_liabilities + noncurrent_liabilities` is the standard derivation when applicable.
4. `future_results` may enter the construction only where required by the source accounting presentation.
5. A line named `Total do Passivo` is not automatically interpreted as liabilities; its accounting meaning must first be verified.

Expected sign: non-negative.

### 4.6 `equity`

Published residual equity attributable to the relevant entity or consolidated group.

Negative equity remains negative.

For a consolidated perimeter, `equity` means **total consolidated equity, including non-controlling interests**.

When parent/controller equity and non-controlling interest are published separately, both may map to `equity`; the ETL intentionally sums multiple staging rows mapped to the same standardized variable.

This rule is part of the approved final CORE methodology.

Expected sign: positive or negative.

### 4.7 `net_result`

Final accounting result for the fiscal year.

Sign convention:

- profit / surplus -> positive
- loss / deficit -> negative

Preferred source hierarchy:

1. Income Statement (DRE).
2. Statement of Changes in Equity (DMPL), when necessary.
3. Cash Flow Statement (DFC), only when the final accounting result is supported there and a preferred statement is unavailable.

If DRE and DMPL differ, preserve the DRE unless a formal restatement explicitly supersedes it.

---

## 5. Approved helper variables

Approved staging helpers include:

- `noncurrent_liabilities`
- `noncurrent_assets_component`
- `future_results`

They exist only to construct or validate CORE variables and are removed from the final CORE dataset.

---

## 6. Direct and derived values

Priority:

`direct published value > approved accounting-identical derivation`

A derivation is allowed only when:

- every component is document-supported;
- the accounting relationship is unambiguous;
- no estimate, interpolation, discretionary allocation or balancing plug is required.

Approved examples include:

`total_liabilities = current_liabilities + noncurrent_liabilities`

and, when unequivocally supported:

`current_assets = total_assets - noncurrent_assets_component`

A club-year is usable only when all seven CORE variables are document-supported.

---

## 7. Units and precision

Staging preserves the original value and published unit.

Approved monetary units include:

- `BRL`
- `BRL_thousands`

The ETL standardizes monetary values to BRL thousands.

`value_original` is never overwritten by the analytical conversion.

---

## 8. Source and provenance rules

Every staging row retains source lineage through `source_file`.

A staging row may be created only from a PDF/file accepted into the project workflow.

Web research may locate candidate source documents, but web evidence alone does not create staging rows.

Reconstructed documents are accepted only under the frozen reconstruction rules: full CORE support, explicit provenance and no estimates or balancing plugs.

If any CORE variable is unsupported, the club-year remains a documentary gap.

---

## 9. Restatements and comparative figures

A later formal restatement or reclassification supersedes the affected original analytical value.

`latest formal official restatement > affected original value`

A changed comparative figure is not automatically treated as a restatement without documentary support.

Historical source files remain preserved even when a later formal restatement becomes canonical.

---

## 10. ETL behavior and quality assurance

The financial ETL intentionally uses aggregation when multiple documented staging components share the same `standard_variable`.

Unit conversion:

`value_brl_thousands = value_original / 1000 if unit == 'BRL' else value_original`

The accounting identity is checked as:

`total_assets = total_liabilities + equity`

Small published rounding differences may be tolerated. Material inconsistencies require investigation before a club-year is accepted.

Final ETL/CORE QA status: **CLOSED**.

The approved 2016-2025 CORE has:

- 339 usable club-years;
- no missing CORE variable in usable years;
- no accounting inconsistency above tolerance.

---

## 11. Final historical corrections retained in the methodology

The final CORE incorporates the approved historical QA corrections made before the ETL/CORE phase was closed.

### Non-controlling interest

For consolidated equity:

- Chapecoense 2020 includes BRL 171 thousand of non-controlling interest and closes with consolidated `equity = -105899`.
- Botafogo 2021 includes BRL 8 thousand of non-controlling interest and closes with consolidated `equity = -790903`.

### Santos 2018

Santos 2018 uses the formally re-presented balance-sheet values adopted in the final validated CORE:

- `current_liabilities = 368167`
- `total_liabilities = 603314`
- `equity = -339843`
- `total_assets = 263471`

These corrections are closed historical decisions and are not pending methodological questions.

---

## 12. Final documentary coverage

Project window: `2016-2025`

Clubs: `35`

Potential club-years: `350`

Usable financial club-years: `339`

Coverage: `96.9%`

The 11 definitive documentary gaps are:

- Cuiabá - 2016
- Mirassol - 2019
- CSA - 2025
- Figueirense - 2024
- Figueirense - 2025
- Remo - 2016
- Remo - 2017
- Remo - 2018
- Vitória - 2017
- Vitória - 2018
- Vitória - 2019

These are closed documentary gaps, not pending observations.

---

## 13. Financial Fragility Framework — complete historical reference

The final descriptive framework uses the **same documented financial CORE**:
35 clubs, 2016–2025, 339 available club-years in the published snapshot.

Its three dimensions remain `current_liquidity`, `liability_ratio` and
`return_on_assets`, transformed into percentile-based risk components with
equal weights. `negative_equity` and `previous_loss_rate` are auxiliary only.

All percentile ranks are **recalculated from the entire retrospective CORE**.
The earlier 27-club, 135-row reference is superseded; old percentile scores
must not be mixed with the complete-history scores. Previous-loss history uses
only preceding observed years, while SQL year-over-year score differences
require consecutive fiscal years.

This framework is descriptive and **not** a credit rating, default-probability
model, or feature in the project's separate predictive experiments. See
[`docs/fragility_framework.md`](fragility_framework.md) for formulas,
reproducibility, limitations, and interpretation.

---

## 14. Final downstream files

Canonical financial CORE:

`data/processed/core_financials.csv`

Final predictive datasets:

- `data/processed/modeling_data_v1.csv`
- `data/processed/modeling_data_v2.csv`

The CORE also feeds:

- `data/processed/financial_sporting_data.csv`
- the predictive notebooks;
- the final results workflow.

The active complete-history descriptive artifacts are:

- `data/processed/fragility_reference.csv`
- `data/processed/financial_fragility_scores.csv`

Both are rebuilt from `data/processed/core_financials.csv` by
`src/build_financial_fragility.py`. The SQL dashboard uses the latter.

---

## 15. Detailed accounting expansion

Additional accounting variables such as revenue, operating result, financial result, financial expenses and personnel expenses were investigated after the CORE was completed.

They were not added to the final predictive layer because historical coverage and semantic comparability were insufficient for a defensible longitudinal cross-club dataset.

This is a closed methodological decision, not an unfinished collection task.

---

## 16. Version control

Changes to any of the following require a new documented methodological revision:

- CORE variable membership;
- variable definitions;
- accounting perimeter;
- direct/derived construction rules;
- restatement treatment;
- sign convention;
- source/provenance rules.

Version 2.1 retains the final financial CORE methodology and documents the full-history descriptive framework recalibration.

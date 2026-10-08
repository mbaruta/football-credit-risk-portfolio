# Data Dictionary v1.0

> **Historical version.** This document records the original CORE dictionary used during the feasibility stage. It is retained for methodological history and is superseded by [Data Dictionary v2](data_dictionary_v2.md) for the final 2016-2025 project.

## 1. Purpose

This document defines the canonical accounting variables used in the CORE dataset of the Football Credit Risk project.

The dictionary was defined after a structural review of the 2021–2025 financial statements of six Brazilian football clubs:

- Palmeiras
- Corinthians
- São Paulo
- Santos
- Red Bull Bragantino
- Mirassol

The objective is to ensure that variables used in the analytical dataset represent equivalent economic concepts across clubs and years, despite differences in accounting presentation, terminology and level of disclosure.

This version is considered FROZEN.

Any future change to the definitions or construction rules must be explicitly documented as a new methodological revision.

---

## 2. Unit of analysis

The analytical unit is:

`club × fiscal_year`

The CORE dataset will contain one observation per club and fiscal year.

The accounting perimeter is the legal entity represented in the club's official financial statements.

---

## 3. CORE variables

### 3.1 cash

**Standard variable:** `cash`

**Definition:**  
Cash and immediately available financial resources, including cash on hand, bank balances and short-term investments classified by the entity as cash equivalents or immediately available funds.

**Preferred source:**  
Balance Sheet.

**Construction rule:**

1. Use the explicitly published subtotal for:
   - Caixa e equivalentes de caixa;
   - Disponibilidades;
   - or an economically equivalent account.
2. If the subtotal is not explicitly published, it may be reconstructed only when all components are clearly identified and their aggregation is unambiguous.
3. Do not include receivables or other current financial assets that are not immediately available.

**Expected sign:**  
Non-negative.

---

### 3.2 current_assets

**Standard variable:** `current_assets`

**Definition:**  
Total assets classified as current in the Balance Sheet.

**Preferred source:**  
Balance Sheet.

**Construction rule:**

1. Prefer the explicitly published `Ativo Circulante` subtotal.
2. If no subtotal is published, it may be derived from clearly identified Balance Sheet components.
3. No estimation or approximate allocation is permitted.

**Expected sign:**  
Non-negative.

---

### 3.3 total_assets

**Standard variable:** `total_assets`

**Definition:**  
Total assets recognized by the entity at the end of the fiscal year.

**Preferred source:**  
Balance Sheet.

**Construction rule:**

Use the published total assets amount.

No reconstructed value should be used when an explicit total is available.

**Expected sign:**  
Non-negative.

---

### 3.4 current_liabilities

**Standard variable:** `current_liabilities`

**Definition:**  
Total obligations classified as current liabilities at the end of the fiscal year.

**Preferred source:**  
Balance Sheet.

**Construction rule:**

Use the explicitly published `Passivo Circulante` subtotal or its economically equivalent presentation.

**Expected sign:**  
Non-negative.

---

### 3.5 total_liabilities

**Standard variable:** `total_liabilities`

**Definition:**  
Total obligations recognized by the entity, excluding equity.

Therefore:

`total_liabilities ≠ total liabilities and equity`

**Preferred source:**  
Balance Sheet.

**Construction rule:**

1. Use an explicitly published total liabilities subtotal when it excludes equity.
2. Otherwise calculate:

`total_liabilities = current_liabilities + noncurrent_liabilities`

3. Do not use a line called `Total do Passivo` automatically. Its accounting meaning must first be verified because some statements use this label for liabilities plus equity.

**Expected sign:**  
Non-negative.

---

### 3.6 equity

**Standard variable:** `equity`

**Definition:**  
Residual equity of the entity after deducting total liabilities from total assets.

Depending on the entity, the original financial statement may use terminology such as:

- Patrimônio Líquido;
- Patrimônio Social;
- Passivo a Descoberto.

**Preferred source:**  
Balance Sheet.

**Construction rule:**

Use the explicitly published total equity amount.

Negative equity or uncovered liabilities must remain negative.

**Expected sign:**  
Positive or negative.

---

### 3.7 net_result

**Standard variable:** `net_result`

**Definition:**  
Final accounting result for the fiscal year after all recognized revenues, expenses, financial effects, taxes and other effects included in the entity's income statement.

The terminology used by the original entity may include:

- Superávit do exercício;
- Déficit do exercício;
- Lucro líquido;
- Prejuízo do exercício.

**Preferred source:**  
Income Statement.

**Construction rule:**

Use the final reported accounting result of the entity.

Sign convention:

- profit / surplus → positive;
- loss / deficit → negative.

**Expected sign:**  
Positive or negative.

---

## 4. Auxiliary staging variables

Auxiliary variables may be stored when required to construct or validate a CORE variable.

They are not part of the final CORE analytical dataset.

Currently approved auxiliary variables include:

### noncurrent_liabilities

Total liabilities classified as non-current.

Primary use:

`total_liabilities = current_liabilities + noncurrent_liabilities`

when total liabilities excluding equity are not directly published.

### noncurrent_assets

Total assets classified as non-current.

It may be stored when required to reconstruct or validate current assets or total assets.

Additional auxiliary variables may only be introduced when they are necessary for a reproducible accounting derivation.

They must not silently become new CORE variables.

---

## 5. Source data rules

### 5.1 Original values

`value_original` must preserve the value published in the source document.

No unit conversion, inflation adjustment or analytical transformation should overwrite the original value in staging.

---

### 5.2 Units

The original unit must be preserved.

Examples:

- `BRL`
- `BRL_thousands`

Unit standardization will be performed during ETL.

The analytical dataset will use a single monetary unit.

---

### 5.3 Direct values

A value is considered direct when the required accounting concept is explicitly presented in the official financial statement.

Direct values are preferred over derived values.

---

### 5.4 Derived values

A CORE variable may be derived only when the calculation is accounting-identical and unambiguous.

Example:

`total_liabilities = current_liabilities + noncurrent_liabilities`

Derived values must be reproducible from source values stored in staging.

Approximation, discretionary allocation and semantic inference are not permitted.

---

### 5.5 Missing values

If the financial statements do not provide sufficient information to construct a variable reliably, the analytical value must be stored as:

`NULL`

A defensible missing value is preferable to a falsely comparable value.

---

## 6. Restatements and reclassifications

When a later official financial statement presents an earlier fiscal year as officially restated or reclassified, the most recent official version will be used as the canonical analytical value.

Therefore:

`latest official restatement > originally published value`

The original financial statement and its original values must remain preserved in the raw data and source lineage.

Restatement does not mean deleting historical evidence.

The analytical dataset uses the most recent official representation because it reflects the entity's latest accounting treatment of that fiscal year.

---

## 7. Accounting identity validation

For each `club × fiscal_year`, the following identity must hold:

`total_assets = total_liabilities + equity`

This identity will be tested during the QA stage.

Differences caused by rounding may be accepted within a predefined tolerance to be established during implementation.

Material differences must be investigated before the observation enters the analytical dataset.

---

## 8. Sign convention

### Balance Sheet

Assets and liabilities are stored as positive balances unless the original accounting concept is intrinsically negative.

Equity may be negative.

### Income Statement

For `net_result`:

- surplus / profit = positive;
- deficit / loss = negative.

---

## 9. Source hierarchy

Preferred source order:

1. Official annual financial statements;
2. Official restated/reclassified comparative financial statements;
3. Notes to the financial statements;
4. Official supplementary accounting statements;
5. Trial balances or equivalent supporting accounting documents, only when required.

A trial balance should not replace a formal Balance Sheet when the formal Balance Sheet is available.

---

## 10. Data lineage

Every staging record must retain sufficient information to trace the analytical value to its source.

Current lineage fields:

- `club`
- `fiscal_year`
- `statement`
- `account_original`
- `value_original`
- `unit`
- `standard_variable`
- `source_file`
- `notes`

`account_original` must preserve the terminology of the source.

`standard_variable` represents the harmonized accounting concept.

---

## 11. Extended variables

Variables outside the seven CORE variables are not part of Data Dictionary v1.0 CORE.

Examples under future evaluation include:

- revenue measures;
- operating results;
- financial result;
- financial expenses;
- personnel expenses;
- image-right expenses;
- athlete transfer results;
- broadcasting revenue;
- sponsorship revenue.

These variables will be evaluated separately after the CORE dataset is constructed and validated.

They must not be forced into cross-club equivalence before their accounting definitions are verified.

---

## 12. CORE analytical schema

The first canonical analytical dataset will have the structure:

`club`
`fiscal_year`
`cash`
`current_assets`
`total_assets`
`current_liabilities`
`total_liabilities`
`equity`
`net_result`

Expected initial size for the feasibility MVP:

`6 clubs × 5 fiscal years = 30 observations`

---

## 13. Version control

**Version:** 1.0  
**Status:** FROZEN

Any methodological change affecting:

- variable definition;
- accounting perimeter;
- construction rule;
- restatement treatment;
- sign convention;
- or CORE variable membership

must be explicitly proposed, reviewed and documented before being applied to the dataset.

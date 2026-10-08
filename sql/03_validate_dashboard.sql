-- Read-only SQL checks after executing scripts 01, importing the full CSV,
-- and executing script 02. Compare with Python's printed source counts.
USE [football_credit_risk];
GO
SELECT COUNT(*) AS club_years,
       COUNT(DISTINCT club) AS clubs,
       MIN(fiscal_year) AS min_year,
       MAX(fiscal_year) AS max_year
FROM dbo.financial_fragility_scores;
GO
SELECT fiscal_year, COUNT(*) AS documented_club_years
FROM dbo.financial_fragility_scores
GROUP BY fiscal_year ORDER BY fiscal_year;
GO
SELECT COUNT(*) AS missing_or_invalid_scores
FROM dbo.financial_fragility_scores
WHERE current_liquidity IS NULL OR liability_ratio IS NULL
   OR return_on_assets IS NULL OR financial_fragility_score IS NULL
   OR financial_fragility_score NOT BETWEEN 0 AND 100
   OR ABS(total_assets - total_liabilities - equity) > 1;
GO
SELECT COUNT(*) AS invalid_annual_change
FROM dbo.vw_financial_fragility_dashboard AS v
WHERE v.fragility_score_change IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM dbo.financial_fragility_scores AS p
    WHERE p.club = v.club AND p.fiscal_year = v.fiscal_year - 1
);
GO
-- All expected: first query matches Python counts and period;
-- missing_or_invalid_scores = 0; invalid_annual_change = 0.

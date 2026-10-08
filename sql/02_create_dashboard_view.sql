-- Recreate the dashboard view after loading the FULL historical score table.
-- Compare score changes only when the previous CALENDAR year is available.
USE [football_credit_risk];
GO
CREATE OR ALTER VIEW dbo.vw_financial_fragility_dashboard AS
WITH historical AS (
    SELECT
        s.*,
        LAG(fiscal_year) OVER (
            PARTITION BY club ORDER BY fiscal_year
        ) AS preceding_year,
        LAG(financial_fragility_score) OVER (
            PARTITION BY club ORDER BY fiscal_year
        ) AS preceding_score
    FROM dbo.financial_fragility_scores AS s
)
SELECT
    club, fiscal_year,
    cash, current_assets, total_assets, current_liabilities,
    total_liabilities, equity, net_result,
    current_liquidity, liability_ratio, return_on_assets,
    negative_equity, liquidity_risk, solvency_risk, profitability_risk,
    financial_fragility_score, previous_loss_rate,
    CASE WHEN preceding_year = fiscal_year - 1
         THEN preceding_score END AS previous_fragility_score,
    CASE WHEN preceding_year = fiscal_year - 1
         THEN financial_fragility_score - preceding_score END AS fragility_score_change
FROM historical;
GO

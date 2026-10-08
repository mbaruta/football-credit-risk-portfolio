"""Rebuild the descriptive financial fragility dataset from the approved full CORE.

Run from anywhere: python src/build_financial_fragility.py

Percentiles share one fixed retrospective reference: all available club-years
in core_financials.csv at the time of the published dataset snapshot.
This is not a probability of default, rating, or predictive feature.
"""
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = PROJECT_ROOT / 'data' / 'processed' / 'core_financials.csv'
SCORES_PATH = PROJECT_ROOT / 'data' / 'processed' / 'financial_fragility_scores.csv'
REFERENCE_PATH = PROJECT_ROOT / 'data' / 'processed' / 'fragility_reference.csv'

CORE_VARIABLES = [
    'cash', 'current_assets', 'total_assets', 'current_liabilities',
    'total_liabilities', 'equity', 'net_result',
]
INDICATORS = ['current_liquidity', 'liability_ratio', 'return_on_assets']
RISK_COMPONENTS = ['liquidity_risk', 'solvency_risk', 'profitability_risk']
OUTPUT_COLUMNS = [
    'club', 'fiscal_year', *CORE_VARIABLES, *INDICATORS,
    'negative_equity', *RISK_COMPONENTS, 'financial_fragility_score',
    'previous_loss_rate',
]


def build_fragility(core):
    """Calculate descriptive indicators and shared-sample percentile scores."""
    required = ['club', 'fiscal_year', *CORE_VARIABLES]
    missing_columns = sorted(set(required).difference(core.columns))
    if missing_columns:
        raise ValueError(f'Missing CORE columns: {missing_columns}')

    df = core[required].copy()
    if df[required].isna().any().any():
        raise ValueError('CORE has missing values in required fields')
    if df.duplicated(['club', 'fiscal_year']).any():
        raise ValueError('Duplicate club / fiscal_year keys in CORE')
    if df['club'].astype(str).str.strip().eq('').any():
        raise ValueError('Blank club names in CORE')

    df['fiscal_year'] = pd.to_numeric(df['fiscal_year'], errors='raise').astype(int)
    for name in CORE_VARIABLES:
        df[name] = pd.to_numeric(df[name], errors='raise')

    values = df[CORE_VARIABLES].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError('CORE contains non-finite numeric values')
    if (df[['total_assets', 'current_liabilities']] <= 0).any().any():
        raise ValueError('A ratio denominator is zero or negative; investigate sources')

    # Same accounting identity and published-rounding threshold as the CORE ETL.
    accounting_difference = (
        df['total_assets'] - df['total_liabilities'] - df['equity']
    )
    if (accounting_difference.abs() > 1.0).any():
        bad = df.loc[
            accounting_difference.abs() > 1.0, ['club', 'fiscal_year']
        ].to_dict('records')
        raise ValueError(f'Accounting identity outside CORE tolerance: {bad}')

    df = df.sort_values(['club', 'fiscal_year']).reset_index(drop=True)
    df['current_liquidity'] = df['current_assets'] / df['current_liabilities']
    df['liability_ratio'] = df['total_liabilities'] / df['total_assets']
    df['return_on_assets'] = df['net_result'] / df['total_assets']
    df['negative_equity'] = (df['equity'] < 0).astype(int)

    # Preserve the original percentile direction and equal weights.
    # Only the retrospective reference sample has changed to the FULL CORE.
    df['liquidity_risk'] = (1 - df['current_liquidity'].rank(pct=True)) * 100
    df['solvency_risk'] = df['liability_ratio'].rank(pct=True) * 100
    df['profitability_risk'] = (1 - df['return_on_assets'].rank(pct=True)) * 100
    df['financial_fragility_score'] = df[RISK_COMPONENTS].mean(axis=1)

    # Past-only loss history, computed over prior AVAILABLE observations.
    # A documentary gap may exist in the past; the current year is excluded.
    df['previous_loss_rate'] = (
        df.groupby('club')['net_result']
        .transform(lambda s: s.lt(0).shift().expanding().mean())
    )

    if not np.isfinite(df[INDICATORS + RISK_COMPONENTS +
                             ['financial_fragility_score']].to_numpy(dtype=float)).all():
        raise ValueError('Non-finite financial indicator or risk component')
    if not df[RISK_COMPONENTS + ['financial_fragility_score']].apply(
        lambda s: s.between(0, 100).all()
    ).all():
        raise ValueError('A risk component or score falls outside 0-100')
    if not df.groupby('club').head(1)['previous_loss_rate'].isna().all():
        raise ValueError('First observed year must have undefined prior-loss rate')

    scores = df[OUTPUT_COLUMNS].copy()
    reference = df[['club', 'fiscal_year', *INDICATORS]].copy()
    assert len(scores) == len(core) == len(reference)
    assert not scores.duplicated(['club', 'fiscal_year']).any()
    return scores, reference


def main():
    core = pd.read_csv(CORE_PATH)
    scores, reference = build_fragility(core)
    SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(SCORES_PATH, index=False, float_format='%.12g')
    reference.to_csv(REFERENCE_PATH, index=False, float_format='%.12g')

    saved = pd.read_csv(SCORES_PATH)
    restored_reference = pd.read_csv(REFERENCE_PATH)
    pd.testing.assert_frame_equal(
        saved[['club', 'fiscal_year', *INDICATORS]],
        restored_reference[['club', 'fiscal_year', *INDICATORS]],
        check_exact=False, rtol=1e-10, atol=1e-10,
    )
    print('Full CORE source:', CORE_PATH)
    print('Clubs:', saved['club'].nunique())
    print('Club-years:', len(saved))
    print('Fiscal years:', saved.fiscal_year.min(), '-', saved.fiscal_year.max())
    print('Gaps against rectangular panel:',
          saved.club.nunique() * saved.fiscal_year.nunique() - len(saved))
    print('Scores:', SCORES_PATH)
    print('Reference:', REFERENCE_PATH)
    print('QA: passed')


if __name__ == '__main__':
    main()

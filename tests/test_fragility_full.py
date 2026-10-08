"""Focused regression checks; run from root using python -m unittest discover -s tests."""
import unittest

import numpy as np
import pandas as pd

from src.build_financial_fragility import build_fragility


class FragilityTests(unittest.TestCase):
    def setUp(self):
        # Three clubs, one intentionally missing intervening year.
        self.core = pd.DataFrame([
            ['A', 2016, 5, 40, 80, 20, 50, 30, -2],
            ['A', 2018, 6, 50, 100, 25, 75, 25, 8],
            ['A', 2019, 3, 35, 70, 35, 80, -10, -9],
            ['B', 2016, 4, 30, 60, 30, 30, 30, 3],
            ['B', 2017, 7, 40, 80, 20, 70, 10, -3],
        ], columns=['club', 'fiscal_year', 'cash', 'current_assets',
                    'total_assets', 'current_liabilities',
                    'total_liabilities', 'equity', 'net_result'])

    def test_full_sample_percentiles_and_history(self):
        scores, ref = build_fragility(self.core)
        self.assertEqual(len(scores), 5)
        self.assertEqual(len(ref), 5)
        self.assertEqual(scores['club'].nunique(), 2)
        self.assertTrue(scores.financial_fragility_score.between(0, 100).all())
        a = scores[scores.club == 'A'].set_index('fiscal_year')
        self.assertTrue(np.isnan(a.loc[2016, 'previous_loss_rate']))
        self.assertEqual(a.loc[2018, 'previous_loss_rate'], 1.0)
        self.assertEqual(a.loc[2019, 'previous_loss_rate'], 0.5)
        self.assertAlmostEqual(scores.liquidity_risk.mean(), 40)
        self.assertAlmostEqual(scores.solvency_risk.mean(), 60)
        self.assertTrue(np.allclose(
            scores.financial_fragility_score,
            scores[['liquidity_risk', 'solvency_risk', 'profitability_risk']].mean(axis=1),
        ))

    def test_accounting_identity_failure(self):
        corrupted = self.core.copy()
        corrupted.loc[0, 'equity'] += 10
        with self.assertRaisesRegex(ValueError, 'Accounting identity'):
            build_fragility(corrupted)

    def test_duplicate_failure(self):
        dupe = pd.concat([self.core, self.core.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            build_fragility(dupe)


if __name__ == '__main__':
    unittest.main()

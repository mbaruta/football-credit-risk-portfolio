"""Regression check for the SQL view's consecutive-year comparison rule."""
from pathlib import Path
import sqlite3
import unittest


class GapAwareSQLTests(unittest.TestCase):
    def test_previous_score_only_when_years_are_consecutive(self):
        view_sql = (Path(__file__).resolve().parents[1] / 'sql/02_create_dashboard_view.sql').read_text(encoding='utf-8')
        self.assertIn('preceding_year = fiscal_year - 1', view_sql)
        self.assertIn('FROM dbo.financial_fragility_scores', view_sql)

        db = sqlite3.connect(':memory:')
        db.execute('CREATE TABLE scores (club TEXT, fiscal_year INTEGER, score REAL)')
        db.executemany('INSERT INTO scores VALUES (?,?,?)', [
            ('A', 2016, 40), ('A', 2018, 70), ('A', 2019, 60),
            ('B', 2018, 20), ('B', 2019, 25),
        ])
        result = db.execute('''
            WITH q AS (
                SELECT club, fiscal_year, score,
                       LAG(fiscal_year) OVER (
                           PARTITION BY club ORDER BY fiscal_year
                       ) AS previous_year,
                       LAG(score) OVER (
                           PARTITION BY club ORDER BY fiscal_year
                       ) AS previous_score
                FROM scores
            )
            SELECT club, fiscal_year,
                   CASE WHEN previous_year=fiscal_year-1
                        THEN score-previous_score END AS annual_change
            FROM q ORDER BY club, fiscal_year
        ''').fetchall()
        self.assertEqual(result,
            [('A', 2016, None), ('A', 2018, None), ('A', 2019, -10.0),
             ('B', 2018, None), ('B', 2019, 5.0)])
        db.close()


if __name__ == '__main__':
    unittest.main()

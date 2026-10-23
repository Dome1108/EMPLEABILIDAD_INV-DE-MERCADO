import unittest
import pandas as pd
from industry import ciiu, match_employers, monthly_sales, macroindustry_summary, growth_summary, compact_usd, MACRO_BY_SECTION, SALES


class IndustryRules(unittest.TestCase):
    def test_growth_comparable_period_and_zero_base(self):
        sales = pd.DataFrame([['K641901', 2025, 1, 10, 20, 30, 40], ['K641901', 2026, 1, 20, 40, 60, 80]], columns=['CIIU', 'Año', 'Mes', *SALES])
        result = growth_summary(sales, ['K641901'], 2026, 1)
        self.assertEqual(result['total'], 200)
        self.assertEqual(result['growth'], 100)
        self.assertEqual(result['top']['CIIU'], 'K641901')
        self.assertTrue(pd.isna(growth_summary(sales, ['K641901'], 2026, 2)['growth']))
        sales.loc[0, SALES] = 0
        self.assertIsNone(growth_summary(sales, ['K641901'], 2026, 1)['top'])
        self.assertEqual(compact_usd(138700000000), 'USD 138,7 mil millones')

    def test_macroindustries_merge_sections_and_deduplicate_people(self):
        mapping = pd.DataFrame({'RUCEMP': ['0000000000001', '0000000000002'], 'CIIU': ['K641901', 'L682002']})
        jobs = pd.DataFrame({'person': ['1', '1', '2'], 'RUCEMP': ['1', '2', '2']})
        sales = pd.DataFrame([['K641901', 2026, 1, 10, 20, 30, 40], ['L682002', 2026, 1, 1, 2, 3, 4]],
                             columns=['CIIU', 'Año', 'Mes', *SALES])
        result = macroindustry_summary(jobs, mapping, sales, ['K641901', 'L682002'], 2026, 1)
        self.assertEqual(len(result), 12)
        finance = result[result.Macroindustria.eq(MACRO_BY_SECTION['K'])].iloc[0]
        self.assertEqual(finance.Graduados, 2)
        self.assertEqual(finance['Ventas totales'], 110)
        self.assertEqual(MACRO_BY_SECTION['D'], MACRO_BY_SECTION['E'])
        self.assertEqual(MACRO_BY_SECTION['O'], MACRO_BY_SECTION['U'])

    def test_sales_not_multiplied_by_employees_and_missing_preserved(self):
        mapping = pd.DataFrame({'RUCEMP': ['0000000000001', '0000000000002'], 'CIIU': ['M711022', 'M711022']})
        jobs = pd.DataFrame({'person': ['1', '2', '2', '3'], 'RUCEMP': ['1', '1', '1', '2']})
        catalog, matched, total = match_employers(jobs, mapping)
        self.assertEqual(catalog.iloc[0].Graduados, 3)
        self.assertEqual(catalog.iloc[0].Empresas, 2)
        sales = pd.DataFrame([['M711022', 2026, 1, 10, 20, 30, 40],
                              ['M711022', 2026, 2, None, 0, None, 0]], columns=['CIIU', 'Año', 'Mes', *SALES])
        result = monthly_sales(sales, ['M711022', 'M711022'])
        self.assertEqual(result.iloc[0]['Personas naturales'], 40)
        self.assertEqual(result.iloc[0]['Sociedades'], 60)
        self.assertTrue(pd.isna(result.iloc[1]['Personas naturales']))
        self.assertEqual(result.iloc[1]['Sociedades'], 0)
        self.assertEqual(ciiu(' F4100.10 '), 'F410010')

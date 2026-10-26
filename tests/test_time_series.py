import unittest

import numpy as np
import pandas as pd

from industry import SALES
from time_series import (complete_monthly, comparable_panel, longest_monthly_block, transform,
                         stationarity, autocorrelation, differencing_flags)


class MonthlyDiagnostics(unittest.TestCase):
    def test_fixed_panel_works_when_one_contributor_type_is_always_missing(self):
        sales=pd.DataFrame([['K641901',2026,m,None,100*m,None,200*m] for m in range(1,5)],
                           columns=['CIIU','Año','Mes',*SALES])
        strict,_=complete_monthly(sales,['K641901'])
        self.assertTrue(strict['Ventas totales'].isna().all())
        panel,detail=comparable_panel(sales,['K641901'],'Ventas totales')
        self.assertEqual(panel.tolist(),[300,600,900,1200])
        self.assertEqual(int(detail.Incluida.sum()),2)
        self.assertTrue(detail.loc[detail.Incluida,'Campo'].str.contains('Sociedades').all())
        natural,_=comparable_panel(sales,['K641901'],'Personas naturales')
        self.assertTrue(natural.isna().all())

    def test_fixed_panel_excludes_intermittent_cell_from_every_month(self):
        sales=pd.DataFrame([['M711022',2026,1,10,20,30,40],['M711022',2026,2,None,20,30,40]],
                           columns=['CIIU','Año','Mes',*SALES])
        panel,detail=comparable_panel(sales,['M711022','J620101'],'Ventas totales')
        self.assertEqual(panel.tolist(),[90,90])
        self.assertEqual(int(detail.Incluida.sum()),3)
        self.assertFalse(detail.loc[detail.CIIU.eq('J620101'),'Incluida'].any())

    def series(self, values):
        return pd.Series(values, index=pd.date_range('2020-01-01', periods=len(values), freq='MS'))

    def test_log_regular_and_seasonal_differences_preserve_dates(self):
        original=self.series(np.exp(np.arange(48)/20))
        result,base,meta=transform(original,'Logaritmo',1,1,12)
        expected=np.log(original).diff(12).diff().iloc[13:]
        np.testing.assert_allclose(result,expected,atol=1e-14)
        self.assertEqual(result.index[0],original.index[13])
        self.assertEqual((meta['d'],meta['D'],meta['s']),(1,1,12))
        growth,_,_=transform(original,'Logaritmo',1,0)
        np.testing.assert_allclose(growth,.05,atol=1e-14)

    def test_no_log_shift_no_compression_of_missing_months(self):
        for kind in ['Logaritmo','Box-Cox']:
            with self.assertRaises(ValueError):
                transform(self.series([1,0,3]),kind)
            with self.assertRaises(ValueError):
                transform(self.series([1,-1,3]),kind)
        original=self.series(np.arange(30,dtype=float)+1)
        original.iloc[5]=np.nan
        with self.assertRaises(ValueError):
            transform(original,'Logaritmo')
        with self.assertRaises(ValueError):
            transform(original.dropna(),'Logaritmo')
        self.assertEqual(stationarity(original)['status'],'unavailable')
        self.assertTrue(autocorrelation(original).empty)

    def test_coverage_does_not_turn_partial_sector_data_into_a_full_series(self):
        sales=pd.DataFrame([
            ['K641901',2026,1,1,2,3,4],['J620101',2026,1,10,20,30,40],
            ['K641901',2026,2,1,2,3,4],['J620101',2026,2,None,20,30,40],
            ['K641901',2026,4,0,0,0,0],['J620101',2026,4,0,0,0,0],
        ],columns=['CIIU','Año','Mes',*SALES])
        series,coverage=complete_monthly(sales,['K641901','J620101','K641901'])
        self.assertEqual(series.iloc[0]['Ventas totales'],110)
        self.assertTrue(pd.isna(series.iloc[1]['Ventas totales']))
        self.assertEqual(series.iloc[1]['Sociedades'],66)
        self.assertAlmostEqual(coverage.iloc[1]['Ventas totales'],7/8)
        self.assertTrue(series.iloc[2].isna().all()) # marzo ausente
        self.assertEqual(series.iloc[3]['Ventas totales'],0) # cero informado válido
        absent,_=complete_monthly(sales,['K641901','J620101','M711022'])
        self.assertTrue(absent.isna().all().all())

    def test_longest_block_ties_choose_latest_without_stitching(self):
        series=self.series([1,2,np.nan,3,4,np.nan])
        block=longest_monthly_block(series)
        self.assertEqual(block.tolist(),[3,4])
        self.assertEqual(block.index[0],pd.Timestamp('2020-04-01'))
        self.assertTrue(longest_monthly_block(self.series([np.nan]*5)).empty)

    def test_boxcox_and_deterministic_trend(self):
        original=self.series(np.exp(np.random.default_rng(2).normal(2,.5,80)))
        result,base,meta=transform(original,'Box-Cox')
        self.assertTrue(np.isfinite(meta['boxcox_lambda']))
        self.assertTrue(np.isfinite(result).all())
        trend=self.series(10+3*np.arange(80)+np.random.default_rng(3).normal(0,.2,80))
        residual,_,_=transform(trend,detrend=True)
        self.assertAlmostEqual(np.polyfit(np.arange(80),residual,1)[0],0,places=10)
        with self.assertRaises(ValueError):
            transform(trend,d=1,detrend=True)

    def test_short_constant_white_noise_and_random_walk(self):
        self.assertEqual(stationarity(self.series([1,2,3]))['status'],'unavailable')
        self.assertEqual(stationarity(self.series([4]*40))['status'],'unavailable')
        rng=np.random.default_rng(18)
        white=self.series(rng.normal(size=500))
        self.assertEqual(stationarity(white)['status'],'stationary')
        random_walk=self.series(np.cumsum(rng.normal(size=500)))
        self.assertEqual(stationarity(random_walk)['status'],'nonstationary')
        differenced,_,_=transform(random_walk,d=1)
        self.assertEqual(stationarity(differenced)['status'],'stationary')

    def test_excess_difference_produces_caution_not_automatic_extra_order(self):
        white=self.series(np.random.default_rng(42).normal(size=500))
        difference,_,_=transform(white,d=1)
        self.assertTrue(differencing_flags(white,difference,'Niveles',1,0))


if __name__ == '__main__':
    unittest.main()

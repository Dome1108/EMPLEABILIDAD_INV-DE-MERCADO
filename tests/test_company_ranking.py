import unittest
import os
import json
from pathlib import Path
from unittest.mock import patch
import pandas as pd

from company_ranking import prepare_ranking,ranking_summary,match_sim_companies,company_name_key,graduate_distribution


class CompanyRankingRules(unittest.TestCase):
    def test_graduate_charts_remain_without_any_ranking_match(self):
        from streamlit.testing.v1 import AppTest
        import company_ranking_view
        empty=pd.DataFrame(columns=['year','company_id','company','CIIU','activity','employees','macroindustry'])
        with patch.dict(os.environ,{'DASHBOARD_DEMO':'1'}), \
             patch.object(company_ranking_view,'prepare_ranking',return_value=(empty,{})):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
            self.assertFalse(app.exception)
            self.assertFalse(any('No se pudo leer el ranking de empresas' in w.value for w in app.warning))
            matches=next(m.value for m in app.metric if m.label=='Empresas identificadas en ranking')
            self.assertEqual(matches,'0')
            chart=next(json.loads(node.proto.spec) for node in app.get('plotly_chart')
                       if json.loads(node.proto.spec).get('layout',{}).get('title',{}).get('text')=='Top 10 empresas por graduados')
            self.assertGreater(len(chart['data'][0]['x']),0)

    def test_graduate_participation_counts_people_not_company_headcount(self):
        jobs=pd.DataFrame({'person':['a','a','b','c','b'],'RUCEMP':['1','1','1','1','2'],
                           'NOMEMP':['ALFA']*4+['BETA']})
        mapping=pd.DataFrame({'RUCEMP':['0000000000001','0000000000002'],'CIIU':['G471101','G471101']})
        companies,by_code,by_macro,total=graduate_distribution(jobs,mapping)
        self.assertEqual(total,3)
        by_ruc=companies.set_index('SIM_RUC')
        self.assertEqual(by_ruc.loc['0000000000001','sim_graduates'],3)
        self.assertEqual(by_ruc.loc['0000000000001','share'],100)
        self.assertAlmostEqual(by_ruc.loc['0000000000002','share'],100/3)
        self.assertEqual(by_code.iloc[0].sim_graduates,3) # misma persona en dos empresas del sector
        self.assertEqual(by_macro.iloc[0].sim_graduates,3)
        self.assertEqual(by_code.iloc[0].share,100)

    def test_unmatched_employers_remain_in_graduate_counts(self):
        jobs=pd.DataFrame({'person':['a','b'],'RUCEMP':['1','2'],'NOMEMP':['ALFA','DESCONOCIDA']})
        mapping=pd.DataFrame({'RUCEMP':['0000000000001'],'CIIU':['J620101']})
        ranking,_=prepare_ranking(self.raw([[2025,'1','ALFA','J6201.01 - SOFTWARE',5000]]))
        matches,_=match_sim_companies(jobs,ranking)
        companies,by_code,by_macro,total=graduate_distribution(jobs,mapping,matches)
        self.assertEqual(len(companies),2)
        self.assertEqual(total,2)
        self.assertTrue(companies.share.eq(50).all())
        self.assertTrue(companies.sim_graduates.eq(1).all())
        self.assertIn('Sin actividad identificada',by_macro.label.tolist())
        self.assertNotIn('Otros servicios',by_macro.label.tolist())

    def test_sim_company_name_cross_limits_ranking_to_actual_employers(self):
        ranking,_=prepare_ranking(self.raw([
            [2025,'1','COMPAÑÍA CÁCERES C. A.','G4711.01 - COMERCIO',100],
            [2025,'2','OTRA EMPRESA SA','G4711.01 - COMERCIO',5000],
        ]))
        jobs=pd.DataFrame({'person':['a','a','b'],'RUCEMP':['1','1','1'],
                           'NOMEMP':['COMPANIA CACERES CA']*3})
        matches,quality=match_sim_companies(jobs,ranking)
        self.assertEqual(quality['matched'],1)
        self.assertEqual(matches.iloc[0].company_id,'1')
        self.assertEqual(matches.iloc[0].employees,100)
        self.assertEqual(matches.iloc[0].sim_graduates,2)
        self.assertEqual(company_name_key('ACME Sociedad Anónima'),company_name_key('Acme S. A.'))

    def test_homonyms_multiple_rucs_and_unknown_names_never_assign_employees(self):
        ranking,_=prepare_ranking(self.raw([
            [2025,'1','ALFA SA','J6201.01 - SOFTWARE',10],
            [2025,'2','Alfa S. A.','J6201.01 - SOFTWARE',20],
            [2025,'3','BETA CIA LTDA','J6201.01 - SOFTWARE',30],
        ]))
        jobs=pd.DataFrame({'person':['a','b','c','d'],'RUCEMP':['1','2','3','4'],
                           'NOMEMP':['ALFA SA','BETA CIA LTDA','BETA CIA LTDA','OTRA FIRMA']})
        matches,quality=match_sim_companies(jobs,ranking)
        self.assertEqual(quality['matched'],0)
        self.assertEqual(quality['ambiguous'],3)
        self.assertTrue(matches.employees.isna().all())
        self.assertTrue(matches.company_id.isna().all())

    def test_ranking_charts_and_grouping_are_available(self):
        from streamlit.testing.v1 import AppTest
        with patch.dict(os.environ,{'DASHBOARD_DEMO':'1'}):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
            self.assertFalse(app.exception)
            self.assertFalse(any('No se pudo leer el ranking' in x.value for x in app.warning))
            self.assertTrue(any(m.label=='Empleados reportados' for m in app.metric))
            self.assertEqual(app.radio(key='ranking_grouping').value,'Actividad económica · CIIU')
            chart=next(json.loads(node.proto.spec) for node in app.get('plotly_chart')
                       if json.loads(node.proto.spec).get('layout',{}).get('title',{}).get('text')=='Top 10 empresas por graduados')
            denominator=int(next(m.value for m in app.metric if m.label=='Graduados empleados con empresa SIM').replace('.',''))
            self.assertTrue(all(value<=denominator for value in chart['data'][0]['x']))
            self.assertEqual(chart['layout']['xaxis']['title']['text'],'Cantidad de graduados · SIM enero 2026')
            for count,custom in zip(chart['data'][0]['x'],chart['data'][0]['customdata']):
                self.assertAlmostEqual(custom[1],100*count/denominator)
            app.radio(key='ranking_grouping').set_value('Macroindustria').run()
            self.assertFalse(app.exception)
            self.assertFalse(any('No se pudo leer el ranking' in x.value for x in app.warning))

    def raw(self,rows):
        return pd.DataFrame(rows,columns=['Año','Expediente','Nombre','Actividad económica','Cant. Empleados'])

    def test_deduplication_and_employee_aggregation_by_ciiu(self):
        raw=self.raw([
            [2025,'001','A','G4711.01 - COMERCIO',100],
            [2025,1.0,'A','G4711.01 - COMERCIO',100],
            [2025,'2','B','G471101 - COMERCIO',50],
            [2025,'3','C','J6201.01 - SOFTWARE',10],
            [2024,'1','A','G4711.01 - COMERCIO',20],
        ])
        ranking,quality=prepare_ranking(raw)
        self.assertEqual(quality['duplicate_rows_removed'],1)
        selected,codes,macro=ranking_summary(ranking,['G471101','G471101'])
        self.assertEqual(len(selected),2)
        self.assertEqual(codes.iloc[0].companies,2)
        self.assertEqual(codes.iloc[0].employees,150)
        self.assertEqual(macro.iloc[0].employees,150)

    def test_missing_is_not_zero_and_conflicting_companies_are_excluded(self):
        raw=self.raw([
            [2025,'1','A','J6201.01 - SOFTWARE',None],
            [2025,'2','B','J6201.01 - SOFTWARE',0],
            [2025,'3','C','J6201.01 - SOFTWARE',-1],
            [2025,'4','D','J6201.01 - SOFTWARE',50],
            [2025,'4','D','G4711.01 - COMERCIO',50],
            [2025,'5','E','J6201.01 - SOFTWARE',100],
            [2025,'5','E','J6201.01 - SOFTWARE',101],
            [2025,'6','F','SIN CODIGO',30],
        ])
        ranking,quality=prepare_ranking(raw)
        self.assertEqual(quality['conflicting_companies'],2)
        self.assertEqual(quality['invalid_ciiu'],1)
        selected,codes,_=ranking_summary(ranking,['J620101'])
        self.assertEqual(len(selected),3)
        self.assertEqual(codes.iloc[0].companies_with_employees,1)
        self.assertEqual(codes.iloc[0].employees,0)
        only_unknown=ranking[ranking.company_id.eq('1')]
        _,unknown,_=ranking_summary(only_unknown,['J620101'])
        self.assertTrue(pd.isna(unknown.iloc[0].employees))


if __name__=='__main__':
    unittest.main()

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from integracion_viabilidad import resumen_compartido
from analytics import calculate
from data_access import demo_data

ROOT=Path(__file__).resolve().parents[1]


class IntegracionViabilidadTest(unittest.TestCase):
    def test_filtros_persisten_al_salir_y_regresar(self):
        with patch.dict(os.environ,{'DASHBOARD_DEMO':'1'}):
            app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
            options=app.multiselect(key='selected_careers').options
            selected=[options[-1]]
            app.multiselect(key='selected_careers').set_value(selected).run()
            app.selectbox(key='color_palette').set_value('Vino').run()
            app.selectbox(key='employment_cutoff').set_value(2025).run()
            level=app.selectbox(key='academic_level').value
            for page in ('views/carreras.py','views/educacion_continua.py'):
                app.switch_page(page).run()
                self.assertFalse(app.exception)
            app.switch_page('views/empleabilidad.py').run()
            self.assertFalse(app.exception)
            self.assertEqual(app.multiselect(key='selected_careers').value,selected)
            self.assertEqual(app.selectbox(key='color_palette').value,'Vino')
            self.assertEqual(app.selectbox(key='academic_level').value,level)
            self.assertEqual(app.selectbox(key='employment_cutoff').value,2025)

    def test_consulta_directa_carga_perfil_sin_visitar_otra_pagina(self):
        import pandas as pd
        from consulta_perfil_carrera import consultar
        from data_access import demo_atlas
        from industry import SALES
        grads,jobs,sri=demo_data()
        names=sorted(grads.CARRERA_HOMOLOGADA.unique())
        catalog=pd.DataFrame({'carrera':names,'nivel':['Prueba']*len(names),'nivel_origen':['Prueba']*len(names)})
        # Use the normalized cohort IDs produced by the real analytics pipeline.
        from analytics import calculate
        cohort=calculate(grads,jobs,sri)[2][2026]
        employers=pd.DataFrame({'person':cohort.person,'RUCEMP':'0000000000001','NOMEMP':'Empresa prueba'})
        mapping=pd.DataFrame({'RUCEMP':['0000000000001'],'CIIU':['M732001']})
        sales=pd.DataFrame([{'CIIU':'M732001','Año':2026,'Mes':1,**{s:10.0 for s in SALES}}])
        with patch('data_access.load',return_value=(grads,jobs,sri)),patch('data_access.load_employers',return_value=employers),patch('data_access.load_atlas',return_value=demo_atlas(tuple(cohort.person))),patch('industry.read_sources',return_value=(mapping,sales,0)):
            result=consultar({},names,'Prueba',catalog)
        self.assertEqual(len(result['empleo']),4)
        self.assertTrue(result['sector']['empresas'])
        self.assertTrue(result['sector']['macroindustrias'])
        self.assertFalse(result['notas_consulta'])

    def test_empresas_deduplica_personas_y_no_expone_identificadores(self):
        import pandas as pd
        from integracion_viabilidad import principales_empresas
        jobs=pd.DataFrame({'person':['a','a','b','b','c'],
            'RUCEMP':['1','1','1','2','2'],'NOMEMP':['Uno','Uno','Uno','Dos','Dos']})
        result=principales_empresas(jobs)
        self.assertEqual(len(result),2)
        for row in result:
            self.assertEqual(row['Graduados'],2)
            self.assertAlmostEqual(row['Participación (%)'],200/3)
            self.assertEqual(set(row),{'Empresa','Graduados','Participación (%)'})

    def test_frontera_solo_comparte_agregados(self):
        grads,jobs,sri=demo_data()
        summary,*_=calculate(grads,jobs,sri)
        payload=resumen_compartido(summary,['Economía'],'Todos los niveles',True)
        self.assertEqual(len(payload['empleo']),4)
        self.assertTrue(payload['demostracion'])
        for row in payload['empleo']:
            self.assertNotIn('person',row)
            self.assertNotIn('IDENTIFICACION',row)
            self.assertNotIn('RUCEMP',row)

    def test_navegacion_comparte_sector_y_conserva_edco_cr(self):
        with patch.dict(os.environ,{'DASHBOARD_DEMO':'1'}):
            app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
            self.assertFalse(app.exception)
            context=app.session_state['mercado_compartido']
            self.assertTrue(context['demostracion'])
            self.assertTrue(context['sector']['ventas'])
            self.assertTrue(context['sector']['macroindustrias'])
            self.assertTrue(context['sector']['empresas'])
            app.switch_page('views/carreras.py').run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.tabs),12)
            carrera=app.selectbox(key='carrera_negocios').value
            self.assertFalse(app.exception)
            self.assertFalse(any(str(b.key).startswith('vincular_mercado_') for b in app.button))
            self.assertEqual(app.session_state['mercado_compartido']['carreras'],context['carreras'])
            self.assertTrue(any('Principales empresas' in m.value for m in app.markdown))
            self.assertTrue(any('datos sintéticos' in message.value for message in app.warning))
            app.switch_page('views/educacion_continua.py').run()
            self.assertFalse(app.exception)
            app.selectbox(key='edco_institucion').set_value('ulatina_cr').run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.selectbox(key='edco_programa').options),2)
            self.assertTrue(app.checkbox(key='edco_eval_sector').value)
            app.switch_page('views/empleabilidad.py').run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['mercado_compartido']['carreras'],context['carreras'])

    def test_viabilidad_no_depende_de_conexion_sql(self):
        with patch.dict(os.environ,{'DASHBOARD_DEMO':'0'}),patch('data_access.career_catalog',side_effect=RuntimeError('Sin conexión de prueba')):
            app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
            self.assertFalse(app.exception)
            self.assertTrue(app.error)
            app.switch_page('views/educacion_continua.py').run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.tabs),4)

    def test_analisis_funciona_sin_pdf_originales_locales(self):
        original=Path.is_file
        def available(path):
            if path.name.startswith('brief_') and path.suffix=='.pdf':return False
            return original(path)
        with patch.dict(os.environ,{'DASHBOARD_DEMO':'1'}),patch.object(Path,'is_file',available):
            app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
            app.switch_page('views/educacion_continua.py').run()
            self.assertFalse(app.exception)
            app.selectbox(key='edco_institucion').set_value('ulatina_cr').run()
            self.assertFalse(app.exception)
            self.assertTrue(app.checkbox(key='edco_eval_sector').value)


if __name__=='__main__':unittest.main()

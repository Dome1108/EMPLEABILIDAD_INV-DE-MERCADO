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
            app.switch_page('views/carreras.py').run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.tabs),12)
            carrera=app.selectbox(key='carrera_negocios').value
            app.button(key='vincular_mercado_negocios').click().run()
            self.assertFalse(app.exception)
            self.assertIn(carrera,app.session_state['evidencia_por_carrera'])
            self.assertTrue(any('datos sintéticos' in message.value for message in app.warning))
            app.switch_page('views/educacion_continua.py').run()
            self.assertFalse(app.exception)
            app.selectbox(key='edco_institucion').set_value('ulatina_cr').run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.selectbox(key='edco_programa').options),2)
            self.assertTrue(app.checkbox(key='edco_eval_sector').value)
            app.switch_page('views/empleabilidad.py').run()
            self.assertFalse(app.exception)
            self.assertIn(carrera,app.session_state['evidencia_por_carrera'])

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

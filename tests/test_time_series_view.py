import os
os.environ["TENDENCIAS_DESACTIVADO"] = "1"  # sin conexión a la base real de Tendencias
import tempfile
os.environ.setdefault("PRESENTACIONES_COLA", os.path.join(tempfile.mkdtemp(), "cola.sqlite3"))  # cola .pptx temporal
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class MonthlyDiagnosticFlow(unittest.TestCase):
    def test_log_and_combined_differences_render_and_keep_monthly_calendar(self):
        with patch.dict(os.environ, {'DASHBOARD_DEMO':'1'}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60)
            app.session_state['selected_careers'] = ['Economía']  # el filtro inicia vacío
            app.run()
            self.assertFalse(app.exception)
            self.assertFalse(any('No fue posible completar el cruce' in w.value for w in app.warning))
            self.assertEqual(app.selectbox(key='ts_measure').value,'Ventas totales')
            app.selectbox(key='ts_kind').set_value('Logaritmo')
            app.number_input(key='ts_d').set_value(1)
            app.number_input(key='ts_D').set_value(1)
            app.run()
            self.assertFalse(app.exception)
            self.assertFalse(any('No fue posible completar el cruce' in w.value for w in app.warning))
            self.assertTrue(any('d = 1' in c.value and 'D = 1' in c.value for c in app.code))
            comparison=next(d.value for d in app.dataframe if 'ADF · p' in d.value.columns and len(d.value)==2)
            self.assertEqual(comparison.iloc[0]['Meses']-comparison.iloc[1]['Meses'],13)


if __name__=='__main__':
    unittest.main()

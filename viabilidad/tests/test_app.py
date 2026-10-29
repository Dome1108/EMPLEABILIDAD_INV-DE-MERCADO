from pathlib import Path
import sys
import unittest
from streamlit.testing.v1 import AppTest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

class AppTestCase(unittest.TestCase):
    def test_reporte_precio_sin_metadatos(self):
        from unittest.mock import patch
        from graficos_simulados import crear_grafico_precio
        def sin_metadatos(*args,**kwargs):
            fig=crear_grafico_precio(*args,**kwargs)
            fig.layout.meta=None
            return fig
        with patch('graficos_simulados.crear_grafico_precio',side_effect=sin_metadatos):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
            self.assertEqual(len(app.exception),0)
            self.assertEqual(len(app.metric),12)
            self.assertEqual(sum('Rango orientativo' in text.value for text in app.markdown),12)

    def test_carga_y_cambio_de_carrera(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
        self.assertEqual(len(app.exception),0)
        self.assertEqual(app.selectbox[0].value,'Derecho')
        app.selectbox[0].select('Negocios Internacionales').run(timeout=30)
        self.assertEqual(len(app.exception),0)
        self.assertEqual(app.metric[0].value,'100.00 / 100')
        app.selectbox[0].select('Software').run(timeout=30)
        self.assertEqual(len(app.exception),0)
        from modelo import cargar_datos,evaluar
        data=cargar_datos()
        expected=evaluar(next(a for a in data if a['carrera']=='Software'),data[0])['total']
        self.assertEqual(app.metric[0].value,f'{expected:.2f} / 100')

    def test_control_de_pesos(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
        app.number_input(key='weight0_negocios').set_value(25).run(timeout=30)
        self.assertEqual(len(app.exception),0)
        self.assertEqual(len(app.error),1)
        self.assertIn('95%',app.error[0].value)

    def test_pestana_software_independiente(self):
        from modelo import cargar_datos,evaluar
        data=cargar_datos()
        software=next(a for a in data if a['carrera']=='Software')
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
        self.assertEqual(len(app.exception),0)
        self.assertEqual([t.label for t in app.tabs],[f'Referencia: {a["carrera"]}' for a in data])
        self.assertEqual(len([s for s in app.selectbox if s.label=='Filtrar por carrera']),12)
        # Cada vista evalúa el programa inicial contra su propia referencia.
        selected=next(a for a in data if a['carrera']=='Derecho')
        for i,reference in enumerate(data):
            expected=evaluar(selected,reference)['total']
            self.assertEqual(app.metric[i].value,f'{expected:.2f} / 100')
        app.selectbox(key='carrera_negocios').select('Software').run(timeout=30)
        app.selectbox(key='carrera_software').select('Negocios Internacionales').run(timeout=30)
        self.assertEqual(len(app.exception),0)
        self.assertEqual(app.selectbox(key='carrera_negocios').value,'Software')
        self.assertEqual(app.selectbox(key='carrera_software').value,'Negocios Internacionales')
        self.assertEqual(app.metric[0].value,f"{evaluar(software,data[0])['total']:.2f} / 100")
        self.assertEqual(app.metric[1].value,f"{evaluar(data[0],software)['total']:.2f} / 100")
        app.selectbox(key='carrera_software').select('Software').run(timeout=30)
        self.assertEqual(app.metric[1].value,'100.00 / 100')
        app.selectbox(key='nivel_software').select('Posgrado').run(timeout=30)
        self.assertEqual(len(app.exception),0)
        self.assertEqual(app.metric[1].value,'100.00 / 100')
        self.assertEqual(app.selectbox(key='nivel_negocios').value,'Pregrado')

if __name__=='__main__':unittest.main()

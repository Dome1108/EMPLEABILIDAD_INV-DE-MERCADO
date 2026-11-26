from pathlib import Path
import sys
import unittest
from streamlit.testing.v1 import AppTest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import pandas as pd
from unittest.mock import patch
import streamlit as st


def precios_sinteticos():
    """Derecho con 6 competidores y UDLA en 202520; sin acceso a SQL Server."""
    rows=[('3ER NIVEL','DERECHO','202520',sigla,str(price),str(price*1.1))
          for sigla,price in [('UDLA',3500),('PUCE',4000),('USFQ',5200),('UTE',3000),('UIDE',3300),('UHE',2800),('UTPL',2500)]]
    # Posgrado: Derecho Penal con 6 competidores (precio en TOTAL) y Derecho Administrativo con 1.
    rows+=[('4TO NIVEL','MAESTRIA EN DERECHO PENAL','202610',sigla,'1',str(total))
           for sigla,total in [('UDLA',9000),('PUCE',8000),('USFQ',12000),('UTE',7000),('UIDE',9500),('UHE',6500),('UTPL',6000)]]
    rows+=[('4TO NIVEL','MAESTRIA EN DERECHO ADMINISTRATIVO','202610',sigla,'1',str(total)) for sigla,total in [('UDLA',8500),('PUCE',7000)]]
    rows+=[('4TO NIVEL','MAESTRIA EN MEDICINA VETERINARIA','202610','UTE','1','5000')]
    return pd.DataFrame(rows,columns=['NIVEL ACADEMICO','CARRERA UDLA','Semestre Pos','SIGLA','ARANCEL','TOTAL'])


class AppTestCase(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()
        patcher=patch('data_access.load_reference_prices',side_effect=lambda config:precios_sinteticos())
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_referencia_de_precios(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=60)
        self.assertEqual(len(app.exception),0)
        self.assertEqual(len(app.metric),12)
        headers=[text.value for text in app.markdown if 'Rango aceptable · PMC–PME' in text.value]
        self.assertEqual(len(headers),12)
        # Competidores [2500,2800,3000,3300,4000,5200]: PMC≈3228, PME≈4550; UDLA 3500 dentro.
        self.assertIn('$3,228 — $4,550',headers[0])
        self.assertTrue(any(e.label=='Ver cálculo paso a paso' for e in app.expander))
        self.assertIn('Dentro del rango',headers[0])
        self.assertEqual(app.selectbox(key='periodo_precios_negocios_Pregrado_DERECHO').value,'202520')

    def test_posgrado_cambia_el_grafico(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=60)
        app.selectbox(key='nivel_negocios').select('Posgrado').run(timeout=60)
        self.assertEqual(len(app.exception),0)
        program=app.selectbox(key='programa_posgrado_negocios')
        # Programas de Derecho, el de más competidores primero; nunca Medicina Veterinaria.
        self.assertEqual(program.options,['MAESTRIA EN DERECHO PENAL','MAESTRIA EN DERECHO ADMINISTRATIVO'])
        header=next(t.value for t in app.markdown if 'Rango aceptable · PMC–PME' in t.value and '4TO NIVEL' in t.value)
        self.assertIn('Maestria En Derecho Penal',header)
        self.assertIn('$9,000',header)
        self.assertNotIn('—</strong>',header.split('PMC–PME')[1].split('</div>')[0])
        program.select('MAESTRIA EN DERECHO ADMINISTRATIVO').run(timeout=60)
        self.assertEqual(len(app.exception),0)
        header=next(t.value for t in app.markdown if 'Rango aceptable · PMC–PME' in t.value and 'Administrativo' in t.value)
        self.assertIn('Muestra insuficiente',header)

    def test_posgrado_sin_programas(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=60)
        app.selectbox(key='carrera_negocios').select('Software').run(timeout=60)
        app.selectbox(key='nivel_negocios').select('Posgrado').run(timeout=60)
        self.assertEqual(len(app.exception),0)
        self.assertTrue(any('Software no tiene programas de posgrado' in i.value for i in app.info))

    def test_carrera_sin_precios(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=60)
        app.selectbox(key='carrera_negocios').select('Medicina').run(timeout=60)
        self.assertEqual(len(app.exception),0)
        self.assertTrue(any('MEDICINA' in i.value.upper() or 'Medicina' in i.value for i in app.info))

    def test_error_sql_no_rompe_la_pestana(self):
        st.cache_data.clear()
        with patch('data_access.load_reference_prices',side_effect=RuntimeError('sin red')):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=60)
        self.assertEqual(len(app.exception),0)
        self.assertTrue(any('Precios_Homologados' in w.value for w in app.warning))

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



class CarreraModeloTestCase(unittest.TestCase):
    def test_variantes_de_graduados_nueva(self):
        from modelo import carrera_modelo
        casos={'SOFTWARE':'Software','Ingeniería de Software':'Software','MAESTRIA EN SOFTWARE':'Software',
               'MAESTRIA EN DESARROLLO DE SOFTWARE':'Software','MAESTRIA EN PSICOLOGIA':'Psicología',
               'MAESTRIA EN RELACIONES INTERNACIONALES MENCION SEGURIDAD':'RRII',
               'MEDICINA VETERINARIA':None,'MAESTRIA EN MEDICINA VETERINARIA Y ZOOTECNIA':None,
               'DIPLOMADO EN ARQUITECTURA DE LA INFORMACION':None,'BIOMEDICINA':None,'ECONOMIA':None}
        for nombre,esperado in casos.items():
            self.assertEqual(carrera_modelo(nombre),esperado,nombre)


if __name__=='__main__':unittest.main()

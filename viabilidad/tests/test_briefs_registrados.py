from pathlib import Path
import json
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from modelo_edcos import cargar_edcos,validar_ficha
from registrar_briefs_edcos import BRIEFS,construir_ficha
from completar_investigacion_edcos import INVESTIGACION,completar,verificar_referencias

BASE=Path(__file__).resolve().parents[1]
IDS={d['id'] for d in BRIEFS}


def investigacion(brief_id):
    path=INVESTIGACION/f'{brief_id}.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None


class BriefsRegistrados(unittest.TestCase):
    def test_fichas_guardadas_coinciden_con_brief_e_investigacion(self):
        saved={f['id']:f for f in cargar_edcos()}
        for datos in BRIEFS:
            with self.subTest(brief=datos['id']):
                research=investigacion(datos['id'])
                expected=completar(datos,research) if research else construir_ficha(datos)
                self.assertEqual(saved[datos['id']],expected)

    def test_investigados_completos_y_trazables(self):
        for ficha in cargar_edcos():
            if ficha['id'] not in IDS:continue
            with self.subTest(brief=ficha['id']):
                result=validar_ficha(ficha)
                self.assertTrue((BASE/ficha['brief']['copia_local']).is_file())
                if investigacion(ficha['id']) is None:
                    self.assertIsNone(result['total'])
                    self.assertEqual(result['estado'],'En evaluación')
                    continue
                self.assertEqual(result['evaluados'],5)
                self.assertIsNotNone(result['total'])
                verificar_referencias(ficha)
                self.assertEqual(len(ficha['recomendaciones']),5)
                self.assertTrue(ficha['comparativa_contenidos']['ofertas'])
                self.assertTrue(ficha['evidencia_visual']['empleabilidad']['publicaciones'])
                # Las menciones del proponente nunca cuentan como precio verificado.
                self.assertTrue(all(not o.get('precio_verificado') for o in ficha['ofertas'] if o['fuente']=='brief'))
                expected='bccr' if ficha['institucion_id']=='ulatina_cr' else None
                self.assertEqual(ficha['evidencia_visual']['sector'].get('origen'),expected)

    def test_sector_ecuador_calculado_con_sri(self):
        ficha=next(f for f in cargar_edcos() if f['id']=='diseno_generativo_ia')
        if investigacion('diseno_generativo_ia') is None:self.skipTest('Sin investigación registrada.')
        from sector_edcos import calcular_sector_sri
        expected=calcular_sector_sri(BASE.parent/'data'/'consulta_sri_1.xlsx','M7410.09')['puntaje']
        self.assertAlmostEqual(ficha['evaluacion']['sector']['puntaje'],expected)
        self.assertTrue((BASE/ficha['evidencia_visual']['sector']['archivo_mensual']).is_file())

    def test_paises_e_instituciones(self):
        fichas={f['id']:f for f in cargar_edcos()}
        self.assertEqual(fichas['diseno_generativo_ia']['institucion_id'],'udla_ec')
        self.assertEqual(fichas['diseno_generativo_ia']['brief']['ciiu'],'M7410.09')
        self.assertEqual(sum(fichas[i]['institucion_id']=='ulatina_cr' for i in IDS),12)

    def test_cada_brief_se_ve_en_todos_los_apartados(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(BASE/'app.py'))
        app.session_state['apartado']='Educación continua'
        app.run(timeout=60)
        for ficha in cargar_edcos():
            if ficha['id'] not in IDS:continue
            with self.subTest(brief=ficha['id']):
                app.selectbox(key='edco_institucion').set_value(ficha['institucion_id']).run(timeout=60)
                app.selectbox(key='edco_programa').set_value(ficha['nombre']).run(timeout=60)
                self.assertEqual(len(app.exception),0)
                self.assertTrue(any(ficha['brief']['objetivo'] in m.value for m in app.markdown))
                pending=any('pendientes de investigación' in i.value for i in app.info)
                if investigacion(ficha['id']) is None:
                    self.assertTrue(pending)
                    continue
                self.assertFalse(pending)
                # Diagnóstico: radar, matriz de contenidos, mapa y gráficos de cada dimensión.
                self.assertGreaterEqual(len(app.get('plotly_chart')),6)
                self.assertTrue(any(m.label=='Publicaciones identificadas' for m in app.metric))
                self.assertTrue(app.checkbox(key='edco_eval_sector').value)


if __name__=='__main__':
    unittest.main()

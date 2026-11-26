from copy import deepcopy
from io import BytesIO
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pptx import Presentation
from modelo_edcos import cargar_edcos,validar_ficha
from edcos_pptx import construir_pptx,nombre_archivo


def textos(prs):
    return [' '.join(s.text_frame.text for s in slide.shapes if s.has_text_frame)+' '+' '.join(c.text for s in slide.shapes if s.has_table for r in s.table.rows for c in r.cells) for slide in prs.slides]


class EdcosPptxTest(unittest.TestCase):
    def test_todas_las_fichas_generan_diagnostico(self):
        for ficha in cargar_edcos():
            with self.subTest(ficha=ficha['id']):
                prs=Presentation(BytesIO(construir_pptx(ficha,validar_ficha(ficha))))
                content=textos(prs)
                self.assertIn(ficha['nombre'],content[0])
                self.assertIn('Perfil de viabilidad',content[1])
                for label in ['Demanda e interés','Competencia','Sector económico']:
                    self.assertTrue(any(label in t for t in content),label)
                # Solo el Diagnóstico: sin las pestañas de cálculo ni brief.
                self.assertFalse(any('Pesos y reglas EdCo' in t or 'Ficha del proponente' in t for t in content))
                self.assertTrue(nombre_archivo(ficha).endswith('.pptx'))

    def test_pendientes_no_se_muestran_como_cero(self):
        ficha=deepcopy(cargar_edcos()[0])
        ficha['evaluacion']['demanda']['puntaje']=None
        content=textos(Presentation(BytesIO(construir_pptx(ficha,validar_ficha(ficha)))))
        self.assertIn('Sin calificar',content[1])
        self.assertIn('—',content[0])

    def test_filtro_de_oferentes_se_respeta(self):
        ficha=cargar_edcos()[0]
        full=textos(Presentation(BytesIO(construir_pptx(ficha,validar_ficha(ficha)))))
        only=textos(Presentation(BytesIO(construir_pptx(ficha,validar_ficha(ficha),{'tipos':['Oferta propia']}))))
        matrix=lambda content:next(t for t in content if '¿Qué contenidos declara' in t)
        self.assertLess(len(matrix(only)),len(matrix(full)))


if __name__=='__main__':
    unittest.main()

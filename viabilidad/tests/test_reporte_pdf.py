from io import BytesIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from pypdf import PdfReader
from streamlit.delta_generator import DeltaGenerator
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
APP = str(Path(__file__).resolve().parents[1] / 'app.py')


def run_and_capture():
    """Ejecuta la pestaña y guarda la función de cada botón «Descargar reporte PDF»."""
    captured = {}
    original = DeltaGenerator.download_button

    def capture(self, label, data, *args, **kwargs):
        if label == 'Descargar reporte PDF':
            captured[kwargs['key']] = (data, kwargs['file_name'])
        return original(self, label, data, *args, **kwargs)
    with patch.object(DeltaGenerator, 'download_button', capture):
        app = AppTest.from_file(APP).run(timeout=60)
    return app, captured


class ReportePDF(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app, cls.captured = run_and_capture()
        data, cls.name = cls.captured['pdf_negocios']
        cls.pdf = data()
        cls.reader = PdfReader(BytesIO(cls.pdf))
        cls.text = '\n'.join(page.extract_text() for page in cls.reader.pages)

    def test_un_boton_por_referencia_y_nombre_de_archivo(self):
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(len(self.captured), 12)
        self.assertRegex(self.name, r'^viabilidad_Derecho_\d{4}-\d{2}-\d{2}\.pdf$')

    def test_pdf_con_los_mismos_resultados_de_la_pagina(self):
        from modelo import cargar_datos, evaluar, recomendaciones, Config
        self.assertTrue(self.pdf.startswith(b'%PDF'))
        data = cargar_datos()
        reference, program = data[0], next(d for d in data if d['carrera'] == 'Derecho')
        result = evaluar(program, reference)
        self.assertEqual(self.app.metric[0].value, f"{result['total']:.2f} / 100")
        self.assertIn(f"{result['total']:.2f} / 100", self.text)
        self.assertIn(result['clasificacion'], self.text)
        self.assertIn(result['cuadrante'], self.text)
        for title, _ in recomendaciones(program, result, Config()):
            self.assertIn(title, self.text)

    def test_incluye_secciones_plegadas_y_paginas_verticales(self):
        for section in ('Configuración del modelo', 'Perfil del programa', 'Recomendaciones', 'Demanda vs. competencia',
                        'Cómo se forma el resultado', 'Sensibilidad de precio', 'Indicadores y valores originales',
                        'Dato informativo', 'Un mismo punto de partida para todos', 'Tabla comparativa', 'Reglas del modelo',
                        'Precio frente a la media', 'Oportunidad de mercado', 'Lectura provisional del total'):
            self.assertIn(section, self.text)
        self.assertNotIn('Descargar', self.text)  # Sin controles de la interfaz.
        orientation = ['h' if page.mediabox.width > page.mediabox.height else 'v' for page in self.reader.pages]
        self.assertEqual(set(orientation), {'v'})  # Todo el reporte en A4 vertical.

    def test_tabla_de_precio_sale_del_modelo(self):
        from modelo import precio
        # Mismos valores que la tabla fija anterior, ahora derivados de modelo.precio.
        self.assertEqual([round(precio(g), 2) for g in (-.25, -.20, 0, .15, .20, .25)], [50, 75, 100, 83.33, 66.67, 50])
        rules = ' '.join(self.text[self.text.index('Reglas del modelo'):].split())
        for label, score in (('25% más barato', '50'), ('15% más caro', '83.33'), ('20% más caro', '66.67')):
            self.assertIn(f'{label} {score}', rules)


    def test_fuente_century_gothic_si_esta_instalada(self):
        from figuras_pdf import fuente_reporte
        family = fuente_reporte()[0]
        fonts = {str(page['/Resources']['/Font'][f]['/BaseFont']) for page in self.reader.pages for f in page['/Resources']['/Font']}
        expected = 'CenturyGothic' if family == 'Century Gothic' else 'DejaVuSans'
        self.assertTrue(any(expected in font for font in fonts), fonts)


class Faltantes(unittest.TestCase):
    def test_valores_y_graficos_sin_datos(self):
        from reporte_pdf import NO_CHART, NO_DATA, chart, filename, number
        self.assertEqual(number(None), NO_DATA)
        self.assertEqual(number(float('nan')), NO_DATA)
        self.assertEqual(number(0.0), '0')
        self.assertEqual(chart(None, 10, 5)._cellvalues[0][0].text, NO_CHART)
        self.assertEqual(filename('Multimedia y producción / audiovisual', '2026-10-30'),
                         'viabilidad_Multimedia_y_produccion_audiovisual_2026-10-30.pdf')


if __name__ == '__main__':
    unittest.main()

from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modelo_referencia_precios import (calcular_modelo, crear_figura, cruces_van_westendorp, posicion_en_rango,
                                       posicion_udla, rango_van_westendorp)

COLUMNS = ['NIVEL ACADEMICO', 'CARRERA UDLA', 'Semestre Pos', 'SIGLA', 'ARANCEL', 'TOTAL']


def frame(rows):
    return pd.DataFrame(rows, columns=COLUMNS)


class ModeloReferenciaPreciosTest(unittest.TestCase):
    def test_mediana_por_institucion_y_rango(self):
        rows = [('3ER NIVEL', 'Derecho', '202520', s, p, '') for s, p in
                [('UDLA', '3500'), ('PUCE', '3800'), ('PUCE', '4200'), ('USFQ', '5200'), ('UTE', '3000'),
                 ('UIDE', '3300'), ('UHE', '2800'), ('UTPL', '2500'), ('UCE', '0')]]
        r = calcular_modelo(frame(rows), '3er nivel', 'DERECHO', 202520)
        # PUCE pesa una vez (mediana 4000); el precio 0 se descarta.
        self.assertEqual(r['n'], 6)
        self.assertEqual(r['columna'], 'ARANCEL')
        self.assertEqual(r['precio_udla'], 3500)
        self.assertEqual((r['referencias']['p50'], r['referencias']['p75']), (3150, 3825))
        self.assertEqual(posicion_udla(r), 'dentro')
        self.assertIsNotNone(r['curvas'])
        fig = crear_figura(r)
        self.assertEqual([t.name for t in fig.data][:4], ['Demasiado barato', 'Barato', 'Caro', 'Demasiado caro'])

    def test_franja_va_de_pmc_a_pme(self):
        rows = [('3ER NIVEL', 'Derecho', '202520', s, str(p), '') for s, p in
                [('UDLA', 3500), ('PUCE', 4000), ('USFQ', 5200), ('UTE', 3000), ('UIDE', 3300), ('UHE', 2800), ('UTPL', 2500)]]
        r = calcular_modelo(frame(rows), '3ER NIVEL', 'Derecho', '202520')
        cruces = cruces_van_westendorp(r)
        self.assertEqual(set(cruces), {'PMC', 'OPP', 'IPP', 'PME'})
        rango = rango_van_westendorp(r)
        self.assertEqual(rango, (cruces['PMC'][0], cruces['PME'][0]))
        self.assertLess(rango[0], rango[1])
        self.assertEqual(posicion_en_rango(3500, rango), 'dentro')
        self.assertEqual(posicion_en_rango(rango[0] - 1, rango), 'debajo')
        fig = crear_figura(r)
        # Franja sombreada y bordes punteados exactamente en las X del PMC y del PME.
        franja = [s for s in fig.layout.shapes if s.type == 'rect']
        self.assertEqual((franja[0].x0, franja[0].x1), rango)
        bordes = [s.x0 for s in fig.layout.shapes if s.type == 'line' and s.line.dash == 'dash']
        self.assertEqual(bordes, list(rango))
        xs = list(next(t for t in fig.data if t.name == 'Cruces').x)
        self.assertIn(rango[0], xs)
        self.assertIn(rango[1], xs)

    def test_cuarto_nivel_usa_total_y_muestra_pequena(self):
        rows = [('4TO NIVEL', 'MBA', '202610', s, '1', t) for s, t in [('UDLA', '9000'), ('PUCE', '8000'), ('USFQ', '12000')]]
        r = calcular_modelo(frame(rows), '4TO NIVEL', 'MBA', '202610')
        self.assertEqual(r['columna'], 'TOTAL')
        self.assertEqual(r['n'], 2)
        self.assertIsNone(r['curvas'])
        self.assertEqual(posicion_udla(r), 'debajo')

    def test_columnas_faltantes(self):
        with self.assertRaises(ValueError):
            calcular_modelo(pd.DataFrame({'SIGLA': []}), '3ER NIVEL', 'X', '1')


if __name__ == '__main__':
    unittest.main()

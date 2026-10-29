import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sector_edcos import puntaje_evolucion, calcular_sector_sri
from modelo_edcos import cargar_edcos, evaluar_edco

class SectorAbsolutoTest(unittest.TestCase):
    def test_escala_y_topes(self):
        for tasa, esperado in [(-.5,0),(-.2,0),(-.1,25),(0,50),(.1,75),(.2,100),(.5,100)]:
            self.assertAlmostEqual(puntaje_evolucion(tasa),esperado)
        with self.assertRaises(ValueError): puntaje_evolucion(float('nan'))

    def test_recalculo_con_excel_y_ficha(self):
        root=Path(__file__).resolve().parents[1]
        archivo=root.parent/'data'/'consulta_sri_1.xlsx'
        if not archivo.exists(): archivo=root/'edcos_fuentes'/'ventas_sri_original.xlsx'
        r=calcular_sector_sri(archivo,'M7320.01')
        self.assertEqual(r['universo'],92)
        self.assertAlmostEqual(r['ventas_actual'],19006127.53,places=2)
        self.assertAlmostEqual(r['ventas_anterior'],16382537.93,places=2)
        ficha=next(f for f in cargar_edcos() if f['institucion_id']=='udla_ec')
        self.assertAlmostEqual(ficha['evaluacion']['sector']['puntaje'],r['puntaje'])
        self.assertAlmostEqual(evaluar_edco(ficha)['total'],64.12609373227818)

    def test_faltantes_no_son_cero_y_duplicados_se_rechazan(self):
        import tempfile, openpyxl
        with tempfile.TemporaryDirectory() as carpeta:
            archivo=Path(carpeta)/'ventas.xlsx'
            w=openpyxl.Workbook();s=w.active;s.title='Ventas SRI'
            s.append(['ciiu','year','month','a','b','c','d'])
            s.append(['M732001',2025,1,1,1,1,1])
            s.append(['M732001',2026,1,1,None,1,1]);w.save(archivo)
            with self.assertRaisesRegex(ValueError,'completas'):calcular_sector_sri(archivo,'M732001',mes_corte=1)
            s.append(['M732001',2026,1,1,1,1,1]);w.save(archivo)
            with self.assertRaisesRegex(ValueError,'duplicados'):calcular_sector_sri(archivo,'M732001',mes_corte=1)

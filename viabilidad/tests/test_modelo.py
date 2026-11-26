import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from modelo import Config,cargar_datos,evaluar,precio,cuadrante

class ModeloTest(unittest.TestCase):
    def setUp(self):
        self.data=cargar_datos();self.base=self.data[0]

    def test_precio_anclas_acordadas(self):
        for gap,expected in [(-.25,50),(-.20,75),(-.15,100),(0,100),(.10,100),(.15,83.3333333333),(.20,66.6666666667),(.25,50)]:
            with self.subTest(gap=gap):self.assertAlmostEqual(precio(gap),expected)

    def test_negocios_es_cien_y_todos_estan_acotados(self):
        r=evaluar(self.base,self.base)
        self.assertAlmostEqual(r['total'],100)
        self.assertEqual(r['cuadrante'],'Mercado competido')
        for a in self.data:
            r=evaluar(a,self.base)
            self.assertTrue(0<=r['total']<=100)
            self.assertTrue(all(0<=v<=100 for v in r['indices']+r['bloques']))

    def test_cuadrantes_y_cortes_inclusivos(self):
        cases=[(75,5,'Mercado atractivo'),(100,6,'Mercado competido'),(74.99,5,'Baja tracción'),(74.99,6,'Mercado débil'),(100,0,'Mercado atractivo')]
        for demand,comp,label in cases:
            with self.subTest(label=label,demand=demand):
                self.assertEqual(cuadrante(demand,comp,Config()),label)

    def test_demanda_baja_no_se_convierte_en_oportunidad_verde(self):
        self.assertEqual(cuadrante(20,0,Config()),'Baja tracción')

    def test_umbral_busquedas_no_modifica_puntaje(self):
        for a in self.data:
            default=evaluar(a,self.base)
            changed=evaluar(a,self.base,Config(umbral_busquedas=20))
            self.assertEqual(default['total_sin_tope'],changed['total_sin_tope'])

    def test_competencia_no_penaliza_busquedas_dos_veces(self):
        original=evaluar(dict(self.base,carrera='Programa de prueba'),self.base)
        changed=evaluar(dict(self.base,carrera='Programa de prueba',busquedas=self.base['busquedas']/2),self.base)
        self.assertEqual(original['bloques'][2],changed['bloques'][2])
        self.assertAlmostEqual(original['total_sin_tope']-changed['total_sin_tope'],13.65/2)

    def test_ventajas_no_compensan_fuera_de_su_peso(self):
        a=dict(self.base,carrera='Programa de prueba',alineacion=self.base['alineacion']/2,salario=self.base['salario']*2)
        r=evaluar(a,self.base)
        self.assertAlmostEqual(r['bloques'][1],77.5)
        self.assertAlmostEqual(r['total'],81.05)

    def test_cero_competidores_no_divide_por_cero(self):
        r=evaluar(dict(self.base,carrera='Programa de prueba',competidores=0),self.base)
        self.assertEqual(r['bloques'][2],100)
        self.assertEqual(r['total'],100)

    def test_musica_no_puede_aportar_mas_del_peso_competitivo(self):
        music=self.data[10]
        r=evaluar(music,self.base)
        self.assertEqual(r['indices'][6],100)
        self.assertAlmostEqual(r['bloques'][2]*Config().pesos[2]/100,28)
        self.assertLess(r['total'],100)

    def test_crecimiento_negativo_no_produce_puntaje_negativo(self):
        music=next(a for a in self.data if a['carrera']=='Música')
        r=evaluar(music,self.base)
        self.assertGreater(r['indices'][0],0);self.assertLess(r['indices'][0],50)

    def test_vacantes_no_afectan_calculo(self):
        for a in self.data:
            expected=evaluar(a,self.base)
            for vac in [0,None,100000]:
                modified=dict(a,vacantes=vac)
                modified_base=dict(self.base,vacantes=vac)
                actual=evaluar(modified,modified_base)
                self.assertEqual(actual['total'],expected['total'])
                self.assertEqual(actual['bloques'],expected['bloques'])

    def test_empleabilidad_incluye_profesionales(self):
        a=dict(self.base,carrera='Programa de prueba',alineacion=self.base['alineacion']/2,salario=self.base['salario']/2)
        self.assertAlmostEqual(evaluar(a,self.base)['bloques'][1],65)

    def test_profesionales_aporta_hasta_su_peso(self):
        zero=evaluar(dict(self.base,carrera='Programa de prueba',profesionales=0),self.base)
        half=evaluar(dict(self.base,carrera='Programa de prueba',profesionales=60),self.base)
        double=evaluar(dict(self.base,carrera='Programa de prueba',profesionales=240),self.base)
        self.assertAlmostEqual(zero['total'],79.4)
        self.assertAlmostEqual(half['total'],82.7)
        self.assertAlmostEqual(double['total'],86)

    def test_competencia_limite_absoluto(self):
        for nivel,limit in [('Pregrado',5),('Posgrado',3)]:
            for count in [0,2,3,4,5,6,10]:
                r=evaluar(dict(self.base,carrera='Programa de prueba',competidores=count),self.base,Config(nivel=nivel))
                self.assertAlmostEqual(r['bloques'][2],100 if count<=limit else limit/count*100)
                self.assertEqual(r['cuadrante'],'Mercado atractivo' if count<=limit else 'Mercado competido')
        changed_ref=dict(self.base,competidores=50)
        self.assertEqual(evaluar(self.base,self.base)['total'],evaluar(self.base,changed_ref)['total'])

    def test_pesos_invalidos_no_calculan(self):
        with self.assertRaises(ValueError):evaluar(self.base,self.base,Config([20,20,20,20,10]))

    def test_todas_las_referencias_contra_si_mismas_son_cien(self):
        for nivel in ['Pregrado','Posgrado']:
            for base in self.data:
                r=evaluar(dict(base),base,Config(nivel=nivel))
                self.assertEqual(r['total'],100)
                self.assertEqual(r['bloques'],[100]*5)
                self.assertTrue(all(v==100 for v in r['indices']))

if __name__=='__main__':unittest.main()

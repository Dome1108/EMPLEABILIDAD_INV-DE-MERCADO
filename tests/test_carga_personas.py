import unittest
from unittest.mock import Mock,patch
from data_access import insertar_personas,load_employers


class CargaPersonasTest(unittest.TestCase):
    def test_reintento_solo_para_conexion_rota(self):
        import pyodbc
        from data_access import load
        progress=Mock()
        with patch('data_access._load_once',side_effect=[pyodbc.Error('08S01','10054'),('completo',)]) as query:
            self.assertEqual(load({},['Derecho'],progress),('completo',))
            self.assertEqual(query.call_count,2)
            progress.assert_called_once()
        for state,attempts in [('08S01',2),('42000',1)]:
            with patch('data_access._load_once',side_effect=pyodbc.Error(state,'error')) as query:
                with self.assertRaises(pyodbc.Error):load({},['Derecho'])
                self.assertEqual(query.call_count,attempts)

    def test_lotes_conservan_ids_deduplicados_y_parametrizados(self):
        cursor=Mock()
        ids=[str(i).zfill(10) for i in range(1201)]
        insertar_personas(cursor,'#industry_people',ids+ids[:2])
        self.assertEqual(cursor.execute.call_count,3)
        parameters=[]
        for call in cursor.execute.call_args_list:
            query,*values=call.args
            self.assertLessEqual(len(values),500)
            self.assertEqual(query.count('(?)'),len(values))
            self.assertNotIn(ids[0],query)
            parameters.extend(values)
        self.assertEqual(parameters,ids)

    def test_vacio_no_conecta_y_tabla_se_valida(self):
        with patch('data_access.connect') as connect:
            self.assertTrue(load_employers({},()).empty)
            connect.assert_not_called()
        with self.assertRaises(ValueError):insertar_personas(Mock(),'otra',[])

import unittest
import pandas as pd
from geography import locations, territorial_summary


class TerritorialRules(unittest.TestCase):
    def test_duplicates_conflicts_and_local_denominator(self):
        atlas = pd.DataFrame([
            ('1', 'Pichincha', 'Quito', 'Centro'),
            ('0000000001', 'PICHINCHA', 'QUITO', 'CENTRO'),
            ('2', 'Pichincha', 'Quito', 'Centro'),
            ('3', 'Guayas', 'Guayaquil', 'Tarqui'),
            ('4', 'Pichincha', 'Quito', 'Centro'),
            ('4', 'Guayas', 'Guayaquil', 'Tarqui'),
        ], columns=['cedula', 'provincia', 'canton', 'parroquia'])
        geo, conflicts = locations(atlas)
        self.assertEqual(conflicts, 1)
        self.assertEqual(len(geo), 3)
        people = pd.DataFrame(dict(person=[str(i).zfill(10) for i in range(1, 6)],
            visible=[True, False, True, True, True], dependent=[True, False, True, True, True],
            salary=[1000., None, 5000., 2000., 3000.]))
        joined = people.merge(geo, how='left', on='person', validate='one_to_one')
        result = territorial_summary(joined, 'PICHINCHA', 'QUITO', 'CENTRO')
        self.assertEqual(result['graduates'], 2)
        self.assertEqual(result['rate'], 50)
        self.assertEqual(result['p25'], 1000)
        self.assertEqual(result['p75'], 1000)
        self.assertEqual(len(people), 5)
        self.assertTrue(pd.isna(territorial_summary(joined, 'AZUAY')['rate']))

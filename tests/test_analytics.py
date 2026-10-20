import unittest
import pandas as pd

from analytics import calculate, normalize_id, sri_status, SNAPSHOTS


class EmploymentRules(unittest.TestCase):
    def test_identity_preserves_zero_and_rejects_ruc(self):
        self.assertEqual(normalize_id(" 123456789 "), "0123456789")
        self.assertIsNone(normalize_id("0123456789001"))
        self.assertIsNone(normalize_id("ABC123"))
        self.assertIsNone(normalize_id(None))

    def test_cohorts_priority_deduplication_salary_and_multiple_degrees(self):
        grads = pd.DataFrame([
            ["123456789", "2020-01-01", "A", "Economía"],
            ["123456789", "2020-01-01", "A", "Economía"],
            ["123456789", "2024-01-01", "B", "Economía"],
            ["223456789", "2020-01-01", "A", "Economía"],
            ["323456789", "2024-04-01", "B", "Economía"],
            ["423456789", "2026-02-01", "B", "Economía"],
            ["bad", "2020-01-01", "B", "Economía"],
            ["523456789", None, "B", "Economía"],
        ],columns=["IDENTIFICACION","FECHA_REGISTRO","INSTITUCION_EDUCACION_SUPERIOR","CARRERA_HOMOLOGADA"])
        jobs = {s.year: pd.DataFrame([
            ["123456789", "EMP1", 1000], ["123456789", "EMP1", 1000],
            ["123456789", "EMP2", 500], ["323456789", "EMP1", 2500],
        ], columns=["NUMAFI","RUCEMP","salary"]) for s in SNAPSHOTS}
        sri = pd.DataFrame([
            ["0123456789001", "ACTIVO", "2019-01-01", None, None, "2026-01-01", "2026-01-01"],
            ["0223456789001", "ACTIVO", "2019-01-01", None, None, "2026-01-01", "2026-01-01"],
        ],columns=["NUMERO_RUC","ESTADO_CONTRIBUYENTE","FECHA_INICIO_ACTIVIDADES","FECHA_SUSPENSION_DEFINITIVA","FECHA_REINICIO_ACTIVIDADES","FECHA_CARGA","FECHA_ACTUALIZACION"])
        summary, institutions, people, quality = calculate(grads,jobs,sri,as_of='2026-10-20')
        first = summary.iloc[0]
        self.assertEqual(first.graduates,2)
        self.assertEqual(first.dependent,1)
        self.assertEqual(first.independent,1)
        self.assertEqual(first.rate,100)
        self.assertEqual(first.p25,1500)
        second = summary.iloc[1]
        self.assertEqual(second.graduates,3)
        self.assertEqual(second.recent,2) # incluye segunda titulación de la primera persona
        self.assertEqual(second.p25,1750)
        self.assertEqual(second.p75,2250)
        self.assertEqual(summary.iloc[-1].graduates,3) # registro de febrero excluido de enero
        self.assertEqual(quality['invalid_ids'],1)
        self.assertEqual(quality['invalid_dates'],1)
        self.assertEqual(quality['recent_2026'],1)
        self.assertEqual(quality['recent_2026_cutoff'],'2026-02-01')
        self.assertTrue(all(summary.employed <= summary.graduates))
        self.assertTrue(all(summary.dependent+summary.independent+summary.unknown == summary.graduates))

    def test_current_2026_card_and_private_ies_deduplicate_aliases(self):
        grads = pd.DataFrame([
            ['123456789','2020-01-01','Universidad de las Américas'],
            ['123456789','2026-03-15','UNIVERSIDAD DE LAS AMERICAS'],
            ['123456789','2026-03-15','UDLA'],
            ['223456789','2020-01-01','UNIVERSIDAD TECNOLOGICA EQUINOCCIAL'],
            ['223456789','2021-01-01','UNIVERSIDAD UTE'],
            ['323456789','2026-06-01','UNIVERSIDAD DE LAS AMERICAS'],
            ['423456789','2026-12-01','UNIVERSIDAD DE LAS AMERICAS'],
            ['523456789','2027-01-01','UNIVERSIDAD DE LAS AMERICAS'],
        ], columns=['IDENTIFICACION','FECHA_REGISTRO','INSTITUCION_EDUCACION_SUPERIOR'])
        jobs = {s.year:pd.DataFrame(columns=['NUMAFI','RUCEMP','salary']) for s in SNAPSHOTS}
        sri = pd.DataFrame(columns=['NUMERO_RUC','ESTADO_CONTRIBUYENTE','FECHA_INICIO_ACTIVIDADES','FECHA_SUSPENSION_DEFINITIVA','FECHA_REINICIO_ACTIVIDADES','FECHA_CARGA','FECHA_ACTUALIZACION'])
        summary, institutions, _, quality = calculate(grads,jobs,sri,as_of='2026-10-20')
        self.assertEqual(quality['recent_2026'],2)
        self.assertEqual(quality['recent_2026_cutoff'],'2026-06-01')
        self.assertEqual(summary.iloc[-1].graduates,2)
        self.assertEqual(summary.iloc[-1].recent,2)
        self.assertEqual(summary.iloc[-1].academic_cutoff,'2026-06-01')
        private=pd.DataFrame(quality['private_institutions'])
        cut=private[private.year.eq(2026)].set_index('code')
        self.assertEqual(len(cut),18)
        self.assertEqual(cut.loc['UTE','professionals'],1)
        self.assertEqual(cut.loc['UDLA','professionals'],2)
        self.assertEqual(cut.loc['UDLA','recent'],2)
        self.assertEqual(cut.loc['UTPL','professionals'],0)

    def test_sri_temporal_events(self):
        row = dict(FECHA_INICIO_ACTIVIDADES=pd.Timestamp('2020-01-01'),
            FECHA_SUSPENSION_DEFINITIVA=pd.Timestamp('2024-01-01'),
            FECHA_REINICIO_ACTIVIDADES=pd.Timestamp('2025-06-01'),ESTADO_CONTRIBUYENTE='ACTIVO')
        self.assertEqual(sri_status(row,pd.Timestamp('2023-02-28')),'Activo')
        self.assertEqual(sri_status(row,pd.Timestamp('2024-05-31')),'Inactivo')
        self.assertEqual(sri_status(row,pd.Timestamp('2025-01-31')),'Inactivo')
        self.assertEqual(sri_status(row,pd.Timestamp('2026-01-31')),'Activo')
        row['FECHA_SUSPENSION_DEFINITIVA'] = pd.NaT
        self.assertEqual(sri_status(row,pd.Timestamp('2024-05-31')),'Indeterminado')

    def test_missing_history_not_assumed_inactive_or_active(self):
        row = dict(FECHA_INICIO_ACTIVIDADES=pd.Timestamp('2020-01-01'),
            FECHA_SUSPENSION_DEFINITIVA=pd.NaT,FECHA_REINICIO_ACTIVIDADES=pd.NaT,
            ESTADO_CONTRIBUYENTE='SUSPENDIDO')
        self.assertEqual(sri_status(row,pd.Timestamp('2023-02-28')),'Indeterminado')


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

import data_access
from market_data import (NO_PRICE, UNCLASSIFIED, aggregate_prices, enrollment_table,
                         graduates_table, price_metrics)
from market_fixtures import GRADUATES, INSTITUTIONS, PRICES


class MarketQueries(unittest.TestCase):
    def run_query(self, function, *args, has_financing_column=False):
        cursor = MagicMock()
        cursor.description = [("A",)]
        cursor.fetchall.return_value = []
        cursor.fetchone.return_value = (1,) if has_financing_column else None
        connection = MagicMock()
        connection.cursor.return_value = cursor
        with patch("data_access.connect", return_value=connection):
            function({}, *args)
        return [call.args for call in cursor.execute.call_args_list]

    def test_enrollment_sums_total_matriculados_with_parameters(self):
        sql, *params = self.run_query(data_access.load_enrollment, ["ECONOMIA"], "TERCER NIVEL", "PICHINCHA")[-1]
        self.assertIn("SUM(CAST(m.TOTAL_MATRICULADOS AS bigint))", sql)
        self.assertNotIn("COUNT", sql.upper())
        self.assertNotIn("SELECT *", sql)
        self.assertIn("[senescyt].[Matriculados_Senescyt]", sql)
        self.assertEqual(params, ["ECONOMIA", "TERCER NIVEL", 2020, 2024, "PICHINCHA"])

    def test_graduates_count_records_by_year_of_fecha_registro(self):
        sql, *params = self.run_query(data_access.load_graduates_by_year, ["ECONOMIA"], "TERCER NIVEL")[-1]
        self.assertIn("[senescyt].[Graduados_nueva]", sql)
        self.assertIn("YEAR(COALESCE(TRY_CONVERT(date, g.FECHA_REGISTRO, 103)", sql)
        self.assertIn("COUNT_BIG(*)", sql)
        self.assertEqual(params, ["ECONOMIA", "TERCER NIVEL", 2020, 2024])

    def test_prices_use_final_career_and_homologated_columns(self):
        for exists, expected in ((True, "p.HOMOLOGADOS_FINANCIAMIENTO"), (False, "p.FINANCIAMIENTO")):
            with self.subTest(column_exists=exists):
                sql, *params = self.run_query(data_access.load_prices, ["ECONOMIA"], "TERCER NIVEL",
                                              has_financing_column=exists)[-1]
                self.assertIn("p.CARRERA_HOMOLOGADA_FINAL", sql)
                self.assertIn("p.HOMOLOGADOS_NIVEL_ACADEMICO", sql)
                self.assertIn(expected, sql)
                # CARRERA_UDLA solo se lee para el arancel UDLA; la carrera se filtra por la columna final.
                where = sql[sql.index("WHERE"):]
                self.assertIn("CARRERA_HOMOLOGADA_FINAL", where)
                self.assertNotIn("CARRERA_UDLA", where)
                self.assertEqual(params, ["ECONOMIA", "TERCER NIVEL"])

    def test_udla_prices_query_filters_udla_and_level(self):
        sql, *params = self.run_query(data_access.load_udla_prices, "TERCER NIVEL")[-1]
        self.assertIn("LTRIM(RTRIM(p.SIGLA)) = 'UDLA'", sql)
        self.assertIn("HOMOLOGADOS_NIVEL_ACADEMICO", sql[sql.index("WHERE"):])
        self.assertNotIn("SELECT *", sql)
        self.assertEqual(params, ["TERCER NIVEL"])

    def test_market_queries_are_read_only(self):
        for name in ("load_enrollment", "load_graduates_by_year", "load_prices", "load_udla_prices", "market_catalog",
                     "institution_financing", "enrollment_provinces"):
            args = {"load_enrollment": (["X"], "TERCER NIVEL"), "load_graduates_by_year": (["X"], "TERCER NIVEL"),
                    "load_prices": (["X"], "TERCER NIVEL"), "load_udla_prices": ("TERCER NIVEL",)}.get(name, ())
            for sql, *_ in self.run_query(getattr(data_access, name), *args):
                self.assertFalse(any(word in sql.upper() for word in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER")))


class MarketCalculations(unittest.TestCase):
    def test_enrollment_table_projects_2025_and_filters_financing(self):
        raw = pd.DataFrame([[y, "PUBLICO", 100 + 10 * (y - 2020)] for y in range(2020, 2025)]
                           + [[2024, "PRIVADO", 7]], columns=["ANIO", "FINANCIAMIENTO", "TOTAL_MATRICULADOS"])
        table, growth = enrollment_table(raw)
        self.assertAlmostEqual(table.loc["PUBLICO", 2025], 150)
        self.assertEqual(table.loc["TOTAL", 2024], 147)
        self.assertAlmostEqual(growth.loc["PUBLICO", "CREC_2021"], 10.0)
        only_private, _ = enrollment_table(raw, "PRIVADO")
        self.assertEqual(list(only_private.index), ["PRIVADO", "TOTAL"])
        self.assertEqual(only_private.loc["TOTAL", 2024], 7)

    def test_growth_rate_projection_uses_2023_to_2024(self):
        raw = pd.DataFrame([[2023, "PUBLICO", 100], [2024, "PUBLICO", 120], [2024, "PRIVADO", 9]],
                           columns=["ANIO", "FINANCIAMIENTO", "TOTAL_MATRICULADOS"])
        table, _ = enrollment_table(raw, method="CRECIMIENTO")
        self.assertAlmostEqual(table.loc["PUBLICO", 2025], 144)
        self.assertEqual(table.loc["PRIVADO", 2025], 9)  # 2023 = 0: tasa indefinida, se mantiene 2024
        graduates, _ = graduates_table(GRADUATES, INSTITUTIONS, method="CRECIMIENTO")
        self.assertIn(2025, graduates.columns)

    def test_graduates_inherit_institution_financing_and_aliases(self):
        table, _ = graduates_table(GRADUATES, INSTITUTIONS)
        self.assertEqual(table.loc["PUBLICO", 2022], 30)
        self.assertEqual(table.loc["PRIVADO", 2024], 5)  # Tecnológica Equinoccial → UTE
        self.assertEqual(table.loc[UNCLASSIFIED, 2024], 2)
        self.assertEqual(table.loc["TOTAL", list(range(2020, 2025))].sum(), 49)

    def test_aggregate_prices_one_row_per_institution_and_keeps_missing_prices(self):
        result = aggregate_prices(PRICES)
        self.assertEqual(list(result["SIGLA"]), ["UTPL", "UDLA", "PUCE", "UCE"])
        self.assertEqual(set(result["SEMESTRE_POS"]), {202520})
        utpl = result.set_index("SIGLA").loc["UTPL"]
        self.assertEqual((utpl.ARANCEL_MINIMO, utpl.ARANCEL_PROMEDIO, utpl.ARANCEL_MAXIMO), (1200, 1300, 1400))
        self.assertEqual(result.set_index("SIGLA").loc["UCE", "ESTADO_PRECIO"], NO_PRICE)
        self.assertEqual(list(aggregate_prices(PRICES, semester=202420)["SIGLA"]), ["UDLA"])
        self.assertEqual(list(aggregate_prices(PRICES, financing="PUBLICO")["SIGLA"]), ["UCE"])

    def test_price_metrics_compare_udla_with_competition(self):
        metrics = price_metrics(aggregate_prices(PRICES))
        self.assertEqual((metrics["offering"], metrics["competitors"], metrics["priced"], metrics["without_price"]),
                         (4, 3, 3, 1))
        self.assertEqual(metrics["coverage"], 75)
        self.assertEqual((metrics["market_min"], metrics["market_max"]), (1200, 3900))
        self.assertEqual(metrics["competitor_mean"], 2600)
        self.assertEqual(metrics["own_gap"], 400)

    def test_price_boxplot_is_vertical_box_with_labeled_points(self):
        from education_visuals import price_boxplot

        figure = price_boxplot(aggregate_prices(PRICES), "Economía")
        self.assertEqual([trace.type for trace in figure.data], ["box", "scatter", "scatter"])
        self.assertEqual(figure.data[2].name, "UDLA")
        self.assertIn("Semestre", figure.data[1].hovertemplate)
        self.assertEqual(figure.layout.yaxis.tickprefix, "$")



def career_rows(career, carrera_udla, facultad, semester="202520"):
    """Ofertas de competidores de una carrera sin oferta UDLA propia."""
    return pd.DataFrame(
        [[semester, "PUCE", career, "TERCER NIVEL", "PRIVADO", "3900", carrera_udla, facultad],
         [semester, "UTPL", career, "TERCER NIVEL", "PRIVADO", "1300", carrera_udla, facultad]],
        columns=["SEMESTRE_POS", "SIGLA", "CARRERA_HOMOLOGADA_FINAL", "HOMOLOGADOS_NIVEL_ACADEMICO",
                 "HOMOLOGADOS_FINANCIAMIENTO", "ARANCEL", "CARRERA_UDLA", "FACULTAD"])


class ArancelUDLA(unittest.TestCase):
    def resolve(self, prices, semester=202520):
        from market_data import obtener_arancel_udla
        from market_fixtures import UDLA_PRICES
        table = aggregate_prices(prices, semester=semester)
        return obtener_arancel_udla(prices, UDLA_PRICES, table, "TERCER NIVEL", semester)

    def test_a_precio_real_de_la_oferta_udla(self):
        info = self.resolve(PRICES)
        self.assertEqual((info["tipo"], info["arancel"], info["carrera_udla"]), ("real", 3000.0, "ECONOMIA"))

    def test_a_precio_real_por_carrera_udla(self):
        from market_fixtures import ECON
        info = self.resolve(career_rows("COMERCIO EXTERIOR", "NEGOCIOS INTERNACIONALES", ECON))
        self.assertEqual((info["tipo"], info["arancel"], info["carrera_udla"]), ("real", 3500.0, "NEGOCIOS INTERNACIONALES"))

    def test_b_e_f_estimado_por_facultad_y_nivel_una_vez_por_carrera(self):
        from market_fixtures import ECON
        for missing in ("SIN REGISTRO", None, "", " sin registro "):
            with self.subTest(carrera_udla=missing):
                info = self.resolve(career_rows("ADMINISTRACION PUBLICA", missing, ECON))
                self.assertEqual(info["tipo"], "estimado")
                # ECONOMIA 3000, NEGOCIOS 3500, ADMINISTRACION (3 filas) 4000; sin arancel 0 ni maestrías.
                self.assertAlmostEqual(info["arancel"], 3500.0)
                self.assertEqual(info["carreras_referencia"],
                                 ["ADMINISTRACION DE EMPRESAS", "ECONOMIA", "NEGOCIOS INTERNACIONALES"])
                self.assertEqual((info["facultad"], info["periodo"], info["historico"]), (ECON, 202520, False))
                detail = info["detalle"].set_index("REFERENCIA")
                self.assertEqual(detail.loc["ADMINISTRACION DE EMPRESAS", "REGISTROS"], 3)
                self.assertNotIn("MAESTRIA EN FINANZAS", info["carreras_referencia"])
                self.assertNotIn("CONTABILIDAD Y AUDITORIA", info["carreras_referencia"])

    def test_c_sin_facultad_no_promedia_toda_la_udla(self):
        for faculty in ("SIN REGISTRO", None, ""):
            with self.subTest(facultad=faculty):
                info = self.resolve(career_rows("AGRONOMIA", "SIN REGISTRO", faculty))
                self.assertEqual((info["tipo"], info["arancel"]), ("sin_informacion", None))

    def test_d_facultad_sin_precios_validos(self):
        for career, faculty in (("PRODUCCION MUSICAL", "ESCUELA DE MUSICA"), ("MEDICINA FAMILIAR", "FACULTAD DE MEDICINA")):
            with self.subTest(facultad=faculty):
                info = self.resolve(career_rows(career, "SIN REGISTRO", faculty))
                self.assertEqual((info["tipo"], info["arancel"], info["facultad"]), ("sin_informacion", None, faculty))

    def test_periodo_anterior_solo_si_no_hay_datos_y_marcado_historico(self):
        info = self.resolve(career_rows("DERECHO PENAL", "SIN REGISTRO", "FACULTAD DE DERECHO"))
        self.assertEqual((info["tipo"], info["periodo"], info["historico"], info["arancel"]), ("estimado", 202420, True, 3400.0))
        # Nunca usa periodos posteriores al seleccionado.
        later = self.resolve(career_rows("DERECHO PENAL", "SIN REGISTRO", "FACULTAD DE DERECHO", "202410"), 202410)
        self.assertEqual(later["tipo"], "sin_informacion")

    def test_facultad_desde_la_carrera_udla_si_la_fila_no_la_trae(self):
        info = self.resolve(career_rows("CIENCIA DE DATOS", "INGENIERIA EN SOFTWARE", "SIN REGISTRO", "202610"), 202610)
        self.assertEqual((info["tipo"], info["facultad"], info["periodo"], info["arancel"]),
                         ("estimado", "FACULTAD DE INGENIERIA Y CIENCIAS APLICADAS", 202520, 3153.0))

    def test_precio_desconocido_no_es_cero(self):
        info = self.resolve(career_rows("AGRONOMIA", "SIN REGISTRO", "SIN REGISTRO"))
        metrics = price_metrics(aggregate_prices(career_rows("AGRONOMIA", "SIN REGISTRO", "SIN REGISTRO")), own_info=info)
        self.assertTrue(pd.isna(metrics["own_price"]))
        self.assertTrue(pd.isna(metrics["own_gap"]))
        self.assertEqual(metrics["competitor_mean"], 2600)

    def test_grafico_distingue_udla_estimado(self):
        from education_visuals import price_boxplot
        from market_fixtures import ECON
        prices = career_rows("ADMINISTRACION PUBLICA", "SIN REGISTRO", ECON)
        figure = price_boxplot(aggregate_prices(prices), "Administración pública", own_info=self.resolve(prices))
        estimated = next(trace for trace in figure.data if trace.name == "UDLA estimado")
        self.assertEqual(estimated.marker.symbol, "diamond-open")
        self.assertIn("Carreras utilizadas: 3", estimated.hovertemplate)
        self.assertEqual(figure.layout.shapes[0].line.dash, "dash")

if __name__ == "__main__":
    unittest.main()

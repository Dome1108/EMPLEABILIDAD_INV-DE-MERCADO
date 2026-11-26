import json
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import trends_analysis as ta
from market_fixtures import fake_market_sources

PAGE = Path(__file__).resolve().parents[1] / "views" / "demanda_interes.py"

PROJECTS = pd.DataFrame([
    dict(id=10, tipo_carpeta="CARRERAS PREGRADO", carrera_referencia="Negocios Internacionales",
         carrera_estudio="ECONOMIA + RRII", creado=date(2026, 10, 6), palabras=3, filas_regionales=0),
    dict(id=20, tipo_carpeta="CARRERAS PREGRADO", carrera_referencia="Negocios Internacionales",
         carrera_estudio="ECONOMIA", creado=date(2026, 10, 7), palabras=8, filas_regionales=6),
    dict(id=30, tipo_carpeta="POSGRADOS TENDENCIA", carrera_referencia="Maestria en enfermeria",
         carrera_estudio="M. GERONTOLOGIA", creado=date(2026, 10, 19), palabras=0, filas_regionales=0),
])
KEYWORDS = pd.DataFrame({"palabra": [f"p{i}" for i in range(8)], "palabra_ingles": None,
                         "promedio": [60, 50, 40, 30, 20, 10, 5, 1]})
REGIONAL = pd.DataFrame([
    ("economia", "economics", 2024, "Ecuador", 40.0, None), ("economia", "economics", 2024, "Perú", 60.0, None),
    ("economia", "economics", 2024, "España", 20.0, None), ("economia", "economics", 2025, "Ecuador", 50.0, None),
    ("economia", "economics", 2025, "Perú", 70.0, None), ("economia", "economics", 2025, "España", 30.0, None),
], columns=["palabra_espanol", "palabra_ingles", "anio", "pais", "valor_espanol", "valor_ingles"])
BASE = pd.DataFrame([("Negocios Internacionales", "Pregrado", f"b{i}", 10 + i) for i in range(5)]
                    + [("Negocios Internacionales", "Posgrado", "x", 999)],
                    columns=["carrera", "nivel", "palabra", "cantidad"])
EXTRACTED = pd.Timestamp("2026-11-12 10:00")
COMPARISON = pd.DataFrame([
    ("economia", "economics", "today 5-y", "Ecuador", 90.0, 10.0, EXTRACTED),
    ("economia", "economics", "today 5-y", "Estados Unidos", 15.0, 85.0, EXTRACTED),
    ("economia", "economics", "today 5-y", "Filipinas", 1.0, 99.0, EXTRACTED),
    ("economia", "economics", "today 5-y", "Groenlandia", None, None, EXTRACTED),
], columns=["palabra_espanol", "palabra_ingles", "periodo", "pais", "valor_espanol", "valor_ingles", "extraido_en"])
TIE = pd.DataFrame([("software", "software", "today 5-y", "Chequia", 50.0, 50.0, EXTRACTED)],
                   columns=COMPARISON.columns)


class TrendsAnalysis(unittest.TestCase):
    def test_comparison_table_assigns_each_country_to_its_winning_word(self):
        table = ta.comparison_table(pd.concat([COMPARISON, TIE]))
        self.assertEqual(table["País"].tolist(), ["Ecuador", "Chequia", "Estados Unidos", "Filipinas"])  # sin Groenlandia
        self.assertEqual(table["Predomina"].tolist(), ["Español", "Empate", "Inglés", "Inglés"])
        self.assertEqual(table["ISO3"].tolist(), ["ECU", "CZE", "USA", "PHL"])
        self.assertTrue(ta.comparison_table(None).empty)

    def test_country_codes_cover_google_trends_spanish_names(self):
        for name, code in (("Côte d’Ivoire", "CIV"), ("Arabia Saudí", "SAU"), ("Myanmar (Birmania)", "MMR"),
                           ("Islas Malvinas (Islas Falkland)", "FLK"), ("Perú", "PER")):
            self.assertEqual(ta.country_code(name), code)

    def test_best_project_prefers_exact_study_program(self):
        self.assertEqual(ta.best_project(PROJECTS, "ECONOMIA", "TERCER NIVEL"), 20)
        self.assertEqual(ta.best_project(PROJECTS, "NEGOCIOS INTERNACIONALES", "TERCER NIVEL"), 20)
        self.assertIsNone(ta.best_project(PROJECTS, "MEDICINA", "TERCER NIVEL"))

    def test_search_interest_uses_top6_and_reference_base_of_same_level(self):
        project = PROJECTS.set_index("id").loc[20]
        base = ta.reference_base(BASE, project)
        self.assertEqual(len(base), 5)  # sin la fila de posgrado
        result = ta.search_interest(KEYWORDS, base)
        self.assertAlmostEqual(result["top_mean"], 35.0)       # (60+50+40+30+20+10)/6
        self.assertAlmostEqual(result["base_mean"], 12.0)      # 10..14
        self.assertAlmostEqual(result["ratio"], 35 / 12 * 100)
        self.assertAlmostEqual(result["points"], ta.TRENDS_WEIGHT)  # tope de 8,57

    def test_regional_series_and_slopes(self):
        series, trends = ta.regional_series(REGIONAL)
        self.assertEqual(list(series.index), [2024, 2025])
        # Medianas 2024: 40 y 2025: 50 -> referencia 45; factores 1,125 y 0,9.
        self.assertAlmostEqual(series.loc[2024, "Ecuador"], 45)
        self.assertAlmostEqual(series.loc[2024, "LATAM"], 56.25)        # (40 + 60) / 2 × 1,125
        self.assertAlmostEqual(series.loc[2025, "LATAM"], 54)           # (50 + 70) / 2 × 0,9
        self.assertAlmostEqual(series.loc[2025, "Todo el mundo"], 45)   # promedio 50 × 0,9
        self.assertAlmostEqual(trends["LATAM"]["slope"], -2.25)         # recta del primer al último punto
        self.assertAlmostEqual(trends["Ecuador"]["slope"], 0)

    def test_trend_line_reaches_the_last_point(self):
        import numpy as np

        line, slope = ta._slope(np.array([2020., 2025., 2026.]), np.array([10., 20., 4.]))
        self.assertAlmostEqual(line[0], 10)       # primer punto
        self.assertAlmostEqual(line[-1], 4)       # último punto (2026*)
        self.assertAlmostEqual(slope, -1)         # (4 − 10) / 6 años

    def test_regional_chart_has_shaded_areas(self):
        import trends_visuals as tv

        series, trends = ta.regional_series(REGIONAL)
        fig = tv.regional_figure(series, trends)
        lines = [t for t in fig.data if t.name in ("Ecuador", "LATAM", "Todo el mundo")]
        self.assertTrue(all(t.fill == "tozeroy" and t.fillcolor.startswith("rgba") for t in lines))

    def test_only_countries_present_every_year(self):
        fixed = [f"País {i}" for i in range(10)]
        rows = [("x", None, year, p, 20.0, None) for year in (2024, 2025) for p in fixed]
        rows += [("x", None, 2025, "Isla nueva", 100.0, None)]
        series, _ = ta.regional_series(pd.DataFrame(rows, columns=REGIONAL.columns))
        self.assertAlmostEqual(series.loc[2024, "Todo el mundo"], series.loc[2025, "Todo el mundo"])

    def test_new_leader_country_does_not_rescale_the_others(self):
        # 2025: aparece una isla con 100 y Google reescala a los demás a la mitad.
        rows = [("x", None, 2024, p, v, None) for p, v in (("Ecuador", 40.0), ("Perú", 60.0), ("Etiopía", 100.0),
                                                             ("India", 20.0), ("Chile", 40.0))]
        rows += [("x", None, 2025, p, v, None) for p, v in (("Ecuador", 20.0), ("Perú", 30.0), ("Etiopía", 50.0),
                                                             ("India", 10.0), ("Chile", 20.0), ("Santa Elena", 100.0))]
        series, _ = ta.regional_series(pd.DataFrame(rows, columns=REGIONAL.columns))
        # Sin corrección Ecuador caería a la mitad (40 -> 20); corregido cae solo por el país nuevo.
        self.assertAlmostEqual(series.loc[2025, "Ecuador"] / series.loc[2024, "Ecuador"], 0.8)

    def test_country_table(self):
        table = ta.country_table(REGIONAL)
        self.assertEqual(table.loc[0, "País"], "Perú")
        self.assertEqual(table.loc[0, "ISO3"], "PER")
        self.assertEqual(table.loc[0, "Valor último año"], 70)
        self.assertIn("sin dato en inglés", table.loc[0, "Idioma"])


class TrendsSection(unittest.TestCase):
    def setUp(self):
        import streamlit as st
        st.cache_data.clear()

    def run_page(self, **extra):
        with fake_market_sources() as stack:
            stack.enter_context(patch("tendencias_data.database_url", return_value="postgresql://prueba"))
            stack.enter_context(patch("tendencias_data.load_trend_projects", return_value=PROJECTS))
            loader = stack.enter_context(patch("tendencias_data.load_trend_project", return_value=dict(
                keywords=KEYWORDS, regional=REGIONAL, base=BASE, **extra)))
            app = AppTest.from_file(str(PAGE), default_timeout=30)
            app.session_state['selected_careers'] = ['ECONOMIA']  # sin carrera la página no muestra datos
            app.run()
            return app, loader

    def test_map_is_the_comparative_breakdown_with_word_colors(self):
        app, _ = self.run_page(comparison=COMPARISON)
        self.assertFalse(app.exception)
        self.assertTrue(any("Desglose comparativo por región" in m.value for m in app.markdown))
        self.assertFalse(any("Español frente a inglés" in m.value for m in app.markdown))  # sección quitada
        charts = [json.loads(c.proto.spec) for c in app.get("plotly_chart")]
        self.assertEqual(len(charts), 5)  # matriculados, titulados, palabras, regional, mapa
        traces = charts[4]["data"]
        maps = {t["name"]: t for t in traces if t["type"] == "choropleth"}
        self.assertEqual(maps["economia (español)"]["locations"], ["ECU"])
        self.assertEqual(sorted(maps["economics (inglés)"]["locations"]), ["PHL", "USA"])
        legend = [t["name"] for t in traces if t["type"] == "scattergeo" and t.get("showlegend")]
        self.assertEqual(legend, ["economia (español)", "economics (inglés)"])  # color de cada palabra
        self.assertTrue(any("12/11/2026" in c.value for c in app.caption))

    def test_without_comparison_keeps_spanish_index_map(self):
        app, _ = self.run_page()
        self.assertFalse(app.exception)
        self.assertTrue(any("Interés por país" in m.value for m in app.markdown))
        self.assertTrue(any("desglose comparativo" in c.value for c in app.caption))

    def test_section_shows_google_trends_charts(self):
        app, loader = self.run_page()
        self.assertFalse(app.exception)
        self.assertTrue(any("Interés en Google Trends" in s.value for s in app.subheader))
        box = next(s for s in app.selectbox if s.label == "Proyecto de Google Trends")
        self.assertEqual(box.value, 20)               # coincide con la carrera filtrada (Economía)
        self.assertFalse(any(str(o).startswith("30 ·") for o in box.options))  # proyecto sin datos
        loader.assert_called_once_with("postgresql://prueba", 20)
        metrics = {m.label: m.value for m in app.metric}
        self.assertEqual(metrics["Promedio top 6 palabras"], "35,0")
        self.assertEqual(metrics["Aporte al puntaje web"], "8,57 / 8,57")
        charts = [json.loads(c.proto.spec) for c in app.get("plotly_chart")]
        self.assertEqual(len(charts), 5)  # matriculados, titulados, palabras, regional, mapa
        regional = charts[3]
        self.assertEqual([t["name"] for t in regional["data"] if t.get("showlegend") is not False],
                         ["Ecuador", "LATAM", "Todo el mundo"])
        self.assertEqual(charts[4]["data"][0]["type"], "choropleth")

    def test_without_connection_shows_instructions(self):
        with fake_market_sources():
            app = AppTest.from_file(str(PAGE), default_timeout=30)
            app.session_state['selected_careers'] = ['ECONOMIA']  # sin carrera la página no muestra datos
            app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any("database_url" in i.value for i in app.info))

    def test_connection_error_keeps_page(self):
        with fake_market_sources() as stack:
            stack.enter_context(patch("tendencias_data.database_url", return_value="postgresql://prueba"))
            stack.enter_context(patch("tendencias_data.load_trend_projects", side_effect=RuntimeError("sin red")))
            app = AppTest.from_file(str(PAGE), default_timeout=30)
            app.session_state['selected_careers'] = ['ECONOMIA']  # sin carrera la página no muestra datos
            app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Tendencias" in w.value for w in app.warning))


class ComparisonQuery(unittest.TestCase):
    class Cursor:
        def __init__(self, view_exists):
            self.view_exists, self.queries, self.description = view_exists, [], None

        def execute(self, query, params=None):
            self.queries.append(query)
            self.params = getattr(self, "params", []) + [params]
            self.description = [(c,) for c in ("palabra_espanol", "palabra_ingles", "periodo", "pais",
                                                "valor_espanol", "valor_ingles", "extraido_en")]

        def fetchone(self):
            return (self.view_exists,)

        def fetchall(self):
            return []

    def test_missing_view_returns_empty_frame_without_querying_it(self):
        import tendencias_data

        cursor = self.Cursor(view_exists=False)
        comparison, timeline = tendencias_data._load_comparison(cursor, 20)
        self.assertTrue(comparison.empty and timeline.empty)
        self.assertIn("valor_ingles", comparison.columns)
        self.assertIn("fecha", timeline.columns)
        self.assertEqual(len(cursor.queries), 1)

    def test_existing_view_reads_breakdown_and_world_timeline(self):
        import tendencias_data

        cursor = self.Cursor(view_exists=True)
        tendencias_data._load_comparison(cursor, 20)
        self.assertEqual(cursor.params[1:], [(20, "comparacion_pais"), (20, "interes_en_el_tiempo")])
        self.assertTrue(all("vw_google_trends" in q for q in cursor.queries[1:]))
        self.assertEqual(len(cursor.queries), 3)

    def test_world_line_follows_the_timeline(self):
        fixed = [f"País {i}" for i in range(10)]
        rows = [("x", None, year, p, 20.0, None) for year in (2024, 2025) for p in fixed]
        regional = pd.DataFrame(rows, columns=REGIONAL.columns)
        months = pd.date_range("2024-01-01", "2025-12-01", freq="MS")
        timeline = pd.DataFrame({"fecha": months, "valor_espanol": [30.0 if d.year == 2024 else 60.0 for d in months]})
        series, _ = ta.regional_series(regional, timeline)
        self.assertAlmostEqual(series.loc[2025, "Todo el mundo"] / series.loc[2024, "Todo el mundo"], 2)
        self.assertAlmostEqual(series["Todo el mundo"].mean(), 20)
        # Serie incompleta: se mantiene el promedio de países.
        partial, _ = ta.regional_series(regional, timeline[timeline["fecha"].dt.year.eq(2025)])
        self.assertAlmostEqual(partial.loc[2024, "Todo el mundo"], partial.loc[2025, "Todo el mundo"])


if __name__ == "__main__":
    unittest.main()

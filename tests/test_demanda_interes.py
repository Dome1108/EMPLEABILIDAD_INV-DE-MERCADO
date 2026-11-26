import json
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from market_fixtures import fake_market_sources

PAGE = Path(__file__).resolve().parents[1] / "views" / "demanda_interes.py"


class DemandaInteresView(unittest.TestCase):
    def test_page_renders_enrollment_and_graduate_charts(self):
        with fake_market_sources() as _:
            app = AppTest.from_file(str(PAGE), default_timeout=30)
            app.session_state['selected_careers'] = ['ECONOMIA']  # sin carrera la página no muestra datos
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Demanda e interés académico" in item.value for item in app.title))
            self.assertTrue(any("Matriculados" in item.value for item in app.subheader))
            self.assertTrue(any("Titulados" in item.value for item in app.subheader))
            self.assertFalse(any("posteriormente" in item.value for item in app.markdown))
            charts = [json.loads(chart.proto.spec) for chart in app.get("plotly_chart")]
            self.assertEqual(len(charts), 2)
            enrollment = next(t for t in charts[0]["data"] if t["name"] == "Total")
            self.assertEqual(enrollment["x"][-1], "2025*")
            self.assertEqual(enrollment["y"][0], 140)
            graduates = next(t for t in charts[1]["data"] if t["name"] == "Total")
            self.assertEqual(graduates["x"][-1], "2025*")
            bar = next(t for t in charts[0]["data"] if t["type"] == "bar")
            self.assertEqual(bar["marker"]["opacity"], 1)  # 2025* con el mismo color que los demás años
            self.assertNotIn("pattern", bar["marker"])
            # Totales por año debajo de cada título; sin tabla de crecimiento en proyección lineal.
            totals = [frame.value for frame in app.dataframe]
            self.assertEqual(len(totals), 2)
            self.assertEqual(list(totals[0]["Financiamiento"]), ["Público", "Privado"])
            self.assertEqual(totals[0].loc[0, "2020"], "100")
            self.assertEqual(list(totals[1]["Financiamiento"]), ["Público", "Privado"])
            self.assertIn("2025*", totals[0].columns)
            # Carrera y nivel ya no son filtros visibles en esta página.
            keys = {box.key for box in app.selectbox}
            self.assertNotIn("market_career", keys)
            self.assertNotIn("market_level", keys)
            self.assertTrue(any("Economia" in c.value for c in app.caption))

    def test_projection_method_switches_2025(self):
        with fake_market_sources() as _:
            app = AppTest.from_file(str(PAGE), default_timeout=30)
            app.session_state['selected_careers'] = ['ECONOMIA']  # sin carrera la página no muestra datos
            app.run()
            total = lambda: next(t for t in json.loads(app.get("plotly_chart")[0].proto.spec)["data"]
                                 if t["name"] == "Total")["y"][-1]
            self.assertAlmostEqual(total(), 240)  # lineal: 140 + 20 por año (10 público + 10 privado)
            app.selectbox(key="market_projection").set_value("CRECIMIENTO").run()
            self.assertFalse(app.exception)
            self.assertAlmostEqual(total(), 140 ** 2 / 130 + 80 ** 2 / 70)
            self.assertTrue(any("Tasa de crecimiento anual" in m.value for m in app.markdown))
            growth = [frame.value for frame in app.dataframe if "2021" in frame.value.columns
                      and "2020" not in frame.value.columns]
            self.assertEqual(len(growth), 2)
            self.assertEqual(growth[0].set_index("Financiamiento").loc["Público", "2021"], "+10,0 %")
            self.assertEqual(list(growth[1]["Financiamiento"]), ["Público", "Privado", "Total"])

    def test_uses_career_and_level_chosen_elsewhere(self):
        with fake_market_sources() as _, patch("data_access.load_enrollment") as enrollment:
            from market_fixtures import ENROLLMENT
            enrollment.return_value = ENROLLMENT
            app = AppTest.from_file(str(PAGE), default_timeout=30)
            app.session_state["market_level"] = "CUARTO NIVEL"
            # La carrera viene siempre de Oferta de valor-empleabilidad (multiselect selected_careers).
            app.session_state["selected_careers"] = ["MAESTRÍA EN FINANZAS"]
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Maestria En Finanzas" in c.value and "Oferta de valor-empleabilidad" in c.value
                                for c in app.caption))
            enrollment.assert_not_called()  # la carrera no existe en Matriculados

    def test_first_employment_career_with_data_is_used(self):
        with fake_market_sources() as _:
            app = AppTest.from_file(str(PAGE), default_timeout=30)
            app.session_state["selected_careers"] = ["CARRERA INEXISTENTE", "ECONOMIA"]
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["market_career"], "ECONOMIA")
            self.assertTrue(any("primera de las 2 carreras" in c.value for c in app.caption))

    def test_software_joins_names_used_by_each_table(self):
        import pandas as pd
        from market_data import career_sources
        from market_filters import career_with_equivalents
        catalog = pd.DataFrame([["TITULADOS", "SOFTWARE", "TERCER NIVEL"],
                                ["MATRICULADOS", "INGENIERIA DE SOFTWARE", "TERCER NIVEL"],
                                ["PRECIOS", "INGENIERIA EN SOFTWARE", "TERCER NIVEL"]],
                               columns=["FUENTE", "CARRERA", "NIVEL"])
        name, found = career_with_equivalents(career_sources(catalog, "TERCER NIVEL"), "SOFTWARE")
        self.assertEqual(name, "INGENIERIA EN SOFTWARE")
        self.assertEqual(found, {"TITULADOS": ["SOFTWARE"], "MATRICULADOS": ["INGENIERIA DE SOFTWARE"],
                                 "PRECIOS": ["INGENIERIA EN SOFTWARE"]})

    def test_employment_career_without_market_data_warns(self):
        with fake_market_sources() as _:
            app = AppTest.from_file(str(PAGE), default_timeout=30)
            app.session_state["selected_careers"] = ["CARRERA INEXISTENTE"]
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Carrera Inexistente" in w.value for w in app.warning))
            self.assertEqual(len(app.get("plotly_chart")), 0)

    def test_filters_requery_and_switch_series(self):
        with fake_market_sources() as _, patch("data_access.load_enrollment") as enrollment:
            from market_fixtures import ENROLLMENT
            enrollment.return_value = ENROLLMENT
            app = AppTest.from_file(str(PAGE), default_timeout=30)
            app.session_state['selected_careers'] = ['ECONOMIA']  # sin carrera la página no muestra datos
            app.run()
            app.selectbox(key="market_province").set_value("PICHINCHA").run()
            self.assertFalse(app.exception)
            self.assertEqual(enrollment.call_args.args[3], "PICHINCHA")
            app.selectbox(key="market_financing").set_value("PRIVADO").run()
            chart = json.loads(app.get("plotly_chart")[0].proto.spec)
            self.assertEqual([t["name"] for t in chart["data"]], ["Privado", "Total"])

    def test_stale_chart_module_is_reloaded(self):
        import education_visuals
        with fake_market_sources() as _, patch.object(education_visuals, "MARKET_VISUAL_VERSION", 1):
            app = AppTest.from_file(str(PAGE), default_timeout=30)
            app.session_state['selected_careers'] = ['ECONOMIA']  # sin carrera la página no muestra datos
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(education_visuals.MARKET_VISUAL_VERSION, 3)

    def test_connection_failure_shows_error(self):
        import streamlit as st
        st.cache_data.clear()
        with patch("data_access.market_catalog", side_effect=RuntimeError("sin red")):
            app = AppTest.from_file(str(PAGE), default_timeout=30)
            app.session_state['selected_careers'] = ['ECONOMIA']  # sin carrera la página no muestra datos
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any("SQL Server" in item.value for item in app.error))


if __name__ == "__main__":
    unittest.main()

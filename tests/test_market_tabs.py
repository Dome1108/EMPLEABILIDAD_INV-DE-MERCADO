import json
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from market_fixtures import fake_market_sources

ROOT = Path(__file__).resolve().parents[1]


class MarketTabs(unittest.TestCase):
    def test_without_career_pages_show_nothing(self):
        for name in ("demanda_interes.py", "posicionamiento_competencia_precios.py"):
            with self.subTest(page=name), fake_market_sources() as _:
                app = AppTest.from_file(str(ROOT / "views" / name), default_timeout=30).run()
                self.assertFalse(app.exception)
                self.assertTrue(any("Selecciona al menos una carrera" in item.value for item in app.info))
                self.assertEqual(len(app.get("plotly_chart")), 0)
                self.assertNotIn("market_career", app.session_state)

    def test_positioning_page_shows_price_boxplot_and_metrics(self):
        page = ROOT / "views" / "posicionamiento_competencia_precios.py"
        with fake_market_sources() as _:
            app = AppTest.from_file(str(page), default_timeout=30)
            app.session_state['selected_careers'] = ['ECONOMIA']  # sin carrera la página no muestra datos
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Posicionamiento-competencia y precios" in item.value for item in app.title))
            charts = app.get("plotly_chart")
            self.assertEqual(len(charts), 1)
            types = [trace["type"] for trace in json.loads(charts[0].proto.spec)["data"]]
            self.assertEqual(types[0], "box")
            self.assertNotIn("bar", types)
            metrics = {m.label: m.value for m in app.metric}
            self.assertEqual(metrics["Universidades ofertantes"], "4")
            self.assertEqual(list(metrics), ["Universidades ofertantes", "Competidores", "Arancel promedio",
                                             "Arancel UDLA", "Promedio competencia"])
            self.assertEqual(metrics["Arancel UDLA"], "$3.000")
            self.assertEqual(metrics["Promedio competencia"], "$2.600")
            self.assertFalse(any("SIN INFORMACI" in w.value for w in app.warning))

            app.selectbox(key="market_financing").set_value("PUBLICO").run()
            self.assertFalse(app.exception)
            self.assertEqual({m.label: m.value for m in app.metric}["Universidades ofertantes"], "1")


    def run_with_prices(self, prices):
        from unittest.mock import patch
        page = ROOT / "views" / "posicionamiento_competencia_precios.py"
        with fake_market_sources() as _, patch("data_access.load_prices", return_value=prices):
            app = AppTest.from_file(str(page), default_timeout=30)
            app.session_state['selected_careers'] = ['ECONOMIA']  # sin carrera la página no muestra datos
            app.run()
        self.assertFalse(app.exception)
        return app

    def test_arancel_udla_estimado_por_facultad(self):
        from market_fixtures import ECON
        from test_market_data import career_rows
        app = self.run_with_prices(career_rows("ADMINISTRACION PUBLICA", "SIN REGISTRO", ECON))
        metrics = {m.label: m.value for m in app.metric}
        self.assertNotIn("Arancel UDLA", metrics)
        self.assertEqual(metrics["Arancel UDLA estimado"], "$3.500")
        self.assertTrue(any("Estimado con 3 carrera(s) relacionada(s)" in c.value for c in app.caption))
        names = [trace["name"] for trace in json.loads(app.get("plotly_chart")[0].proto.spec)["data"]]
        self.assertIn("UDLA estimado", names)
        self.assertTrue(any("Detalle del arancel UDLA estimado" in e.label for e in app.expander))

    def test_arancel_udla_sin_informacion(self):
        from test_market_data import career_rows
        app = self.run_with_prices(career_rows("AGRONOMIA", "SIN REGISTRO", "SIN REGISTRO"))
        metrics = {m.label: m.value for m in app.metric}
        self.assertEqual(metrics["Arancel UDLA"], "Sin información")
        self.assertTrue(any("Sin información suficiente para estimar el arancel UDLA" in c.value for c in app.caption))
        self.assertEqual(metrics["Promedio competencia"], "$2.600")

    def test_filtro_publico_no_convierte_el_precio_real_en_estimado(self):
        page = ROOT / "views" / "posicionamiento_competencia_precios.py"
        with fake_market_sources() as _:
            app = AppTest.from_file(str(page), default_timeout=30)
            app.session_state['selected_careers'] = ['ECONOMIA']  # sin carrera la página no muestra datos
            app.run()
            app.selectbox(key="market_financing").set_value("PUBLICO").run()
        metrics = {m.label: m.value for m in app.metric}
        self.assertEqual(metrics["Arancel UDLA"], "$3.000")

if __name__ == "__main__":
    unittest.main()

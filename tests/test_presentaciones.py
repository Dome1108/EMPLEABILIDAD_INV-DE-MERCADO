import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["TENDENCIAS_DESACTIVADO"] = "1"  # sin conexión a la base real de Tendencias
from pptx import Presentation
from streamlit.testing.v1 import AppTest

from market_fixtures import fake_market_sources
from presentaciones import cola
from presentaciones import datos as D
from presentaciones import filtros as F
from presentaciones import generador as G
from presentaciones import worker as W

ROOT = Path(__file__).resolve().parents[1]


class ColaTemporal(unittest.TestCase):
    """Cada prueba usa su propia cola SQLite (nunca presentaciones/trabajo/cola.sqlite3)."""

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(self.carpeta.cleanup)
        entorno = patch.dict(os.environ, {"PRESENTACIONES_COLA": os.path.join(self.carpeta.name, "cola.sqlite3")})
        entorno.start()
        self.addCleanup(entorno.stop)


class FiltrosTest(unittest.TestCase):
    def test_reads_every_app_filter_with_defaults(self):
        f = F.desde_estado({"selected_careers": ["SOFTWARE"], "academic_level": "Tercer nivel",
                            "employment_cutoff": 2024, "market_financing": "PRIVADO",
                            "market_province": "PICHINCHA", "market_projection": "CRECIMIENTO",
                            "market_semester": 202710, "industry_ciiu": ["J620101", "K641910"],
                            "industry_month": 6, "geo_provincia": "GUAYAS", "trends_project_SOFTWARE": 150,
                            "color_palette": "Vino"}, demo=False)
        self.assertEqual(f["carreras"], ["SOFTWARE"])
        self.assertEqual(f["mercado_nivel"], "TERCER NIVEL")  # sin market_level: se deriva del nivel académico
        self.assertEqual((f["corte"], f["financiamiento"], f["provincia"], f["proyeccion"], f["semestre"]),
                         (2024, "PRIVADO", "PICHINCHA", "CRECIMIENTO", 202710))
        self.assertEqual((f["ciiu"], f["mes_acumulado"]), (["J620101", "K641910"], 6))
        self.assertEqual(f["territorio"]["provincia"], "GUAYAS")
        self.assertEqual(f["proyectos_tendencias"], {"SOFTWARE": 150})
        self.assertNotIn("color_palette", str(f))  # la paleta no cambia la presentación
        vacio = F.desde_estado({}, demo=False)
        self.assertEqual((vacio["carreras"], vacio["financiamiento"], vacio["proyeccion"], vacio["corte"]),
                         (["ECONOMIA"], "TODOS", "LINEAL", 2026))

    def test_key_changes_only_with_filters(self):
        a = F.desde_estado({"selected_careers": ["SOFTWARE"], "color_palette": "Azul"}, demo=False)
        b = F.desde_estado({"selected_careers": ["SOFTWARE"], "color_palette": "Vino"}, demo=False)
        c = F.desde_estado({"selected_careers": ["SOFTWARE"], "market_financing": "PUBLICO"}, demo=False)
        self.assertEqual(F.clave(a), F.clave(b))
        self.assertNotEqual(F.clave(a), F.clave(c))


class ColaTest(ColaTemporal):
    def test_one_active_job_per_filters(self):
        f = F.desde_estado({"selected_careers": ["SOFTWARE"]}, demo=False)
        primero, nuevo = cola.encolar(F.clave(f), f)
        repetido, otra_vez = cola.encolar(F.clave(f), f)
        self.assertTrue(nuevo)
        self.assertFalse(otra_vez)
        self.assertEqual(primero, repetido)
        self.assertEqual(cola.ultimo(F.clave(f))["estado"], "queued")

    def test_lease_protects_publication_and_expired_job_is_retaken(self):
        f = F.desde_estado({"selected_careers": ["SOFTWARE"]}, demo=False)
        cola.encolar(F.clave(f), f)
        trabajo = cola.tomar(lease=0.01)
        self.assertEqual(trabajo["filtros"], f)
        self.assertIsNone(cola.tomar())  # nadie más lo toma mientras su lease esté vigente…
        time.sleep(.05)
        segundo = cola.tomar()  # …pero si el worker se cae, el lease vence y otro lo retoma
        self.assertEqual((segundo["id"], segundo["intentos"]), (trabajo["id"], 2))
        self.assertFalse(cola.publicar(trabajo["id"], trabajo["lease_token"], "x.pptx", b"viejo"))
        self.assertTrue(cola.publicar(segundo["id"], segundo["lease_token"], "x.pptx", b"nuevo"))
        self.assertEqual(cola.archivo(segundo["id"]), ("x.pptx", b"nuevo"))
        self.assertTrue(cola.ultimo(F.clave(f))["tiene_archivo"])
        nuevo, es_nuevo = cola.encolar(F.clave(f), f)  # terminado: se puede volver a generar
        self.assertTrue(es_nuevo)
        self.assertNotEqual(nuevo, segundo["id"])

    def test_job_fails_after_max_attempts(self):
        f = F.desde_estado({}, demo=False)
        cola.encolar(F.clave(f), f)
        for _ in range(cola.MAX_INTENTOS):
            self.assertIsNotNone(cola.tomar(lease=0.01))
            time.sleep(.03)
        self.assertIsNone(cola.tomar())
        trabajo = cola.ultimo(F.clave(f))
        self.assertEqual(trabajo["estado"], "error")
        self.assertIn("se detuvo", trabajo["error"])


class WorkerTest(ColaTemporal):
    def test_worker_publishes_file_or_records_error(self):
        f = F.desde_estado({"selected_careers": ["SOFTWARE"]}, demo=False)
        cola.encolar(F.clave(f), f)

        def generar(filtros, ruta):
            Path(ruta).write_bytes(b"pptx de prueba")
            return ruta

        self.assertTrue(W.procesar(cola.tomar(), generar=generar))
        trabajo = cola.ultimo(F.clave(f))
        self.assertEqual(trabajo["estado"], "finished")
        self.assertTrue(trabajo["archivo_nombre"].startswith("Software_2026"))
        self.assertEqual(cola.archivo(trabajo["id"])[1], b"pptx de prueba")
        cola.encolar(F.clave(f), f)

        def falla(filtros, ruta):
            raise RuntimeError("sin conexión de prueba")

        self.assertFalse(W.procesar(cola.tomar(), generar=falla))
        trabajo = cola.ultimo(F.clave(f))
        self.assertEqual((trabajo["estado"], trabajo["error"]), ("error", "sin conexión de prueba"))


class GeneradorTest(unittest.TestCase):
    def test_builds_deck_from_filters_without_template_samples(self):
        estado = {"selected_careers": ["Economía"], "academic_level": "Todos los niveles", "employment_cutoff": 2025,
                  "market_projection": "CRECIMIENTO"}
        f = F.desde_estado(estado, demo=True)
        emp = D.empleabilidad({}, f)
        mercado_f = {**F.desde_estado({**estado, "selected_careers": ["ECONOMIA"]}, demo=False)}
        with fake_market_sources():
            mercado = D.mercado({}, mercado_f)
        self.assertEqual(mercado["carrera"], "ECONOMIA")
        datos = dict(filtros=f, empleabilidad=emp, notas=["Google Trends: sin proyecto de prueba"],
                     instituciones=D.instituciones(emp, f), territorio=D.territorio({}, emp, f), sector=None,
                     mercado=mercado, trends=None, linkedin=None, viabilidad=None)
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = G.generar(datos, os.path.join(carpeta, G.nombre_archivo(f)), avisar=lambda _: None)
            prs = Presentation(ruta)
        textos = "\n".join(s.text_frame.text for slide in prs.slides for s in slide.shapes if s.has_text_frame)
        self.assertEqual(len(prs.slides), 27)  # las 27 de la plantilla, como en Tendencias
        # Ningún dato de ejemplo de la plantilla queda como si fuera real.
        for muestra in ("Nombre programa propuesto", "9.725", "Agosto 2026", "Capacidad de Análisis", "72.3%",
                        "mercado saturado", "186 vacantes", "presenta la mayor valoración (100%)"):
            self.assertNotIn(muestra, textos)
        for esperado in ("Carreras: Economía", "Corte de análisis: Enero 2025", "Proyección 2025: Tasa de crecimiento",
                         "valor 2024 × tasa de crecimiento", "Composición del empleo · 2025",
                         "Sin datos: Google Trends: sin proyecto de prueba", "N/D: no hay resultados de Google Trends",
                         "N/D: no hay proyecto de Tendencias con datos de LinkedIn",
                         "N/D: la carrera no está entre las 12", "Next Steps"):
            self.assertIn(esperado, textos)

    def test_viability_slides_use_the_dashboard_model(self):
        f = F.desde_estado({"selected_careers": ["INGENIERIA EN SOFTWARE"], "weight0_negocios": 30,
                            "busquedas_negocios": 60}, demo=True)
        via = D.viabilidad_carreras(f)
        self.assertEqual((via["carrera"], via["referencia"], via["config"].umbral_busquedas),
                         ("Software", "Negocios Internacionales", 60))
        emp = D.empleabilidad({}, F.desde_estado({"selected_careers": ["Economía"]}, demo=True))
        datos = dict(filtros=f, empleabilidad=emp, notas=[], instituciones=None, territorio=None, sector=None,
                     mercado=None, trends=None, linkedin=None, viabilidad=via)
        with tempfile.TemporaryDirectory() as carpeta:
            prs = Presentation(G.generar(datos, os.path.join(carpeta, "v.pptx"), avisar=lambda _: None))
        textos = "\n".join(s.text_frame.text for slide in prs.slides for s in slide.shapes if s.has_text_frame)
        total = G.decimal(via["actual"]["total"])
        self.assertIn(f"{total}/100", textos)
        self.assertIn(via["actual"]["clasificacion"], textos)
        self.assertIn(f"La carrera de Software se ubica en el cuadrante «{via['actual']['cuadrante'].lower()}»", textos)
        with self.assertRaises(ValueError):  # Economía no está entre las 12 carreras del modelo
            D.viabilidad_carreras(F.desde_estado({"selected_careers": ["ECONOMIA"]}, demo=True))


class BotonesTest(ColaTemporal):
    def run_app(self):
        with patch.dict(os.environ, {"DASHBOARD_DEMO": "1"}):
            app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
            app.session_state['selected_careers'] = ['Economía']  # el filtro inicia vacío
            app.run()
        self.assertFalse(app.exception)
        return app

    def boton(self, app, clave):
        return next(b for b in app.button if b.key == clave)

    def test_generate_enqueues_current_filters_and_download_follows_them(self):
        app = self.run_app()
        self.assertFalse(self.boton(app, "pptx_generar").disabled)
        self.assertTrue(self.boton(app, "pptx_descargar_inactivo").disabled)
        self.assertTrue(any("Aún no se ha generado" in c.value for c in app.caption))
        self.assertTrue(any("worker de presentaciones no está encendido" in c.value for c in app.caption))
        with patch.dict(os.environ, {"DASHBOARD_DEMO": "1"}):
            self.boton(app, "pptx_generar").click().run()
        from contextlib import closing
        with closing(cola.conectar()) as c:
            clave = c.execute("SELECT clave FROM trabajos ORDER BY id DESC LIMIT 1").fetchone()["clave"]
        trabajo = cola.ultimo(clave)
        self.assertEqual((trabajo["estado"], trabajo["filtros"]["carreras"], trabajo["filtros"]["corte"]),
                         ("queued", ["Economía"], 2026))
        self.assertTrue(self.boton(app, "pptx_generar").disabled)
        # El worker termina: la descarga se activa para esos mismos filtros.
        tomado = cola.tomar()
        cola.publicar(tomado["id"], tomado["lease_token"], "Economia_2026_mercado.pptx", b"pptx")
        with patch.dict(os.environ, {"DASHBOARD_DEMO": "1"}):
            app.run()
        self.assertIn("Descargar .pptx", [d.proto.label for d in app.get("download_button")])
        self.assertTrue(any("Lista ·" in c.value for c in app.caption))
        # Con otros filtros la presentación anterior no se ofrece.
        with patch.dict(os.environ, {"DASHBOARD_DEMO": "1"}):
            app.selectbox(key="employment_cutoff").set_value(2024).run()
        self.assertTrue(self.boton(app, "pptx_descargar_inactivo").disabled)


if __name__ == "__main__":
    unittest.main()

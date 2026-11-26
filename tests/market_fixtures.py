"""Datos mínimos de mercado para probar las vistas sin SQL Server."""
from contextlib import ExitStack
from unittest.mock import patch

import pandas as pd

CATALOG = pd.DataFrame(
    [
        ["MATRICULADOS", "ECONOMIA", "TERCER NIVEL"],
        ["TITULADOS", "Economía", "TERCER NIVEL"],
        ["PRECIOS", "ECONOMIA", "TERCER NIVEL"],
        ["PRECIOS", "MAESTRIA EN FINANZAS", "CUARTO NIVEL"],
    ],
    columns=["FUENTE", "CARRERA", "NIVEL"],
)
ENROLLMENT = pd.DataFrame(
    [[year, fin, value + 10 * (year - 2020)] for year in range(2020, 2025)
     for fin, value in (("PUBLICO", 100), ("PRIVADO", 40))],
    columns=["ANIO", "FINANCIAMIENTO", "TOTAL_MATRICULADOS"],
)
GRADUATES = pd.DataFrame(
    [["UNIVERSIDAD CENTRAL DEL ECUADOR", 2022, 30], ["UNIVERSIDAD DE LAS AMÉRICAS", 2023, 12],
     ["UNIVERSIDAD TECNOLÓGICA EQUINOCCIAL", 2024, 5], ["UNIVERSIDAD EXTRANJERA", 2024, 2]],
    columns=["INSTITUCION", "ANIO", "TITULADOS"],
)
INSTITUTIONS = pd.DataFrame(
    [["UNIVERSIDAD CENTRAL DEL ECUADOR", "PUBLICO"], ["UNIVERSIDAD DE LAS AMERICAS", "PRIVADO"],
     ["UNIVERSIDAD UTE", "PRIVADO"]],
    columns=["NOMBRE_IES", "FINANCIAMIENTO"],
)
PRICES = pd.DataFrame(
    [["202520", "UDLA", "ECONOMIA", "TERCER NIVEL", "PRIVADO", "3000"],
     ["202520", "PUCE", "ECONOMIA", "TERCER NIVEL", "PRIVADO", "3900"],
     ["202520", "UTPL", "ECONOMIA", "TERCER NIVEL", "PRIVADO", "1200"],
     ["202520", "UTPL", "ECONOMIA", "TERCER NIVEL", "PRIVADO", "1400"],
     ["202520", "UCE", "ECONOMIA", "TERCER NIVEL", "PUBLICO", "0"],
     ["202420", "UDLA", "ECONOMIA", "TERCER NIVEL", "PRIVADO", "2800"]],
    columns=["SEMESTRE_POS", "SIGLA", "CARRERA_HOMOLOGADA_FINAL", "HOMOLOGADOS_NIVEL_ACADEMICO",
             "HOMOLOGADOS_FINANCIAMIENTO", "ARANCEL"],
).assign(CARRERA_UDLA="ECONOMIA", FACULTAD="FACULTAD DE CIENCIAS ECONOMICAS Y ADMINISTRATIVAS")
ECON = "FACULTAD DE CIENCIAS ECONOMICAS Y ADMINISTRATIVAS"
# Ofertas UDLA (SIGLA = 'UDLA') para el arancel real o estimado por facultad.
UDLA_PRICES = pd.DataFrame(
    [["202520", "ECONOMIA", "ECONOMIA", ECON, "TERCER NIVEL", "3000"],
     ["202520", "NEGOCIOS INTERNACIONALES", "NEGOCIOS INTERNACIONALES", ECON, "TERCER NIVEL", "3500"],
     # Tres filas de una misma carrera: debe contar una sola vez (promedio 4000).
     ["202520", "ADMINISTRACION DE EMPRESAS", "ADMINISTRACION DE EMPRESAS", ECON, "TERCER NIVEL", "3800"],
     ["202520", "ADMINISTRACION DE EMPRESAS", "ADMINISTRACION DE EMPRESAS", ECON, "TERCER NIVEL", "4000"],
     ["202520", "ADMINISTRACION DE EMPRESAS", "ADMINISTRACION DE EMPRESAS", ECON, "TERCER NIVEL", "4200"],
     ["202520", "CONTABILIDAD Y AUDITORIA", "CONTABILIDAD Y AUDITORIA", ECON, "TERCER NIVEL", "0"],
     ["202520", "MAESTRIA EN FINANZAS", "MAESTRIA EN FINANZAS", ECON, "CUARTO NIVEL", "9000"],
     ["202520", "INGENIERIA EN SOFTWARE", "INGENIERIA EN SOFTWARE", "FACULTAD DE INGENIERIA Y CIENCIAS APLICADAS",
      "TERCER NIVEL", "3153"],
     ["202420", "DERECHO", "DERECHO", "FACULTAD DE DERECHO", "TERCER NIVEL", "3400"],
     # Facultad con carreras UDLA pero ningún arancel válido.
     ["202520", "MEDICINA", "MEDICINA", "FACULTAD DE MEDICINA", "TERCER NIVEL", "0"],
     ["202520", "MEDICINA", "MEDICINA", "FACULTAD DE MEDICINA", "TERCER NIVEL", None]],
    columns=["SEMESTRE_POS", "CARRERA_UDLA", "CARRERA_HOMOLOGADA_FINAL", "FACULTAD", "HOMOLOGADOS_NIVEL_ACADEMICO",
             "ARANCEL"],
)


def fake_market_sources():
    """Sustituye las lecturas SQL de mercado; devuelve un ExitStack con los mocks activos."""
    import streamlit as st

    st.cache_data.clear()
    stack = ExitStack()
    stack.enter_context(patch("data_access.market_catalog", return_value=CATALOG))
    stack.enter_context(patch("data_access.enrollment_provinces", return_value=["GUAYAS", "PICHINCHA"]))
    stack.enter_context(patch("data_access.load_enrollment", return_value=ENROLLMENT))
    stack.enter_context(patch("data_access.load_graduates_by_year", return_value=GRADUATES))
    stack.enter_context(patch("data_access.institution_financing", return_value=INSTITUTIONS))
    stack.enter_context(patch("data_access.load_prices", return_value=PRICES))
    stack.enter_context(patch("data_access.load_udla_prices", return_value=UDLA_PRICES))
    # Sin base de Tendencias salvo que la prueba la active (evita conectarse a PostgreSQL real).
    stack.enter_context(patch("tendencias_data.database_url", return_value=None))
    return stack

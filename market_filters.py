"""Filtros compartidos de las vistas de mercado (demanda y precios)."""
import streamlit as st

import data_access
from market_data import (CAREER_EQUIVALENTS, PROJECTION_METHODS, career_sources,  # noqa: F401
                         career_with_equivalents, normalize_text)

LEVEL_LABELS = {"TERCER NIVEL": "Tercer nivel", "CUARTO NIVEL": "Cuarto nivel", "TECNOLOGIA": "Tecnología"}
FINANCING_LABELS = {"TODOS": "Público y privado", "PUBLICO": "Público", "PRIVADO": "Privado"}
NATIONAL = "NACIONAL"
SOURCE_LABELS = {"MATRICULADOS": "Matriculados", "TITULADOS": "Titulados", "PRECIOS": "Precios"}
MARKET_KEYS = ("market_career", "market_level", "market_financing", "market_province", "market_projection")
# Niveles del filtro de Empleabilidad → categorías homologadas de mercado.
EMPLOYMENT_LEVELS = {"Tecnológico": "TECNOLOGIA", "Tercer nivel": "TERCER NIVEL",
                     "Cuarto nivel, especialidades y doctorados": "CUARTO NIVEL"}


def sql_config():
    try:
        return dict(st.secrets.get("sql", {}))
    except FileNotFoundError:
        return {}


@st.cache_data(ttl=3600, show_spinner=False, max_entries=2)
def cached_catalog(config):
    return data_access.market_catalog(config)


@st.cache_data(ttl=3600, show_spinner=False, max_entries=2)
def cached_provinces(config):
    return data_access.enrollment_provinces(config)


def connection_error(exc):
    st.error("No fue posible conectar con SQL Server. Comprueba la conexión a la red institucional o VPN.")
    st.info("Servidor: SNBI03 · Base: BDD_IDM · Autenticación de Windows con el usuario de la sesión actual.")
    with st.expander("Detalle técnico"):
        st.code(str(exc))
    st.stop()


def _keep_valid(key, options, default):
    if st.session_state.get(key) not in options:
        st.session_state[key] = default


def _resolve(key, options, default):
    """Valor compartido de un filtro que esta página no muestra."""
    _keep_valid(key, options, default)
    return st.session_state[key]


def employment_careers():
    """Carreras elegidas en Oferta de valor-empleabilidad (normalizadas); vacía si aún no hay."""
    return [normalize_text(c) for c in st.session_state.get("selected_careers", []) if c]


def render(config, show_province=False, show_career_level=True, show_projection=False):
    """Dibuja la barra de filtros y devuelve la selección con los textos originales por fuente.

    La carrera no es un filtro de estas páginas: siempre es la elegida en Oferta de
    valor-empleabilidad (la primera que tenga datos en este nivel, si hay varias).
    show_career_level solo decide si el nivel académico se muestra aquí o se reutiliza.
    """
    chosen = employment_careers()
    if not chosen:
        # Sin carrera elegida no se muestra ninguna: no se sustituye por una carrera por defecto.
        st.session_state.pop("market_career", None)
        st.info("Selecciona al menos una carrera en la pestaña Oferta de valor-empleabilidad para comenzar el análisis.")
        st.stop()
    try:
        with st.spinner("Conectando con SQL Server…"):
            catalog = cached_catalog(config)
            provinces = cached_provinces(config) if show_province else []
    except Exception as exc:
        connection_error(exc)

    previous_level = EMPLOYMENT_LEVELS.get(st.session_state.get("academic_level"), "TERCER NIVEL")
    with st.container(border=True):
        st.markdown("**Área de análisis**")
        widths = (([1.2] if show_career_level else []) + [1.3] + ([1.4] if show_province else [])
                  + ([1.4] if show_projection else []))
        columns = iter(st.columns(widths))
        if show_career_level:
            _keep_valid("market_level", list(LEVEL_LABELS), previous_level)
            with next(columns):
                level = st.selectbox("Nivel académico", list(LEVEL_LABELS), format_func=LEVEL_LABELS.get,
                                     key="market_level")
        else:
            level = _resolve("market_level", list(LEVEL_LABELS), previous_level)
        sources = career_sources(catalog, level)
        career, found = next(((name, found) for name, found in (career_with_equivalents(sources, c) for c in chosen)
                              if found), (None, None))
        if career is None:
            names = ", ".join(c.title() for c in chosen)
            st.warning(f"La carrera elegida en Oferta de valor-empleabilidad ({names}) no aparece en matriculados, "
                       f"titulados ni precios para {LEVEL_LABELS[level]}. Cámbiala en esa pestaña"
                       + (" o elige otro nivel académico." if show_career_level else "."))
            st.stop()
        st.session_state["market_career"] = career  # carrera vigente para las páginas de mercado
        _keep_valid("market_financing", list(FINANCING_LABELS), "TODOS")
        with next(columns):
            financing = st.selectbox("Financiamiento", list(FINANCING_LABELS), format_func=FINANCING_LABELS.get,
                                     key="market_financing")
        province = None
        if show_province:
            _keep_valid("market_province", [NATIONAL, *provinces], NATIONAL)
            with next(columns):
                province = st.selectbox("Provincia IES (matriculados)", [NATIONAL, *provinces], key="market_province",
                                        format_func=lambda p: "Nacional" if p == NATIONAL else p.title())
        projection = None
        if show_projection:
            _keep_valid("market_projection", list(PROJECTION_METHODS), "LINEAL")
            with next(columns):
                projection = st.selectbox("Proyección 2025", list(PROJECTION_METHODS),
                                          format_func=PROJECTION_METHODS.get, key="market_projection",
                                          help="Proyección lineal: tendencia 2020–2024. Tasa de crecimiento: "
                                               "2024 × (2024 / 2023).")
        note = f"Carrera: **{career.title()}** — se elige en Oferta de valor-empleabilidad"
        if len(chosen) > 1:
            note += f" (primera de las {len(chosen)} carreras seleccionadas con datos en este nivel)"
        if not show_career_level:
            note += f" · Nivel: **{LEVEL_LABELS[level]}** — se elige en Posicionamiento-competencia y precios"
        st.caption(note + ". Se aplica a CARRERA_HOMOLOGADA en matriculados y titulados, y a "
                   "CARRERA_HOMOLOGADA_FINAL en precios.")
        st.caption("Fuentes con esta carrera y nivel: " + " · ".join(
            f"{label} {'✓ (' + ', '.join(t.title() for t in found[source]) + ')' if source in found else '✗'}"
            for source, label in SOURCE_LABELS.items()))
    return dict(career=career, level=level, financing=None if financing == "TODOS" else financing,
                province=None if province in (None, NATIONAL) else province, sources=found,
                projection=projection)

import importlib

import pandas as pd
import streamlit as st

import data_access
import education_visuals as education_visuals_module
import market_filters

# Una sesión abierta puede conservar la versión anterior del módulo de gráficos.
if getattr(education_visuals_module, "MARKET_VISUAL_VERSION", None) != 3:
    education_visuals_module = importlib.reload(education_visuals_module)
from education_visuals import SERIES_LABELS, trend_figure
from market_data import PROJECTION_YEAR, UNCLASSIFIED, YEARS, enrollment_table, graduates_table
from palettes import theme_colors


palette = st.session_state.get("color_palette", "Azul")

st.markdown(
    theme_colors(
        """<style>
        .demanda-hero {margin-bottom: 1.8rem;}
        .demanda-eyebrow {color:#5b83aa;font-size:.7rem;font-weight:800;
            letter-spacing:.19em;text-transform:uppercase;}
        .demanda-hero p {color:#68809b;font-size:.95rem;margin:0;}
        div[data-testid="stVerticalBlockBorderWrapper"]>div {
            background:white;border-color:#e1eaf5!important;
            border-radius:17px!important;}
        </style>""",
        palette,
    ),
    unsafe_allow_html=True,
)

st.markdown(
    """<div class="demanda-hero">
        <div class="demanda-eyebrow">Inteligencia de mercado · etapa 1</div>
    </div>""",
    unsafe_allow_html=True,
)
st.title("Demanda e interés académico")
st.caption("Evolución anual de matriculados y titulados, 2020–2024.")

config = market_filters.sql_config()
selection = market_filters.render(config, show_province=True, show_career_level=False, show_projection=True)
career, level, financing, province, projection = (
    selection[k] for k in ("career", "level", "financing", "province", "projection"))
sources = selection["sources"]


@st.cache_data(ttl=900, show_spinner=False, max_entries=32)
def cached_enrollment(config, careers, level, province):
    return data_access.load_enrollment(config, list(careers), level, province)


@st.cache_data(ttl=900, show_spinner=False, max_entries=32)
def cached_graduates(config, careers, level):
    return data_access.load_graduates_by_year(config, list(careers), level)


@st.cache_data(ttl=3600, show_spinner=False, max_entries=2)
def cached_institutions(config):
    return data_access.institution_financing(config)


def show_query_error(exc):
    st.error("No fue posible completar la consulta. Revisa la conexión y los permisos de lectura en BDD_IDM.")
    with st.expander("Detalle técnico"):
        st.code(str(exc))


def year_label(year):
    return f"{year}*" if year == PROJECTION_YEAR else str(year)


def totals_view(table):
    """Público y privado por año, con separador de miles (sin fila total ni no clasificado)."""
    view = table.drop(index=["TOTAL", UNCLASSIFIED], errors="ignore").round(0).map(lambda value: f"{value:,.0f}".replace(",", "."))
    view.columns = [year_label(year) for year in table.columns]
    return view.rename(index=lambda row: SERIES_LABELS.get(row, row.title())).reset_index(names="Financiamiento")


def growth_rate_view(growth):
    """Tasa de crecimiento anual frente al año anterior (%), sin la fila no clasificado."""
    view = growth.drop(index=UNCLASSIFIED, errors="ignore").map(lambda value: "—" if pd.isna(value) else f"{value:+.1f} %".replace(".", ","))
    view.columns = [year_label(int(column.replace("CREC_", ""))) for column in growth.columns]
    return view.rename(index=lambda row: SERIES_LABELS.get(row, row.title())).reset_index(names="Financiamiento")


def market_panel(table, growth, measure, notes):
    st.dataframe(totals_view(table), hide_index=True, width="stretch")
    fig = trend_figure(table, measure, palette, projected=(PROJECTION_YEAR,))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    for note in notes:
        st.caption(note)
    if projection == "CRECIMIENTO":
        st.markdown("**Tasa de crecimiento anual**")
        st.dataframe(growth_rate_view(growth), hide_index=True, width="stretch")


projection_note = (f"{PROJECTION_YEAR}*: proyección lineal 2020–2024 por financiamiento." if projection == "LINEAL"
                   else f"{PROJECTION_YEAR}*: valor 2024 × tasa de crecimiento 2023–2024, por financiamiento.")
scope = " · ".join(x for x in [career.title(), level.title(), (province or "Nacional").title()] if x)
matriculados, titulados = st.columns(2)

with matriculados:
    with st.container(border=True):
        st.subheader("Matriculados")
        st.caption(f"{scope} · SUM(TOTAL_MATRICULADOS)")
        if "MATRICULADOS" not in sources:
            st.info("La carrera seleccionada no aparece en Matriculados_Senescyt para este nivel.")
        else:
            try:
                with st.spinner("Consultando matriculados…"):
                    raw = cached_enrollment(config, tuple(sources["MATRICULADOS"]), level, province)
                table, growth = enrollment_table(raw, financing, projection)
                if not table.loc["TOTAL", YEARS].sum():
                    st.info("No hay matriculados para la combinación de carrera, nivel, financiamiento y provincia.")
                else:
                    market_panel(table, growth, "matriculados", [projection_note])
            except Exception as exc:
                show_query_error(exc)

with titulados:
    with st.container(border=True):
        st.subheader("Titulados")
        st.caption(f"{career.title()} · {level.title()} · registros de Graduados_nueva por año de FECHA_REGISTRO")
        if "TITULADOS" not in sources:
            st.info("La carrera seleccionada no aparece en Graduados_nueva para este nivel.")
        else:
            try:
                with st.spinner("Consultando titulados…"):
                    raw = cached_graduates(config, tuple(sources["TITULADOS"]), level)
                    institutions = cached_institutions(config)
                table, growth = graduates_table(raw, institutions, financing, projection)
                if not table.loc["TOTAL", YEARS].sum():
                    st.info("No hay titulados para la combinación de carrera, nivel y financiamiento.")
                else:
                    notes = [projection_note]
                    if province:
                        notes.append("Graduados_nueva no informa provincia: el filtro provincial solo aplica a matriculados.")
                    if UNCLASSIFIED in table.index and table.loc[UNCLASSIFIED].sum():
                        notes.append("No clasificado: IES (incluidos títulos extranjeros) sin financiamiento "
                                     "identificable en Matriculados_Senescyt.")
                    market_panel(table, growth, "titulados", notes)
            except Exception as exc:
                show_query_error(exc)


# --- Google Trends: resultados ya guardados por el proyecto Tendencias (solo lectura) ---
import tendencias_data
import trends_analysis
import trends_visuals


@st.cache_data(ttl=900, show_spinner=False, max_entries=2)
def cached_trend_projects(url):
    return tendencias_data.load_trend_projects(url)


@st.cache_data(ttl=900, show_spinner=False, max_entries=16)
def cached_trend_project(url, project_id):
    return tendencias_data.load_trend_project(url, project_id)


def number(value, digits=1):
    return "—" if value is None else f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


project_label = trends_analysis.project_label


st.write("")
with st.container(border=True):
    st.subheader("Interés en Google Trends")
    st.caption("Resultados que el proyecto Tendencias ya obtuvo de Google Trends y guardó en su base "
               "(tablas tendencias, tendencias_regional y tendencias_carrera). Aquí solo se consultan.")
    url = tendencias_data.database_url()
    projects = None
    if not url:
        st.info("Falta la conexión a la base de Tendencias: agrega `[tendencias] database_url` en "
                ".streamlit/secrets.toml (mismo valor que DATABASE_URL del proyecto Tendencias).")
    else:
        try:
            with st.spinner("Consultando proyectos de Google Trends…"):
                projects = cached_trend_projects(url)
        except Exception as exc:
            st.warning("No fue posible leer la base de Tendencias (PostgreSQL). Los demás indicadores siguen disponibles.")
            with st.expander("Detalle técnico"):
                st.code(str(exc))
    if projects is not None and projects.empty:
        st.info("La base de Tendencias no tiene proyectos.")
    elif projects is not None:
        projects = projects[projects["palabras"].gt(0) | projects["filas_regionales"].gt(0)].reset_index(drop=True)
        default = trends_analysis.best_project(projects, career, level)
        ids = projects["id"].astype(int).tolist()
        labels = {int(row["id"]): project_label(row) for _, row in projects.iterrows()}
        if default is None:
            st.caption(f"Ningún proyecto de Tendencias coincide con «{career.title()}». Elige uno de la lista.")
        project_id = st.selectbox(
            "Proyecto de Google Trends", ids, index=ids.index(default) if default in ids else 0,
            format_func=labels.get, key=f"trends_project_{trends_analysis.normalize(career)}",
            help="Por defecto, el proyecto cuyo programa o carrera de referencia coincide con la carrera filtrada.")
        project = projects.set_index("id").loc[project_id].copy()
        project["id"] = project_id
        try:
            with st.spinner("Consultando resultados de Google Trends…"):
                trend_data = cached_trend_project(url, project_id)
        except Exception as exc:
            trend_data = None
            st.warning("No fue posible leer los resultados de este proyecto.")
            with st.expander("Detalle técnico"):
                st.code(str(exc))
        if trend_data is not None:
            keywords, regional = trend_data["keywords"], trend_data["regional"]
            base = trends_analysis.reference_base(trend_data["base"], project)
            interest = trends_analysis.search_interest(keywords, base)
            a, b, c, d = st.columns(4)
            top_label = ("Promedio de la palabra consultada" if interest["top_n"] == 1
                         else f"Promedio top {interest['top_n']} palabras")
            a.metric(top_label, number(interest["top_mean"]),
                     help=f"Promedio de las {trends_analysis.TOP_KEYWORDS} palabras con mayor promedio (o todas, si hay menos).")
            b.metric("Promedio base · carrera de referencia", number(interest["base_mean"]),
                     help=f"{interest['base_n']} palabras base de {str(project['carrera_referencia']).title()} (tendencias_carrera).")
            c.metric("Interés relativo", "—" if interest["ratio"] is None else f"{number(interest['ratio'])} %",
                     help="Promedio top 6 ÷ promedio base × 100.")
            d.metric("Aporte al puntaje web", "—" if interest["points"] is None
                     else f"{number(interest['points'], 2)} / {number(trends_analysis.TRENDS_WEIGHT, 2)}",
                     help="Regla de Tendencias: mín(interés relativo × 8,57 %, 8,57 puntos).")
            left, right = st.columns([1, 1.25], gap="medium")
            with left:
                st.markdown("**Palabras clave del programa**")
                if keywords["promedio"].notna().any():
                    st.plotly_chart(trends_visuals.keywords_figure(keywords, interest["base_mean"], palette),
                                    width="stretch", config={"displayModeBar": False}, key="trends_keywords")
                    st.caption(f"En color principal, las {trends_analysis.TOP_KEYWORDS} palabras con mayor promedio, "
                               "que forman el indicador. Línea roja: promedio de las palabras base de la carrera de referencia.")
                else:
                    st.info("Este proyecto no tiene promedios de palabras clave.")
            with right:
                st.markdown("**Evolución del interés a nivel regional**")
                timeline = trend_data.get("timeline", pd.DataFrame())
                series, trends = trends_analysis.regional_series(regional, timeline)
                world_real = trends_analysis.world_from_timeline(timeline, list(series.index)) is not None
                if series.empty:
                    st.info("Este proyecto no tiene serie regional de Google Trends (tendencias_regional).")
                else:
                    st.plotly_chart(trends_visuals.regional_figure(series, trends, palette), width="stretch",
                                    config={"displayModeBar": False}, key="trends_regional")
                    words = regional[["palabra_espanol", "palabra_ingles"]].dropna().drop_duplicates().head(1)
                    term = f"«{words.iloc[0, 0]}»" if len(words) else "el término del proyecto"
                    world_note = ("Todo el mundo sigue la serie de tiempo mundial de Google Trends desde 2020, al "
                                  "nivel del promedio de los países. " if world_real else
                                  "Todo el mundo promedia los países (sin serie de tiempo mundial guardada para "
                                  "este proyecto). ")
                    st.caption(f"Promedio anual del índice de Google Trends (0–100) para {term}. LATAM promedia "
                               "sus países con dato en todos los años; cada año se ajusta con su mediana para que "
                               "los años sean comparables (Google da 100 al país líder de cada año y, si cambia, "
                               "reescala a todos). " + world_note + "Línea punteada: recta del primer punto al "
                               "último punto. * año en curso, dato parcial.")
            comparison = trend_data.get("comparison", pd.DataFrame())
            breakdown = trends_analysis.comparison_table(comparison)
            countries = trends_analysis.country_table(regional) if not regional.empty else None
            if not breakdown.empty:
                # Desglose comparativo por región de Google Trends (palabra en español vs. inglés).
                words = (str(comparison["palabra_espanol"].iloc[0]), str(comparison["palabra_ingles"].iloc[0]))
                extracted = pd.to_datetime(comparison["extraido_en"], errors="coerce").max()
                st.markdown("**Desglose comparativo por región**")
                st.plotly_chart(trends_visuals.comparison_map(breakdown, words, palette), width="stretch",
                                config=trends_visuals.MAP_CONFIG, key="trends_map")
                st.caption("Cada país lleva el color de la palabra que más se busca allí (ver leyenda); "
                           "al pasar el cursor se ven los porcentajes de ambas. Google Trends, todo el mundo, "
                           + ("últimos cinco años" if str(comparison["periodo"].iloc[0]) == "today 5-y"
                              else "desde 2020")
                           + (f" · extraído por Tendencias el {extracted:%d/%m/%Y}." if pd.notna(extracted) else "."))
                with st.expander("Ver desglose por país"):
                    st.dataframe(breakdown.drop(columns="ISO3"), hide_index=True, width="stretch")
            elif countries is not None:
                st.markdown("**Interés por país**")
                st.plotly_chart(trends_visuals.country_map(countries, palette), width="stretch",
                                config=trends_visuals.MAP_CONFIG, key="trends_map")
                st.caption(f"Promedio {int(regional['anio'].min())}–{int(regional['anio'].max())} del índice en español. "
                           "Este proyecto aún no tiene el desglose comparativo español frente a inglés: se genera "
                           "al volver a ejecutar Google Trends en el proyecto Tendencias.")
            if countries is not None:
                with st.expander("Ver índice por país"):
                    st.dataframe(countries.drop(columns="ISO3"), hide_index=True, width="stretch")

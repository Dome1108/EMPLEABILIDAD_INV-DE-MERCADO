import importlib

import pandas as pd
import streamlit as st

import data_access
import education_visuals as education_visuals_module
import market_data as market_data_module
import market_filters

# Una sesión abierta puede conservar versiones anteriores de los módulos de mercado.
if getattr(education_visuals_module, "MARKET_VISUAL_VERSION", None) != 3:
    importlib.reload(education_visuals_module)
if not hasattr(market_data_module, "obtener_arancel_udla"):
    importlib.reload(market_data_module)
from education_visuals import price_boxplot
from market_data import aggregate_prices, obtener_arancel_udla, price_metrics, price_semesters
from palettes import theme_colors


palette = st.session_state.get("color_palette", "Azul")

st.markdown(
    theme_colors(
        """<style>
        .posicionamiento-eyebrow {color:#5b83aa;font-size:.7rem;font-weight:800;
            letter-spacing:.19em;text-transform:uppercase;}
        .posicionamiento-caption {color:#68809b;font-size:.95rem;margin:0 0 1.2rem;}
        div[data-testid="stVerticalBlockBorderWrapper"]>div {
            background:white;border-color:#e1eaf5!important;
            border-radius:17px!important;}
        </style>""",
        palette,
    ),
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="posicionamiento-eyebrow">Inteligencia de mercado · etapa 1</div>',
    unsafe_allow_html=True,
)
st.title("Posicionamiento-competencia y precios")
st.markdown(
    '<div class="posicionamiento-caption">Comparación de ofertas académicas y aranceles del mercado.</div>',
    unsafe_allow_html=True,
)

config = market_filters.sql_config()
selection = market_filters.render(config)
career, level, financing, sources = (selection[k] for k in ("career", "level", "financing", "sources"))


@st.cache_data(ttl=900, show_spinner=False, max_entries=32)
def cached_prices(config, careers, level, columns_version=2):
    # columns_version: la consulta incluye CARRERA_UDLA y FACULTAD.
    return data_access.load_prices(config, list(careers), level)


@st.cache_data(ttl=900, show_spinner=False, max_entries=4)
def cached_udla_prices(config, level):
    return data_access.load_udla_prices(config, level)


def money(value):
    if pd.isna(value):
        return "—"
    return "$" + f"{value:,.0f}".replace(",", ".")


if "PRECIOS" not in sources:
    st.info("La carrera seleccionada no aparece en Precios_Homologados (CARRERA_HOMOLOGADA_FINAL) para este nivel.")
    st.stop()

try:
    with st.spinner("Consultando aranceles en BDD_IDM…"):
        prices = cached_prices(config, tuple(sources["PRECIOS"]), level)
except Exception as exc:
    st.error("No fue posible consultar la fuente de precios.")
    with st.expander("Detalle técnico"):
        st.code(str(exc))
    st.stop()

semesters = price_semesters(prices)
if st.session_state.get("market_semester") not in [None, *semesters]:
    st.session_state["market_semester"] = None  # el semestre guardado no existe para esta carrera
semester = st.selectbox("Semestre de precios", [None, *semesters], key="market_semester",
                        format_func=lambda s: "Último disponible" if s is None else str(s))
table = aggregate_prices(prices, financing=financing, semester=semester)
if table.empty:
    st.warning("No hay ofertas para la carrera, nivel, financiamiento y semestre seleccionados.")
    st.stop()
used = int(table["SEMESTRE_POS"].iat[0])
# El arancel UDLA no depende del filtro de financiamiento: se busca en toda la oferta del semestre.
try:
    udla_prices = cached_udla_prices(config, level)
except Exception as exc:
    udla_prices = pd.DataFrame()
    st.warning("No fue posible consultar las ofertas UDLA para estimar su arancel.")
    with st.expander("Detalle técnico"):
        st.code(str(exc))
own_info = obtener_arancel_udla(prices, udla_prices, aggregate_prices(prices, semester=used), level, used)
metrics = price_metrics(table, own_info=own_info)
st.caption(f"{career.title()} · {level.title()} · semestre {used}"
           + ("" if semester else " (último con aranceles válidos)"))

if own_info["tipo"] == "estimado":
    own_label = "Arancel UDLA estimado"
    own_help = "Estimado con carreras del mismo nivel académico pertenecientes a la misma facultad."
    own_note = (f"Estimado con {own_info['numero_carreras']} carrera(s) relacionada(s) de "
                f"{own_info['facultad'].title()}."
                + (f" Estimación histórica: periodo {own_info['periodo']}, sin datos UDLA de la facultad en "
                   f"{own_info['periodo_solicitado']}." if own_info["historico"] else ""))
elif own_info["tipo"] == "real":
    own_label = "Arancel UDLA"
    own_help = f"{own_info['fuente']}, semestre {own_info['periodo']}."
    own_note = (f"Carrera UDLA: {own_info['carrera_udla'].title()}."
                if own_info["fuente"] != "Oferta UDLA de la carrera" else None)
else:
    own_label = "Arancel UDLA"
    own_help = own_info["motivo"]
    own_note = "Sin información suficiente para estimar el arancel UDLA."

for column, (label, value, help_text) in zip(st.columns(5), [
    ("Universidades ofertantes", f"{metrics['offering']}", None),
    ("Competidores", f"{metrics['competitors']}", None),
    ("Arancel promedio", money(metrics["market_mean"]), "Promedio del arancel representativo de cada institución."),
    (own_label, "Sin información" if pd.isna(metrics["own_price"]) else money(metrics["own_price"]), own_help),
    ("Promedio competencia", money(metrics["competitor_mean"]), "Instituciones con precio, excluida UDLA."),
]):
    with column:
        with st.container(border=True):
            st.metric(label, value, help=help_text)
            if label.startswith("Arancel UDLA") and own_note:
                st.caption(own_note)

with st.container(border=True):
    st.subheader("Precios y ofertas")
    st.plotly_chart(price_boxplot(table, career.title(), palette, own_info=own_info), width="stretch",
                    config={"displayModeBar": False})
    st.caption("Cada punto es una institución (SIGLA) con su arancel promedio del semestre. La caja muestra "
               "mediana y cuartiles; los bigotes, el rango sin valores atípicos. Se excluyen aranceles nulos o ≤ 0.")
    with st.expander("Ver detalle por institución"):
        st.dataframe(table, hide_index=True, width="stretch")
    if own_info["tipo"] == "estimado":
        with st.expander("Detalle del arancel UDLA estimado"):
            st.markdown(f"**Arancel UDLA estimado:** {money(own_info['arancel'])} · **Facultad:** "
                        f"{own_info['facultad'].title()} · **Nivel:** {own_info['nivel'].title()} · "
                        f"**Periodo:** {own_info['periodo']} · **Carreras utilizadas:** {own_info['numero_carreras']}")
            st.caption("Promedio de un arancel representativo por carrera UDLA (promedio de sus registros "
                       "válidos), para que cada carrera pese una vez. Solo ofertas UDLA; nunca competidores.")
            st.dataframe(own_info["detalle"].rename(columns={
                "REFERENCIA": "Carrera UDLA", "ARANCEL_REPRESENTATIVO": "Arancel representativo",
                "REGISTROS": "Registros válidos"}), hide_index=True, width="stretch",
                column_config={"Arancel representativo": st.column_config.NumberColumn(format="$%.2f")})
    if prices.attrs.get("financing_source") == "FINANCIAMIENTO":
        st.caption("Precios_Homologados aún no tiene HOMOLOGADOS_FINANCIAMIENTO: público/privado se deriva "
                   "de FINANCIAMIENTO (PUBLICA → PUBLICO, PARTICULAR → PRIVADO) en la consulta SQL.")

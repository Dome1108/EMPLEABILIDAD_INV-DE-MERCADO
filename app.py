import html
import importlib
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analytics as analytics_module

# Una sesión abierta puede conservar el módulo anterior tras actualizar archivos.
# Recargar solo cuando cambie el contrato de resultados, antes de consultar la caché.
EXPECTED_RESULT_SCHEMA = 4
if getattr(analytics_module, "RESULT_SCHEMA_VERSION", None) != EXPECTED_RESULT_SCHEMA:
    analytics_module = importlib.reload(analytics_module)

from analytics import SNAPSHOTS, calculate
from data_access import career_catalog, demo_data, load, ACADEMIC_LEVELS
import education_visuals as education_visuals_module
if getattr(education_visuals_module, "VISUAL_LAYOUT_VERSION", None) != 2:
    education_visuals_module = importlib.reload(education_visuals_module)
from education_visuals import education_panels, education_figure, education_png
from palettes import PALETTES, theme_colors, theme_figure
from data_access import load_atlas, demo_atlas
from geography import locations, territorial_summary

st.set_page_config(page_title="Observatorio de empleabilidad", page_icon="📊", layout="wide")

palette = st.session_state.get("color_palette", "Azul")
BLUE, LIGHT, MUTED = PALETTES[palette]
NAVY = theme_colors("#123F70", palette)
COLORS = [BLUE, LIGHT, MUTED]

st.markdown(theme_colors("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;600;700;800&display=swap');
html, body, [class*="css"], .stApp {font-family:'DM Sans',sans-serif;}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {background-color:#FFFFFF;}
.block-container {padding:2.4rem 3rem 2rem; max-width:1600px;}
h1,h2,h3 {font-family:'Manrope',sans-serif; letter-spacing:-.035em;}
[data-testid="stSidebar"] {border-right:1px solid #e1eaf5;}
[data-testid="stSidebar"] .block-container {padding:2rem 1.2rem;}
.eyebrow {font-size:.7rem;font-weight:800;letter-spacing:.19em;color:#5b83aa;text-transform:uppercase;}
.masthead {display:flex;justify-content:space-between;align-items:center;gap:1rem;margin-bottom:1.7rem;}
.masthead h1 {font-size:2.55rem;line-height:1.18;margin:.4rem 0;color:#123F70;padding:0;}
.subtitle {color:#68809b;font-size:.95rem;margin:.7rem 0 0;}
.badge {background:#e4f1ff;border:1px solid #cce2f9;color:#176bad;border-radius:30px;padding:9px 15px;font-size:.72rem;white-space:nowrap;font-weight:700;}
.brand {display:flex;align-items:center;gap:12px;margin:0 0 2.5rem;}
.brand-icon {width:42px;height:42px;background:linear-gradient(145deg,#126eae,#1b3660);color:white;display:grid;place-items:center;border-radius:13px;font-size:23px;}
.brand strong {color:#153f6a;font-family:Manrope,sans-serif;font-size:1rem;}
.brand small {color:#7d94ab;font-size:.68rem;letter-spacing:.11em;}
.side-note {font-size:.78rem;color:#71869c;line-height:1.65;margin-top:1.4rem;}
.time-card {background:white;border:1px solid #dfE9F4;border-radius:17px;padding:20px 22px;position:relative;overflow:hidden;min-height:155px;}
.time-card.latest {background:linear-gradient(120deg,#104278,#087bcc);border-color:#125e9f;}
.time-card .year {font-size:.8rem;letter-spacing:.04em;font-weight:700;color:#6182a3;}
.time-card .value {font:800 2.25rem Manrope,sans-serif;color:#123F70;margin:8px 0 5px;letter-spacing:-.06em;}
.time-card .detail {font-size:.73rem;color:#7d93aa;}
.time-card .delta {font-size:.73rem;font-weight:700;color:#087bcc;float:right;margin-top:3px;}
.time-card.latest .year,.time-card.latest .detail {color:#c3def7;}
.time-card.latest .value,.time-card.latest .delta {color:white;}
.section-heading {font:800 1.23rem Manrope,sans-serif;color:#153f6a;margin:1.7rem 0 .35rem;letter-spacing:-.025em;}
.section-caption {color:#7c91a7;font-size:.78rem;margin-bottom:1rem;}
div[data-testid="stVerticalBlockBorderWrapper"]>div {border-color:#e1eaf5!important;border-radius:17px!important;background:white;}
[data-testid="stMetricLabel"] {font-size:.8rem;color:#7189a3;}
[data-testid="stMetricValue"] {color:#123F70;font-family:Manrope,sans-serif;font-weight:800;letter-spacing:-.05em;}
.panel-title {font:800 1rem Manrope,sans-serif;color:#224a72;letter-spacing:-.02em;}
.panel-caption {font-size:.75rem;color:#7b91a8;margin:5px 0 12px;}
.stat-chip {display:inline-block;padding:6px 10px;background:#eef6ff;border-radius:7px;color:#226da5;font-size:.72rem;margin:3px 6px 3px 0;}
.foot {border-top:1px solid #dce7f3;margin-top:2rem;padding-top:1rem;color:#7f93a9;font-size:.72rem;line-height:1.8;}
[data-testid="stTabs"] [role="tab"] {font-size:1rem;font-weight:700;padding:12px 20px;}
[data-testid="stTabs"] [role="tablist"] {gap:12px;border-bottom:2px solid #dce7f3;}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {background:#e4f1ff;border-radius:10px 10px 0 0;}
@media(max-width:800px){.block-container{padding:1.2rem}.masthead{display:block}.masthead h1{font-size:1.9rem}.badge{display:inline-block;margin-top:1rem}}
</style>""", palette), unsafe_allow_html=True)

if palette == "Vino":
    st.markdown("""<style>
    .stApp {--primary-color:#A5133D;}
    [data-baseweb="tag"] {background-color:#A5133D!important;color:white!important;}
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {color:#A5133D;}
    [data-testid="stButton"] button:hover, [data-testid="stDownloadButton"] button:hover {
        border-color:#A5133D;color:#A5133D;}
    </style>""", unsafe_allow_html=True)


def integer(value):
    return f"{int(value):,}".replace(",", ".")


def decimal(value, digits=1):
    if pd.isna(value):
        return "—"
    return f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def chart_layout(fig, height=300):
    fig.update_layout(height=height, margin=dict(l=5,r=12,t=25,b=15), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font=dict(family="DM Sans, Arial", color="#617d99",size=12),
        hoverlabel=dict(bgcolor="white", font_size=13), separators=",.")
    return theme_figure(fig, palette)


@st.cache_data(ttl=900, show_spinner=False, max_entries=4)
def cached_careers(config):
    return career_catalog(config)


@st.cache_data(ttl=900, show_spinner=False, max_entries=8)
def cached_result(config, selected, result_schema_version, levels=None):
    with st.status("Consultando fuentes institucionales…", expanded=False) as status:
        data = load(config, selected, levels=levels, progress=lambda message: status.update(label=message))
        status.update(label="Calculando indicadores por persona…")
        result = calculate(*data)
        status.update(label="Cuatro cortes calculados", state="complete")
    return result


@st.cache_data(show_spinner=False)
def demo_result(selected, result_schema_version, level="Todos los niveles"):
    grads, jobs, sri = demo_data()
    if level != "Todos los niveles":
        grads = grads[grads.NIVEL_ACADEMICO.eq(level)]
    return calculate(grads[grads.CARRERA_HOMOLOGADA.isin(selected)], jobs, sri)


@st.cache_data(ttl=900, show_spinner=False, max_entries=8)
def cached_atlas(config, people):
    return load_atlas(config, people)


st.markdown('<div class="masthead"><div><div class="eyebrow">Inteligencia de mercado · 2023 — 2026</div><h1>Empleabilidad de graduados</h1><p class="subtitle">Formación académica y presencia laboral, en una sola mirada.</p></div></div>', unsafe_allow_html=True)
filters = st.container(border=True)
with filters:
    filter_heading, demo_control = st.columns([3, 1])
    with filter_heading:
        st.markdown("**Área de análisis**")
        st.caption("Selecciona el nivel académico y una o varias carreras homologadas. Los filtros se aplican a todos los gráficos.")
    with demo_control:
        demo = st.toggle("Vista de demostración", value=os.getenv("DASHBOARD_DEMO", "0") == "1", help="Usa exclusivamente datos sintéticos para explorar el dashboard.")

config = {}
try:
    config = dict(st.secrets.get("sql", {}))
except FileNotFoundError:
    pass

if demo:
    catalog = demo_data()[0].rename(columns={"CARRERA_HOMOLOGADA": "carrera", "NIVEL_ACADEMICO": "nivel"})
    catalog["nivel_origen"] = catalog["nivel"]
else:
    try:
        with st.spinner("Conectando con SQL Server…"):
            catalog = cached_careers(config)
    except Exception as exc:
        st.title("Observatorio de empleabilidad")
        st.error("No fue posible conectar con SQL Server. Puedes activar la vista de demostración en el área de análisis.")
        st.info("Servidor predeterminado: SNBI03 · Autenticación de Windows. Comprueba acceso a la red institucional y permisos de lectura en BDD_IDM y Northwind.")
        with st.expander("Configuración de la conexión"):
            st.code('[sql]\nserver = "SNBI03"\ndatabase = "BDD_IDM"\ntrusted_connection = true\nencrypt = true\ntrust_server_certificate = true',language="toml")
            st.caption("Guardar en .streamlit/secrets.toml. Hay una plantilla incluida en el proyecto.")
            st.code(str(exc))
        st.stop()

with filters:
    st.selectbox("Paleta de colores", list(PALETTES), key="color_palette")
    level = st.selectbox("Nivel académico", ["Todos los niveles", *ACADEMIC_LEVELS], key="academic_level")
    filtered_catalog = catalog if level == "Todos los niveles" else catalog[catalog.nivel.eq(level)]
    options = sorted(filtered_catalog.carrera.unique())
    levels = None if level == "Todos los niveles" else tuple(sorted(filtered_catalog.nivel_origen.dropna().unique()))
    if "selected_careers" in st.session_state:
        st.session_state.selected_careers = [c for c in st.session_state.selected_careers if c in options]
    else:
        st.session_state.selected_careers = [next((x for x in options if x.upper() in ('ECONOMÍA', 'ECONOMIA')), options[0])] if options else []
    career_control, cutoff_control, refresh_control = st.columns([3, 1.3, 1], vertical_alignment="bottom")
    with career_control:
        selected = st.multiselect("Carreras homologadas", options, key="selected_careers", placeholder="Busca una carrera…")
    with cutoff_control:
        year = st.selectbox("Corte de análisis", [s.year for s in SNAPSHOTS], index=3, format_func=lambda y: next(s.label for s in SNAPSHOTS if s.year==y))
    with refresh_control:
        if st.button("Actualizar datos", width="stretch"):
            cached_careers.clear()
            cached_result.clear()
            demo_result.clear()
            cached_atlas.clear()
            st.rerun()
    st.caption(f"{len(selected)} carrera(s) seleccionada(s) · {len(options):,} disponibles".replace(",", "."))
if demo:
    st.warning("Vista de demostración con datos sintéticos. Estas cifras no corresponden a los registros institucionales.")
if not selected:
    st.info("Selecciona al menos una carrera para comenzar el análisis.")
    st.stop()

employment_tab, education_tab, methodology_tab = st.tabs(["Empleo y salarios", "Educación e instituciones", "Metodología y calidad"])

with st.spinner("Calculando cohortes y cruces de empleo…"):
    try:
        summary, institutions, cohorts, quality = demo_result(tuple(sorted(selected)), EXPECTED_RESULT_SCHEMA, level) if demo else cached_result(config, tuple(sorted(selected)), EXPECTED_RESULT_SCHEMA, levels)
    except Exception as exc:
        st.error("No fue posible completar la consulta. Revisa los permisos de lectura, las tablas y los tipos de datos.")
        with st.expander("Detalle técnico"):
            st.code(str(exc))
        st.stop()

with employment_tab:
    st.markdown(" · ".join(f'<span class="stat-chip">{html.escape(c)}</span>' for c in selected), unsafe_allow_html=True)
    st.markdown('<div class="section-heading">Evolución del empleo visible</div>', unsafe_allow_html=True)
    for i, (column, row) in enumerate(zip(st.columns(4), summary.to_dict("records"))):
        delta = row['rate'] - summary.iloc[i-1]['rate'] if i else float('nan')
        change = f"{'+' if delta >= 0 else ''}{decimal(delta)} pp" if pd.notna(delta) else "Primer corte"
        with column:
            st.markdown(f'<div class="time-card {"latest" if i==3 else ""}"><div class="year">{row["year"]} <span class="delta">{change}</span></div><div class="value">{decimal(row["rate"])}{" %" if pd.notna(row["rate"]) else ""}</div></div>', unsafe_allow_html=True)

    st.caption("Variación frente al corte anterior en puntos porcentuales. Los cortes corresponden a meses distintos; no son promedios anuales.")
    st.markdown('<div class="section-heading">Una mirada al corte</div>', unsafe_allow_html=True)
    row = summary.set_index("year").loc[year]
    st.caption(f"Registro académico acumulado hasta el {pd.Timestamp(row['cutoff']).strftime('%d/%m/%Y')}. El corte cambia la vista de detalle; las cuatro tarjetas permanecen visibles.")
    metrics = st.columns(4)
    for i, (col, label, value) in enumerate(zip(metrics, ["Graduados históricos", "Profesionales ejerciendo", "Recién titulados · 2026", "Tasa de empleo visible"], [integer(row.graduates), integer(row.employed), integer(quality['recent_2026']), decimal(row.rate)+(" %" if pd.notna(row.rate) else "")])):
        with col:
            with st.container(border=True):
                st.metric(label, value)
                if i == 2:
                    academic_cutoff = quality['recent_2026_cutoff']
                    st.caption(f"01/01/2026 – {pd.Timestamp(academic_cutoff).strftime('%d/%m/%Y')}" if academic_cutoff else "Sin registros de 2026 para estas carreras")

    left, right = st.columns([1, 1.22])
    with left:
        with st.container(border=True):
            st.markdown('<div class="panel-title">Composición del empleo</div>', unsafe_allow_html=True)
            values = [int(row.dependent), int(row.independent), int(row.unknown)]
            if row.graduates:
                fig = go.Figure(go.Pie(labels=["Dependientes", "Independientes", "Sin información laboral"], values=values,
                    hole=.73, sort=False, marker=dict(colors=COLORS,line=dict(color="white",width=3)), textinfo="percent",textposition="outside",
                    hovertemplate="%{label}<br>%{value:,.0f} personas · %{percent}<extra></extra>"))
                fig.update_layout(showlegend=False, annotations=[dict(text=f'<b>{decimal(row.rate)}%</b><br><span style="font-size:12px;color:#7b91a8">empleo visible</span>', x=.5,y=.5,showarrow=False,font=dict(size=29,color=NAVY))])
                st.plotly_chart(chart_layout(fig,300), width="stretch", config={"displayModeBar":False})
            else:
                st.info("No hay graduados elegibles en este corte.")
            for color,label,value in zip(COLORS,["Dependientes","Independientes","Sin información laboral"], values):
                st.markdown(f'<div style="display:flex;justify-content:space-between;margin:9px 4px;font-size:.83rem"><span><span style="color:{color}">●</span> {label}</span><b>{integer(value)}</b></div>',unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            st.markdown('<div class="panel-title">Banda salarial</div><div class="panel-caption">Rango intercuartílico</div>',unsafe_allow_html=True)
            if row.salary_n:
                fig = go.Figure(go.Scatter(x=[row.p25,row.p75],y=[0,0],mode="lines+markers+text",text=[f"${decimal(row.p25,0)}",f"${decimal(row.p75,0)}"],
                    textposition=["top left","top right"],line=dict(color=BLUE,width=7),marker=dict(size=19,color=BLUE),
                    hovertemplate="$%{x:,.2f}<extra></extra>"))
                span=max(row.p75-row.p25,100)
                fig.update_xaxes(range=[max(0,row.p25-span*.35), row.p75+span*.35],visible=False)
                fig.update_yaxes(range=[-1,1],visible=False)
                fig.update_layout(annotations=[dict(x=row.p25,y=-.4,text="PERCENTIL 25",showarrow=False,font=dict(size=11,color="#7b91a8")),dict(x=row.p75,y=-.4,text="PERCENTIL 75",showarrow=False,font=dict(size=11,color="#7b91a8"))])
                st.plotly_chart(chart_layout(fig,180),width="stretch",config={"displayModeBar":False})
            else:
                st.info("No hay salarios válidos para calcular los percentiles.")
            if row.dependent > row.salary_n:
                st.caption(f"{integer(row.dependent-row.salary_n)} dependientes sin ingreso positivo informado quedan fuera de la banda.")
        with st.container(border=True):
            st.markdown('<div class="panel-title">Trayectoria del empleo visible</div>',unsafe_allow_html=True)
            fig = go.Figure(go.Scatter(x=summary.year.astype(str),y=summary.rate,mode="lines+markers+text",text=[decimal(x)+"%" if pd.notna(x) else "" for x in summary.rate],textposition="top center",line=dict(color=BLUE,width=3),marker=dict(size=9),fill="tozeroy",fillcolor="rgba(8,123,204,.07)",hovertemplate="%{x}<br>%{y:.1f}%<extra></extra>"))
            fig.update_yaxes(range=[0,110],ticksuffix="%",gridcolor="#edf2f9",zeroline=False)
            fig.update_xaxes(showgrid=False,type="category", range=[-.3,3.3])
            st.plotly_chart(chart_layout(fig,220),width="stretch",config={"displayModeBar":False})

    with st.container(border=True):
        latest = SNAPSHOTS[-1]
        st.markdown(f"**Empleo por domicilio · {latest.label}**")
        st.caption("Indicador territorial adicional. La selección geográfica solo afecta este panel; las cifras nacionales se conservan.")
        try:
            cohort = cohorts[latest.year]
            ids = tuple(sorted(cohort.person.unique()))
            with st.spinner("Consultando domicilios en Atlas…"):
                atlas = demo_atlas(ids) if demo else cached_atlas(config, ids)
                geo, conflicts = locations(atlas)
            located = cohort.merge(geo, on='person', how='left', validate='one_to_one')
            provinces = sorted(x for x in geo.provincia.unique() if x)
            if not provinces:
                st.info("No hay provincias identificadas en Atlas para los graduados de este corte.")
            else:
                province_col, canton_col, parish_col = st.columns(3)
                with province_col:
                    province = st.selectbox("Provincia (domicilio)", provinces, index=provinces.index('PICHINCHA') if 'PICHINCHA' in provinces else 0)
                cantons = sorted(x for x in geo.loc[geo.provincia.eq(province), 'canton'].unique() if x)
                with canton_col:
                    canton = st.selectbox("Cantón (domicilio)", ['', *cantons], format_func=lambda x: x or 'Todos los cantones')
                parish_rows = geo[geo.provincia.eq(province)]
                if canton:
                    parish_rows = parish_rows[parish_rows.canton.eq(canton)]
                parishes = sorted(x for x in parish_rows.parroquia.unique() if x)
                with parish_col:
                    parish = st.selectbox("Parroquia (domicilio)", ['', *parishes], format_func=lambda x: x or 'Todas las parroquias', disabled=not canton)
                territory = territorial_summary(located, province, canton, parish if canton else '')
                a, b, c = st.columns(3)
                a.metric("Tasa de empleo visible · zona", decimal(territory['rate']) + (' %' if territory['graduates'] else ''))
                b.metric("Graduados · zona", integer(territory['graduates']))
                c.metric("Profesionales ejerciendo · zona", integer(territory['employed']))
                composition_col, salary_col = st.columns([1, 1.22])
                with composition_col:
                    with st.container(border=True):
                        st.markdown('<div class="panel-title">Composición del empleo · zona</div>', unsafe_allow_html=True)
                        labels = ["Dependientes", "Independientes", "Sin información laboral"]
                        values = [territory[k] for k in ('dependent', 'independent', 'unknown')]
                        if territory['graduates']:
                            fig = go.Figure(go.Pie(labels=labels, values=values,
                                hole=.73, sort=False, marker=dict(colors=COLORS, line=dict(color='white', width=3)),
                                textinfo='percent', textposition='outside',
                                hovertemplate='%{label}<br>%{value:,.0f} personas · %{percent}<extra></extra>'))
                            fig.update_layout(showlegend=False, annotations=[dict(
                                text=f'<b>{decimal(territory["rate"])}%</b><br><span style="font-size:12px">empleo visible</span>',
                                x=.5, y=.5, showarrow=False, font=dict(size=29, color=NAVY))])
                            st.plotly_chart(chart_layout(fig, 300), width='stretch', key='territorial_composition', config={'displayModeBar': False})
                        else:
                            st.info('No hay graduados elegibles en esta zona.')
                        for color, label, value in zip(COLORS, labels, values):
                            st.markdown(f'<div style="display:flex;justify-content:space-between;margin:9px 4px;font-size:.83rem"><span><span style="color:{color}">●</span> {label}</span><b>{integer(value)}</b></div>', unsafe_allow_html=True)
                with salary_col:
                    with st.container(border=True):
                        st.markdown('<div class="panel-title">Banda salarial · zona</div><div class="panel-caption">Rango intercuartílico</div>', unsafe_allow_html=True)
                        if territory['salary_n']:
                            p25, p75 = territory['p25'], territory['p75']
                            fig = go.Figure(go.Scatter(x=[p25, p75], y=[0, 0], mode='lines+markers+text',
                                text=[f'${decimal(p25, 0)}', f'${decimal(p75, 0)}'], textposition=['top left', 'top right'],
                                line=dict(color=BLUE, width=7), marker=dict(size=19, color=BLUE),
                                hovertemplate='$%{x:,.2f}<extra></extra>'))
                            span = max(p75-p25, 100)
                            fig.update_xaxes(range=[max(0, p25-span*.35), p75+span*.35], visible=False)
                            fig.update_yaxes(range=[-1, 1], visible=False)
                            fig.update_layout(annotations=[dict(x=p25, y=-.4, text='PERCENTIL 25', showarrow=False, font=dict(size=11)), dict(x=p75, y=-.4, text='PERCENTIL 75', showarrow=False, font=dict(size=11))])
                            st.plotly_chart(chart_layout(fig, 300), width='stretch', key='territorial_salary', config={'displayModeBar': False})
                        else:
                            st.info('Sin salarios válidos para calcular la banda de esta zona.')
        except Exception as exc:
            st.warning("No fue posible consultar el panel territorial de Atlas. Los indicadores nacionales siguen disponibles.")
            with st.expander("Detalle de conexión Atlas"):
                st.code(str(exc))

with education_tab:
    inst = institutions[institutions.year.eq(year)].sort_values("professionals",ascending=False)
    private = pd.DataFrame(quality['private_institutions'])
    private = private[private.year.eq(year)].sort_values(["professionals", "code"], ascending=[False, True])
    panels = education_panels(inst, private)
    with st.container(border=True):
        st.markdown('<div class="panel-title">Instituciones educativas</div>',unsafe_allow_html=True)
        if len(inst):
            st.plotly_chart(education_figure(panels, palette=palette), width="stretch", config={"displayModeBar":False})
        else:
            st.info("No hay instituciones con graduados en este corte.")
    if len(inst):
        st.download_button("Descargar educación para diapositiva · PNG 16:9", education_png(panels, year, selected, demo=demo, palette=palette),
            file_name=f"educacion_{year}{'_DEMO' if demo else ''}_16x9.png",mime='image/png')
    with st.expander("Ver todas las instituciones"):
        st.dataframe(inst.rename(columns={"INSTITUCION_EDUCACION_SUPERIOR":"Institución","professionals":"Profesionales históricos","recent":"Recién titulados"}).drop(columns="year"),hide_index=True,width="stretch")
    with st.expander("Ver detalle de Privadas Sierra"):
        st.dataframe(private.rename(columns={"institution":"Institución", "code":"Sigla", "professionals":"Profesionales históricos", "recent":"Recién titulados al corte"}).drop(columns="year"), hide_index=True, width="stretch")

with methodology_tab:
    st.markdown("**Reglas del análisis**")
    st.markdown("""
    - **Población:** personas únicas de las carreras seleccionadas con `FECHA_REGISTRO` hasta el último día del mes de corte. Se usa la fecha de registro como aproximación a la titulación.
    - **Cruce:** cédula y `NUMAFI` normalizados a diez dígitos, conservando ceros iniciales. En SRI se busca exclusivamente **cédula + `001`**.
    - **Dependientes:** presencia en SIM/APOR del corte. La presencia tiene prioridad incluso si la persona tiene RUC activo.
    - **Independientes:** RUC con actividad vigente inferida al corte y ausencia en SIM/APOR. Un RUC inactivo no cuenta como empleo independiente.
    - **Profesionales ejerciendo:** unión sin duplicados de dependientes e independientes. Este indicador mide presencia laboral; no determina afinidad del empleo con la carrera.
    - **Sin información laboral:** no se identifica empleo en las fuentes disponibles, incluidos casos SRI indeterminados sin SIM. No equivale a desempleo.
    - **Recién titulados:** personas con al menos un registro académico de las carreras seleccionadas en el año analizado, aunque tengan registros previos. Para 2026 se usa desde enero hasta la última fecha disponible sin superar hoy; para 2023–2025, hasta el corte correspondiente.
    - **Salario:** en 2024 y 2025 se usa `SALARIO_TOTAL`, con respaldo de `SALARIO_FIJO` si está vacío o en cero; en 2023 y 2026, `SALARIO`. Se toma el mayor valor por persona y empleador para deduplicar y se suman empleadores. Se excluyen ingresos no positivos. No se usan salarios promedio de 12 meses ni se atribuyen ingresos al SRI.
    - **Banda salarial:** percentiles 25 y 75 con interpolación lineal sobre el ingreso mensual por persona dependiente.
    """)
    st.markdown("**Educación 2026:** la tarjeta, los dos gráficos de instituciones y los recién titulados del CSV usan toda la información académica de 2026 disponible hasta hoy (hora de Ecuador). El histórico de instituciones también se acumula hasta esa fecha. Los denominadores y resultados de empleo conservan el corte laboral de enero de 2026; el CSV identifica ambas fechas por separado.")
    st.caption("Privadas Sierra utiliza exclusivamente las 18 IES indicadas. Se normalizan tildes, mayúsculas, espacios y puntuación; también se reconocen siglas, Universidad Tecnológica Equinoccial como UTE y Universidad Internacional SEK como UISEK. Los registros con nombres equivalentes se deduplican por persona dentro de cada IES.")
    st.warning("SRI histórico inferido: el catastro aporta el último estado y fechas de inicio, suspensión y reinicio, sin el historial completo de eventos. Los intervalos no reconstruibles quedan indeterminados. Los estados inferidos deben validarse con catastros históricos para obtener una serie definitiva.")
    st.caption("Se conserva el registro SRI con FECHA_CARGA más reciente por RUC y, ante igual carga, la última FECHA_ACTUALIZACION. No se utiliza el estado del establecimiento para clasificar a la persona.")
    q1,q2,q3 = st.columns(3)
    q1.metric("Filas con identificación inválida",integer(quality['invalid_ids']))
    q2.metric("Filas sin fecha válida",integer(quality['invalid_dates']))
    q3.metric("SRI indeterminado sin SIM · corte",integer(row.sri_uncertain))
    st.caption("Las filas académicas inválidas se excluyen. Los conteos de calidad son de filas, excepto SRI indeterminado, que cuenta personas. El nivel académico filtra los registros de titulación antes de calcular los indicadores. No se filtra por nacionalidad.")

with st.expander("Resumen de los cuatro cortes y descarga"):
    st.caption(f"Nivel académico: {level}")
    export = summary.rename(columns={"year":"Año","cutoff":"Fecha de corte laboral","academic_cutoff":"Fecha de corte académico","label":"Corte laboral","graduates":"Graduados al corte laboral","employed":"Profesionales ejerciendo","rate":"Empleo visible (%)","dependent":"Dependientes","independent":"Independientes","unknown":"Sin información laboral","sri_uncertain":"SRI indeterminado sin SIM","p25":"Salario P25","p75":"Salario P75","salary_n":"Personas con salario","recent":"Recién titulados"})
    st.dataframe(export,hide_index=True,width="stretch")
    export = export.assign(**{"Nivel académico": level})
    payload = "# " + ("DEMOSTRACIÓN · DATOS SINTÉTICOS" if demo else "DATOS INSTITUCIONALES") + "\n# Carreras: " + " | ".join(c.replace('\n',' ') for c in selected) + "\n" + export.to_csv(index=False,sep=";",decimal=",")
    st.download_button("Descargar resumen CSV",payload.encode("utf-8-sig"),file_name=f"empleabilidad_{'DEMO' if demo else 'resumen'}.csv",mime="text/csv")

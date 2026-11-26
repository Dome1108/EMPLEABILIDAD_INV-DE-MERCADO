from datetime import datetime
from html import escape
import json
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from modelo import BLOQUES, VARIABLES, carrera_modelo, Config, cargar_datos, evaluar, precio, recomendaciones
import importlib
import modelo_referencia_precios
# Un servidor en marcha puede conservar una versión anterior del módulo de precios.
if not hasattr(modelo_referencia_precios,'tablas_calculo'):
    importlib.reload(modelo_referencia_precios)
from modelo_referencia_precios import _norm, calcular_modelo, crear_figura, posicion_en_rango, rango_van_westendorp, tablas_calculo

if not globals().get('APARTADO_INTEGRADO'):
    st.set_page_config(page_title='Observatorio · Viabilidad académica',page_icon='◈',layout='wide',initial_sidebar_state='collapsed')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"],.stApp{font-family:'DM Sans',sans-serif;color:#172c43}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stHeader"]{background:#fff}.block-container{padding:2.2rem 2.7rem 3rem;max-width:1680px}
h1,h2,h3{font-family:'Manrope',sans-serif;letter-spacing:-.035em}h3{font-size:1.15rem!important}
[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"]{display:none}
[data-testid="stVerticalBlockBorderWrapper"]>div{border-radius:18px!important;border-color:#e4eaf1!important;background:#fff}
.eyebrow{text-transform:uppercase;font-size:10px;letter-spacing:2px;font-weight:800;color:#65809b;margin-bottom:12px}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:40px}.brandmark{background:#0072bc;color:white;width:42px;height:42px;border-radius:13px;display:grid;place-items:center;font-size:26px}.brand strong{font-family:Manrope,sans-serif;font-size:16px}.brand small{font-size:11px;color:#71859b}
.side-note{font-size:12px;line-height:1.7;color:#657b91;margin:18px 0}.reference{padding:15px;background:#f0f6fc;border:1px solid #d9e7f4;border-radius:12px;font-size:12px;line-height:1.6}.reference b{color:#0072bc}
.header{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:22px}.header h1{font-size:35px;font-weight:800;margin:0;color:#123452;padding:0}.header p{color:#6d8094;font-size:13px;margin:10px 0 0}.header .stamp{border:1px solid #d9e3ed;border-radius:24px;padding:8px 14px;color:#54708c;white-space:nowrap;font-size:11px;background:white}
.hero{background:linear-gradient(120deg,#073759,#005e9d);border-radius:18px;padding:26px 30px;color:#fff;min-height:170px;position:relative;overflow:hidden}.hero:after{content:'';position:absolute;width:220px;height:220px;border:32px solid #ffffff08;border-radius:50%;right:-80px;top:-95px}.hero .eyebrow{color:#a9cee5;margin:0 0 5px}.score{font-family:Manrope,sans-serif;font-size:57px;line-height:1.2;font-weight:800;letter-spacing:-3px}.score small{font-size:22px;font-weight:500;color:#a6cbdf;letter-spacing:0}.hero-bottom{display:flex;justify-content:space-between;align-items:center;margin-top:12px;font-size:12px;color:#bed8e9}.hero-pill{border-radius:20px;background:#ffffff20;color:#fff;padding:6px 12px;font-weight:600}
.kpi{border:1px solid #e2e9f1;background:white;border-radius:18px;padding:21px 22px;min-height:170px}.kpi-label{font-size:11px;font-weight:600;color:#6f8398;margin-bottom:15px}.kpi-number{font-family:Manrope,sans-serif;font-size:30px;font-weight:800;color:#153954;line-height:1.2}.kpi p{font-size:12px;color:#7c8fa0;margin:10px 0 0}.quad-pill{font-size:14px;font-weight:700;border-radius:8px;padding:8px 11px;display:inline-block;margin:2px 0 6px}.quad-pill.green{color:#248064;background:#e8f5ee}.quad-pill.amber{color:#a46e21;background:#fff5df}.quad-pill.red{color:#b7545d;background:#fceef0}.quad-pill.slate{color:#5a6f85;background:#edf1f5}
.section-title{display:flex;align-items:center;justify-content:space-between;margin:3px 0 3px}.section-title h3{margin:0;padding:0}.section-title small{font-size:11px;color:#8595a5}.caption{font-size:12px;color:#7b8b9a;line-height:1.6;margin-bottom:12px}
.rank-label{font-size:10px;letter-spacing:1.3px;color:#6f879c;font-weight:700;margin:12px 0 10px}.rank-label.low{margin-top:25px}.rank-row{display:flex;justify-content:space-between;gap:10px;font-size:12px;padding:10px 0;border-bottom:1px solid #eef2f6}.rank-row b{color:#0072bc;white-space:nowrap}.rank-row.weak b{color:#bd7c2e}
.rec{display:flex;gap:12px;padding:13px 0;border-bottom:1px solid #eaf0f6}.rec:last-child{border-bottom:none}.rec-index{flex-shrink:0;width:25px;height:25px;background:#eaf3fc;border-radius:8px;color:#0072bc;display:grid;place-items:center;font-size:11px;font-weight:700}.rec-title{font-size:12px;font-weight:700;color:#126ba5;margin-bottom:5px}.rec p{font-size:12px;line-height:1.6;color:#60758b;margin:0}
.weight-row{display:flex;justify-content:space-between;font-size:11px;margin:11px 0 5px;color:#60758b}.weight-track{height:4px;border-radius:5px;background:#edf2f7}.weight-track div{height:4px;background:#0072bc;border-radius:5px}
.footer-note{font-size:11px;color:#8293a3;border-top:1px solid #e1e8f0;margin-top:30px;padding-top:15px;line-height:1.7}.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:10px;color:#718298;margin:6px 0 12px}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}
button[data-baseweb="tab"]{font-size:13px!important}div[data-testid="stTabs"]{margin-top:22px}div[data-testid="stMetricValue"]{font-size:25px}
.hero{background:#fff;color:#153954;border:1px solid #e2e9f1}.hero:after{display:none}.hero .eyebrow{color:#6f8398}.score small{color:#8b9baa}.hero-bottom{color:#60758b}.hero-pill{background:#fff;color:#0072bc;border:1px solid #d9e7f1}.reference{background:#fff}.rec-index{background:#fff;border:1px solid #dce8f2}
.header{padding:8px 0 22px;border-bottom:1px solid #d9e2eb}.header h1{color:#0072bc}.hero{border-top:4px solid #0072bc;box-shadow:0 3px 14px rgba(21,57,84,.035)}.score{color:#123e60}.kpi{border-top:4px solid #dbe5ee;box-shadow:0 3px 14px rgba(21,57,84,.025)}.section-title{padding-bottom:12px;margin-bottom:12px;border-bottom:1px solid #e5ebf0}.section-title h3{color:#153954;font-weight:800}.rank-label{color:#0072bc}.rank-label.low{color:#60758b}.price-report-header{border-bottom-width:2px}.price-summary strong{font-family:'Manrope',sans-serif;font-weight:800}.price-report-note{border-top:1px solid #edf0f4;padding-top:12px}
.price-report-header{display:flex;justify-content:space-between;gap:24px;align-items:center;padding:10px 4px 20px;border-bottom:1px solid #dfe5ec}.price-report-header h3{font-size:24px!important;color:#0072bc;margin:0;padding:0}.price-report-program{border-left:2px solid #dfe5ec;padding-left:22px;max-width:35%;font-size:13px;color:#153954}.price-report-program small{display:block;font-size:9px;letter-spacing:1.5px;color:#8b98a5;margin-bottom:6px}.price-summary{display:grid;grid-template-columns:1.4fr 1fr 1fr;gap:25px;padding:20px 4px;border-bottom:1px solid #edf0f4}.price-summary small{display:block;color:#7b8b99;font-size:10px;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px}.price-summary strong{font-size:20px;color:#153954;font-weight:700}.price-summary .udla strong{color:#bd535e}.price-summary .position strong{font-size:14px}.price-report-note{font-size:11px;color:#8090a0;padding:5px 4px;line-height:1.6}
@media(max-width:850px){.price-report-header{align-items:flex-start}.price-report-header h3{font-size:19px!important}.price-summary{grid-template-columns:1fr;gap:15px}.price-report-program{max-width:42%}}
@media(max-width:850px){.block-container{padding:1.2rem}.header h1{font-size:27px}.stamp{display:none}.hero,.kpi{min-height:150px}.score{font-size:48px}}
@media print{[data-testid="stSidebar"],header,footer,[data-testid="stToolbar"]{display:none}.block-container{padding:0}.stApp{background:white}.hero,.kpi,.rec{break-inside:avoid}}
</style>''',unsafe_allow_html=True)

# Nombres de la pestaña que difieren de CARRERA_UDLA en Precios_Homologados.
CARRERA_PRECIOS={'SOFTWARE':'INGENIERIA EN SOFTWARE','RRII':'RELACIONES INTERNACIONALES','MUSICA':'ARTES MUSICALES'}
# Nivel de Precios_Homologados según el selector Pregrado/Posgrado de la pestaña.
NIVEL_PRECIOS={'Pregrado':'3ER NIVEL','Posgrado':'4TO NIVEL'}
# Posgrado: no existe la carrera en 4TO NIVEL; se ofrecen los programas UDLA cuyo nombre
# contiene estas palabras (sin tildes, en mayúsculas). EXCLUIR evita falsos positivos.
POSGRADO_CLAVES={'NEGOCIOS INTERNACIONALES':['NEGOCIOS'],'SOFTWARE':['SOFTWARE'],'ENFERMERIA':['ENFERMER'],
    'MEDICINA':['MEDICINA'],'ODONTOLOGIA':['ODONTO','ENDODON','ORTODON'],'MULTIMEDIA Y PRODUCCION AUDIOVISUAL':['AUDIOVISUAL','MULTIMEDIA'],
    'DERECHO':['DERECHO'],'ARQUITECTURA':['ARQUITECT'],'RRII':['RELACIONES INTERNACIONALES'],'GASTRONOMIA':['GASTRONOM'],
    'MUSICA':['MUSIC'],'PSICOLOGIA':['PSICOLOG']}
POSGRADO_EXCLUIR=['VETERINARIA']


def programas_posgrado(prices,carrera):
    """Programas UDLA de 4TO NIVEL vinculados a la carrera.

    Primero los que tienen más competidores en su período más reciente, que es el que
    el gráfico muestra por defecto.
    """
    claves=POSGRADO_CLAVES.get(_norm(carrera),[_norm(carrera)])
    data=prices[prices['NIVEL ACADEMICO'].map(_norm).eq(NIVEL_PRECIOS['Posgrado'])].copy()
    data['_programa']=data['CARRERA UDLA'].map(_norm)
    data=data[data['_programa'].map(lambda p:any(k in p for k in claves) and not any(e in p for e in POSGRADO_EXCLUIR))]
    if data.empty:
        return []
    data['_periodo']=data['Semestre Pos'].astype(str).str.strip()
    ultimo=data.groupby('_programa')['_periodo'].transform('max')
    precio=pd.to_numeric(data['TOTAL'],errors='coerce')
    recientes=data[data['_periodo'].eq(ultimo)&precio.gt(0)&data['SIGLA'].map(_norm).ne('UDLA')]
    competidores=recientes.groupby('_programa')['SIGLA'].nunique()
    nombres=data.groupby('_programa')['CARRERA UDLA'].first()
    orden=sorted(nombres.index,key=lambda p:(-int(competidores.get(p,0)),p))
    return [nombres[p] for p in orden]


# CARRERA_EMPLEABILIDAD y carrera_modelo viven en modelo.py: los usan esta pestaña y la presentación .pptx.


def carrera_empleabilidad():
    """(carrera del modelo, carreras elegidas): la primera elegida en Empleabilidad que esté entre las 12."""
    chosen=[c for c in st.session_state.get('selected_careers',[]) if c] or ['ECONOMIA']
    found=next((m for m in map(carrera_modelo,chosen) if m),None)
    return found,chosen


def sql_config():
    try:
        return dict(st.secrets.get('sql',{}))
    except Exception:
        return {}


@st.cache_data(ttl=3600,show_spinner='Leyendo precios de Precios_Homologados…',max_entries=1)
def precios_referencia(config):
    import sys
    from pathlib import Path
    root=str(Path(__file__).resolve().parent.parent)
    if root not in sys.path:
        sys.path.insert(0,root)
    import importlib
    import data_access
    # Un servidor en marcha puede tener cargada una versión previa sin esta consulta.
    if not hasattr(data_access,'load_reference_prices'):
        data_access=importlib.reload(data_access)
    return data_access.load_reference_prices(config)


# Posiciones de precio de la tabla de reglas; el puntaje sale de modelo.precio.
POSICIONES_PRECIO=[('25% más barato',-.25),('20% más barato',-.20),('−15% a +10%',0.0),('15% más caro',.15),('20% más caro',.20),('25% más caro',.25)]


def reglas_modelo(level,reference,search_limit,competitor_limit,competition_weight):
    """Textos y tablas de «Reglas del modelo»: los usa la pestaña y el reporte PDF."""
    reference_name=reference['carrera']
    return dict(
        intro=[('md',f'**Nivel de evaluación: {level}.** Competencia permite hasta 5 competidores en pregrado y hasta 3 en posgrado. La regla es inclusiva y se aplica también al corte del cuadrante.'),
               ('md',f'**Carrera de referencia:** {reference_name}. Contra sí misma obtiene siempre 100 por definición: completa el aporte de todas las variables. Para las demás carreras, competencia usa el límite por nivel y precio el rango acordado frente al mercado. Cada variable aporta como máximo su peso; bloques y total quedan entre 0 y 100.')],
        col1=[('title','Regla de tres'),
              ('latex',(r'\text{Aporte}=\min\left(\text{peso},\frac{\text{valor del programa}}{\text{valor de referencia}}\times\text{peso}\right)','Aporte = mín( peso ,  valor del programa / valor de referencia × peso )')),
              ('md',f'Ejemplo con los pesos originales: búsquedas pesa 13,65 puntos. Una carrera con 80% de las búsquedas de {reference_name} aporta 10,92 puntos; con 120% aporta el máximo de 13,65. Competencia se evalúa contra el límite aceptable, sin compararla con la carrera base. Los aportes mostrados usan los pesos activos.'),
              ('md','Para matrícula y titulados se comparan **factores de crecimiento (1 + tasa)**. Así podemos evaluar caídas sin dividir tasas negativas. Las vacantes son exclusivamente informativas; la cantidad de profesionales sí entra al cálculo como indicador de tamaño del campo, donde más es mejor.'),
              ('md','**Subpesos de demanda:** nombre 65% (búsquedas 70%, rúbrica 30%); educativa 35% (matriculados 60%, titulados 40%). **Empleabilidad:** profesionales 30%, alineación 45% y salario 25%. El bloque conserva 22% global: aportes máximos de 6,60, 9,90 y 5,50 puntos respectivamente.'),
              ('md',f'**Alineación con el mercado laboral:** mayor es mejor. Puntaje = mínimo entre 100 y (alineación del programa / alineación de {reference_name} ×100). La alineación base es {reference["alineacion"]:.0%}. Su aporte total máximo con los pesos originales es 9,90 puntos.'),
              ('md',f'**Profesionales:** aporte = mínimo entre 6,60 y (profesionales del programa / {reference["profesionales"]:,.0f} profesionales de {reference_name} ×6,60). Mide tamaño del campo, sin interpretarse como una tasa de empleabilidad. Más profesionales permite completar el aporte, sin exceder su peso.')],
        col2=[('title','Precio frente a la media'),
              ('table',pd.DataFrame({'Posición de precio':[label for label,_ in POSICIONES_PRECIO],'Puntaje':[round(precio(gap),2) for _,gap in POSICIONES_PRECIO]})),
              ('caption','Por debajo del rango se restan 5 puntos por punto porcentual; por encima, 3,33. Mínimo 0. Este bloque mide posicionamiento de precio, sin estimar capacidad de pago ni rentabilidad.')],
        resto=[('title',f'Competencia · {competition_weight}% del modelo'),
               ('md',f'**Hasta {competitor_limit} competidores, inclusive:** 100 puntos. **Por encima:** {competitor_limit} / competidores ×100. El aporte máximo al total es el peso activo del bloque (28 puntos con los pesos originales). Con cero competidores se asigna 100, sin dividir por cero. La misma regla se aplica a la carrera base.'),
               ('title','Oportunidad de mercado · diagnóstico visual, sin peso adicional'),
               ('table',pd.DataFrame({'Cuadrante':['Mercado atractivo','Mercado competido','Baja tracción','Mercado débil'],'Búsquedas':[f'≥{search_limit}%',f'≥{search_limit}%',f'<{search_limit}%',f'<{search_limit}%'],'Competidores':[f'≤{competitor_limit}',f'>{competitor_limit}',f'≤{competitor_limit}',f'>{competitor_limit}']})),
               ('caption','El cuadrante no añade un puntaje propio. El umbral de búsquedas modifica la clasificación visual y el límite de competidores modifica el bloque competitivo de las carreras evaluadas. La referencia contra sí misma conserva 100 por definición; su posición en el cuadrante refleja sus datos reales.'),
               ('md','**Lectura provisional del total:** 100 puntaje máximo; 90–<100 puntaje alto; 75–<90 resultado intermedio; 60–<75 requiere ajustes; <60 puntaje bajo. Son rangos iniciales, no una autorización de apertura. Revisar las dimensiones débiles incluso si el promedio es favorable.'),
               ('md','**Alcance de los datos:** se usa la tabla principal del archivo entregado, con búsquedas locales y sin palabras clave. Para precio se conserva la brecha por carrera de esa tabla. El sector económico suma ventas de personas naturales y sociedades de 36 meses: mide tamaño, no crecimiento.'),
               ('caption','Las búsquedas aportan puntos solo en demanda. Su uso en el cuadrante es informativo. Profesionales sí entra al cálculo; vacantes y palabras clave no. Los pesos siguen siendo de criterio y requieren validación con casos de desempeño diverso.')])


def mostrar_reglas(items):
    for kind,value in items:
        if kind=='title':st.markdown(f'**{value}**')
        elif kind=='md':st.markdown(value)
        elif kind=='caption':st.caption(value)
        elif kind=='latex':st.latex(value[0])
        elif kind=='table':st.dataframe(value,hide_index=True,width='stretch')


def render_dashboard(reference,tab_key,fixed_career=None):
    """fixed_career: carrera elegida en Oferta de valor-empleabilidad; sin ella, filtro propio."""
    data=cargar_datos()
    reference_name=reference['carrera']
    header=st.empty()
    pdf_slot=st.empty()
    with st.container(border=True):
        selector,level_selector,reference_info=st.columns([1.5,.7,1],gap='large',vertical_alignment='center')
        with selector:
            if fixed_career:
                selected=fixed_career
                st.markdown(f'<div class="reference">CARRERA EVALUADA<br><b>{escape(selected)}</b> · se elige en Oferta de valor-empleabilidad</div>',unsafe_allow_html=True)
            else:
                selected=st.selectbox('Filtrar por carrera',[d['carrera'] for d in data],index=6,key=f'carrera_{tab_key}',help='Selecciona un programa para actualizar todos los resultados y gráficos.')
        with level_selector:
            level=st.selectbox('Nivel de evaluación',['Pregrado','Posgrado'],key=f'nivel_{tab_key}',help='Define el límite de competencia:5 en pregrado y3 en posgrado. No cambia los datos originales del programa.')
        with reference_info:
            st.markdown(f'<div class="reference">COMPARAR CONTRA<br><b>{escape(reference_name)}</b> · base de comparación</div>',unsafe_allow_html=True)
    with st.expander('Pesos y configuración del modelo',expanded=False):
        st.caption('Los pesos deben sumar 100%. Los cambios solo afectan esta sesión.')
        weight_columns=st.columns(5)
        weights=[]
        for i,(label,value) in enumerate(zip(BLOQUES,[30,22,28,12,8])):
            with weight_columns[i]:
                weight=st.number_input(label,min_value=0,max_value=100,value=value,step=1,key=f'weight{i}_{tab_key}')
                weights.append(weight)
                st.markdown(f'<div class="weight-track"><div style="width:{weight}%"></div></div>',unsafe_allow_html=True)
        threshold_columns=st.columns(2)
        with threshold_columns[0]:
            search_limit=st.slider('Umbral de búsquedas (%)',1,99,75,key=f'busquedas_{tab_key}',help=f'Índice frente a {reference_name}; no es el índice bruto de Google Trends.')
        with threshold_columns[1]:
            competitor_limit=5 if level=='Pregrado' else 3
            st.markdown(f'**Límite de competencia · {level}: {competitor_limit}**')
            st.caption('Aplica al cálculo y al cuadrante. Hasta el límite obtiene100; por encima, límite / competidores ×100.')

    if sum(weights)!=100:
        st.error(f'Los pesos suman {sum(weights)}%. Ajústalos a 100% para calcular el comparativo.');return
    config=Config(weights,search_limit,nivel=level)
    results=[evaluar(d,reference,config) for d in data]
    current=next(r for r in results if r['carrera']==selected)
    raw=next(d for d in data if d['carrera']==selected)
    baseline=next(r for r in results if r['carrera']==reference_name)
    colors={'Mercado atractivo':('#248064','green'),'Mercado competido':('#c18b37','amber'),'Baja tracción':('#c46d79','red'),'Mercado débil':('#6b8194','slate')}
    quadcolor,quadclass=colors[current['cuadrante']]

    header.markdown(f'<div class="header"><div><div class="eyebrow">MODELO DE APERTURA · COMPARATIVO ACADÉMICO</div><h1>Resultados de viabilidad</h1><p>{escape(selected)} <span style="color:#b7c3cf">&nbsp; / &nbsp;</span> frente a {escape(reference_name)}</p></div><div class="stamp">● &nbsp; Modelo exploratorio</div></div>',unsafe_allow_html=True)

    a,b,c=st.columns([1.35,1,1],gap='medium')
    with a:
        st.markdown(f'<div class="hero"><div class="eyebrow">Índice comparativo ponderado</div><div class="score">{current["total"]:.1f}<small> / 100</small></div><div class="hero-bottom"><span class="hero-pill">{current["clasificacion"]}</span><span>Referencia: {baseline["total"]:.0f} puntos</span></div></div>',unsafe_allow_html=True)
    with b:
        st.markdown(f'<div class="kpi"><div class="kpi-label">POSICIÓN EN EL MERCADO</div><span class="quad-pill {quadclass}">{current["cuadrante"]}</span><p>{current["competidores"]:g} competidores</p></div>',unsafe_allow_html=True)
    with c:
        gap=raw['brecha_precio']
        in_range=-.15<=gap<=.10
        costtext='Dentro del rango aceptable' if in_range else 'Fuera del rango aceptable'
        st.markdown(f'<div class="kpi"><div class="kpi-label">PRECIO FRENTE A LA MEDIA</div><div class="kpi-number">{gap:+.1%}</div><p>{costtext}</p></div>',unsafe_allow_html=True)

    diagnosis=st.container()

    def radar(values):
        labels=['Demanda','Empleabilidad','Competencia','Precio','Sector económico']
        radial_max=105
        fig=go.Figure()
        fig.add_trace(go.Scatterpolar(r=values+[values[0]],theta=labels+[labels[0]],fill='toself',fillcolor='rgba(0,141,193,.10)',line=dict(color='#008ec1',width=2.6),mode='lines+markers',marker=dict(size=6,color='#008ec1'),name=selected,hovertemplate='%{theta}: %{r:.1f} · referencia 100<extra></extra>'))
        fig.add_trace(go.Scatterpolar(r=[100]*6,theta=labels+[labels[0]],mode='lines',line=dict(color='#b4c2d0',width=1.7,dash='dash'),name='Máximo del modelo',showlegend=False,hovertemplate='%{theta}: máximo 100<extra></extra>'))
        fig.update_layout(height=365,margin=dict(l=75,r=75,t=35,b=45),paper_bgcolor='rgba(0,0,0,0)',font=dict(family='Arial',color='#60758b',size=11),showlegend=False,polar=dict(bgcolor='white',radialaxis=dict(range=[0,radial_max],tickvals=[25,50,75,100],ticksuffix='%',tickfont=dict(size=9,color='#90a1b1'),gridcolor='#e5edf4',linecolor='#e5edf4'),angularaxis=dict(rotation=90,direction='clockwise',gridcolor='#e5edf4',linecolor='#e5edf4')))
        return fig

    def market_chart(show_all):
        fig=go.Figure()
        ymax=max([d['competidores'] for d in data]+[config.umbral_competidores])*1.25
        xmax=max([r['busquedas'] for r in results] if show_all else [100,current['busquedas']])*1.12
        t=config.umbral_busquedas;c=config.umbral_competidores
        for x0,x1,y0,y1,col in [(0,t,0,c,'#fcf0f2'),(t,xmax,0,c,'#eaf6ef'),(0,t,c,ymax,'#edf2f6'),(t,xmax,c,ymax,'#fcf6e9')]:
            fig.add_shape(type='rect',x0=x0,x1=x1,y0=y0,y1=y1,line_width=0,fillcolor=col,layer='below')
        fig.add_vline(x=t,line=dict(color='#9cadbb',dash='dash',width=1))
        fig.add_hline(y=c,line=dict(color='#9cadbb',dash='dash',width=1))
        for x,y,text,color in [(t/2,ymax*.95,'MERCADO DÉBIL','#70869b'),((t+xmax)/2,ymax*.95,'MERCADO COMPETIDO','#b68b4b'),(t/2,ymax*.04,'BAJA TRACCIÓN','#bd7b86'),((t+xmax)/2,ymax*.04,'MERCADO ATRACTIVO','#468870')]:
            fig.add_annotation(x=x,y=y,text=text,showarrow=False,font=dict(size=9,color=color))
        if show_all:
            # Agrupar coordenadas idénticas para que el hover muestre todas las carreras.
            groups={}
            for item in results:
                groups.setdefault((item['busquedas'],item['competidores']),[]).append(item['carrera'])
            for (x,y),names in groups.items():
                fig.add_trace(go.Scatter(x=[x],y=[y],mode='markers',marker=dict(size=9,color='#9db6cb',line=dict(width=1,color='white')),hovertemplate='<br>'.join(escape(n) for n in names)+f'<br>Búsquedas: {x:.1f}%<br>Competidores: {y:g}<extra></extra>',showlegend=False))
        fig.add_trace(go.Scatter(x=[baseline['busquedas']],y=[baseline['competidores']],mode='markers',marker=dict(symbol='diamond',size=13,color='#153954',line=dict(width=2,color='white')),name=reference_name,hovertemplate=escape(reference_name)+'<br>Búsquedas: %{x:.1f}%<br>Competidores: %{y}<extra></extra>'))
        fig.add_trace(go.Scatter(x=[current['busquedas']],y=[current['competidores']],mode='markers',marker=dict(size=20,color=quadcolor,line=dict(width=3,color='white'),opacity=.9),name=selected,hovertemplate=escape(selected)+'<br>Búsquedas: %{x:.1f}%<br>Competidores: %{y}<extra></extra>'))
        fig.update_layout(height=360,margin=dict(l=40,r=18,t=15,b=45),showlegend=False,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='white',font=dict(family='Arial',size=11,color='#71869a'),xaxis=dict(title=f'Búsquedas relativas · {reference_name} = 100%',range=[0,xmax],ticksuffix='%',showgrid=False,zeroline=False),yaxis=dict(title='Número de competidores',range=[0,ymax],dtick=2,showgrid=True,gridcolor='rgba(255,255,255,.55)',zeroline=False))
        return fig

    with diagnosis:
        st.write('')
        left,right=st.columns([1.48,1],gap='medium')
        with left:
            with st.container(border=True):
                st.markdown('<div class="section-title"><h3>Perfil del programa</h3><small>5 dimensiones</small></div>',unsafe_allow_html=True)
                plot,rank=st.columns([1.8,1],gap='small')
                with plot:
                    radar_fig=radar(current['bloques'])
                    st.plotly_chart(radar_fig,width='stretch',config={'displayModeBar':False},key=f'radar_{tab_key}')
                    st.markdown('<div class="legend"><span><i class="dot" style="background:#008ec1"></i>Programa seleccionado</span></div>',unsafe_allow_html=True)
                ranked=sorted(enumerate(current['bloques']),key=lambda x:x[1],reverse=True)
                strengths=[(BLOQUES[idx],value) for idx,value in ranked if value>=75][:2]
                gaps=[(BLOQUES[idx],value) for idx,value in sorted(ranked[-2:],key=lambda x:x[1])]
                with rank:
                    st.markdown('<div class="rank-label">FORTALEZAS · TOP 2</div>',unsafe_allow_html=True)
                    for name,value in strengths:st.markdown(f'<div class="rank-row"><span>{name}</span><b>{value:.1f}%</b></div>',unsafe_allow_html=True)
                    if not strengths:
                        st.markdown('<div class="caption">Ningún bloque alcanza el 75%.</div>',unsafe_allow_html=True)
                    st.markdown('<div class="rank-label low">MAYORES BRECHAS · BOTTOM 2</div>',unsafe_allow_html=True)
                    for name,value in gaps:st.markdown(f'<div class="rank-row weak"><span>{name}</span><b>{value:.1f}%</b></div>',unsafe_allow_html=True)
        with right:
            with st.container(border=True):
                st.markdown('<div class="section-title"><h3>Recomendaciones</h3><small>Según los resultados</small></div>',unsafe_allow_html=True)
                recs=recomendaciones(raw,current,config)
                for i,(title,text) in enumerate(recs,1):
                    st.markdown(f'<div class="rec"><div class="rec-index">{i:02}</div><div><div class="rec-title">{title}</div><p>{escape(text)}</p></div></div>',unsafe_allow_html=True)
        st.write('')
        left,right=st.columns([1.48,1],gap='medium')
        with left:
            with st.container(border=True):
                st.markdown('<div class="section-title"><h3>Demanda vs. competencia</h3><small>La zona verde es el objetivo</small></div>',unsafe_allow_html=True)
                allpoints=st.toggle('Mostrar todas las carreras',value=True,key=f'todas_{tab_key}')
                market_fig=market_chart(allpoints)
                st.plotly_chart(market_fig,width='stretch',config={'displayModeBar':False},key=f'quadrants_{tab_key}')
                market_note=f"Zona verde: búsquedas ≥{config.umbral_busquedas:.0f}% de {reference_name} y hasta {config.umbral_competidores:g} competidores."
                st.caption(market_note+" Puntos coincidentes se agrupan en el detalle al pasar el cursor.")
        with right:
            with st.container(border=True):
                st.markdown('<div class="section-title"><h3>Cómo se forma el resultado</h3></div><div class="caption">Puntaje de cada bloque × su peso en el modelo.</div>',unsafe_allow_html=True)
                contribution=pd.DataFrame({'Dimensión':BLOQUES,'Puntaje':[f'{x:.1f}' for x in current['bloques']],'Peso':[f'{x}%' for x in weights],'Aporte':[round(x*p/100,2) for x,p in zip(current['bloques'],weights)]})
                st.dataframe(contribution,hide_index=True,width='stretch',column_config={'Aporte':st.column_config.NumberColumn(format='%.2f')})
                st.metric('Índice ponderado',f"{current['total']:.2f} / 100")
        st.write('')
        # Referencia competitiva con precios reales de Precios_Homologados (modelo_referencia_precios).
        price_fig=None
        low=high=own_price=None
        price_position='Sin datos de precios'
        price_detail=None
        price_level=NIVEL_PRECIOS[level]
        price_career=CARRERA_PRECIOS.get(_norm(selected),selected)
        program_label=selected
        with st.container(border=True):
            header_slot=st.empty()
            try:
                prices=precios_referencia(sql_config())
            except Exception as exc:
                prices=None
                st.warning('No fue posible leer los precios de SQL Server (Precios_Homologados).')
                with st.expander('Detalle técnico'):
                    st.code(str(exc))
            periods=[]
            if prices is not None and level=='Posgrado':
                programs=programas_posgrado(prices,selected)
                if programs:
                    price_career=st.selectbox('Programa de posgrado',programs,index=0,key=f'programa_posgrado_{tab_key}',
                        help='Programas UDLA de 4TO NIVEL vinculados a la carrera (CARRERA_UDLA). Primero los que tienen más competidores.')
                    program_label=f'{selected} · {price_career.title()}'
                else:
                    price_career=None
                    st.info(f'{selected} no tiene programas de posgrado (4TO NIVEL) en Precios_Homologados.')
            if prices is not None and price_career:
                subset=prices[prices['NIVEL ACADEMICO'].map(_norm).eq(price_level)&prices['CARRERA UDLA'].map(_norm).eq(_norm(price_career))]
                periods=sorted(subset['Semestre Pos'].dropna().astype(str).str.strip().unique(),reverse=True)
                if not periods:
                    st.info(f'«{price_career}» no tiene precios de {price_level} en Precios_Homologados.')
            if periods:
                # Clave por programa: al cambiar de carrera o programa vuelve al período más reciente.
                period=st.selectbox('Período de precios',periods,index=0,key=f'periodo_precios_{tab_key}_{level}_{_norm(price_career)}',help='SEMESTRE_POS de Precios_Homologados. Por defecto, el más reciente.')
                model=calcular_modelo(prices,price_level,price_career,period)
                ref=model['referencias']
                own_price=model['precio_udla']
                # Igual que el modelo: sin curvas (muestra < 5 o sin variación) no hay rango.
                # Rango de Van Westendorp: del cruce PMC al cruce PME, los mismos que marca el gráfico.
                if model['curvas'] is not None:
                    vw_range=rango_van_westendorp(model)
                    if vw_range is not None:
                        low,high=vw_range
                        place=posicion_en_rango(own_price,vw_range)
                        price_position={'dentro':'Dentro del rango','debajo':'Por debajo del rango','encima':'Por encima del rango'}.get(place,'Sin precio UDLA en el período')
                    else:
                        price_position='Las curvas no definen un rango'
                else:
                    price_position='Muestra insuficiente' if model['n'] else 'Sin competidores con precio'
                if model['curvas'] is not None:
                    price_fig=crear_figura(model)
                    st.plotly_chart(price_fig,width='stretch',theme=None,config={'displayModeBar':False},key=f'precios_referencia_{tab_key}')
                elif model['n']:
                    st.info('Muestra pequeña o sin variación suficiente (menos de 5 competidores o menos de 3 precios distintos). Se muestran precios observados, sin curvas.')
                if model['n']:
                    price_detail=model['competidores'].rename(columns={'_institucion':'Universidad',model['columna']:'Precio (mediana del período)'}).sort_values('Precio (mediana del período)')
                    with st.expander(f"Ver precios de los {model['n']} competidores"):
                        st.dataframe(price_detail,hide_index=True,width='stretch',column_config={'Precio (mediana del período)':st.column_config.NumberColumn(format='$%.2f')})
                if model['curvas'] is not None:
                    percentiles,distances,thresholds,crossings=tablas_calculo(model)
                    money=st.column_config.NumberColumn(format='$%.2f')
                    with st.expander('Ver cálculo paso a paso'):
                        st.markdown(f"**1. Percentiles** de los {model['n']} precios de la competencia (posición = (n − 1) × q; si cae entre dos precios, se interpola).")
                        st.dataframe(percentiles,hide_index=True,width='stretch',column_config={'Valor':money})
                        st.markdown('**2. Distancias** desde la mediana.')
                        st.dataframe(distances,hide_index=True,width='stretch',column_config={'Valor':money})
                        st.markdown('**3. Umbrales por universidad**: precio − distancia (barato, mínimo $0) o precio + distancia (caro). Cada círculo del gráfico es uno de estos valores.')
                        st.dataframe(thresholds,hide_index=True,width='stretch',column_config={c:money for c in thresholds.columns if c!='Universidad'})
                        st.markdown(f"**4. Curvas**: en cada precio, % de universidades con umbral ≥ precio (Demasiado barato, Barato) o ≤ precio (Caro, Demasiado caro). Cada universidad vale 1/{model['n']} = {100/model['n']:.1f} %.")
                        st.markdown('**5. Cruces** donde se cortan las líneas. El rango aceptable va del PMC al PME.')
                        st.dataframe(crossings,hide_index=True,width='stretch',column_config={'Precio':money,'Porcentaje':st.column_config.NumberColumn(format='%.1f %%')})
                if 0<model['n']<10:
                    st.caption(f"Resultado exploratorio: solo {model['n']} instituciones competidoras.")
                price_note=(f"Programa: {price_career} · variable comparada: {model['columna']} · {price_level} · período {period} · {model['n']} competidores (una mediana por universidad). "
                            'Rango aceptable: del cruce Demasiado barato × Caro (PMC) al cruce Barato × Demasiado caro (PME). '
                            'Curvas Van Westendorp construidas con precios observados de la competencia, no con encuestas: '
                            'no miden disposición a pagar y sus cruces no determinan un precio óptimo. Fuera del índice de viabilidad.')
            else:
                price_note='Sin datos de precios para esta carrera.'
            own_label=f'${own_price:,.0f}' if own_price is not None else '—'
            range_label=f'${low:,.0f} — ${high:,.0f}' if low is not None else '—'
            header_slot.markdown(f'<div class="price-report-header"><div><div class="eyebrow">VAN WESTENDORP · PRECIOS OBSERVADOS · {price_level}</div><h3>Sensibilidad de precio</h3></div><div class="price-report-program"><small>PROGRAMA EVALUADO</small><b>{escape(program_label)}</b></div></div><div class="price-summary"><div><small>Rango aceptable · PMC–PME</small><strong>{range_label}</strong></div><div class="udla"><small>UDLA · mediana del período</small><strong>{own_label}</strong></div><div class="position"><small>Posición frente al rango</small><strong>{price_position}</strong></div></div>',unsafe_allow_html=True)
            st.markdown(f'<div class="price-report-note">{escape(price_note)}</div>',unsafe_allow_html=True)
        with st.expander('Ver indicadores y valores originales'):
            alignment_note='Alineación con el mercado laboral: el dato denominado «Brecha Mercado Laboral vs Programa Educativo» en la fuente mide coincidencia de competencias. Mayor porcentaje significa mayor alineación y mejor puntaje; no se invierte.'
            st.caption(alignment_note)
            rawvals=[raw['matriculados'],raw['titulados'],raw['busquedas'],raw['nombre'],raw['alineacion'],raw['salario'],raw['competidores'],raw['brecha_precio'],raw['ventas_naturales']+raw['ventas_sociedades'],raw['profesionales']]
            refvals=[reference['matriculados'],reference['titulados'],reference['busquedas'],reference['nombre'],reference['alineacion'],reference['salario'],reference['competidores'],reference['brecha_precio'],reference['ventas_naturales']+reference['ventas_sociedades'],reference['profesionales']]
            def formatraw(i,x):
                if x is None:return 'Ver cuadrante'
                if i in [0,1,4,7]:return f'{x:.2%}'
                return f'{x:,.2f}'
            variable_weights=[weights[0]*.35*.6,weights[0]*.35*.4,weights[0]*.65*.7,weights[0]*.65*.3,weights[1]*.45,weights[1]*.25,weights[2],weights[3],weights[4],weights[1]*.3]
            indicators=pd.DataFrame({'Indicador':VARIABLES,'Programa':[formatraw(i,v) for i,v in enumerate(rawvals)],'Referencia para el cálculo':['Referencia contra sí misma: 100' if current['es_referencia'] else f'Límite: {competitor_limit} competidores' if i==6 else 'Media del mercado: rango −15% a +10%' if i==7 else formatraw(i,v) for i,v in enumerate(refvals)],'Índice aplicado (máx. 100)':[round(v,2) for v in current['indices']],'Peso máximo (puntos)':[round(v,2) for v in variable_weights],'Aporte al total':[round(v*p/100,2) for v,p in zip(current['indices'],variable_weights)]})
            st.dataframe(indicators,hide_index=True,width='stretch')
            indicator_notes=[f'En los demás indicadores la referencia es {reference_name}. Solo competencia y precio utilizan reglas propias, sin comparación con la carrera base.',
                             'Dato informativo, sin peso en el índice: vacantes. Un cero o un dato faltante aquí no reduce el puntaje. Profesionales sí participa en empleabilidad.']
            for note in indicator_notes:st.caption(note)
            informative=pd.DataFrame({'Dato informativo':['Vacantes'],'Programa':[raw.get('vacantes')],reference_name:[reference.get('vacantes')]})
            st.dataframe(informative,hide_index=True,width='stretch')

    if globals().get('APARTADO_INTEGRADO')=='Carreras':
        from integracion_viabilidad import render_evidencia_compartida
        render_evidencia_compartida(selected,tab_key)

    with st.expander('Comparar las 12 carreras',expanded=False):
        st.write('')
        ranking_title='Un mismo punto de partida para todos'
        ranking_note=f'{reference_name} es la referencia fija de esta pestaña. Las clasificaciones describen brechas comparativas; no son una autorización de apertura.'
        st.subheader(ranking_title)
        st.caption(ranking_note)
        ranking=pd.DataFrame([{'Carrera':r['carrera'],'Índice':round(r['total'],2),'Lectura':r['clasificacion'],'Cuadrante':r['cuadrante'],**{label:round(val,2) for label,val in zip(BLOQUES,r['bloques'])}} for r in results]).sort_values('Índice',ascending=False)
        ranking_fig=go.Figure(go.Bar(x=ranking['Índice'].tolist()[::-1],y=ranking['Carrera'].tolist()[::-1],orientation='h',marker_color=['#0072bc' if name==selected else '#153954' if name==reference['carrera'] else '#c8dce9' for name in ranking['Carrera'].tolist()[::-1]],text=[f'{x:.1f}' for x in ranking['Índice'].tolist()[::-1]],textposition='outside',hovertemplate='%{y}<br>Índice: %{x:.2f} /100<extra></extra>'))
        ranking_fig.update_layout(height=490,margin=dict(l=10,r=40,t=10,b=20),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(color='#60758b'),xaxis=dict(range=[0,108],gridcolor='#e4ebf1',title='Índice comparativo'),yaxis=dict(automargin=True))
        st.plotly_chart(ranking_fig,width='stretch',config={'displayModeBar':False},key=f'ranking_{tab_key}')
        st.dataframe(ranking,hide_index=True,width='stretch',column_config={'Índice':st.column_config.ProgressColumn(min_value=0,max_value=100,format='%.2f')})
        st.download_button('Descargar comparativo · CSV',ranking.assign(Nivel=level).to_csv(index=False).encode('utf-8-sig'),f'comparativo_{tab_key}_{level.lower()}.csv','text/csv',key=f'csv_{tab_key}')

    rules=reglas_modelo(level,reference,search_limit,competitor_limit,weights[2])
    with st.expander('Reglas del modelo',expanded=False):
        st.write('')
        st.subheader('Reglas acordadas, a la vista')
        mostrar_reglas(rules['intro'])
        col1,col2=st.columns(2)
        with col1:mostrar_reglas(rules['col1'])
        with col2:mostrar_reglas(rules['col2'])
        mostrar_reglas(rules['resto'])
        st.download_button('Descargar datos del tablero · JSON',json.dumps(data,ensure_ascii=False,indent=2),'datos_programas.json','application/json',key=f'json_{tab_key}')

    # Reporte PDF: mismos resultados, figuras y textos de la pestaña; se genera solo al pulsar.
    generated=datetime.now(ZoneInfo('America/Guayaquil'))
    report=dict(programa=selected,referencia=reference_name,nivel=level,generado=generated.strftime('%Y-%m-%d %H:%M'),
        resumen=dict(total=current['total'],clasificacion=current['clasificacion'],total_referencia=baseline['total'],
            cuadrante=current['cuadrante'],tono_cuadrante=quadclass,competidores_texto=f"{current['competidores']:g}",
            brecha_texto=f'{gap:+.1%}',precio_en_rango=in_range,lectura_precio=costtext),
        configuracion=dict(bloques=BLOQUES,pesos=weights,umbral_busquedas=search_limit,limite_competencia=competitor_limit,
            nota='Los pesos deben sumar 100%. Los cambios solo afectan esta sesión.',
            subpesos=indicators[['Indicador','Peso máximo (puntos)']],subpesos_texto=rules['col1'][4][1]),
        perfil=dict(figura=radar_fig,fortalezas=strengths,brechas=gaps,sin_fortalezas='Ningún bloque alcanza el 75%.'),
        recomendaciones=recs,
        mercado=dict(figura=market_fig,nota=market_note,alcance='Mostrar todas las carreras: '+('sí' if allpoints else 'no')+'.'),
        formacion=dict(tabla=contribution,indice=f"{current['total']:.2f} / 100",nota='Puntaje de cada bloque × su peso en el modelo.'),
        precio=dict(rango=range_label,precio_udla=own_label,posicion=price_position,figura=price_fig,nota=price_note),
        indicadores=dict(explicacion=alignment_note,tabla=indicators,notas=indicator_notes,informativo=informative),
        comparativo=dict(titulo=ranking_title,nota=ranking_note,figura=ranking_fig,tabla=ranking),
        reglas=rules)
    from reporte_pdf import build_viability_pdf, filename
    pdf_slot.download_button('Descargar reporte PDF',data=lambda:build_viability_pdf(report),
        file_name=filename(selected,generated.date().isoformat()),mime='application/pdf',on_click='ignore',
        icon=':material/picture_as_pdf:',key=f'pdf_{tab_key}',help='Reporte con todos los resultados de esta selección, incluidas las secciones plegadas.')


apartado=globals().get('APARTADO_INTEGRADO') or st.radio('Apartado',['Carreras','Educación continua'],horizontal=True,key='apartado',label_visibility='collapsed')
if apartado=='Educación continua':
    import importlib
    import modelo_edcos
    import graficos_edcos
    import datos_visuales_edcos
    import edcos_presentacion
    import habilidades_edcos
    import competencia_edcos
    # La vista puede seguir importada de una versión anterior del brief.
    # Recargarla evita ejecutar accesos a campos retirados durante el desarrollo.
    importlib.reload(modelo_edcos)
    importlib.reload(graficos_edcos)
    importlib.reload(datos_visuales_edcos)
    importlib.reload(edcos_presentacion)
    importlib.reload(habilidades_edcos)
    importlib.reload(competencia_edcos)
    import competencia_edcos_vista
    importlib.reload(competencia_edcos_vista)
    import figuras_pdf
    import edcos_pptx
    importlib.reload(figuras_pdf)
    importlib.reload(edcos_pptx)
    import edcos_vista
    importlib.reload(edcos_vista).render_edcos()
else:
    programas=cargar_datos()
    fixed=None
    if globals().get('APARTADO_INTEGRADO')=='Carreras':
        # En el observatorio la carrera se elige en Oferta de valor-empleabilidad. Si no está entre
        # las 12 del modelo (p. ej. Economía), se muestra igual el análisis con su selector propio.
        fixed,_=carrera_empleabilidad()
    reference_tabs=st.tabs([f'Referencia: {p["carrera"]}' for p in programas])
    for index,(tab,reference) in enumerate(zip(reference_tabs,programas)):
        tab_key='negocios' if index==0 else 'software' if reference['carrera']=='Software' else f'referencia_{index}'
        with tab:
            render_dashboard(reference,tab_key,fixed)

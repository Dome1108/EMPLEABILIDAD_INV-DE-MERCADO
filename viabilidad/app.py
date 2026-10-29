from html import escape
import json
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from modelo import BLOQUES, VARIABLES, Config, cargar_datos, evaluar, recomendaciones
from graficos_simulados import crear_grafico_precio, cruce_lineal

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

def render_dashboard(reference,tab_key):
    data=cargar_datos()
    reference_name=reference['carrera']
    header=st.empty()
    with st.container(border=True):
        selector,level_selector,reference_info=st.columns([1.5,.7,1],gap='large',vertical_alignment='center')
        with selector:
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
        costtext='Dentro del rango aceptable' if -.15<=gap<=.10 else 'Fuera del rango aceptable'
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
                    st.plotly_chart(radar(current['bloques']),width='stretch',config={'displayModeBar':False},key=f'radar_{tab_key}')
                    st.markdown('<div class="legend"><span><i class="dot" style="background:#008ec1"></i>Programa seleccionado</span></div>',unsafe_allow_html=True)
                ranked=sorted(enumerate(current['bloques']),key=lambda x:x[1],reverse=True)
                with rank:
                    st.markdown('<div class="rank-label">FORTALEZAS · TOP 2</div>',unsafe_allow_html=True)
                    strengths=[(idx,value) for idx,value in ranked if value>=75][:2]
                    for idx,value in strengths:st.markdown(f'<div class="rank-row"><span>{BLOQUES[idx]}</span><b>{value:.1f}%</b></div>',unsafe_allow_html=True)
                    if not strengths:
                        st.markdown('<div class="caption">Ningún bloque alcanza el 75%.</div>',unsafe_allow_html=True)
                    st.markdown('<div class="rank-label low">MAYORES BRECHAS · BOTTOM 2</div>',unsafe_allow_html=True)
                    for idx,value in sorted(ranked[-2:],key=lambda x:x[1]):st.markdown(f'<div class="rank-row weak"><span>{BLOQUES[idx]}</span><b>{value:.1f}%</b></div>',unsafe_allow_html=True)
        with right:
            with st.container(border=True):
                st.markdown('<div class="section-title"><h3>Recomendaciones</h3><small>Según los resultados</small></div>',unsafe_allow_html=True)
                for i,(title,text) in enumerate(recomendaciones(raw,current,config),1):
                    st.markdown(f'<div class="rec"><div class="rec-index">{i:02}</div><div><div class="rec-title">{title}</div><p>{escape(text)}</p></div></div>',unsafe_allow_html=True)
        st.write('')
        left,right=st.columns([1.48,1],gap='medium')
        with left:
            with st.container(border=True):
                st.markdown('<div class="section-title"><h3>Demanda vs. competencia</h3><small>La zona verde es el objetivo</small></div>',unsafe_allow_html=True)
                allpoints=st.toggle('Mostrar todas las carreras',value=True,key=f'todas_{tab_key}')
                st.plotly_chart(market_chart(allpoints),width='stretch',config={'displayModeBar':False},key=f'quadrants_{tab_key}')
                st.caption(f"Zona verde: búsquedas ≥{config.umbral_busquedas:.0f}% de {reference_name} y hasta {config.umbral_competidores:g} competidores. Puntos coincidentes se agrupan en el detalle al pasar el cursor.")
        with right:
            with st.container(border=True):
                st.markdown('<div class="section-title"><h3>Cómo se forma el resultado</h3></div><div class="caption">Puntaje de cada bloque × su peso en el modelo.</div>',unsafe_allow_html=True)
                contribution=pd.DataFrame({'Dimensión':BLOQUES,'Puntaje':[f'{x:.1f}' for x in current['bloques']],'Peso':[f'{x}%' for x in weights],'Aporte':[round(x*p/100,2) for x,p in zip(current['bloques'],weights)]})
                st.dataframe(contribution,hide_index=True,width='stretch',column_config={'Aporte':st.column_config.NumberColumn(format='%.2f')})
                st.metric('Índice ponderado',f"{current['total']:.2f} / 100")
        st.write('')
        price_fig=crear_grafico_precio(selected,level,precio_udla=raw.get('precio_udla'))
        # El resumen se deriva de las curvas visibles, sin depender de layout.meta.
        curves={trace.name:trace for trace in price_fig.data}
        price_points=curves['Barato'].x
        low,_=cruce_lineal(price_points,curves['Demasiado barato'].y,[100-y for y in curves['Barato'].y])
        high,_=cruce_lineal(price_points,curves['Demasiado caro'].y,[100-y for y in curves['Caro'].y])
        if not any(shape.type=='rect' and shape.x0==low and shape.x1==high for shape in (price_fig.layout.shapes or [])):
            price_fig.add_vrect(x0=low,x1=high,fillcolor='rgba(0,114,188,.075)',line_width=0,layer='below')
            for limit in [low,high]:
                price_fig.add_shape(type='line',x0=limit,x1=limit,y0=0,y1=100,line=dict(color='#8396a8',width=1.3,dash='dash'),layer='below')
        own_price=raw.get('precio_udla')
        price_position='Por debajo del rango' if own_price is not None and own_price<low else 'Por encima del rango' if own_price is not None and own_price>high else 'Dentro del rango' if own_price is not None else 'Sin precio disponible'
        own_label=f'${own_price:,.0f}' if own_price is not None else '—'
        with st.container(border=True):
            st.markdown(f'<div class="price-report-header"><div><div class="eyebrow">VAN WESTENDORP · ESCENARIO SIMULADO</div><h3>Sensibilidad de precio</h3></div><div class="price-report-program"><small>PROGRAMA EVALUADO</small><b>{escape(selected)}</b></div></div><div class="price-summary"><div><small>Rango orientativo · simulado</small><strong>${low:,.0f} — ${high:,.0f}</strong></div><div class="udla"><small>UDLA · precio base de pregrado</small><strong>{own_label}</strong></div><div class="position"><small>Posición frente a la simulación</small><strong>{price_position}</strong></div></div>',unsafe_allow_html=True)
            st.plotly_chart(price_fig,width='stretch',theme=None,config={'displayModeBar':False},key=f'precios_simulados_{tab_key}')
            st.markdown('<div class="price-report-note">Curvas y rango ilustrativos, fuera del índice de viabilidad. Línea roja: precio UDLA de pregrado del archivo entregado. La simulación no estima matrícula ni garantiza llenar una cohorte.</div>',unsafe_allow_html=True)
        with st.expander('Ver indicadores y valores originales'):
            st.caption('Alineación con el mercado laboral: el dato denominado «Brecha Mercado Laboral vs Programa Educativo» en la fuente mide coincidencia de competencias. Mayor porcentaje significa mayor alineación y mejor puntaje; no se invierte.')
            rawvals=[raw['matriculados'],raw['titulados'],raw['busquedas'],raw['nombre'],raw['alineacion'],raw['salario'],raw['competidores'],raw['brecha_precio'],raw['ventas_naturales']+raw['ventas_sociedades'],raw['profesionales']]
            refvals=[reference['matriculados'],reference['titulados'],reference['busquedas'],reference['nombre'],reference['alineacion'],reference['salario'],reference['competidores'],reference['brecha_precio'],reference['ventas_naturales']+reference['ventas_sociedades'],reference['profesionales']]
            def formatraw(i,x):
                if x is None:return 'Ver cuadrante'
                if i in [0,1,4,7]:return f'{x:.2%}'
                return f'{x:,.2f}'
            variable_weights=[weights[0]*.35*.6,weights[0]*.35*.4,weights[0]*.65*.7,weights[0]*.65*.3,weights[1]*.45,weights[1]*.25,weights[2],weights[3],weights[4],weights[1]*.3]
            st.dataframe(pd.DataFrame({'Indicador':VARIABLES,'Programa':[formatraw(i,v) for i,v in enumerate(rawvals)],'Referencia para el cálculo':['Referencia contra sí misma: 100' if current['es_referencia'] else f'Límite: {competitor_limit} competidores' if i==6 else 'Media del mercado: rango −15% a +10%' if i==7 else formatraw(i,v) for i,v in enumerate(refvals)],'Índice aplicado (máx. 100)':[round(v,2) for v in current['indices']],'Peso máximo (puntos)':[round(v,2) for v in variable_weights],'Aporte al total':[round(v*p/100,2) for v,p in zip(current['indices'],variable_weights)]}),hide_index=True,width='stretch')
            st.caption(f'En los demás indicadores la referencia es {reference_name}. Solo competencia y precio utilizan reglas propias, sin comparación con la carrera base.')
            st.caption('Dato informativo, sin peso en el índice: vacantes. Un cero o un dato faltante aquí no reduce el puntaje. Profesionales sí participa en empleabilidad.')
            st.dataframe(pd.DataFrame({'Dato informativo':['Vacantes'],'Programa':[raw.get('vacantes')],reference_name:[reference.get('vacantes')]}),hide_index=True,width='stretch')

    if globals().get('APARTADO_INTEGRADO')=='Carreras':
        from integracion_viabilidad import render_evidencia_compartida
        render_evidencia_compartida(selected,tab_key)

    with st.expander('Comparar las 12 carreras',expanded=False):
        st.write('')
        st.subheader('Un mismo punto de partida para todos')
        st.caption(f'{reference_name} es la referencia fija de esta pestaña. Las clasificaciones describen brechas comparativas; no son una autorización de apertura.')
        ranking=pd.DataFrame([{'Carrera':r['carrera'],'Índice':round(r['total'],2),'Lectura':r['clasificacion'],'Cuadrante':r['cuadrante'],**{label:round(val,2) for label,val in zip(BLOQUES,r['bloques'])}} for r in results]).sort_values('Índice',ascending=False)
        fig=go.Figure(go.Bar(x=ranking['Índice'].tolist()[::-1],y=ranking['Carrera'].tolist()[::-1],orientation='h',marker_color=['#0072bc' if name==selected else '#153954' if name==reference['carrera'] else '#c8dce9' for name in ranking['Carrera'].tolist()[::-1]],text=[f'{x:.1f}' for x in ranking['Índice'].tolist()[::-1]],textposition='outside',hovertemplate='%{y}<br>Índice: %{x:.2f} /100<extra></extra>'))
        fig.update_layout(height=490,margin=dict(l=10,r=40,t=10,b=20),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(color='#60758b'),xaxis=dict(range=[0,108],gridcolor='#e4ebf1',title='Índice comparativo'),yaxis=dict(automargin=True))
        st.plotly_chart(fig,width='stretch',config={'displayModeBar':False},key=f'ranking_{tab_key}')
        st.dataframe(ranking,hide_index=True,width='stretch',column_config={'Índice':st.column_config.ProgressColumn(min_value=0,max_value=100,format='%.2f')})
        st.download_button('Descargar comparativo · CSV',ranking.assign(Nivel=level).to_csv(index=False).encode('utf-8-sig'),f'comparativo_{tab_key}_{level.lower()}.csv','text/csv',key=f'csv_{tab_key}')

    with st.expander('Reglas del modelo',expanded=False):
        st.write('')
        st.subheader('Reglas acordadas, a la vista')
        st.markdown(f'**Nivel de evaluación: {level}.** Competencia permite hasta5 competidores en pregrado y hasta3 en posgrado. La regla es inclusiva y se aplica también al corte del cuadrante.')
        st.markdown(f'**Carrera de referencia:** {reference_name}. Contra sí misma obtiene siempre100 por definición: completa el aporte de todas las variables. Para las demás carreras, competencia usa el límite por nivel y precio el rango acordado frente al mercado. Cada variable aporta como máximo su peso; bloques y total quedan entre0 y100.')
        col1,col2=st.columns(2)
        with col1:
            st.markdown('**Regla de tres**')
            st.latex(r'\text{Aporte}=\min\left(\text{peso},\frac{\text{valor del programa}}{\text{valor de referencia}}\times\text{peso}\right)')
            st.markdown(f'Ejemplo con los pesos originales: búsquedas pesa13,65 puntos. Una carrera con80% de las búsquedas de {reference_name} aporta10,92 puntos; con120% aporta el máximo de13,65. Competencia se evalúa contra el límite aceptable, sin compararla con la carrera base. Los aportes mostrados usan los pesos activos.')
            st.markdown('Para matrícula y titulados se comparan **factores de crecimiento (1 + tasa)**. Así podemos evaluar caídas sin dividir tasas negativas. Las vacantes son exclusivamente informativas; la cantidad de profesionales sí entra al cálculo como indicador de tamaño del campo, donde más es mejor.')
            st.markdown('**Subpesos de demanda:** nombre65% (búsquedas70%, rúbrica30%); educativa35% (matriculados60%, titulados40%). **Empleabilidad:** profesionales30%, alineación45% y salario25%. El bloque conserva22% global: aportes máximos de6,60,9,90 y5,50 puntos respectivamente.')
            st.markdown(f'**Alineación con el mercado laboral:** mayor es mejor. Puntaje = mínimo entre100 y (alineación del programa / alineación de {reference_name} ×100). La alineación base es {reference["alineacion"]:.0%}. Su aporte total máximo con los pesos originales es9,90 puntos.')
            st.markdown(f'**Profesionales:** aporte = mínimo entre6,60 y (profesionales del programa / {reference["profesionales"]:,.0f} profesionales de {reference_name} ×6,60). Mide tamaño del campo, sin interpretarse como una tasa de empleabilidad. Más profesionales permite completar el aporte, sin exceder su peso.')
        with col2:
            st.markdown('**Precio frente a la media**')
            st.dataframe(pd.DataFrame({'Posición de precio':['25% más barato','20% más barato','−15% a +10%','15% más caro','20% más caro','25% más caro'],'Puntaje':[50,75,100,83.33,66.67,50]}),hide_index=True,width='stretch')
            st.caption('Por debajo del rango se restan 5 puntos por punto porcentual; por encima, 3,33. Mínimo 0. Este bloque mide posicionamiento de precio, sin estimar capacidad de pago ni rentabilidad.')
        st.markdown('**Competencia · 28% del modelo**')
        st.markdown(f'**Hasta {competitor_limit} competidores, inclusive:**100 puntos. **Por encima:** {competitor_limit} / competidores ×100. El aporte máximo al total es el peso activo del bloque (28 puntos con los pesos originales). Con cero competidores se asigna100, sin dividir por cero. La misma regla se aplica a la carrera base.')
        st.markdown('**Oportunidad de mercado · diagnóstico visual, sin peso adicional**')
        st.dataframe(pd.DataFrame({'Cuadrante':['Mercado atractivo','Mercado competido','Baja tracción','Mercado débil'],'Búsquedas':[f'≥{search_limit}%',f'≥{search_limit}%',f'<{search_limit}%',f'<{search_limit}%'],'Competidores':[f'≤{competitor_limit}',f'>{competitor_limit}',f'≤{competitor_limit}',f'>{competitor_limit}']}),hide_index=True,width='stretch')
        st.caption('El cuadrante no añade un puntaje propio. El umbral de búsquedas modifica la clasificación visual y el límite de competidores modifica el bloque competitivo de las carreras evaluadas. La referencia contra sí misma conserva100 por definición; su posición en el cuadrante refleja sus datos reales.')
        st.markdown('**Lectura provisional del total:**100 puntaje máximo;90–<100 puntaje alto;75–<90 resultado intermedio;60–<75 requiere ajustes;<60 puntaje bajo. Son rangos iniciales, no una autorización de apertura. Revisar las dimensiones débiles incluso si el promedio es favorable.')
        st.markdown('**Alcance de los datos:** se usa la tabla principal del archivo entregado, con búsquedas locales y sin palabras clave. Para precio se conserva la brecha por carrera de esa tabla. El sector económico suma ventas de personas naturales y sociedades de 36 meses: mide tamaño, no crecimiento.')
        st.caption('Las búsquedas aportan puntos solo en demanda. Su uso en el cuadrante es informativo. Profesionales sí entra al cálculo; vacantes y palabras clave no. Los pesos siguen siendo de criterio y requieren validación con casos de desempeño diverso.')
        st.download_button('Descargar datos del tablero · JSON',json.dumps(data,ensure_ascii=False,indent=2),'datos_programas.json','application/json',key=f'json_{tab_key}')


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
    import edcos_vista
    importlib.reload(edcos_vista).render_edcos()
else:
    programas=cargar_datos()
    reference_tabs=st.tabs([f'Referencia: {p["carrera"]}' for p in programas])
    for index,(tab,reference) in enumerate(zip(reference_tabs,programas)):
        tab_key='negocios' if index==0 else 'software' if reference['carrera']=='Software' else f'referencia_{index}'
        with tab:
            render_dashboard(reference,tab_key)

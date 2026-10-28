"""Navegación y evidencia agregada compartida entre los módulos del observatorio."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import runpy
import sys
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT=Path(__file__).resolve().parent


def ejecutar_viabilidad(apartado):
    """Mantiene ejecutable el tablero original y evita depender del directorio actual."""
    folder=ROOT/'viabilidad'
    previous=sys.path.copy()
    try:
        sys.path.insert(0,str(folder))
        runpy.run_path(str(folder/'app.py'),init_globals={'APARTADO_INTEGRADO':apartado},run_name='__main__')
    finally:
        sys.path[:]=previous


def resumen_compartido(summary,selected,level,demo):
    columns=['year','cutoff','graduates','employed','rate','dependent','independent','unknown','p25','p75','salary_n','academic_cutoff']
    records=summary[[c for c in columns if c in summary]].copy()
    # La frontera entre módulos contiene exclusivamente agregados, nunca personas/RUC.
    records=records.astype(object).where(pd.notna(records),None)
    return dict(carreras=sorted(selected),nivel=level,demostracion=bool(demo),
        fecha_consulta=datetime.now(ZoneInfo('America/Guayaquil')).date().isoformat(),
        empleo=records.to_dict('records'))


def compartir_empleo(summary,selected,level,demo):
    old=st.session_state.get('mercado_compartido',{})
    new=resumen_compartido(summary,selected,level,demo)
    same=all(old.get(k)==new[k] for k in ('carreras','nivel','demostracion'))
    if same and old.get('sector'):
        new['sector']=old['sector']
    st.session_state['mercado_compartido']=new


def compartir_industrias(catalog,monthly,codes,matched,total):
    context=st.session_state.get('mercado_compartido')
    if not context:return
    # Ventas mensuales ya deduplicadas por CIIU por industry.monthly_sales.
    rows=monthly[[c for c in ['Año','Mes','Personas naturales','Sociedades','Ventas totales'] if c in monthly]].copy()
    rows=rows.astype(object).where(pd.notna(rows),None)
    context['sector']=dict(ciiu=catalog.loc[catalog.CIIU.isin(codes),['CIIU','Industria','Graduados']].to_dict('records'),
        ventas=rows.to_dict('records'),graduados_con_ciiu=int(matched),graduados_con_empleador=int(total),corte_laboral='2026-01-31')
    st.session_state['mercado_compartido']=context


def render_evidencia_compartida(carrera,tab_key):
    with st.container(border=True):
        st.markdown('### Empleabilidad y sectores vinculados')
        current=st.session_state.get('mercado_compartido')
        linked=st.session_state.get('evidencia_por_carrera',{}).get(carrera)
        if current:
            selection=' · '.join(current['carreras'])
            st.caption('Selección consultada en Empleabilidad: '+selection+' · '+current['nivel'])
            if st.button('Vincular esta selección a '+carrera,key='vincular_mercado_'+tab_key):
                links=deepcopy(st.session_state.get('evidencia_por_carrera',{}))
                links[carrera]=deepcopy(current)
                st.session_state['evidencia_por_carrera']=links
                linked=links[carrera]
        if not linked:
            st.info('Consulta las carreras homologadas en Empleabilidad y mercado y vincula esa selección aquí para ver su empleo y ventas SRI.')
            return
        if linked['demostracion']:
            st.warning('Evidencia de demostración: datos sintéticos, fuera del cálculo de viabilidad.')
        st.caption('Carreras institucionales: '+' · '.join(linked['carreras'])+' · consulta '+linked['fecha_consulta'])
        frame=pd.DataFrame(linked['empleo'])
        latest=frame.sort_values('year').iloc[-1]
        a,b,c=st.columns(3)
        a.metric('Graduados al corte laboral',f"{latest['graduates']:,.0f}")
        b.metric('Graduados con empleo visible',f"{latest['employed']:,.0f}")
        c.metric('Empleo visible',f"{latest['rate']:.1f}%" if pd.notna(latest['rate']) else 'Sin dato')
        st.caption('Corte laboral: '+str(latest['cutoff'])+'. Empleo visible no implica afinidad ocupacional con la carrera.')
        sector=linked.get('sector')
        if sector and sector['ventas']:
            values=pd.DataFrame(sector['ventas'])
            values['Fecha']=pd.to_datetime(dict(year=values['Año'],month=values['Mes'],day=1))
            values=values.sort_values('Fecha')
            fig=go.Figure()
            for col,color in [('Personas naturales','#3975b9'),('Sociedades','#91bbdf')]:
                fig.add_trace(go.Scatter(x=values['Fecha'],y=values[col],name=col,mode='lines+markers',line=dict(color=color,width=2.5),connectgaps=False))
            fig.update_layout(height=350,paper_bgcolor='white',plot_bgcolor='white',margin=dict(l=85,r=25,t=15,b=65),font=dict(color='#60758b'),legend=dict(orientation='h',y=-.25))
            fig.update_xaxes(title='Mes',gridcolor='#edf2f7')
            fig.update_yaxes(title=dict(text='Ventas sectoriales · USD',standoff=20),automargin=True,gridcolor='#edf2f7')
            st.plotly_chart(fig,width='stretch',theme=None,key='sector_compartido_'+tab_key)
            st.caption('Ventas del conjunto de los CIIU seleccionados, no únicamente de los empleadores de los graduados. Último mes: '+values['Fecha'].max().strftime('%Y-%m')+'.')
            with st.expander('Sectores y cobertura del cruce'):
                st.dataframe(pd.DataFrame(sector['ciiu']),hide_index=True,width='stretch')
                st.caption(f"{sector['graduados_con_ciiu']:,} graduados con CIIU de {sector['graduados_con_empleador']:,} con empleador identificado.")
        else:
            st.info('Abre Industrias y ventas SRI para incorporar también el cruce sectorial de esta selección.')
        st.caption('Esta evidencia complementa el diagnóstico. El índice conserva los datos y reglas guardados; no convierte automáticamente inserción laboral en alineación ni crecimiento de ventas en puntaje.')

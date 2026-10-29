"""Navegación y evidencia agregada compartida entre los módulos del observatorio."""
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
    if same:
        for key in ('sector','territorio'):
            if old.get(key):new[key]=old[key]
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


def compartir_territorio(nombre,resumen,corte):
    context=st.session_state.get('mercado_compartido')
    if context is not None:
        context['territorio']=dict(nombre=nombre,resumen=resumen,corte=corte)
        st.session_state['mercado_compartido']=context


def principales_empresas(jobs):
    """Agrega por empleador, sin compartir identificadores personales ni RUC."""
    if jobs.empty or not {'person','RUCEMP','NOMEMP'}<=set(jobs.columns):return []
    from industry import ruc
    data=jobs.copy()
    data['RUCEMP']=data.RUCEMP.map(ruc)
    data=data.dropna(subset=['person','RUCEMP'])
    denominator=data.person.nunique()
    if not denominator:return []
    data['NOMEMP']=data.NOMEMP.fillna('').astype(str).str.strip()
    result=data.groupby('RUCEMP').agg(Empresa=('NOMEMP',lambda s:next((x for x in s if x),'Empresa sin nombre')),
        Graduados=('person','nunique')).reset_index(drop=True)
    result['Participación (%)']=100*result.Graduados/denominator
    return result.sort_values(['Graduados','Empresa'],ascending=[False,True]).head(5).to_dict('records')


def compartir_perfil_sector(macro,jobs,year,month):
    context=st.session_state.get('mercado_compartido')
    if context and context.get('sector'):
        context['sector']['macroindustrias']=macro.astype(object).where(pd.notna(macro),None).to_dict('records')
        context['sector']['periodo_macro']=f'enero–mes {month:02d} de {year}'
        context['sector']['empresas']=principales_empresas(jobs)
        st.session_state['mercado_compartido']=context


def render_evidencia_compartida(carrera,tab_key):
    with st.container(border=True):
        st.markdown('### Empleabilidad y sectores vinculados')
        current=st.session_state.get('mercado_compartido')
        # El perfil sigue la selección vigente de Empleabilidad, sin copiarla
        # bajo nombres de otras carreras del modelo comparativo.
        linked=current
        if current:
            selection=' · '.join(current['carreras'])
            st.caption('Selección consultada en Empleabilidad: '+selection+' · '+current['nivel'])
        else:
            from consulta_perfil_carrera import render_consulta
            render_consulta(carrera,tab_key)
            linked=st.session_state.get('evidencia_por_carrera',{}).get(carrera)
        if not linked:
            st.caption('Selecciona una carrera en Empleabilidad y mercado para mostrar su perfil automáticamente, o consulta los datos aquí.')
            return
        if linked['demostracion']:
            st.warning('Evidencia de demostración: datos sintéticos, fuera del cálculo de viabilidad.')
        st.caption('Carreras institucionales: '+' · '.join(linked['carreras'])+' · consulta '+linked['fecha_consulta'])
        for note in linked.get('notas_consulta',[]):
            st.warning(note)
        from perfil_laboral_viabilidad import render_perfil
        render_perfil(linked,tab_key)
        sector=linked.get('sector')
        if sector and sector['ventas']:
            values=pd.DataFrame(sector['ventas'])
            values['Fecha']=pd.to_datetime(dict(year=values['Año'],month=values['Mes'],day=1))
            values=values.sort_values('Fecha')
            mode=st.radio('Vista de ventas',['Evolución mensual','Acumulado anual comparable'],horizontal=True,key='vista_ventas_'+tab_key)
            chart_values=values
            axis='Fecha'
            if mode=='Acumulado anual comparable':
                cutoff=int(values.groupby('Año')['Mes'].max().min())
                month=st.slider('Acumular hasta el mes',1,cutoff,cutoff,key='mes_ventas_'+tab_key) if cutoff>1 else 1
                chart_values=acumulado_comparable(values,month)
                axis='Año'
                st.caption(f'Acumulado enero–mes {month:02d}, con los mismos meses en cada año.')
            fig=go.Figure()
            from palettes import PALETTES, theme_figure
            palette=st.session_state.get('color_palette','Azul')
            primary,light,_=PALETTES[palette]
            for col,color in [('Personas naturales',primary),('Sociedades',light)]:
                fig.add_trace(go.Scatter(x=chart_values[axis],y=chart_values[col],name=col,mode='lines+markers',line=dict(color=color,width=2.5),connectgaps=False))
            fig.update_layout(height=350,paper_bgcolor='white',plot_bgcolor='white',margin=dict(l=85,r=25,t=15,b=65),font=dict(color='#60758b'),legend=dict(orientation='h',y=-.25))
            fig.update_xaxes(title='Mes' if axis=='Fecha' else 'Año',gridcolor='#edf2f7')
            if axis=='Año':fig.update_xaxes(type='category')
            fig.update_yaxes(title=dict(text='Ventas sectoriales · USD',standoff=20),automargin=True,gridcolor='#edf2f7')
            st.plotly_chart(theme_figure(fig,palette),width='stretch',theme=None,key='sector_compartido_'+tab_key)
            with st.expander('Sectores y cobertura del cruce'):
                st.dataframe(pd.DataFrame(sector['ciiu']),hide_index=True,width='stretch')
                st.caption(f"{sector['graduados_con_ciiu']:,} graduados con CIIU de {sector['graduados_con_empleador']:,} con empleador identificado.")
        else:
            st.info('Abre Industrias y ventas SRI para incorporar también el cruce sectorial de esta selección.')
        st.caption('Esta evidencia complementa el diagnóstico. El índice conserva los datos y reglas guardados; no convierte automáticamente inserción laboral en alineación ni crecimiento de ventas en puntaje.')


def acumulado_comparable(values,month):
    """Un mes o importe ausente deja el acumulado sin dato, nunca en cero."""
    rows=[]
    for year,data in values.groupby('Año'):
        selected=data[data.Mes.le(month)]
        complete=len(selected)==month and set(selected.Mes)==set(range(1,month+1))
        row={'Año':str(year)}
        for field in ('Personas naturales','Sociedades'):
            row[field]=selected[field].sum() if complete and selected[field].notna().all() else None
        rows.append(row)
    return pd.DataFrame(rows)

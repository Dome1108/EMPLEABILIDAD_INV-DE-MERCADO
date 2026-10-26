"""Graduados y participación por empleador SIM, con ranking como complemento."""
from pathlib import Path
import importlib
from textwrap import wrap

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import company_ranking as ranking_module
if getattr(ranking_module,'MATCH_VERSION',None)!=4:
    ranking_module=importlib.reload(ranking_module)
from company_ranking import read_ranking, prepare_ranking, ranking_summary, match_sim_companies, graduate_distribution
from palettes import PALETTES, theme_figure

COMPANY_VIEW_VERSION = 4


@st.cache_data(ttl=900,show_spinner=False,max_entries=2)
def cached_ranking(path,stamp):
    return read_ranking(path)


def render(codes,palette,demo=False,jobs=None,mapping=None):
    st.markdown('### Empresas donde trabajan los graduados')
    ranking=pd.DataFrame(columns=['year','company_id','company','CIIU','activity','employees','macroindustry'])
    quality={}
    try:
        if demo:
            demo_codes=list(mapping.CIIU.unique()) if mapping is not None else codes
            raw=pd.DataFrame([{'Año':2025,'Expediente':f'{i}-{j}', 'Nombre':f'Empresa de ejemplo {i+1}.{j+1}',
                               'Actividad económica':code,'Cant. Empleados':(i+1)*100+(j+1)*30}
                              for i,code in enumerate(demo_codes) for j in range(3)])
            # Usar expedientes numéricos como en la fuente real.
            raw['Expediente']=[str(i+1) for i in range(len(raw))]
            ranking,quality=prepare_ranking(raw)
        else:
            default=Path(__file__).resolve().parent/'data'/'ranking_2025.xlsx'
            with st.expander('Fuente del ranking de empresas'):
                path=st.text_input('Archivo ranking 2025 (Excel)',str(default),key='ranking_path')
                if st.button('Actualizar ranking de empresas',key='ranking_refresh'):
                    cached_ranking.clear()
            if not Path(path).is_file():
                st.info('El ranking no está disponible. El gráfico de graduados usa los registros laborales; agrega el archivo para consultar el tamaño total de las empresas.')
            else:
                try:
                    with st.spinner('Leyendo empresas y empleados del ranking 2025…'):
                        ranking,quality=cached_ranking(path,Path(path).stat().st_mtime_ns)
                except Exception as exc:
                    st.warning('No se pudo leer el ranking. El gráfico de graduados sigue disponible con los registros laborales.')
                    with st.expander('Detalle de la fuente complementaria'):
                        st.code(str(exc))
        if jobs is None or mapping is None:
            st.info('Se necesitan los empleadores y sus nombres para realizar este cruce.')
            return
        matches,match_quality=match_sim_companies(jobs,ranking,2025)
        companies,_,_,graduates_total=graduate_distribution(jobs,mapping,matches)
        if not graduates_total:
            st.info('No hay graduados con empresa identificada para esta selección.')
            return
        found=matches[matches.company_id.notna()]
        selected=ranking[ranking.company_id.isin(found.company_id)&ranking.year.eq(2025)].copy()
        selected['sim_graduates']=selected.company_id.map(found.set_index('company_id').sim_graduates)
        selected['SIM_company']=selected.company_id.map(found.set_index('company_id').SIM_company)
        selected,by_code,by_macro=ranking_summary(selected,selected.CIIU.unique(),2025)
        known=int(selected.employees.notna().sum())
        total=selected.employees.sum(min_count=1)
        fmt=lambda n:f'{int(n):,}'.replace(',','.')
        a,b,c=st.columns(3)
        a.metric('Graduados empleados con empresa identificada',fmt(graduates_total))
        b.metric('Empresas empleadoras',fmt(len(companies)))
        c.metric('Empresas identificadas en ranking',fmt(len(selected)))
        st.caption('Eje X: graduados únicos de las carreras seleccionadas que trabajan en cada empresa. La etiqueta muestra su participación sobre todos los graduados empleados con empresa identificada, incluidos los que no coinciden con el ranking. El top 10 no cambia ese denominador. Una persona puede trabajar en varias empresas; por eso las participaciones pueden sumar más de 100 %.')
        audit=matches.rename(columns={'SIM_RUC':'RUC del empleador','SIM_company':'Nombre del empleador','company':'Nombre en ranking',
            'sim_graduates':'Graduados','company_id':'Expediente ranking','employees':'Empleados ranking 2025',
            'activity':'Actividad ranking','match_status':'Estado del cruce','year':'Año ranking'})
        fields=['RUC del empleador','Nombre del empleador','Nombre en ranking','Estado del cruce','Graduados',
                'Expediente ranking','CIIU','Actividad ranking','Empleados ranking 2025']
        with st.expander('Ver coincidencias, empresas sin dato y casos para revisión',expanded=selected.empty):
            st.dataframe(audit[fields],hide_index=True,width='stretch')
            st.download_button('Descargar revisión del cruce de empresas',audit[fields].to_csv(index=False,sep=';').encode('utf-8-sig'),
                file_name=f"cruce_empresas_ranking{'_DEMO' if demo else ''}.csv",mime='text/csv',key='ranking_match_download')
            st.caption('Se normalizan tildes, mayúsculas, espacios, puntuación y formas jurídicas equivalentes. No se asignan empleados por similitud aproximada. Nombres con varios expedientes o un expediente asociado a varios RUC quedan pendientes de revisión.')
        if selected.empty:
            st.caption('No hay coincidencias unívocas con el ranking 2025. Las empresas permanecen en el gráfico de graduados.')
        blue=PALETTES[palette][0]
        data=companies.rename(columns={'SIM_company':'label'})
        title='Top 10 empresas por graduados'
        key='ranking_companies'
        top=data.sort_values(['sim_graduates','label'],ascending=[False,True]).head(10).iloc[::-1]
        labels=['<br>'.join(wrap(name if len(name)<=70 else name[:67]+'…',35)) for name in top.label]
        fig=go.Figure(go.Bar(x=top.sim_graduates.tolist(),y=list(range(len(top))),orientation='h',marker_color=blue,
            text=[f'{value:.1f} %'.replace('.',',') for value in top.share],textposition='outside',cliponaxis=False,
            customdata=list(zip(top.label,top.share)),
            hovertemplate='%{customdata[0]}<br>%{x:,.0f} graduados<br>Participación: %{customdata[1]:.2f} %<extra></extra>'))
        fig.update_layout(title=title,height=570,margin=dict(l=10,r=70,t=65,b=45),
            xaxis=dict(title='Cantidad de graduados',rangemode='tozero',range=[0,max(top.sim_graduates.max()*1.2,1)],tickformat=',.0f'),
            yaxis=dict(tickmode='array',tickvals=list(range(len(top))),
            ticktext=labels,automargin=True),paper_bgcolor='white',plot_bgcolor='white')
        st.plotly_chart(theme_figure(fig,palette),width='stretch',key=key)
        with st.expander('Ver graduados y participación por empresa'):
            graduates_export=companies.rename(columns={'SIM_RUC':'RUC del empleador','SIM_company':'Empresa',
                'macroindustry':'Macroindustria','sim_graduates':'Graduados','share':'Participación (%)'})
            st.dataframe(graduates_export.sort_values('Graduados',ascending=False),hide_index=True,width='stretch')
            st.download_button('Descargar graduados por empresa',graduates_export.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),
                file_name=f"graduados_por_empresa{'_DEMO' if demo else ''}.csv",mime='text/csv',key='ranking_graduates_download')
        with st.expander('Ver empleados por actividad económica y empresas'):
            st.caption('Dato complementario: tamaño total reportado por las empresas en el ranking 2025. El gráfico principal usa la cantidad de graduados empleados.')
            st.metric('Empleados reportados',fmt(total) if pd.notna(total) else 'Sin dato')
            st.caption(f'Empresas coincidentes con dato de empleados: {known}/{len(selected)}.')
            display=by_code.rename(columns={'companies':'Empresas','companies_with_employees':'Empresas con dato',
                                           'employees':'Empleados reportados'})
            st.dataframe(display.sort_values('Empleados reportados',ascending=False),hide_index=True,width='stretch')
            detail=selected[['company_id','SIM_company','company','CIIU','activity','sim_graduates','employees','year']].rename(columns={
                'company_id':'Expediente','company':'Empresa','activity':'Actividad económica',
                'SIM_company':'Nombre del empleador','sim_graduates':'Graduados','employees':'Empleados reportados','year':'Año'})
            st.dataframe(detail.sort_values('Empleados reportados',ascending=False),hide_index=True,width='stretch')
            st.download_button('Descargar empresas y empleados · 2025',detail.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),
                file_name=f"empresas_empleados_2025{'_DEMO' if demo else ''}.csv",mime='text/csv',key='ranking_download')
        with st.expander('Calidad del ranking'):
            st.json({'Ranking':quality,'Cruce de empleadores':{'Empresas':match_quality['sim_companies'],
                'Coincidencias':match_quality['matched'],'Ambiguas':match_quality['ambiguous'],'Filas con RUC inválido':match_quality['invalid_ruc_rows']}})
            st.caption('El RUC identifica a cada empleador; el Excel no contiene RUC, por lo que se enlaza por nombre. Cada expediente se suma una vez. Los datos de empleados corresponden al ranking 2025 y no representan personas únicas entre empresas.')
    except Exception as exc:
        st.warning('No se pudo leer el ranking de empresas; los demás indicadores siguen disponibles.')
        with st.expander('Detalle del ranking'):
            st.code(str(exc))

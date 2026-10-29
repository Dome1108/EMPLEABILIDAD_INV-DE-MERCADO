"""Consulta institucional del perfil sin salir de Viabilidad de carreras."""
from pathlib import Path
import streamlit as st


@st.cache_data(ttl=900,show_spinner=False)
def catalogo(config):
    from data_access import career_catalog
    return career_catalog(config)


def consultar(config,selected,level,catalog):
    from analytics import calculate,SNAPSHOTS
    from data_access import load,load_employers,load_atlas
    from integracion_viabilidad import resumen_compartido,principales_empresas
    from geography import locations,territorial_summary
    from industry import read_sources,match_employers,monthly_sales,macroindustry_summary
    import pandas as pd
    levels=tuple(sorted(catalog.loc[catalog.nivel.eq(level),'nivel_origen'].dropna().unique()))
    summary,_,cohorts,_=calculate(*load(config,tuple(selected),levels=levels))
    result=resumen_compartido(summary,selected,level,False)
    cohort=cohorts[SNAPSHOTS[-1].year]
    notes=[]
    try:
        atlas,_=locations(load_atlas(config,tuple(sorted(cohort.person.unique()))))
        located=cohort.merge(atlas,on='person',how='left',validate='one_to_one')
        if located.provincia.eq('PICHINCHA').any():
            result['territorio']=dict(nombre='PICHINCHA',resumen=territorial_summary(located,'PICHINCHA'),corte=str(SNAPSHOTS[-1].date.date()))
    except Exception as exc:
        notes.append('Distribución territorial no disponible: '+str(exc))
    try:
        root=Path(__file__).resolve().parent/'data'
        mapping,sales,_=read_sources(root/'validación.txt',root/'consulta_sri_1.xlsx')
        jobs=load_employers(config,tuple(sorted(cohort.loc[cohort.dependent,'person'].unique())))
        catalog,matched,total=match_employers(jobs,mapping)
        codes=catalog.CIIU.tolist()
        monthly=monthly_sales(sales,codes)
        sector=dict(ciiu=catalog[['CIIU','Industria','Graduados']].to_dict('records'),
            ventas=monthly[['Año','Mes','Personas naturales','Sociedades']].astype(object).where(pd.notna(monthly),None).to_dict('records'),
            graduados_con_ciiu=int(matched),graduados_con_empleador=int(total),
            corte_laboral=str(SNAPSHOTS[-1].date.date()),empresas=principales_empresas(jobs))
        if not monthly.empty:
            year=int(monthly['Año'].max());month=int(monthly.loc[monthly['Año'].eq(year),'Mes'].max())
            macro=macroindustry_summary(jobs,mapping,sales,codes,year,month)
            sector.update(macroindustrias=macro.astype(object).where(pd.notna(macro),None).to_dict('records'),periodo_macro=f'enero–mes {month:02d} de {year}')
        result['sector']=sector
    except Exception as exc:
        notes.append('Sectores y empresas no disponibles: '+str(exc))
    result['notas_consulta']=notes
    return result


def render_consulta(carrera,key):
    with st.expander('Consultar datos de esta carrera',expanded=False):
        st.caption('Consulta las fuentes institucionales desde aquí. Requiere acceso a la red de la universidad.')
        config={}
        try:config=dict(st.secrets.get('sql',{}))
        except FileNotFoundError:pass
        if st.button('Cargar catálogo de carreras',key='catalogo_perfil_'+key):
            try:
                with st.spinner('Consultando catálogo institucional…'):
                    st.session_state['catalogo_perfil']=catalogo(config)
            except Exception as exc:
                st.error('No se pudo consultar el catálogo institucional.')
                st.caption(str(exc))
        catalog=st.session_state.get('catalogo_perfil')
        if catalog is None:return
        levels=sorted(catalog.nivel.dropna().unique())
        if not levels:
            st.info('No hay niveles académicos disponibles.');return
        level=st.selectbox('Nivel académico del perfil',levels,key='nivel_perfil_'+key)
        options=sorted(catalog.loc[catalog.nivel.eq(level),'carrera'].unique())
        from analytics import institution_key
        defaults=[o for o in options if institution_key(o)==institution_key(carrera)]
        selected=st.multiselect('Carreras homologadas para este perfil',options,default=defaults,key='seleccion_perfil_'+key)
        if st.button('Consultar y mostrar perfil',disabled=not selected,key='consulta_perfil_'+key):
            try:
                with st.spinner('Consultando empleo, salarios y sectores…'):
                    result=consultar(config,selected,level,catalog)
                links=dict(st.session_state.get('evidencia_por_carrera',{}));links[carrera]=result
                st.session_state['evidencia_por_carrera']=links
            except Exception as exc:
                st.error('No se pudo completar la consulta laboral.');st.caption(str(exc))

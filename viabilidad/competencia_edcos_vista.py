"""Lectura ejecutiva de la comparación competitiva EdCo."""
from copy import deepcopy
from html import escape
import pandas as pd
import streamlit as st
from competencia_edcos import filas_contenidos,resumen_contenidos,grafico_contenidos,posicionamiento
from graficos_edcos import grafico_dimension
from datos_visuales_edcos import leer_evidencia,PLANTILLAS
from modelo_edcos import INSTITUCIONES_EDCO
from graficos_edcos import monedas_precio,moneda_precio


def render_competencia(ficha,source_links):
    institution=INSTITUCIONES_EDCO[ficha['institucion_id']]['nombre']
    data=ficha.get('comparativa_contenidos')
    if not data:
        st.info('Esta propuesta aún no tiene una comparación de contenidos documentada.')
        return
    with st.expander('Filtrar oferentes'):
        types=st.multiselect('Tipo de oferente',['Institucional','Plataforma','Oferta propia'],default=['Institucional','Plataforma','Oferta propia'],key='edco_comp_tipos')
        only_declared=st.checkbox('Solo referencias con inscripción declarada · conservar portafolio propio',value=False,key='edco_comp_inscripcion')
        st.caption('La vista inicial incluye referencias históricas. Las maestrías de otro nivel se conservan en Oferta y plataformas, fuera de esta comparación de educación continua.')
    rows=filas_contenidos(ficha,types,only_declared)
    summary=resumen_contenidos(ficha,rows)
    st.markdown('**¿Qué contenidos declara cada programa?**')
    st.markdown('<div class="legend"><span>✓ &nbsp; Declarado</span><span>· &nbsp; No identificado en la descripción</span></div>',unsafe_allow_html=True)
    st.plotly_chart(grafico_contenidos(ficha,rows),width='stretch',theme=None,config={'displayModeBar':False},key='edco_matriz_contenidos')
    st.caption('La primera fila es la propuesta de '+institution+'. Un tema no identificado no demuestra ausencia en el programa; la comparación se limita a las descripciones revisadas.')

    st.markdown('**Lectura ejecutiva**')
    if summary['total']:
        topics={t['id']:t['etiqueta'].replace('<br>',' ') for t in data['temas']}
        common=sorted(summary['conteos'],key=lambda k:-summary['conteos'][k])[:2]
        messages=[('Territorio compartido',', '.join(topics[k] for k in common)+' son los temas más presentes entre las descripciones externas revisadas.'),
                  ('Diferenciación por enfoque','La propuesta puede destacar la auditoría Neuro-UX y la jornada de laboratorio. Su menor presencia explícita en estas descripciones es una señal para contrastar, no una garantía de demanda.'),
                  ('Portafolio UDLA','La oferta actual ya declara herramientas biométricas. Delimitar el alcance de Neuro-UX y su aplicación digital ayuda a distinguir la nueva propuesta.')]
        if data.get('lectura_ejecutiva'):
            messages=[messages[0]]+[(item['titulo'],item['texto']) for item in data['lectura_ejecutiva']]
        # El portafolio se analiza sobre todas las referencias; no depende de ocultar su fila.
        cards=''.join(f'<article class="edco-pillar"><div class="edco-kicker">{escape(title)}</div><p>{escape(body)}</p></article>' for title,body in messages)
        st.markdown('<div class="edco-pillars">'+cards+'</div>',unsafe_allow_html=True)
        st.caption(f"Base de la lectura: {summary['total']} descripciones externas revisadas. La propuesta y la oferta propia no cuentan como competencia externa; varios programas de un mismo oferente no son instituciones distintas.")
    else:
        st.info('No hay descripciones externas verificadas con los filtros actuales.')

    with st.expander('Mapa de oferentes · precio frente a duración',expanded=True):
        map_ficha=deepcopy(ficha)
        currencies=monedas_precio(ficha)
        if len(currencies)>1:
            map_ficha['evidencia_visual']['precio']['moneda']=st.radio('Moneda del mapa',currencies,horizontal=True,key='edco_mapa_moneda')
        st.caption('Moneda del mapa: '+moneda_precio(map_ficha)+'. Los precios en otras monedas no se convierten.')
        chart,missing=posicionamiento(map_ficha,rows)
        st.plotly_chart(chart,width='stretch',theme=None,config={'displayModeBar':False},key='edco_mapa_oferentes')
        st.caption('Cada punto representa un programa con precio y horas publicados. Derecha: más horas; arriba: mayor precio total. Las horas pueden ser académicas, de dedicación o de vídeo: el mapa no las convierte ni estima calidad o precio óptimo. Las condiciones históricas se muestran al pasar el cursor.')
        st.caption('El programa propuesto no tiene precio ni horas totales informadas: no se le asigna un punto supuesto.')
        if missing:
            st.dataframe(pd.DataFrame(missing).rename(columns={'institucion':'Oferente','programa':'Programa','motivo':'Dato no publicado para ubicar el punto'}),hide_index=True,width='stretch')

    with st.expander('Contenido, criterios y fuentes de la comparación'):
        sources={s['id']:s for s in ficha['fuentes']}
        records=[]
        for row in rows:
            record={'Oferente':row['institucion'],'Programa':row['programa'],'Tipo':row['tipo'],'Disponibilidad':row.get('disponibilidad'),'Base documental':row['revision'].get('base'),'Fuente':sources[row['fuente']].get('url')}
            for topic in data['temas']:
                value=row['revision'].get('contenidos',{}).get(topic['id'])
                record[topic['etiqueta'].replace('<br>',' ')]='Declarado' if value is True else 'No identificado' if value is False else 'Sin verificar'
            records.append(record)
        table=pd.DataFrame(records)
        st.dataframe(table,hide_index=True,width='stretch',column_config={'Fuente':st.column_config.LinkColumn('Fuente')})
        st.download_button('Descargar comparación de contenidos · CSV',table.to_csv(index=False).encode('utf-8-sig'),'comparacion_contenidos_edco.csv','text/csv',key='edco_contenidos_csv')
        for topic in data['temas']:
            st.markdown(f"**{topic['etiqueta'].replace('<br>',' ')}:** {topic['criterio']}")
        for row in rows:
            st.markdown('**'+row['institucion']+' · '+row['programa']+'**')
            st.write(row['revision'].get('detalle','Descripción no verificable.'))
            source_links([row['fuente']])

    with st.expander('Demanda vs. competencia · complemento'):
        chart_ficha=deepcopy(ficha)
        evidence=chart_ficha['evidencia_visual']['competencia']
        st.caption('Esta matriz requiere búsquedas comparables. Sin esa serie, los contenidos y el mapa de oferentes son la lectura principal. Los cortes siguientes son exploratorios y no cambian el puntaje.')
        left,right=st.columns(2)
        with left:evidence['umbral_busquedas']=st.number_input('Corte visual de búsquedas',min_value=1,max_value=99,value=75,key='edco_matrix_x')
        with right:evidence['umbral_competidores']=st.number_input('Corte visual de competidores',min_value=1,max_value=100,value=3,key='edco_matrix_y')
        st.download_button('Estructura CSV de demanda y competencia',','.join(PLANTILLAS['competencia'])+'\n','edco_competencia.csv','text/csv',key='edco_template_competencia')
        upload=st.file_uploader('Importar evidencia CSV · Competencia',type=['csv'],key='edco_csv_competencia')
        if upload is not None:
            try:
                upload.seek(0)
                field,records=leer_evidencia(upload,'competencia',ficha['brief']['ciiu'])
            except (ValueError,TypeError,KeyError) as exc:st.error(str(exc))
            else:
                evidence[field]=records
                ficha['evidencia_visual']['competencia'][field]=records
        st.plotly_chart(grafico_dimension(chart_ficha,'competencia'),width='stretch',theme=None,config={'displayModeBar':False},key='edco_detalle_competencia')

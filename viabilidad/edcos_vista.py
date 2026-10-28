"""Apartado de educación continua, con brief y evidencia de mercado separados."""
from copy import deepcopy
from html import escape
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from modelo_edcos import DIMENSIONES_EDCO,INSTITUCIONES_EDCO,cargar_edcos,validar_ficha,programas_institucion
from graficos_edcos import radar_edco,grafico_dimension,ofertas_precio,monedas_precio,moneda_precio
from datos_visuales_edcos import PLANTILLAS,leer_evidencia
from edcos_presentacion import propuesta_html,participacion_html
from habilidades_edcos import resumir_habilidades
from competencia_edcos_vista import render_competencia


def render_edcos():
    css=Path(__file__).with_name('edcos_estilo.css').read_text(encoding='utf-8')
    st.markdown('<style>'+css+'</style>',unsafe_allow_html=True)
    fichas=cargar_edcos()
    st.markdown('<div class="header"><div><div class="eyebrow">EDUCACIÓN CONTINUA · VIABILIDAD DE NUEVAS PROPUESTAS</div><h1>Viabilidad Educación Continua</h1><p>Del brief del proponente a una evaluación con evidencia de mercado.</p></div><div class="stamp">Investigación inicial</div></div>',unsafe_allow_html=True)
    institution_col,program_col=st.columns([1,2])
    with institution_col:
        institution=st.selectbox('Institución y país',list(INSTITUCIONES_EDCO),format_func=lambda value:INSTITUCIONES_EDCO[value]['etiqueta'],key='edco_institucion')
    available=programas_institucion(fichas,institution)
    with program_col:
        if available:
            names=[f['nombre'] for f in available]
            if st.session_state.get('edco_programa') not in names:
                st.session_state.pop('edco_programa',None)
            choice=st.selectbox('Programa de educación continua',names,key='edco_programa')
        else:
            st.selectbox('Programa de educación continua',[],placeholder='Sin programas registrados',disabled=True,key='edco_programa_vacio')
    if not available:
        st.info('Aún no hay estudios registrados para '+INSTITUCIONES_EDCO[institution]['etiqueta']+'.')
        return
    saved=next(f for f in available if f['nombre']==choice)
    context=saved['id']+'@'+saved.get('version_investigacion','')
    if st.session_state.get('edco_contexto_programa')!=context:
        for widget_key in list(st.session_state):
            if widget_key.startswith('edco_') and widget_key not in ('edco_institucion','edco_programa','edco_contexto_programa') and not widget_key.startswith('edco_revision_'):
                st.session_state.pop(widget_key,None)
        st.session_state['edco_contexto_programa']=context
    ficha=deepcopy(saved)
    revision=st.session_state.get('edco_revision_'+saved['id'])
    if revision:
        # Conservar las valoraciones manuales, usando siempre la estructura actual
        # del brief y de las fuentes, sin recuperar campos eliminados de la sesión.
        for key in ficha['evaluacion']:
            if key in revision.get('evaluacion',{}) and (revision.get('version_investigacion')==saved.get('version_investigacion') or revision['evaluacion'][key].get('estado')=='Revisión manual en sesión'):
                ficha['evaluacion'][key]=deepcopy(revision['evaluacion'][key])
    result=validar_ficha(ficha)
    brief=ficha['brief']
    sources={s['id']:s for s in ficha['fuentes']}
    def source_links(ids):
        for sid in ids:
            item=sources[sid]
            if item.get('url'):
                st.markdown(f'[{item["titulo"]}]({item["url"]}) · consulta {item["fecha"]}')
            else:
                detail=item.get('archivo') or ('páginas '+item.get('paginas','—'))
                st.caption(f'{item["titulo"]} · {detail} · {item["fecha"]}')

    left,right=st.columns([1.25,1])
    with left:
        score='—' if result['total'] is None else f'{result["total"]:.1f}'
        st.markdown(f'<div class="hero"><div class="eyebrow">Resultado de viabilidad</div><div class="score">{score}<small> / 100</small></div><div class="hero-bottom"><span class="hero-pill">{result["estado"]}</span></div></div>',unsafe_allow_html=True)
    with right:
        ranges=[]
        for currency in monedas_precio(ficha):
            prices=[o['precio_'+currency.lower()] for o in ofertas_precio(ficha,currency)]
            ranges.append(f'{currency} {min(prices):,.0f} — {max(prices):,.0f}')
        price_range='<br>'.join(ranges) or 'Sin precios verificados'
        st.markdown(f'<div class="kpi"><div class="kpi-label">REFERENCIAS DE PRECIO · MERCADO</div><div class="kpi-number" style="font-size:23px">{price_range}</div><p>Rango publicado, incluye cohortes históricas.<br>Revisión: {ficha["fecha_revision"]}</p></div>',unsafe_allow_html=True)
    if result['total'] is None:
        st.caption('El resultado final se mantiene en evaluación: las dimensiones sin evidencia suficiente no se sustituyen por cero ni por una nota promedio. Los puntajes disponibles son juicios preliminares identificados como tales.')

    resumen,mercado,calculo,documento=st.tabs(['Diagnóstico EdCo','Oferta y plataformas','Cálculo y evidencia','Brief del proponente'])
    with resumen:
        if not ficha.get('evidencia_visual'):
            st.info('Brief registrado para '+INSTITUCIONES_EDCO[institution]['etiqueta']+'. Las cinco dimensiones están pendientes de investigación de mercado; las referencias del proponente se consultan en Oferta y plataformas.')
        a,b=st.columns([1.2,1])
        with a:
            with st.container(border=True):
                st.markdown('<div class="section-title"><h3>Perfil de viabilidad</h3><small>5 dimensiones</small></div>',unsafe_allow_html=True)
                st.plotly_chart(radar_edco(result),width='stretch',theme=None,config={'displayModeBar':False},key='edco_perfil')
                pending=[r['dimension'] for r in result['filas'] if r['puntaje'] is None]
                if pending:
                    st.caption('Sin calificar: '+ ' · '.join(pending)+'. No se dibujan como cero.')
        with b:
            with st.container(border=True):
                st.markdown('<div class="section-title"><h3>Orientación para la propuesta</h3></div>',unsafe_allow_html=True)
                for i,item in enumerate(ficha['recomendaciones'],1):
                    st.markdown(f'<div class="rec"><div class="rec-index">{i:02}</div><div><div class="rec-title">{escape(item["titulo"])}</div><p>{escape(item["texto"])}</p></div></div>',unsafe_allow_html=True)
        st.markdown(propuesta_html(ficha),unsafe_allow_html=True)
        with st.expander('Ver diferenciadores y contexto del brief'):
            for item in brief['diferenciadores']:
                st.markdown(f'- {item}')
            st.caption('Diferenciadores descritos por el proponente, página 3 del brief.')
            st.caption(ficha['audiencia_propuesta']['origen'])

        st.markdown('<div class="edco-section"><div><div class="edco-kicker">Evidencia de mercado</div><h2>Las cinco dimensiones de viabilidad</h2></div><p>Una lectura del mercado, desde el interés por el tema hasta la dinámica de su sector.</p></div>',unsafe_allow_html=True)
        for index,(key,label,weight) in enumerate(DIMENSIONES_EDCO,1):
            evidence=ficha.get('evidencia_visual',{}).get(key)
            if not evidence:
                continue
            criterion=ficha['evaluacion'][key]
            score='Sin calificar' if criterion['puntaje'] is None else f"{criterion['puntaje']:g}/100"
            with st.container(border=True):
                score_display='—' if criterion['puntaje'] is None else f"{criterion['puntaje']:g}"
                st.markdown(f'<div class="edco-dimension"><div class="edco-dimension-name"><span class="edco-dimension-number">{index:02}</span><div><h3>{escape(label)}</h3><small>Peso en el modelo · {weight}%</small></div></div><div class="edco-dimension-score">{escape(score_display)}<span>/100</span></div></div>',unsafe_allow_html=True)
                if evidence.get('fecha_consulta'):
                    st.caption('Consulta: '+evidence['fecha_consulta']+' · '+evidence.get('actualidad',''))
                title='Top 10 habilidades · participación en publicaciones' if key=='empleabilidad' else 'Participación registrada en cursos relacionados' if key=='demanda' and not evidence.get('serie') else evidence['titulo']
                st.markdown(f"**{title}**")
                if key=='empleabilidad' and evidence.get('origen')=='linkedin':
                    all_posts=evidence['publicaciones']
                    areas=sorted({r['area'] for r in all_posts})
                    states=sorted({r['estado_clasificacion'] for r in all_posts})
                    with st.expander('Filtrar publicaciones y revisar criterios'):
                        area_filter=st.multiselect('Campos de aplicación',areas,default=areas,key='edco_skill_areas')
                        state_filter=st.multiselect('Estado de la publicación',states,default=states,key='edco_skill_states')
                        st.caption('Cerrada: LinkedIn indica que no acepta solicitudes. Solicitud visible: había botón para postular al consultar. No confirmada: no se pudo determinar disponibilidad. Se usan habilidades descritas, no cantidad de vacantes.')
                        for skill in evidence.get('catalogo_habilidades',[]):
                            st.markdown(f"**{skill['habilidad']}:** {skill['criterio']}")
                        st.caption(evidence.get('busqueda',{}).get('alcance',''))
                    summary=resumir_habilidades(evidence,area_filter,state_filter)
                    evidence['publicaciones']=summary['publicaciones']
                    evidence['habilidades']=summary['habilidades'] if summary['total'] else []
                    metrics=st.columns(3)
                    metrics[0].metric('Publicaciones identificadas',summary['total'])
                    metrics[1].metric('Organizaciones',summary['empresas'])
                    metrics[2].metric('Habilidades analizadas',len(evidence.get('catalogo_habilidades',[])))
                    if summary['total']:
                        st.caption('El gráfico muestra las diez más frecuentes; una publicación puede mencionar varias, por lo que las participaciones no suman 100%.')
                    else:st.info('No hay publicaciones para los filtros seleccionados.')
                if key=='sector' and evidence.get('ventas_anuales'):
                    period=st.radio('Período de ventas',['Enero–agosto · todos los años','Totales anuales · 2023–2026 (2026 hasta agosto)'],horizontal=True,key='edco_periodo_sri')
                    if period.startswith('Totales anuales'):
                        annual=deepcopy(evidence['ventas_anuales'])
                        annual_years={r['anio'] for r in annual}
                        annual.extend(deepcopy(r) for r in evidence['ventas'] if r['anio'] not in annual_years)
                        evidence['ventas']=sorted(annual,key=lambda r:r['anio'])
                        st.caption('2023–2025: enero–diciembre. 2026: enero–agosto, sin proyección. La diferencia de cobertura debe considerarse al comparar los totales.')
                if key=='competencia':
                    counts=st.columns(3)
                    declared=[o for o in ficha['ofertas'] if o.get('disponibilidad')=='Inscripción declarada']
                    counts[0].metric('Instituciones · inscripción declarada',len({o['institucion'] for o in declared if o['tipo']=='Institucional'}))
                    counts[1].metric('Plataformas · sustitutos disponibles',len({o['institucion'].split(' · ')[0] for o in declared if o['tipo']=='Plataforma'}))
                    counts[2].metric('Ofertas revisadas',len(ficha['ofertas']))
                    st.caption('Los sustitutos introductorios se distinguen de diplomados; inscripción declarada en una página no confirma cupos ni apertura de cohorte.')
                    render_competencia(ficha,source_links)
                    continue
                if key=='sector' and evidence.get('origen')=='bccr':
                    st.caption(evidence['actividad']+f" · IMAE, base {evidence.get('base',2017)} = 100. "+evidence['alcance'])
                    with st.expander('Datos del gráfico · '+label):
                        sector_data=pd.DataFrame(evidence['serie_indice'])
                        st.dataframe(sector_data,hide_index=True,width='stretch')
                        st.download_button('Descargar serie BCCR · CSV',sector_data.to_csv(index=False).encode('utf-8-sig'),f"bccr_{ficha['id']}.csv",'text/csv',key='edco_bccr_csv')
                    if evidence.get('contexto_2026'):
                        st.caption(evidence['contexto_2026'])
                if key=='precio':
                    currencies=monedas_precio(ficha)
                    if len(currencies)>1:
                        evidence['moneda']=st.radio('Moneda del boxplot',currencies,horizontal=True,key='edco_precio_moneda')
                    elif currencies:
                        evidence['moneda']=currencies[0]
                    if ficha.get('institucion_id')=='ulatina_cr':
                        st.caption(evidence['nota'])
                if key in PLANTILLAS and key!='demanda' and evidence.get('origen')!='bccr':
                    with st.expander('Datos del gráfico · '+label):
                        if key=='sector' and evidence.get('archivo_mensual'):
                            source_file=Path(__file__).parent/evidence['archivo_mensual']
                            st.dataframe(pd.DataFrame(evidence['ventas']),hide_index=True,width='stretch')
                            st.download_button('Descargar detalle mensual SRI · CIIU del programa',source_file.read_bytes(),source_file.name,'text/csv',key='edco_sri_detalle')
                            st.caption('Origen: consulta_sri_1.xlsx · Ventas SRI · casilleros 411 + 413 · CIIU exacto M732001.')
                        st.caption('Permite incorporar una exportación documentada a la vista. No modifica las calificaciones ni guarda cambios sobre el archivo original.')
                        st.download_button('Descargar estructura CSV',','.join(PLANTILLAS[key])+'\n',f'edco_{key}.csv','text/csv',key='edco_template_'+key)
                        if key=='competencia':
                            st.caption('Una fila por programa: búsquedas en escala común 0–100 y competidores activos verificados con el mismo criterio. Consulta identifica período y extracción; fuente identifica la procedencia y el criterio de conteo.')
                        else:
                            st.caption('Una fila por año: naturales y sociedades en USD, CIIU exacto y meses acumulados. Cada serie debe usar la misma cobertura de meses y el mismo tratamiento de ventas. No usar recaudación de impuestos como ventas.')
                        upload=st.file_uploader('Importar evidencia CSV · '+label,type=['csv'],key='edco_csv_'+key)
                        if upload is not None:
                            try:
                                upload.seek(0)
                                field,records=leer_evidencia(upload,key,brief['ciiu'])
                            except (ValueError,TypeError,KeyError) as exc:
                                st.error(f'No se pudo incorporar la evidencia: {exc}')
                            else:
                                evidence[field]=records
                                evidence['nota']='Datos importados en esta sesión; períodos, alcance y fuentes se muestran en el detalle. No actualizan automáticamente el puntaje.'
                                st.dataframe(pd.DataFrame(records),hide_index=True,width='stretch')
                if key=='competencia':
                    with st.expander('Cortes exploratorios de la matriz'):
                        evidence['umbral_busquedas']=st.number_input('Corte visual de búsquedas',min_value=1,max_value=99,value=75,key='edco_matrix_x')
                        evidence['umbral_competidores']=st.number_input('Corte visual de competidores',min_value=1,max_value=100,value=3,key='edco_matrix_y')
                        st.caption('Cortes exploratorios ajustables. No modifican el puntaje de competencia ni trasladan reglas de pregrado a EdCos.')
                if key=='demanda' and not evidence.get('serie'):
                    st.markdown(participacion_html(ficha),unsafe_allow_html=True)
                else:
                    st.plotly_chart(grafico_dimension(ficha,key),width='stretch',theme=None,config={'displayModeBar':False},key='edco_detalle_'+key)
                    if key not in ('empleabilidad','precio','sector'):
                        st.caption(evidence['nota'])
                if key=='empleabilidad':
                    st.markdown('<div class="legend"><span><i class="dot" style="background:#3975b9"></i>Azul oscuro: habilidad explícita</span><span><i class="dot" style="background:#a7c6e2"></i>Azul claro: habilidad homologada</span></div>',unsafe_allow_html=True)
                    st.caption('Homologada: asociación analítica por afinidad con el brief, sujeta a revisión curricular.')
                    skills=pd.DataFrame(evidence.get('habilidades',[]))
                    if 'cobertura' in skills:
                        skills['cobertura']=skills['cobertura'].replace({'Explícita':'Habilidad explícita','Por contrastar':'Habilidad homologada'})
                    cols=[c for c in ['habilidad','menciones','muestra','porcentaje','importancia','cobertura'] if c in skills]
                    with st.expander('Detalle de todas las habilidades'):
                        st.dataframe(skills[cols].rename(columns={'habilidad':'Habilidad','menciones':'Publicaciones con la habilidad','muestra':'Publicaciones revisadas','porcentaje':'Participación (%)','importancia':'Importancia O*NET /100','cobertura':'Cobertura en el brief · interpretación'}),hide_index=True,width='stretch')
                    with st.expander('Publicaciones de LinkedIn revisadas'):
                        for item in evidence.get('publicaciones',[]):
                            st.markdown(f"**{item['empresa']} · {item['cargo']} · {item['ciudad']}**")
                            st.write(item['resumen'])
                            st.caption(item.get('area','')+' · '+', '.join(s['habilidad'] for s in evidence.get('catalogo_habilidades',[]) if s['id'] in item['habilidades']))
                            st.caption(item['estado'])
                            source_links([item['fuente']])
                        st.download_button('Descargar publicaciones y habilidades · CSV',pd.DataFrame([{'Empresa':r['empresa'],'Cargo':r['cargo'],'Ubicación':r['ciudad'],'Área':r['area'],'Estado':r['estado'],'Habilidades':' · '.join(s['habilidad'] for s in evidence['catalogo_habilidades'] if s['id'] in r['habilidades']),'Fuente':sources[r['fuente']]['url']} for r in evidence['publicaciones']]).to_csv(index=False).encode('utf-8-sig'),'habilidades_linkedin_edco.csv','text/csv',key='edco_skill_csv')
                if key=='precio':
                    institutions=[o for o in ficha['ofertas'] if o['tipo']=='Institucional']
                    st.dataframe(pd.DataFrame([{'Institución':o['institucion'],'Programa':o['programa'],'Precio USD':o['precio_usd'],**({'Precio CRC':o.get('precio_crc')} if ficha['brief']['pais']=='Costa Rica' else {}),'Horas':o['horas'],'Condición':o['estado']} for o in institutions]),hide_index=True,width='stretch')
                    missing=[o['institucion'] for o in institutions if all(o.get('precio_'+currency.lower()) is None for currency in ('USD','CRC')) or not o.get('precio_verificado',True)]
                    if missing:st.caption('Sin precio publicado para este programa: '+ ' · '.join(missing)+'. Se muestran en la tabla; no se dibujan como cero.')
                    platforms=[{'Oferente':o['institucion'],'Precio USD':o['precio_usd'],'Condición':o['estado'],'Horas':o['horas']} for o in ficha['ofertas'] if o['tipo']=='Plataforma' and o.get('precio_usd') is not None]
                    if platforms:
                        st.markdown('**Sustitutos introductorios · fuera del boxplot institucional**')
                        st.dataframe(pd.DataFrame(platforms),hide_index=True,width='stretch')
                with st.expander('Interpretación y fuentes · '+label):
                    st.write(criterion['justificacion'])
                    source_links(evidence['fuentes'])
                    if key=='demanda':
                        st.caption(evidence['nota'])
                        for item in evidence.get('observaciones',[]):
                            st.caption(f"Evidencia complementaria · {item['etiqueta']}: {item['valor']:,.0f} inscripciones acumuladas; ubicación no desglosada, no búsquedas locales.")
                    if key=='sector' and evidence.get('origen')!='bccr':
                        st.caption('El gráfico usa ventas del Excel SRI aportado, no transacciones de comercio electrónico ni recaudación tributaria. Se conservan las cuatro columnas originales en el detalle mensual.')

    with mercado:
        st.subheader('Alternativas frente a las que el participante puede elegir')
        market_filter=st.multiselect('Tipo de alternativa',['Institucional','Plataforma','Oferta propia','Otro nivel'],default=['Institucional','Plataforma','Oferta propia','Otro nivel'],key='edco_tipo_oferta')
        offers=[o for o in ficha['ofertas'] if o['tipo'] in market_filter]
        table=[]
        for o in offers:
            table.append({'Institución / plataforma':o['institucion'],'Programa':o['programa'],'Tipo':o['tipo'],'Modalidad':o['modalidad'],'Horas':o['horas'],'Precio publicado USD':o['precio_usd'],'Precio declarado CRC':o.get('precio_crc'),'Condición':o['estado'],'Disponibilidad publicada':o.get('disponibilidad','Por confirmar'),'Tratamiento':'Par cercano, comparabilidad por revisar' if o['competidor_directo'] else 'Oferta propia, fuera de competencia' if o['tipo']=='Oferta propia' else 'Alternativa o referencia; no par directo confirmado','Fuente':sources[o['fuente']].get('url')})
        st.dataframe(pd.DataFrame(table),hide_index=True,width='stretch',column_config={'Fuente':st.column_config.LinkColumn('Fuente'),'Precio publicado USD':st.column_config.NumberColumn(format='$%.2f'),'Horas':st.column_config.NumberColumn(format='%.2f')})
        st.caption('Precios observados en páginas consultadas; no son cotizaciones ni garantizan nuevas convocatorias. Tarifas de promociones y cohortes pasadas se identifican como históricas. Precio desconocido no equivale a cero.')
        own=[o for o in offers if o['tipo']=='Oferta propia']
        for o in own:
            with st.container(border=True):
                st.markdown('**Portafolio interno · posible solapamiento**')
                st.write(o['nota'])
                source_links([o['fuente']])
        with st.expander('Por qué no todas las alternativas son equivalentes'):
            st.write('Se contrastan resultado de aprendizaje, público, intensidad, idioma, modalidad, práctica y acompañamiento. Los programas de otros niveles y los cursos introductorios se distinguen de una certificación ejecutiva.')
            for o in offers:
                st.markdown(f'**{o["institucion"]} · {o["programa"]}**')
                st.write(o['nota'])

    with calculo:
        st.subheader('Pesos y reglas EdCo')
        rows=[]
        for row in result['filas']:
            rows.append({'Dimensión':row['dimension'],'Peso':f'{row["peso"]}%','Puntaje':None if row['puntaje'] is None else row['puntaje'],'Aporte al total':row['aporte'],'Estado':ficha['evaluacion'][row['id']]['estado']})
        st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch',column_config={'Puntaje':st.column_config.NumberColumn(format='%.1f'),'Aporte al total':st.column_config.NumberColumn(format='%.2f')})
        st.markdown('**Aporte = puntaje de la dimensión × peso ÷100.** Los cinco pesos suman100%. Este apartado no usa una carrera de referencia ni hereda los límites de competidores del modelo de carreras.')
        st.caption('Se mantienen las mismas dimensiones del pentágono de carreras. Precio frente al mercado analiza rangos publicados, intensidad, acompañamiento y posicionamiento, sin exigir un precio al proponente. Audiencia y modalidad son información de contexto, no dimensiones adicionales.')
        st.caption('Rúbrica de trabajo:0–25 evidencia desfavorable;26–50 señales débiles o mixtas;51–74 condiciones intermedias;75–89 evidencia favorable;90–100 condiciones excepcionales sustentadas. Es una propuesta metodológica, no una escala calibrada con matrícula.')
        st.caption('Cuando las cinco dimensiones tengan puntaje:75–100 viabilidad favorable;55–<75 condicionada;<55 desfavorable. Estas bandas son provisionales. No se emite un total incompleto ni se renormalizan los pesos para ocultar dimensiones pendientes.')
        for key,label,weight in DIMENSIONES_EDCO:
            criterion=ficha['evaluacion'][key]
            suffix='Sin calificar' if criterion['puntaje'] is None else f'{criterion["puntaje"]:g}/100 · preliminar'
            with st.expander(f'{label} · {weight}% · {suffix}'):
                st.markdown('**Subcategorías:** '+ ' · '.join(criterion['subcategorias']))
                st.caption('Evidencia: '+criterion.get('nivel_evidencia','Revisión analítica'))
                st.write(criterion['justificacion'])
                source_links(criterion['fuentes'])
        with st.expander('Revisión analítica de puntajes · sesión actual'):
            st.caption('Permite revisar la rúbrica con evidencia. No genera investigación automática ni guarda cambios sobre el archivo original. Las reglas y pesos permanecen fijos.')
            with st.form('edco_revision_form'):
                edited=deepcopy(ficha)
                for key,label,_ in DIMENSIONES_EDCO:
                    old=edited['evaluacion'][key]
                    include=st.checkbox(f'Asignar puntaje · {label}',value=old['puntaje'] is not None,key=f'edco_eval_{key}')
                    score=st.number_input(f'Puntaje · {label}',min_value=0,max_value=100,value=int(old['puntaje'] or 0),key=f'edco_score_{key}')
                    reason=st.text_area(f'Justificación · {label}',value=old['justificacion'],key=f'edco_reason_{key}')
                    source_ids=st.multiselect(f'Fuentes · {label}',options=list(sources),default=old['fuentes'],format_func=lambda sid:sources[sid]['titulo'],key=f'edco_sources_{key}')
                    old.update(puntaje=score if include else None,justificacion=reason,fuentes=source_ids,estado='Revisión manual en sesión' if include else 'Sin calificar')
                submit=st.form_submit_button('Aplicar revisión a esta sesión')
            if submit:
                try:
                    validar_ficha(edited)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state['edco_revision_'+saved['id']]=edited
                    st.rerun()
        st.download_button('Descargar análisis EdCo · JSON',json.dumps({'programa':ficha,'resultado':result},ensure_ascii=False,indent=2),'analisis_edco_'+ficha['id']+'.json','application/json',key='edco_download')

    with documento:
        st.subheader('Ficha del proponente')
        st.caption('Información extraída del PDF entregado. Se omiten identificadores personales y metadatos de seguimiento del formulario en la vista.')
        info=[('Programa',ficha['nombre']),('Tipo',brief['tipo']),('Facultad',brief['facultad']),('Unidad',brief['unidad']),('País',brief['pais']),('Duración',brief['duracion']),('Horas totales','No informadas' if brief['horas_totales'] is None else brief['horas_totales']),('Modalidad',brief['modalidad']),('Experto',brief['experto']),('Sector declarado',brief.get('sector_declarado','Ver código CIIU')),('Código CIIU declarado',brief['ciiu'] or 'No declarado')]
        st.dataframe(pd.DataFrame(info,columns=['Campo','Dato del brief']),hide_index=True,width='stretch')
        st.markdown('**Objetivo**');st.write(brief['objetivo'])
        st.markdown('**Ejes**');st.write(' · '.join(brief['ejes']))
        st.markdown('**Nombres alternativos**');st.write(' · '.join(brief['nombres_alternativos']))
        st.markdown('**Palabras clave de investigación**');st.write(' · '.join(brief['palabras_clave']))
        pdf=Path(__file__).parent/brief['copia_local']
        if pdf.is_file():
            st.download_button('Consultar brief original · PDF',pdf.read_bytes(),brief['archivo'],'application/pdf',key='edco_brief_pdf')
        st.markdown('**Distinción de evidencia**')
        st.write('El PDF acredita lo que propone el solicitante. Las páginas de instituciones acreditan lo que publican sus oferentes. Los puntajes y segmentos sugeridos son interpretación analítica. Ninguno de esos elementos sustituye una medición de interés local o una confirmación de matrícula.')


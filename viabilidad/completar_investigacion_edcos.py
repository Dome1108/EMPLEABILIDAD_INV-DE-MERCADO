"""Completa las fichas de los briefs registrados con investigación de mercado.

Combina tres partes, sin recalcular nada en la vista:
1. El brief transcrito (registrar_briefs_edcos.construir_ficha).
2. La investigación web de cada programa: edcos_investigacion/<id>.json
   (formato en edcos_investigacion/ESPECIFICACION.md).
3. El sector económico: IMAE del BCCR para Costa Rica (juicio analítico con el mismo
   criterio de las fichas ya investigadas) y ventas SRI con la regla absoluta de
   sector_edcos para Ecuador.

Uso:
    python completar_investigacion_edcos.py
Si un programa no tiene archivo de investigación, su ficha queda «En evaluación».
"""
import csv
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from actualizacion_bccr_edcos import ARCHIVO as IMAE_ARCHIVO, URL as IMAE_URL, extraer_serie
from habilidades_edcos import resumir_habilidades
from investigacion_sri_edcos import extraer_ventas_sri
from modelo_edcos import DIMENSIONES_EDCO, INSTITUCIONES_EDCO, validar_ficha
from registrar_briefs_edcos import BRIEFS, FECHA_REGISTRO, construir_ficha
from sector_edcos import calcular_sector_sri

BASE = Path(__file__).parent
INVESTIGACION = BASE / 'edcos_investigacion'
EXCEL_SRI = BASE.parent / 'data' / 'consulta_sri_1.xlsx'
VERSION = FECHA_REGISTRO + '-mercado-v1'
BCCR_2026 = 'https://www.bccr.fi.cr/cr/es/noticias/listado-de-noticias/2026/indice-mensual-de-actividad-economica-para-agosto-de-2026.html'

# Indicador IMAE por programa: la actividad declarada en el brief ([Q36]) que mejor
# corresponde al núcleo del programa. Puntaje: mismo criterio que las fichas ya
# investigadas (People Analytics 75 con 94984; TEA 70 con un agregado amplio).
SECTOR_CR = {
    'analisis_noticias_cr': (94981, 75, 'El brief declara primero «Información y comunicación»; el programa produce análisis y contenidos informativos.'),
    'eventos_corporativos_cr': (94984, 75, 'El brief declara actividades profesionales y de servicios administrativos y de apoyo; la organización de eventos pertenece a ese agregado.'),
    'interiores_comerciales_cr': (94984, 75, 'El brief declara «Actividades profesionales, científicas y técnicas»; el diseño especializado de interiores forma parte de ese agregado.'),
    'escritura_creativa_cr': (94987, 70, 'El brief declara únicamente «Actividades artísticas, de entretenimiento y recreativas», incluidas en «Otras actividades» del IMAE.'),
    'fotografia_digital_cr': (94981, 75, 'El brief declara primero «Información y comunicación»; la fotografía del programa se orienta a contenidos digitales, publicidad y producto.'),
    'cooperacion_internacional_cr': (94984, 75, 'El brief declara actividades profesionales, servicios administrativos y administración pública; la formulación y gestión de proyectos corresponde al agregado profesional y de apoyo.'),
    'ataque_defensa_nube_cr': (94984, 75, 'El brief declara únicamente «Actividades profesionales, científicas y técnicas».'),
    'marca_personal_cr': (94981, 75, 'El brief declara primero «Información y comunicación»; el programa se centra en comunicación y contenido digital.'),
    'multiplataformas_deportivas_cr': (94981, 75, 'El brief declara «Información y comunicación» y «Enseñanza»; el programa produce contenidos y medios.'),
    'storymakers_cr': (94981, 75, 'El brief declara «Información y comunicación» y «Enseñanza»; el programa produce contenidos y narrativas.'),
    'manufactura_avanzada_cr': (94949, 60,'El brief declara únicamente «Industrias manufactureras»; el programa forma técnicos de producción, calidad y mantenimiento para ese sector.'),
    'ia_databricks_cr': (94984, 75, 'El brief declara únicamente «Actividades profesionales, científicas y técnicas».'),
}
ACTUALIDAD = {
    'demanda': 'Participaciones acumuladas · alcance internacional',
    'empleabilidad': 'Publicaciones observadas · incluye cerradas y de vigencia no confirmada',
    'competencia': 'Oferta publicada · vigencia detallada por programa',
    'precio': 'Precios documentados · incluye referencias históricas o sin nueva cohorte confirmada',
}


_VACIAS = {'de', 'del', 'la', 'las', 'los', 'el', 'y', 'en', 'universidad', 'escuela', 'instituto', 'centro'}


def _tokens(nombre):
    """Palabras significativas y siglas del nombre de una institución, sin tildes."""
    texto = unicodedata.normalize('NFKD', nombre.casefold())
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return {t for t in re.findall(r'[a-z0-9]+', texto) if t not in _VACIAS}


def _misma_institucion(brief, investigada):
    # «UCR» frente a «Universidad de Costa Rica (UCR) · ECCC», o nombres completos iguales.
    return bool(brief) and (brief <= investigada or investigada <= brief)


def _promedio_ene_ago(serie, anio):
    valores = {r['fecha']: r['valor'] for r in serie}
    meses = [valores[f'{anio}-{m:02}-01'] for m in range(1, 9) if f'{anio}-{m:02}-01' in valores]
    return sum(meses) / len(meses) if len(meses) == 8 else None


def sector_costa_rica(brief_id):
    indicador, puntaje, motivo = SECTOR_CR[brief_id]
    serie = extraer_serie(json.loads(IMAE_ARCHIVO.read_text(encoding='utf-8')), indicador)
    actual, anterior = _promedio_ene_ago(serie['serie_indice'], 2026), _promedio_ene_ago(serie['serie_indice'], 2025)
    variacion = 100 * (actual / anterior - 1)
    if variacion >= 0:
        lectura = 'actividad sostenida'
        regla = ('(75 para un agregado con crecimiento sostenido vinculado al núcleo del programa; 70 cuando el agregado es más amplio), '
                 'sin convertir el índice en puntaje por regla de tres.')
    else:
        # Un agregado vinculado al núcleo pero en contracción no puede recibir la nota de crecimiento sostenido.
        lectura = 'contracción interanual del agregado'
        regla = ('(75 con crecimiento sostenido; 60, banda intermedia, cuando el agregado vinculado al núcleo del programa se contrae), '
                 'sin convertir el índice en puntaje por regla de tres.')
    fuentes =[dict(id='bccr_imae', titulo='BCCR · IMAE por industrias, serie original 2022 = 100', url=IMAE_URL, fecha=FECHA_REGISTRO,
                    observacion=f"Grupo 939, indicador {indicador}. Datos desde enero de 2023 hasta {serie['periodo_hasta']}; sujetos a revisión."),
               dict(id='bccr_2026', titulo='BCCR · Informe IMAE agosto 2026, publicado 13/10/2026', url=BCCR_2026, fecha=FECHA_REGISTRO,
                    observacion='Contexto macroeconómico de 2026, separado de la serie sectorial.')]
    criterio = dict(
        puntaje=puntaje, estado='Juicio analítico preliminar', fuentes=['bccr_imae', 'bccr_2026'],
        nivel_evidencia='IMAE sectorial BCCR · juicio analítico preliminar',
        subcategorias=['Actividad del sector en Costa Rica', 'Evolución del entorno económico', 'Aplicación de las competencias del programa'],
        justificacion=(f"{motivo} El IMAE de «{serie['actividad']}» (base 2022 = 100) promedia {actual:.1f} en enero–agosto de 2026 "
                       f"frente a {anterior:.1f} en el mismo periodo de 2025 ({variacion:+.1f} %): {lectura}. Es un agregado amplio, "
                       f"no ventas ni demanda del programa. Se asigna {puntaje} con el mismo criterio de las fichas ya investigadas de Costa Rica "
                       + regla))
    evidencia = dict(titulo='Actividad económica del sector · Costa Rica', origen='bccr', **serie, fuentes=criterio['fuentes'],
                     nota='Índice de producción, no ventas ni recaudación. Serie original sujeta a estacionalidad y revisión.',
                     alcance='Agregado sectorial; no mide exclusivamente la actividad del programa.', fecha_consulta=FECHA_REGISTRO,
                     archivo_datos='edcos_fuentes/bccr_imae_grupo_939.json',
                     actualidad='Datos hasta ' + serie['periodo_hasta'][:7] + ' · serie vigente, base 2022 = 100')
    return criterio, evidencia, fuentes


def sector_ecuador(brief_id, ciiu):
    calculo = calcular_sector_sri(EXCEL_SRI, ciiu)
    ventas = extraer_ventas_sri(EXCEL_SRI, ciiu)
    sha = hashlib.sha256(EXCEL_SRI.read_bytes()).hexdigest()
    mensual = BASE / 'edcos_fuentes' / f'ventas_{brief_id}_mensuales.csv'
    with mensual.open('w', newline='', encoding='utf-8') as archivo:
        writer = csv.DictWriter(archivo, fieldnames=['anio', 'mes', 'ciiu', 'naturales_411', 'sociedades_411', 'naturales_413', 'sociedades_413'])
        writer.writeheader()
        writer.writerows(ventas['mensual'])
    fuentes = [dict(id='sri_excel', titulo='SRI · Excel de ventas aportado por el usuario', tipo='Base de datos aportada', url=None,
                    fecha=FECHA_REGISTRO, archivo='consulta_sri_1.xlsx',
                    nota=f"Hoja Ventas SRI; {len(ventas['mensual'])} registros mensuales de {calculo['ciiu']}. SHA-256 {sha}")]
    criterio = dict(
        puntaje=calculo['puntaje'], estado='Calculado con ventas SRI', fuentes=['sri_excel'],
        nivel_evidencia='Ventas SRI del CIIU exacto; regla absoluta reproducible',
        subcategorias=['Tamaño económico (40%)', 'Evolución de ventas (60%)'],
        justificacion=(f"Regla absoluta sin programa de referencia (sector_edcos.calcular_sector_sri). Enero–agosto de 2026: USD "
                       f"{calculo['ventas_actual']:,.2f}; mismo periodo de 2025: USD {calculo['ventas_anterior']:,.2f}. Crecimiento: "
                       f"{100 * calculo['crecimiento']:.2f} %; puntaje de evolución {calculo['evolucion']:.2f}/100 (escala lineal: −20 % = 0, "
                       f"0 % = 50, +20 % = 100, con topes). Tamaño: percentil de rango medio {calculo['tamano']:.2f} entre {calculo['universo']} "
                       f"actividades CIIU de seis dígitos de la sección {calculo['seccion']}. Sector = 40 % tamaño + 60 % evolución = "
                       f"{calculo['puntaje']:.2f}/100. Fuente: Excel SRI, casilleros 411 + 413. No se sustituyen datos faltantes por cero."))
    evidencia = dict(titulo='Evolución de ventas de personas naturales y sociedades', fuentes=['sri_excel'],
                     nota=(f"Excel SRI aportado: consulta_sri_1.xlsx, hoja Ventas SRI, CIIU exacto {calculo['ciiu']} ({ciiu}). Se suman "
                           'casilleros 411 + 413 por tipo de contribuyente. Vista principal: enero–agosto de cada año; años completos por separado.'),
                     ventas=ventas['ventas'], ventas_anuales=ventas['ventas_anuales'], mensual=ventas['mensual'], mes_corte=ventas['mes_corte'],
                     archivo_mensual=f'edcos_fuentes/{mensual.name}', archivo_original='../data/consulta_sri_1.xlsx', sha256=sha,
                     fecha_consulta=FECHA_REGISTRO, actualidad=f"Ventas declaradas hasta agosto de 2026 · CIIU {ciiu}")
    return criterio, evidencia, fuentes


def completar(datos, investigacion):
    ficha = construir_ficha(datos)
    institucion = INSTITUCIONES_EDCO[ficha['institucion_id']]
    fuentes = ficha['fuentes'] + [dict(fuente, fecha=fuente.get('fecha', investigacion['fecha_consulta'])) for fuente in investigacion['fuentes']]
    if ficha['institucion_id'] == 'ulatina_cr':
        sector, evidencia_sector, fuentes_sector = sector_costa_rica(datos['id'])
    else:
        sector, evidencia_sector, fuentes_sector = sector_ecuador(datos['id'], ficha['brief']['ciiu'])
    fuentes += fuentes_sector
    ids = [fuente['id'] for fuente in fuentes]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{datos['id']}: identificadores de fuente duplicados.")

    ofertas, revisiones = [], {}
    for item in investigacion['ofertas']:
        oferta = {k: v for k, v in item.items() if k != 'contenidos'}
        ofertas.append(oferta)
        if any(isinstance(v, bool) for v in item.get('contenidos', {}).values()) and oferta['tipo'] != 'Otro nivel':
            if oferta['fuente'] in revisiones:
                raise ValueError(f"{datos['id']}: dos ofertas comparten la fuente {oferta['fuente']}.")
            revisiones[oferta['fuente']] = dict(revisado=True, etiqueta=oferta.get('etiqueta_precio') or oferta['institucion'],
                                                base='Descripción publicada por el oferente', detalle=oferta.get('nota', ''),
                                                contenidos=item['contenidos'])
    # Las menciones del brief solo se añaden si su institución no fue investigada: la
    # investigación ya verificó (con su nombre real) las alternativas del proponente.
    investigadas = [_tokens(o['institucion']) for o in ofertas]
    ofertas += [o for o in ficha['ofertas'] if not any(_misma_institucion(_tokens(o['institucion']), t) for t in investigadas)]

    evaluacion = {}
    for key, _, _ in DIMENSIONES_EDCO:
        if key == 'sector':
            evaluacion[key] = sector
            continue
        criterio = investigacion['evaluacion'][key]
        evaluacion[key] = dict(puntaje=criterio['puntaje'], estado='Juicio analítico preliminar', subcategorias=ficha['evaluacion'][key]['subcategorias'],
                               justificacion=criterio['justificacion'], fuentes=criterio['fuentes'], nivel_evidencia=criterio['nivel_evidencia'])

    empleo = investigacion['empleabilidad']
    catalogo = empleo['catalogo']
    empleabilidad = dict(titulo='Top 10 habilidades · participaciones', origen='linkedin', publicaciones=empleo['publicaciones'],
                         catalogo_habilidades=catalogo, fuentes=evaluacion['empleabilidad']['fuentes'],
                         nota='Habilidades codificadas a partir de las funciones y requisitos publicados.',
                         busqueda=dict(alcance=empleo['alcance']))
    empleabilidad['habilidades'] = resumir_habilidades(empleabilidad)['habilidades']
    monedas = [m for m in ('USD', 'CRC') if any(o['tipo'] == 'Institucional' and o.get('precio_verificado') and o.get('precio_' + m.lower()) is not None for o in ofertas)]
    evidencia = dict(
        demanda=dict(titulo='Participación registrada en formación relacionada', serie=[], observaciones=investigacion['demanda']['observaciones'],
                     fuentes=evaluacion['demanda']['fuentes'], nota=investigacion['demanda']['nota'], lectura=investigacion['demanda']['lectura']),
        empleabilidad=empleabilidad,
        competencia=dict(titulo='Contenidos y posicionamiento competitivo', matriz=[], fuentes=evaluacion['competencia']['fuentes'],
                         nota='Comparación de oferta documentada; no se inventan posiciones de búsquedas.'),
        precio=dict(titulo='Distribución de aranceles publicados', moneda=(monedas or ['USD'])[0], fuentes=evaluacion['precio']['fuentes'],
                    nota=investigacion.get('nota_precio', 'Precios en moneda original, sin conversión.')),
        sector=evidencia_sector,
    )
    for key in ACTUALIDAD:
        evidencia[key].update(fecha_consulta=investigacion['fecha_consulta'], actualidad=ACTUALIDAD[key])

    ficha.update(
        fecha_revision=investigacion['fecha_consulta'], version_investigacion=VERSION, fuentes=fuentes, ofertas=ofertas,
        evaluacion=evaluacion, evidencia_visual=evidencia,
        recomendaciones=[dict(titulo=label, texto=investigacion['recomendaciones'][key]) for key, label, _ in DIMENSIONES_EDCO],
        comparativa_contenidos=dict(
            temas=[dict(tema, criterio='Presencia explícita de ' + tema['etiqueta'].replace('<br>', ' ').lower()
                        + ' en la descripción revisada; no identificado no significa ausente.') for tema in investigacion['temas']],
            propuesta=dict(etiqueta=institucion['nombre'] + ' · Programa propuesto', detalle='Contenidos declarados en el brief del proponente.',
                           contenidos={tema['id']: True for tema in investigacion['temas']}),
            ofertas=revisiones, lectura_ejecutiva=investigacion['lectura_ejecutiva']),
    )
    verificar_referencias(ficha)
    validar_ficha(ficha)
    return ficha


def verificar_referencias(ficha):
    """Toda fuente citada en ofertas, publicaciones, observaciones o evaluación debe existir."""
    ids = {fuente['id'] for fuente in ficha['fuentes']}
    citadas = {o['fuente'] for o in ficha['ofertas']}
    citadas |= {p['fuente'] for p in ficha['evidencia_visual']['empleabilidad']['publicaciones']}
    citadas |= {o['fuente'] for o in ficha['evidencia_visual']['demanda']['observaciones'] if o.get('fuente')}
    for evidencia in ficha['evidencia_visual'].values():
        citadas |= set(evidencia.get('fuentes', []))
    faltantes = citadas - ids
    if faltantes:
        raise ValueError(f"{ficha['id']}: fuentes citadas sin registrar: {sorted(faltantes)}")
    catalogo = {h['id'] for h in ficha['evidencia_visual']['empleabilidad']['catalogo_habilidades']}
    for publicacion in ficha['evidencia_visual']['empleabilidad']['publicaciones']:
        if not set(publicacion['habilidades']) <= catalogo:
            raise ValueError(f"{ficha['id']}: la publicación {publicacion['id']} usa habilidades fuera del catálogo.")


def completar_todos():
    for datos in BRIEFS:
        archivo = INVESTIGACION / f"{datos['id']}.json"
        if not archivo.is_file():
            print('Sin investigación, queda en evaluación:', datos['id'])
            continue
        ficha = completar(datos, json.loads(archivo.read_text(encoding='utf-8')))
        (BASE / 'edcos_data' / datos['archivo_json']).write_text(json.dumps(ficha, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        resultado = validar_ficha(ficha)
        print(f"{datos['id']}: {resultado['total']:.1f} · {resultado['estado']}")


if __name__ == '__main__':
    completar_todos()

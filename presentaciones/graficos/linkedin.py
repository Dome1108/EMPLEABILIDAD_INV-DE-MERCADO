# [Copia de Tendencias · presentation/charts/linkedin.py; solo cambian las rutas de import]
"""Gráficos editables para las métricas que realmente extrae LinkedIn."""
import math
import re

from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_TICK_MARK
from pptx.util import Pt
import unicodedata


def numero_linkedin(valor, porcentaje=False):
    """Convierte números de LinkedIn; un dato ausente nunca se convierte en cero."""
    if valor is None:
        return None
    if isinstance(valor, str):
        texto = valor.strip().replace('\u00a0', '').replace(' ', '').replace('%', '')
        if not re.fullmatch(r'[+-]?\d[\d.,]*', texto):
            return None
        if porcentaje:
            texto = texto.replace(',', '.')
        elif re.fullmatch(r'[+-]?\d{1,3}([.,]\d{3})+', texto):
            texto = texto.replace(',', '').replace('.', '')
        else:
            texto = texto.replace(',', '.')
        valor = texto
    try:
        numero = float(valor)
        return numero if math.isfinite(numero) and numero >= 0 else None
    except (TypeError, ValueError):
        return None


def cantidad_ubicacion(valor):
    """Recupera conteos históricos guardados con punto de miles como decimal."""
    numero = numero_linkedin(valor)
    if numero is not None and not numero.is_integer():
        miles = numero * 1000
        if math.isclose(miles, round(miles), abs_tol=1e-7):
            return float(round(miles))
        return None
    return numero


def reemplazar_grafico(slide, shape, titulo, categorias, series, porcentaje=False,
                      colores=('006DBF', 'A6CAEC')):
    """Reemplaza una imagen en su posición original, conservando el orden de objetos."""
    parent = shape._element.getparent()
    index = parent.index(shape._element)
    if not categorias or not any(v is not None for _, values in series for v in values):
        nuevo = slide.shapes.add_textbox(shape.left, shape.top, shape.width, shape.height)
        nuevo.text_frame.text = f'{titulo}\nN/D'
        for paragraph in nuevo.text_frame.paragraphs:
            paragraph.font.size = Pt(16)
            paragraph.font.color.rgb = RGBColor.from_string(colores[0])
    else:
        data = CategoryChartData()
        data.categories = categorias
        for nombre, valores in series:
            data.add_series(nombre, valores)
        nuevo = slide.shapes.add_chart(
            XL_CHART_TYPE.BAR_CLUSTERED, shape.left, shape.top,
            shape.width, shape.height, data)
        chart = nuevo.chart
        chart.has_title = True
        chart.chart_title.text_frame.text = titulo
        chart.chart_title.text_frame.paragraphs[0].font.size = Pt(14)
        chart.font.name = 'Arial'
        chart.font.size = Pt(11)
        chart.has_legend = len(series) > 1
        if chart.has_legend:
            chart.legend.position = XL_LEGEND_POSITION.BOTTOM
            chart.legend.include_in_layout = False
        chart.category_axis.reverse_order = True
        for axis in (chart.category_axis, chart.value_axis):
            axis.format.line.fill.background()
            axis.major_tick_mark = XL_TICK_MARK.NONE
            axis.minor_tick_mark = XL_TICK_MARK.NONE
        chart.value_axis.has_major_gridlines = True
        chart.value_axis.major_gridlines.format.line.color.rgb = RGBColor.from_string('D9D9D9')
        chart.value_axis.minimum_scale = 0
        maximo = max(v for _, values in series for v in values if v is not None)
        chart.value_axis.tick_labels.number_format = (
            '0.00"%"' if porcentaje else ('0.0,," M"' if maximo >= 1000000 else '#,##0'))
        chart.plots[0].has_data_labels = True
        chart.plots[0].data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
        chart.plots[0].data_labels.number_format = '0.00"%"' if porcentaje else '#,##0'
        for i, serie in enumerate(chart.series):
            serie.format.fill.solid()
            serie.format.fill.fore_color.rgb = RGBColor.from_string(
                colores[i % len(colores)])
            serie.format.line.fill.background()
    parent.remove(nuevo._element)
    parent.remove(shape._element)
    parent.insert(index, nuevo._element)
    return nuevo


def clave_aptitud(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', texto.casefold())
                   if not unicodedata.combining(c)).strip()


def actualizar_porcentajes_cuadros(slide, aptitudes):
    """Actualiza las tarjetas con las mismas aptitudes ordenadas del gráfico."""
    for index, shape in enumerate(list(slide.shapes)[1:6]):
        nombre = aptitudes[index][0] if index < len(aptitudes) else 'N/D'
        paragraph = shape.text_frame.paragraphs[0]
        if paragraph.runs:
            paragraph.runs[0].text = nombre
            for run in list(paragraph.runs)[1:]:
                run.text = ''
        else:
            paragraph.text = nombre
    por_nombre = {clave_aptitud(r[0]): r[1] for r in aptitudes}
    for shape in list(slide.shapes)[1:6]:
        nombre = shape.text.splitlines()[0]
        valor = por_nombre.get(clave_aptitud(nombre))
        pct = numero_linkedin(valor, porcentaje=True)
        nuevo = f'{pct:g}%' if pct is not None else 'N/D'
        for paragraph in shape.text_frame.paragraphs:
            texto = ''.join(run.text for run in paragraph.runs)
            match = re.search(r'\d+(?:[.,]\d+)?\s*%|N/D', texto)
            if match is None:
                continue
            inicio, fin = match.span()
            offset = 0
            inserted = False
            for run in paragraph.runs:
                original = run.text
                end = offset + len(original)
                if offset < fin and end > inicio:
                    izquierda = original[:max(0, inicio - offset)]
                    derecha = original[max(0, fin - offset):] if end > fin else ''
                    run.text = izquierda + (nuevo if not inserted else '') + derecha
                    inserted = True
                offset = end


def actualizar_nombres_cuadros(slide, nombres):
    """Actualiza las tarjetas y limpia las que no fueron capturadas.

    El formulario puede traer menos de cinco aptitudes.  Antes solo se
    modificaban las primeras y las restantes conservaban nombres de ejemplo de
    la plantilla, lo que hacía parecer que existían aptitudes que el usuario no
    había ingresado. Se conserva la geometría de las tarjetas y se marca como
    ``N/D`` la parte que no tiene datos.
    """
    valores = list(nombres or [])[:5]
    for index in range(5):
        shape = slide.shapes[index + 1]
        if index < len(valores) and not str(valores[index]).strip():
            # Una fila vacía explícita conserva la tarjeta que el usuario dejó
            # intacta; las filas ausentes al final sí se marcan como N/D.
            continue
        if index >= len(valores):
            # Conserva la línea de porcentaje de la plantilla (que proviene de
            # la API) pero elimina el nombre de ejemplo para no atribuirlo al
            # programa. ``N/D`` mantiene el equilibrio visual de la tarjeta.
            primer_parrafo = shape.text_frame.paragraphs[0]
            if primer_parrafo.runs:
                primer_parrafo.runs[0].text = 'N/D'
                for run in list(primer_parrafo.runs)[1:]:
                    run.text = ''
            else:
                primer_parrafo.text = 'N/D'
            continue
        paragraph = shape.text_frame.paragraphs[0]
        nombre = str(valores[index]).strip()
        if paragraph.runs:
            paragraph.runs[0].text = nombre
            for run in list(paragraph.runs)[1:]:
                run.text = ''
        else:
            paragraph.text = nombre


# cambiado por samuel
def _texto_parrafo_tarjeta(paragraph, texto):
    if paragraph.runs:
        paragraph.runs[0].text = texto
        for run in list(paragraph.runs)[1:]:
            run.text = ''
    else:
        paragraph.text = texto


def _ocultar_tarjeta(shape, ocultar):
    c_nv_pr = shape._element.nvSpPr.cNvPr
    if ocultar:
        c_nv_pr.set('hidden', '1')
    else:
        c_nv_pr.attrib.pop('hidden', None)


def _geometrias_tarjetas(slide, cantidad, ancho, alto):
    originales = [
        (shape.left, shape.top, shape.width, shape.height)
        for shape in list(slide.shapes)[1:6]
    ]
    if cantidad == 5:
        return originales
    if cantidad == 0:
        return []

    # Las tarjetas se mantienen en la columna derecha de la plantilla, una
    # debajo de otra, centradas verticalmente respecto a la columna completa
    # para no invadir el gráfico de la izquierda.
    left = originales[0][0]
    paso = originales[1][1] - originales[0][1]
    area_top = min(top for _, top, _, _ in originales)
    area_bottom = max(top + height for _, top, _, height in originales)
    alto_total = (cantidad - 1) * paso + alto
    top = int(round((area_top + area_bottom) / 2 - alto_total / 2))
    return [
        (left, top + indice * paso, ancho, alto)
        for indice in range(cantidad)
    ]


def actualizar_tarjetas_competencias(slide, competencias):
    """Renderiza solo las competencias del programa, entre cero y cinco."""
    tarjetas = list(competencias or [])[:5]
    shapes = list(slide.shapes)[1:6]
    if len(shapes) != 5:
        raise ValueError('La diapositiva 11 debe tener cinco shapes de competencia')

    ancho = shapes[0].width
    alto = shapes[0].height
    geometrias = _geometrias_tarjetas(slide, len(tarjetas), ancho, alto)
    for indice, shape in enumerate(shapes):
        if indice >= len(tarjetas):
            shape.text_frame.clear()
            _ocultar_tarjeta(shape, True)
            continue

        nombre, puntaje = tarjetas[indice]
        nombre = str(nombre).strip()
        if not nombre:
            shape.text_frame.clear()
            _ocultar_tarjeta(shape, True)
            continue

        shape.left, shape.top, shape.width, shape.height = geometrias[indice]
        _ocultar_tarjeta(shape, False)
        text_frame = shape.text_frame
        parrafos = text_frame.paragraphs
        if len(parrafos) == 1:
            text_frame.add_paragraph()
            parrafos = text_frame.paragraphs
        _texto_parrafo_tarjeta(parrafos[0], nombre)
        porcentaje = numero_linkedin(puntaje, porcentaje=True)
        texto_porcentaje = (
            f'Porcentaje de alineación con el mercado: {porcentaje:g}%'
            if porcentaje is not None else
            'Porcentaje de alineación con el mercado: N/D'
        )
        _texto_parrafo_tarjeta(parrafos[1], texto_porcentaje)
        for parrafo_extra in list(text_frame.paragraphs)[2:]:
            text_frame._txBody.remove(parrafo_extra._p)
#------------------------------------


def actualizar_graficos_linkedin(prs, aptitudes, region_local, regiones,
                                aptitudes_regionales=None, empresas=None, cargos=None, sectores=None):
    """Llena los cuatro espacios de gráficos laborales de la plantilla de mercado."""
    porcentajes = [numero_linkedin(r[1], porcentaje=True) for r in aptitudes]
    usar_porcentaje = any(v is not None for v in porcentajes)
    valores = porcentajes if usar_porcentaje else [numero_linkedin(r[2]) for r in aptitudes]
    series = [('Profesionales (%)' if usar_porcentaje else 'Profesionales', valores)]
    if aptitudes_regionales is not None:
        categorias_aptitudes = [r[0] for r in aptitudes]
        series = []
        for region in (region_local, 'América Latina'):
            lookup = {clave_aptitud(r[0]): r for r in aptitudes_regionales.get(region, [])}
            serie = [numero_linkedin(lookup[clave_aptitud(n)][1], porcentaje=True)
                     if clave_aptitud(n) in lookup else None for n in categorias_aptitudes]
            series.append((region, serie))
        usar_porcentaje = True
    from .linkedin_template_graphs import (
        insertar_figura, grafico_aptitudes, grafico_empresas_sectores, grafico_cargos)
    # Plantilla de mercado de 28 diapositivas: índices en plantilla_mercado.py.
    # La imagen de empresas ocupa el shape 4 de esa plantilla.
    from presentaciones import plantilla_mercado as PM
    mercado = PM.es_plantilla_mercado(prs)
    empleo_idx, demanda_idx = (PM.EMPRESAS_SECTORES, PM.DEMANDA) if mercado else (12, 13)
    aptitudes_imagen_idx, empresas_imagen_idx = (8, 4) if mercado else (9, 9)
    titulo = (f'Comparación de aptitudes demandadas: {region_local} vs. LATAM'
              if aptitudes_regionales is not None else f'Aptitudes más habituales · {region_local}')
    aptitudes_slide_idx = PM.APTITUDES if mercado else 10
    insertar_figura(prs.slides[aptitudes_slide_idx], prs.slides[aptitudes_slide_idx].shapes[aptitudes_imagen_idx],
        grafico_aptitudes([r[0] for r in aptitudes], series, titulo, usar_porcentaje),
        'Datos de aptitudes extraídos de LinkedIn')
    #------------------------------------
    if empresas is not None:
        insertar_figura(prs.slides[empleo_idx], prs.slides[empleo_idx].shapes[empresas_imagen_idx],
            grafico_empresas_sectores(empresas, sectores or []),
            'Primeros cinco sectores y empleadores: nombre y profesionales')
    if cargos is not None and demanda_idx is not None:
        insertar_figura(prs.slides[demanda_idx], prs.slides[demanda_idx].shapes[4],
            grafico_cargos(cargos), 'Primeros cinco cargos de LinkedIn; conteo de profesionales')
    # La imagen de Instituciones Educativas (shape 2) pertenece a otra fuente.

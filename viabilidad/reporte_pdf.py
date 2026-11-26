"""Reporte PDF de «Viabilidad de carreras».

Recibe el diccionario de resultados que arma ``render_dashboard`` (los mismos
DataFrames, textos y figuras que muestra Streamlit) y solo los maqueta: no
recalcula puntajes, pesos, cuadrantes, precios ni recomendaciones.
"""
from html import escape
from io import BytesIO
import math
import re
import unicodedata

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether,
                                PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)

from figuras_pdf import figura_png, fuente_reporte

NO_DATA = 'Sin información'
NO_CHART = 'No existe información suficiente para generar esta visualización.'

NAVY = colors.HexColor('#153954')
BLUE = colors.HexColor('#0072bc')
MUTED = colors.HexColor('#60758b')
SOFT = colors.HexColor('#8293a3')
BORDER = colors.HexColor('#e2e9f1')
LIGHT = colors.HexColor('#f0f6fc')
CARD = colors.HexColor('#f7f9fb')
TONES = {  # Mismas clases visuales que el tablero (quad-pill).
    'green': ('#248064', '#e8f5ee'), 'amber': ('#a46e21', '#fff5df'),
    'red': ('#b7545d', '#fceef0'), 'slate': ('#5a6f85', '#edf1f5'), 'blue': ('#0072bc', '#eaf3fc'),
}


def _fonts():
    """Century Gothic (o DejaVu Sans si no está instalada), la misma de los gráficos."""
    _, regular, bold = fuente_reporte()
    try:
        if 'Reporte' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('Reporte', str(regular)))
            pdfmetrics.registerFont(TTFont('Reporte-Bold', str(bold)))
            pdfmetrics.registerFontFamily('Reporte', normal='Reporte', bold='Reporte-Bold',
                                          italic='Reporte', boldItalic='Reporte-Bold')
        return 'Reporte', 'Reporte-Bold'
    except Exception:
        return 'Helvetica', 'Helvetica-Bold'


FONT, BOLD = _fonts()


def _style(name, size=9, color=NAVY, bold=False, leading=None, **kw):
    return ParagraphStyle(name, fontName=BOLD if bold else FONT, fontSize=size, textColor=color,
                          leading=leading or size * 1.42, **kw)


S = dict(
    eyebrow=_style('eyebrow', 7, MUTED, True, spaceAfter=4),
    title=_style('title', 24, BLUE, True, leading=29),
    subtitle=_style('subtitle', 11, MUTED),
    h2=_style('h2', 14, NAVY, True, leading=18, spaceBefore=6, spaceAfter=6),
    h3=_style('h3', 10.5, NAVY, True, spaceBefore=6, spaceAfter=3),
    body=_style('body', 9, NAVY, spaceAfter=5),
    caption=_style('caption', 8, SOFT, spaceAfter=4),
    cell=_style('cell', 7.6, NAVY, leading=10),
    head=_style('head', 7.6, MUTED, True, leading=10),
    label=_style('label', 7, MUTED, True),
    big=_style('big', 26, NAVY, True, leading=31),
    number=_style('number', 18, NAVY, True, leading=23),
    rec_title=_style('rec_title', 9, colors.HexColor('#126ba5'), True, spaceAfter=2),
    box=_style('box', 8.5, MUTED, alignment=TA_CENTER),
)


def missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def text(value):
    return NO_DATA if missing(value) else str(value)


def md(value):
    """Markdown mínimo de los textos del tablero (**negrita**) a marcado de ReportLab."""
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', escape(text(value), quote=False))


def number(value, fixed=None):
    """Igual que st.dataframe: hasta 2 decimales sin ceros sobrantes, o formato fijo."""
    if missing(value):
        return NO_DATA
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value)
    if fixed is not None:
        return f'{value:.{fixed}f}'
    return f'{value:.2f}'.rstrip('0').rstrip('.') if isinstance(value, float) else str(value)


def filename(program, date):
    clean = unicodedata.normalize('NFKD', program).encode('ascii', 'ignore').decode()
    clean = re.sub(r'[^A-Za-z0-9]+', '_', clean).strip('_') or 'carrera'
    return f'viabilidad_{clean}_{date}.pdf'


def data_table(frame, widths, fixed=None, numeric=None, size=None, pad=6):
    """Tabla con encabezado repetido en cada página y celdas que ajustan el texto."""
    fixed = fixed or {}
    numeric = set(numeric or [c for c in frame.columns if frame[c].map(lambda v: isinstance(v, (int, float))).all()])
    cell = ParagraphStyle('cellsize', parent=S['cell'], fontSize=size or 7.6, leading=(size or 7.6) * 1.32)
    head = ParagraphStyle('headsize', parent=S['head'], fontSize=size or 7.6, leading=(size or 7.6) * 1.32)
    right = ParagraphStyle('num', parent=cell, alignment=2)
    head_right = ParagraphStyle('numhead', parent=head, alignment=2)
    rows = [[Paragraph(escape(str(c)), head_right if c in numeric else head) for c in frame.columns]]
    for record in frame.itertuples(index=False):
        rows.append([Paragraph(escape(number(v, fixed.get(c))), right if c in numeric else cell)
                     for c, v in zip(frame.columns, record)])
    table = Table(rows, colWidths=widths, repeatRows=1)
    style = [('BACKGROUND', (0, 0), (-1, 0), LIGHT), ('LINEBELOW', (0, 0), (-1, -1), .4, BORDER),
             ('BOX', (0, 0), (-1, -1), .6, BORDER), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
             ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
             ('LEFTPADDING', (0, 0), (-1, -1), pad), ('RIGHTPADDING', (0, 0), (-1, -1), pad)]
    table.setStyle(TableStyle(style))
    return table


def chart(fig, width_cm, height_cm):
    if fig is None or not fig.data:
        return message_box(NO_CHART, width_cm)
    try:
        return Image(BytesIO(figura_png(fig, width_cm, height_cm)), width=width_cm * cm, height=height_cm * cm)
    except Exception:
        return message_box(NO_CHART, width_cm)


def message_box(message, width_cm):
    box = Table([[Paragraph(escape(message), S['box'])]], colWidths=[width_cm * cm], rowHeights=[2.2 * cm])
    box.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), .6, BORDER), ('BACKGROUND', (0, 0), (-1, -1), CARD),
                             ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    return box


def card(content, width, top=BORDER):
    table = Table([[content]], colWidths=[width])
    table.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), .6, BORDER), ('LINEABOVE', (0, 0), (-1, 0), 3, top),
                               ('BACKGROUND', (0, 0), (-1, -1), colors.white), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                               ('TOPPADDING', (0, 0), (-1, -1), 9), ('BOTTOMPADDING', (0, 0), (-1, -1), 10)]))
    return table


def pill(label, tone):
    fg, bg = TONES.get(tone, TONES['slate'])
    table = Table([[Paragraph(escape(label), _style('pill', 9.5, colors.HexColor(fg), True))]])
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(bg)),
                               ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
                               ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
    table.hAlign = 'LEFT'
    return table


def heading(title, subtitle=None):
    items = [Paragraph(escape(title), S['h2'])]
    if subtitle:
        items.insert(0, Paragraph(escape(subtitle).upper(), S['eyebrow']))
    return items


def rule_items(items, width):
    """Bloques de reglas del tablero: md, caption, title, latex y table."""
    flow, title = [], None
    for kind, value in items:
        if kind == 'title':  # El subtítulo viaja con el bloque siguiente.
            title = Paragraph(md(value), S['h3'])
            continue
        start = len(flow)
        if kind == 'md':
            flow.append(Paragraph(md(value), S['body']))
        elif kind == 'caption':
            flow.append(Paragraph(md(value), S['caption']))
        elif kind == 'latex':
            formula = Table([[Paragraph(escape(value[1]), _style('formula', 9.5, NAVY, True, alignment=TA_CENTER))]],
                            colWidths=[width])
            formula.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), LIGHT), ('TOPPADDING', (0, 0), (-1, -1), 8),
                                         ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]))
            flow += [formula, Spacer(1, 5)]
        elif kind == 'table':
            columns = len(value.columns)
            flow += [data_table(value, [width / columns] * columns), Spacer(1, 6)]
        if title is not None:
            flow.insert(start, KeepTogether([title, flow.pop(start)]))
            title = None
    return flow


def build_viability_pdf(r):
    """Devuelve el PDF (bytes) a partir de los resultados ya calculados por la pestaña."""
    buffer = BytesIO()
    program, reference, level, generated = r['programa'], r['referencia'], r['nivel'], r['generado']
    portrait = A4
    margin = 1.7 * cm

    def decorate(canvas, doc):
        width, height = canvas._pagesize
        canvas.saveState()
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(.6)
        canvas.line(margin, height - 1.15 * cm, width - margin, height - 1.15 * cm)
        canvas.line(margin, 1.15 * cm, width - margin, 1.15 * cm)
        canvas.setFont(BOLD, 7)
        canvas.setFillColor(BLUE)
        canvas.drawString(margin, height - .95 * cm, 'RESULTADOS DE VIABILIDAD')
        canvas.setFont(FONT, 7)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(width - margin, height - .95 * cm, 'Modelo exploratorio · comparativo académico')
        canvas.drawString(margin, .75 * cm, f'{program} frente a {reference} · {level} · generado {generated}')
        canvas.drawRightString(width - margin, .75 * cm, f'Página {doc.page}')
        canvas.restoreState()

    doc = BaseDocTemplate(buffer, pagesize=portrait, title=f'Resultados de viabilidad · {program}',
                          author='Observatorio · Viabilidad académica', subject=f'{program} frente a {reference}')
    doc.addPageTemplates([
        PageTemplate('vertical', [Frame(margin, 1.5 * cm, portrait[0] - 2 * margin, portrait[1] - 3 * cm, id='v')],
                     onPage=decorate, pagesize=portrait),
    ])
    W = (portrait[0] - 2 * margin) / cm   # ancho útil, cm (todas las páginas en A4 vertical)
    story = []

    # Cabecera
    story += [Paragraph('MODELO DE APERTURA · COMPARATIVO ACADÉMICO', S['eyebrow']),
              Paragraph('Resultados de viabilidad', S['title']),
              Paragraph(f'{escape(program)} <font color="#b7c3cf">/</font> frente a {escape(reference)}', S['subtitle']),
              Spacer(1, 10)]
    meta = [['Carrera evaluada', program], ['Carrera de referencia', reference], ['Nivel de evaluación', level],
            ['Fecha de generación', generated], ['Tipo de análisis', 'Modelo exploratorio']]
    meta_table = Table([[Paragraph(escape(k), S['label']), Paragraph(escape(v), S['body'])] for k, v in meta],
                       colWidths=[4.5 * cm, (W - 4.5) * cm])
    meta_table.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -1), .4, BORDER), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                    ('BACKGROUND', (0, 0), (0, -1), CARD)]))
    story += [meta_table, Spacer(1, 14)]

    # Resumen ejecutivo
    s = r['resumen']
    third = (W * cm - 16) / 3
    in_range = s['precio_en_rango']
    price_tone = TONES['green' if in_range else 'red'][0]
    cards = Table([[
        card([Paragraph('ÍNDICE COMPARATIVO PONDERADO', S['label']), Spacer(1, 4),
              Paragraph(f'{number(s["total"], 1)}<font size="11" color="#8b9baa"> / 100</font>', S['big']),
              pill(s['clasificacion'], 'blue'),
              Spacer(1, 4), Paragraph(f'Referencia: {number(s["total_referencia"], 0)} puntos', S['caption'])],
             third, BLUE),
        card([Paragraph('POSICIÓN EN EL MERCADO', S['label']), Spacer(1, 6), pill(s['cuadrante'], s['tono_cuadrante']),
              Spacer(1, 6), Paragraph(f'{text(s["competidores_texto"])} competidores', S['caption'])], third),
        card([Paragraph('PRECIO FRENTE A LA MEDIA', S['label']), Spacer(1, 6),
              Paragraph(text(s['brecha_texto']), S['number']),
              Paragraph(f'<font color="{price_tone}">{escape(s["lectura_precio"])}</font>', S['caption'])], third),
    ]], colWidths=[third + 8, third + 8, third])
    cards.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                               ('RIGHTPADDING', (0, 0), (-1, -1), 8)]))
    story += heading('Resumen ejecutivo') + [cards, Spacer(1, 12)]

    # Configuración del modelo
    c = r['configuracion']
    weights = Table([[Paragraph(escape(b), S['head']) for b in c['bloques']],
                     [Paragraph(f'{p}%', _style('w', 12, BLUE, True)) for p in c['pesos']]],
                    colWidths=[W * cm / 5] * 5)
    weights.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), .6, BORDER), ('INNERGRID', (0, 0), (-1, -1), .4, BORDER),
                                 ('BACKGROUND', (0, 0), (-1, 0), LIGHT), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    story += [CondPageBreak(9 * cm)] + heading('Configuración del modelo') + [
        Paragraph(md(c['nota']), S['caption']), weights, Spacer(1, 6),
        Paragraph(f'<b>Umbral de búsquedas:</b> {number(c["umbral_busquedas"])}% frente a {escape(reference)} · '
                  f'<b>Límite de competencia · {escape(level)}:</b> {number(c["limite_competencia"])} competidores',
                  S['body']),
        Paragraph('<b>Subpesos por indicador</b> (peso máximo en puntos con los pesos activos)', S['body']),
        data_table(c['subpesos'], [(W - 3) * cm, 3 * cm], numeric=['Peso máximo (puntos)']), Spacer(1, 4),
        Paragraph(md(c['subpesos_texto']), S['caption'])]

    # Perfil del programa
    p = r['perfil']
    ranks = [Paragraph('FORTALEZAS · TOP 2', _style('top', 7, BLUE, True, spaceAfter=4))]
    ranks += [Table([[Paragraph(escape(n), S['cell']), Paragraph(f'<b>{v:.1f}%</b>', _style('v', 8, BLUE))]],
                    colWidths=[4.2 * cm, 1.6 * cm]) for n, v in p['fortalezas']] or [Paragraph(p['sin_fortalezas'], S['caption'])]
    ranks += [Spacer(1, 10), Paragraph('MAYORES BRECHAS · BOTTOM 2', _style('low', 7, MUTED, True, spaceAfter=4))]
    ranks += [Table([[Paragraph(escape(n), S['cell']), Paragraph(f'<b>{v:.1f}%</b>', _style('v2', 8, colors.HexColor('#bd7c2e')))]],
                    colWidths=[4.2 * cm, 1.6 * cm]) for n, v in p['brechas']]
    profile = Table([[chart(p['figura'], W - 6.6, 8.2), ranks]], colWidths=[(W - 6.4) * cm, 6.4 * cm])
    profile.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
    story += [PageBreak()] + heading('Perfil del programa', '5 dimensiones') + [profile,
              Paragraph(f'Programa seleccionado: {escape(program)}. Línea discontinua: máximo del modelo (100).', S['caption'])]

    # Recomendaciones
    recs = []
    for i, (title, body) in enumerate(r['recomendaciones'], 1):
        recs.append(Table([[Paragraph(f'{i:02}', _style('idx', 8, BLUE, True, alignment=TA_CENTER)),
                            [Paragraph(escape(title), S['rec_title']), Paragraph(escape(body), S['body'])]]],
                          colWidths=[1 * cm, (W - 1) * cm]))
        recs[-1].setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LINEBELOW', (0, 0), (-1, -1), .4, BORDER),
                                      ('BACKGROUND', (0, 0), (0, 0), LIGHT)]))
    story += [Spacer(1, 6), KeepTogether(heading('Recomendaciones', 'Según los resultados') + recs)]

    # Demanda vs. competencia y formación del resultado
    m = r['mercado']
    story += [PageBreak()] + heading('Demanda vs. competencia', 'La zona verde es el objetivo') + [
        chart(m['figura'], W, 9.5), Paragraph(escape(m['nota']), S['caption']),
        Paragraph(escape(m['alcance']), S['caption']), Spacer(1, 10)]
    f = r['formacion']
    story += [KeepTogether(heading('Cómo se forma el resultado') + [
        Paragraph(escape(f['nota']), S['caption']),
        data_table(f['tabla'], [W * .46 * cm, W * .18 * cm, W * .18 * cm, W * .18 * cm], fixed={'Aporte': 2},
                   numeric=['Puntaje', 'Peso', 'Aporte']),
        Spacer(1, 6), Paragraph(f'<b>Índice ponderado:</b> {escape(f["indice"])}', _style('idx2', 12, NAVY))])]

    # Sensibilidad de precio
    pr = r['precio']
    summary = Table([[[Paragraph('RANGO ACEPTABLE · PMC–PME', S['label']), Paragraph(escape(pr['rango']), S['number'])],
                      [Paragraph('UDLA · MEDIANA DEL PERÍODO', S['label']),
                       Paragraph(escape(pr['precio_udla']), _style('udla', 18, colors.HexColor('#bd535e'), True, leading=23))]],
                     [[Paragraph('POSICIÓN FRENTE AL RANGO', S['label']), Paragraph(escape(pr['posicion']), S['h3'])],
                      [Paragraph('PROGRAMA EVALUADO', S['label']), Paragraph(escape(program), S['h3'])]]],
                    colWidths=[W * .5 * cm, W * .5 * cm])
    summary.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -1), .6, BORDER), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                 ('LEFTPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 7)]))
    story += [PageBreak()] + heading('Sensibilidad de precio', 'Van Westendorp · precios observados') + [
        summary, Spacer(1, 8), chart(pr['figura'], W, 10.5), Paragraph(escape(pr['nota']), S['caption'])]

    # Indicadores y valores originales
    ind = r['indicadores']
    story += [PageBreak()] + heading('Indicadores y valores originales') + [Paragraph(md(ind['explicacion']), S['caption']),
        data_table(ind['tabla'], [W * x * cm for x in (.27, .14, .19, .14, .13, .13)], size=7.2,
                   numeric=['Índice aplicado (máx. 100)', 'Peso máximo (puntos)', 'Aporte al total'])]
    story += [Spacer(1, 6)] + [Paragraph(md(n), S['caption']) for n in ind['notas']]
    informative = ind['informativo']
    story += [Paragraph('<b>Dato informativo</b>', S['body']),
              data_table(informative, [W / len(informative.columns) * cm] * len(informative.columns))]

    # Comparar las 12 carreras
    comp = r['comparativo']
    story += [PageBreak()] + heading(comp['titulo'], 'Comparar las carreras') + [Paragraph(escape(comp['nota']), S['caption']),
              chart(comp['figura'], W, 9.5), Spacer(1, 8),
              Paragraph('<b>Tabla comparativa</b>', S['body']),
              data_table(comp['tabla'], [W * x * cm for x in (.15, .07, .12, .12, .1, .125, .105, .105, .105)], pad=3,
                         fixed={'Índice': 2}, size=6.8, numeric=[col for col in comp['tabla'].columns if col not in ('Carrera', 'Lectura', 'Cuadrante')])]

    # Reglas del modelo
    rules = r['reglas']
    story += [PageBreak()] + heading('Reglas del modelo', 'Reglas acordadas, a la vista')
    for part in ('intro', 'col1', 'col2', 'resto'):
        story += rule_items(rules[part], W * cm)

    doc.build(story)
    return buffer.getvalue()

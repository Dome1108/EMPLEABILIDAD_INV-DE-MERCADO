"""Presentación .pptx de la pestaña Diagnóstico EdCo.

Replica el contenido del diagnóstico (resultado, perfil, orientación, propuesta
académica y las cinco dimensiones) con los filtros activos en la sesión. Los
gráficos se dibujan con el mismo convertidor sin navegador del reporte PDF;
la matriz de contenidos y las tablas se insertan como tablas editables.
"""
from copy import deepcopy
from datetime import date
from io import BytesIO
import re
import unicodedata

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from competencia_edcos import filas_contenidos, lectura_ejecutiva, posicionamiento, resumen_contenidos
from edcos_presentacion import pilares_propuesta
from figuras_pdf import figura_png
from graficos_edcos import grafico_dimension, monedas_precio, ofertas_precio, radar_edco
from habilidades_edcos import resumir_habilidades
from modelo_edcos import DIMENSIONES_EDCO, INSTITUCIONES_EDCO

FONT = 'Arial'
NAVY = RGBColor(0x18, 0x39, 0x51)
BLUE = RGBColor(0x26, 0x76, 0xAE)
MUTED = RGBColor(0x60, 0x75, 0x8B)
SOFT = RGBColor(0x8A, 0x9C, 0xAD)
LINE = RGBColor(0xE1, 0xEA, 0xF2)
PALE = RGBColor(0xF3, 0xF7, 0xFB)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)
MARGIN = Inches(.6)
CONTENT_W = SLIDE_W - 2 * MARGIN
TODOS_TIPOS = ['Institucional', 'Plataforma', 'Oferta propia']


def _rgb(value):
    value = value.lstrip('#')
    return RGBColor(int(value[:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def _text(slide, x, y, w, h, text, size=12, color=NAVY, bold=False, align=PP_ALIGN.LEFT,
          anchor=MSO_ANCHOR.TOP, spacing=None, link=None):
    box = slide.shapes.add_textbox(x, y, w, h)
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    for i, line in enumerate(str(text).split('\n')):
        paragraph = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        paragraph.alignment = align
        paragraph.font.size = Pt(size)
        if spacing:
            paragraph.line_spacing = spacing
        run = paragraph.add_run()
        run.text = line
        _font(run.font, size, color, bold)
        if link:
            run.hyperlink.address = link
    return box


def _font(font, size, color=NAVY, bold=False):
    font.name = FONT
    font.size = Pt(size)
    font.bold = bold
    font.color.rgb = color


def _rect(slide, x, y, w, h, fill=WHITE, line=LINE, shape=MSO_SHAPE.RECTANGLE):
    item = slide.shapes.add_shape(shape, x, y, w, h)
    item.shadow.inherit = False
    if fill is None:
        item.fill.background()
    else:
        item.fill.solid()
        item.fill.fore_color.rgb = fill
    if line is None:
        item.line.fill.background()
    else:
        item.line.color.rgb = line
        item.line.width = Pt(.75)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        item.adjustments[0] = .06
    return item


def _fit(text, sizes, limits):
    """Tamaño de letra según la longitud del texto (python-pptx no autoajusta)."""
    length = len(text or '')
    for size, limit in zip(sizes, limits):
        if length <= limit:
            return size
    return sizes[-1]


def _short(text, limit):
    text = re.sub(r'\s+', ' ', str(text or '')).strip()
    return text if len(text) <= limit else text[:limit - 1].rsplit(' ', 1)[0] + '…'


def _picture(slide, fig, x, y, w, h):
    png = figura_png(fig, Emu(w).cm, Emu(h).cm)
    slide.shapes.add_picture(BytesIO(png), x, y, w, h)


class _Deck:
    def __init__(self, ficha, result):
        self.ficha = ficha
        self.result = result
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = SLIDE_W, SLIDE_H
        self.blank = self.prs.slide_layouts[6]
        self.footer = f"{ficha['nombre']} · {INSTITUCIONES_EDCO[ficha['institucion_id']]['etiqueta']}"
        self.sources = {s['id']: s for s in ficha['fuentes']}

    def slide(self, kicker, title, subtitle=None):
        slide = self.prs.slides.add_slide(self.blank)
        _text(slide, MARGIN, Inches(.45), Inches(9), Inches(.3), kicker.upper(), 10, BLUE, True)
        _text(slide, MARGIN, Inches(.72), Inches(9.6), Inches(.6), title, 26, NAVY, True)
        if subtitle:
            _text(slide, Inches(9.2), Inches(.55), Inches(3.53), Inches(.8), subtitle, 10, SOFT,
                  align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.BOTTOM)
        _rect(slide, MARGIN, Inches(1.45), CONTENT_W, Pt(1), LINE, None)
        number = len(self.prs.slides)
        _text(slide, MARGIN, Inches(7.05), Inches(10), Inches(.25), self.footer, 8, SOFT)
        _text(slide, SLIDE_W - MARGIN - Inches(1), Inches(7.05), Inches(1), Inches(.25), str(number), 8, SOFT,
              align=PP_ALIGN.RIGHT)
        return slide

    def notes(self, slide, text):
        slide.notes_slide.notes_text_frame.text = text

    def source_lines(self, ids):
        lines = []
        for sid in ids:
            item = self.sources.get(sid)
            if not item:
                continue
            detail = item.get('url') or item.get('archivo') or ('páginas ' + item.get('paginas', '—'))
            lines.append(f"- {item['titulo']} · {detail} · {item.get('fecha', '')}")
        return lines

    def table(self, slide, x, y, w, rows, widths, size=9, row_h=Inches(.3), header_fill=NAVY, align=None):
        shape = slide.shapes.add_table(len(rows), len(rows[0]), x, y, w, row_h * len(rows))
        table = shape.table
        total = sum(widths)
        for i, width in enumerate(widths):
            table.columns[i].width = int(w * width / total)
        for r, values in enumerate(rows):
            table.rows[r].height = row_h
            for c, value in enumerate(values):
                cell = table.cell(r, c)
                cell.margin_left = cell.margin_right = Inches(.06)
                cell.margin_top = cell.margin_bottom = Inches(.03)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                cell.fill.solid()
                cell.fill.fore_color.rgb = header_fill if r == 0 else (WHITE if r % 2 else PALE)
                frame = cell.text_frame
                frame.word_wrap = True
                paragraph = frame.paragraphs[0]
                paragraph.alignment = (align[c] if align else PP_ALIGN.LEFT)
                paragraph.font.size = Pt(size)  # evita que una celda vacía use 18 pt
                run = paragraph.add_run()
                run.text = '' if value is None else str(value)
                _font(run.font, size, WHITE if r == 0 else NAVY, r == 0)
        return table


def _score(value):
    return '—' if value is None else f'{round(value, 1):g}'


def _price_range(ficha):
    ranges = []
    for currency in monedas_precio(ficha):
        prices = [o['precio_' + currency.lower()] for o in ofertas_precio(ficha, currency)]
        ranges.append(f'{currency} {min(prices):,.0f} — {max(prices):,.0f}')
    return '\n'.join(ranges) or 'Sin precios verificados'


def _portada(deck):
    ficha, result = deck.ficha, deck.result
    slide = deck.prs.slides.add_slide(deck.blank)
    _rect(slide, 0, 0, Inches(.18), SLIDE_H, BLUE, None)
    _text(slide, Inches(.9), Inches(.9), Inches(11), Inches(.3), 'EDUCACIÓN CONTINUA · VIABILIDAD DE NUEVAS PROPUESTAS', 11, BLUE, True)
    _text(slide, Inches(.9), Inches(1.35), Inches(11.4), Inches(1.7), ficha['nombre'], _fit(ficha['nombre'], [40, 34, 28], [40, 60, 200]), NAVY, True)
    _text(slide, Inches(.9), Inches(3.05), Inches(11), Inches(.4),
          INSTITUCIONES_EDCO[ficha['institucion_id']]['etiqueta'] + ' · Diagnóstico EdCo', 16, MUTED)
    score = '—' if result['total'] is None else f"{result['total']:.1f}"
    _rect(slide, Inches(.9), Inches(4.05), Inches(5.4), Inches(2.35), WHITE, LINE, MSO_SHAPE.ROUNDED_RECTANGLE)
    _rect(slide, Inches(.9), Inches(4.05), Inches(5.4), Inches(.07), BLUE, None)
    _text(slide, Inches(1.2), Inches(4.35), Inches(4.8), Inches(.3), 'RESULTADO DE VIABILIDAD', 10, MUTED, True)
    box = _text(slide, Inches(1.2), Inches(4.7), Inches(4.8), Inches(1), score, 54, NAVY, True)
    run = box.text_frame.paragraphs[0].add_run()
    run.text = ' / 100'
    _font(run.font, 18, SOFT)
    pill = _rect(slide, Inches(1.2), Inches(5.8), Inches(3.2), Inches(.4), PALE, None, MSO_SHAPE.ROUNDED_RECTANGLE)
    pill.adjustments[0] = .5
    _text(slide, Inches(1.2), Inches(5.8), Inches(3.2), Inches(.4), result['estado'], 12, BLUE, True, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
    _rect(slide, Inches(6.6), Inches(4.05), Inches(5.8), Inches(2.35), WHITE, LINE, MSO_SHAPE.ROUNDED_RECTANGLE)
    _rect(slide, Inches(6.6), Inches(4.05), Inches(5.8), Inches(.07), LINE, None)
    _text(slide, Inches(6.9), Inches(4.35), Inches(5.2), Inches(.3), 'REFERENCIAS DE PRECIO · MERCADO', 10, MUTED, True)
    _text(slide, Inches(6.9), Inches(4.75), Inches(5.2), Inches(.9), _price_range(ficha), 22, NAVY, True)
    _text(slide, Inches(6.9), Inches(5.75), Inches(5.2), Inches(.5),
          f"Rango publicado, incluye cohortes históricas.\nRevisión: {ficha['fecha_revision']}", 10, MUTED)
    _text(slide, Inches(.9), Inches(6.75), Inches(11.5), Inches(.3),
          f'Generado el {date.today():%d/%m/%Y} desde el tablero de viabilidad · Investigación inicial', 9, SOFT)
    if result['total'] is None:
        deck.notes(slide, 'El resultado final se mantiene en evaluación: las dimensiones sin evidencia suficiente no se sustituyen por cero ni por una nota promedio.')


def _perfil(deck):
    ficha, result = deck.ficha, deck.result
    slide = deck.slide('Diagnóstico EdCo', 'Perfil de viabilidad', '5 dimensiones · pesos del modelo EdCo')
    _picture(slide, radar_edco(result), MARGIN, Inches(1.7), Inches(6.2), Inches(5.1))
    rows = [['Dimensión', 'Peso', 'Puntaje', 'Aporte']]
    for row in result['filas']:
        rows.append([row['dimension'], f"{row['peso']}%", 'Sin calificar' if row['puntaje'] is None else _score(row['puntaje']),
                     '—' if row['aporte'] is None else f"{row['aporte']:.2f}"])
    rows.append(['Total', '100%', '', '—' if result['total'] is None else f"{result['total']:.1f}"])
    x = Inches(7.1)
    table = deck.table(slide, x, Inches(2.1), SLIDE_W - MARGIN - x, rows, [3.2, 1, 1.3, 1.2], 12, Inches(.48),
                       align=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.CENTER])
    for c in range(4):
        table.cell(len(rows) - 1, c).text_frame.paragraphs[0].runs[0].font.bold = True
    pending = [r['dimension'] for r in result['filas'] if r['puntaje'] is None]
    note = ('Sin calificar: ' + ' · '.join(pending) + '. No se dibujan como cero.') if pending else 'Aporte = puntaje de la dimensión × peso ÷ 100.'
    _text(slide, x, Inches(5.65), SLIDE_W - MARGIN - x, Inches(.6), note, 10, MUTED)
    _text(slide, x, Inches(6.15), SLIDE_W - MARGIN - x, Inches(.6), 'Estado: ' + result['estado'], 13, BLUE, True)


def _orientacion(deck):
    items = deck.ficha['recomendaciones']
    slide = deck.slide('Diagnóstico EdCo', 'Orientación para la propuesta')
    longest = max([len(i['texto']) for i in items] + [0])
    size = _fit('x' * longest, [14, 12, 11, 10], [160, 260, 340, 10_000])
    top, height = Inches(1.75), Inches(5.15)
    step = height / max(1, len(items))
    for i, item in enumerate(items, 1):
        y = top + step * (i - 1)
        _text(slide, MARGIN, y, Inches(.8), step, f'{i:02}', 26, _rgb('#c0d1e0'), True)
        _text(slide, MARGIN + Inches(.9), y + Inches(.05), Inches(2.9), step - Inches(.1), item['titulo'], 14, NAVY, True)
        _text(slide, MARGIN + Inches(3.9), y + Inches(.05), CONTENT_W - Inches(3.9), step - Inches(.1), item['texto'], size, MUTED, spacing=1.1)
        if i < len(items):
            _rect(slide, MARGIN + Inches(.9), int(y + step - Inches(.08)), CONTENT_W - Inches(.9), Pt(1), LINE, None)


def _propuesta(deck):
    ficha = deck.ficha
    pillars = pilares_propuesta(ficha)
    segments = ficha['audiencia_propuesta']['segmentos']
    slide = deck.slide('La propuesta académica', 'Qué hace diferente al programa', 'Ejes que definen su enfoque y aplicación profesional.')
    columns = 3 if len(pillars) != 4 else 2
    grid_rows = max(1, -(-len(pillars) // columns))
    gap = Inches(.25)
    area_h = Inches(3.55 if segments else 5.1) if grid_rows > 1 else Inches(2.9)
    card_w = int((CONTENT_W - gap * (columns - 1)) / columns)
    card_h = int((area_h - gap * (grid_rows - 1)) / grid_rows)
    longest = max([len(p[2]) for p in pillars] + [0])
    size = _fit('x' * longest, [13, 12, 11, 10], [120, 170, 220, 10_000]) if grid_rows == 1 else _fit('x' * longest, [11, 10, 9], [140, 190, 10_000])
    for i, (title, tag, summary, _icon, accent) in enumerate(pillars):
        x = MARGIN + (card_w + gap) * (i % columns)
        y = Inches(1.75) + (card_h + gap) * (i // columns)
        _rect(slide, x, y, card_w, card_h, WHITE, LINE)
        _rect(slide, x, y, Inches(.07), card_h, _rgb(accent), None)
        _text(slide, x + Inches(.3), y + Inches(.2), card_w - Inches(.5), Inches(.25), tag.upper(), 8, SOFT, True)
        _text(slide, x + Inches(.3), y + Inches(.45), card_w - Inches(.5), Inches(.6), title, 15 if grid_rows == 1 else 13, NAVY, True)
        _text(slide, x + Inches(.3), y + Inches(1.0 if grid_rows == 1 else .85), card_w - Inches(.5), card_h - Inches(1.1), summary, size, MUTED, spacing=1.1)
    if segments:
        y = Inches(5.55)
        _text(slide, MARGIN, y, Inches(2.6), Inches(.35), 'A quién se dirige', 15, NAVY, True)
        _text(slide, MARGIN, y + Inches(.4), Inches(2.6), Inches(.6), 'Segmentos sugeridos a partir del brief.', 9, SOFT)
        x0 = MARGIN + Inches(2.9)
        seg_w = int((SLIDE_W - MARGIN - x0) / len(segments))
        seg_size = _fit('x' * max(len(s) for s in segments), [11, 10, 9], [50, 80, 10_000])
        for i, text in enumerate(segments):
            x = x0 + seg_w * i
            _rect(slide, x, y, Inches(.03), Inches(1.15), _rgb('#d8e5f0'), None)
            _text(slide, x + Inches(.15), y, seg_w - Inches(.3), Inches(.25), f'{i + 1:02}', 9, SOFT)
            _text(slide, x + Inches(.15), y + Inches(.28), seg_w - Inches(.3), Inches(.9), text, seg_size, NAVY, True)
    notes = ['Diferenciadores descritos por el proponente:'] + [f'- {d}' for d in ficha['brief']['diferenciadores']]
    if ficha['audiencia_propuesta'].get('origen'):
        notes.append(ficha['audiencia_propuesta']['origen'])
    deck.notes(slide, '\n'.join(notes))


def _dimension_slide(deck, index, key, label, weight, kicker_suffix=''):
    criterion = deck.ficha['evaluacion'][key]
    slide = deck.slide(f'Evidencia de mercado · {index:02}{kicker_suffix}', label)
    score = _score(criterion['puntaje'])
    box = _text(slide, Inches(9.6), Inches(.6), Inches(3.13), Inches(.6), score, 30, BLUE, True, PP_ALIGN.RIGHT)
    run = box.text_frame.paragraphs[0].add_run()
    run.text = ' /100'
    _font(run.font, 12, SOFT)
    _text(slide, Inches(9.6), Inches(1.12), Inches(3.13), Inches(.25), f'Peso en el modelo · {weight}%', 9, SOFT, align=PP_ALIGN.RIGHT)
    evidence = deck.ficha['evidencia_visual'][key]
    notes = [f'{label} · {score}/100 · peso {weight}%', '', 'Interpretación:', criterion.get('justificacion', '')]
    if evidence.get('fecha_consulta'):
        notes += ['', 'Consulta: ' + evidence['fecha_consulta'] + ' · ' + evidence.get('actualidad', '')]
    lines = deck.source_lines(evidence.get('fuentes', []))
    if lines:
        notes += ['', 'Fuentes:'] + lines
    deck.notes(slide, '\n'.join(notes))
    return slide


def _caption(slide, text, y=Inches(6.55), h=Inches(.45)):
    if text:
        _text(slide, MARGIN, y, CONTENT_W, h, _short(text, 330), 9, MUTED, spacing=1.05)


def _metrics(deck, slide, values, x, y, w):
    gap = Inches(.2)
    card_w = int((w - gap * (len(values) - 1)) / len(values))
    for i, (label, value) in enumerate(values):
        cx = x + (card_w + gap) * i
        _rect(slide, cx, y, card_w, Inches(1), WHITE, LINE)
        _text(slide, cx + Inches(.2), y + Inches(.12), card_w - Inches(.4), Inches(.35), label, 9, MUTED)
        _text(slide, cx + Inches(.2), y + Inches(.45), card_w - Inches(.4), Inches(.5), str(value), 24, NAVY, True)


def _demanda(deck, index, key, label, weight):
    ficha = deck.ficha
    evidence = ficha['evidencia_visual'][key]
    slide = _dimension_slide(deck, index, key, label, weight)
    if evidence.get('serie'):
        _text(slide, MARGIN, Inches(1.65), CONTENT_W, Inches(.35), evidence['titulo'], 14, NAVY, True)
        _picture(slide, grafico_dimension(ficha, key), MARGIN, Inches(2.05), CONTENT_W, Inches(4.35))
        _caption(slide, evidence.get('nota'))
        return
    _text(slide, MARGIN, Inches(1.65), CONTENT_W, Inches(.35), 'Participación registrada en cursos relacionados', 14, NAVY, True)
    observations = evidence.get('observaciones', [])
    columns = min(4, max(1, len(observations)))
    grid_rows = max(1, -(-len(observations) // columns))
    gap = Inches(.2)
    card_w = int((CONTENT_W - gap * (columns - 1)) / columns)
    card_h = Inches(1.75 if grid_rows == 1 else 1.55)
    for i, row in enumerate(observations):
        platform, _, course = row['etiqueta'].partition(' · ')
        x = MARGIN + (card_w + gap) * (i % columns)
        y = Inches(2.15) + (card_h + gap) * (i // columns)
        _rect(slide, x, y, card_w, card_h, WHITE, LINE)
        _rect(slide, x, y, card_w, Inches(.05), _rgb('#6396c2'), None)
        _text(slide, x + Inches(.2), y + Inches(.15), card_w - Inches(.4), Inches(.3), platform, 11, NAVY, True)
        _text(slide, x + Inches(.2), y + Inches(.42), card_w - Inches(.4), Inches(.5), f"{row['valor']:,.0f}".replace(',', '.'), 24, BLUE, True)
        _text(slide, x + Inches(.2), y + Inches(.88), card_w - Inches(.4), Inches(.2), 'inscripciones acumuladas', 8, SOFT)
        source = deck.sources.get(row.get('fuente'), {})
        _text(slide, x + Inches(.2), y + Inches(1.1), card_w - Inches(.4), card_h - Inches(1.15), _short(course, 70), 9, MUTED,
              link=source.get('url'))
    reading = evidence.get('lectura', 'Estos cursos registran participación en el tema. Las cifras corresponden a cada curso, con distinta antigüedad, alcance y condiciones.')
    y = Inches(2.15) + (card_h + gap) * grid_rows + Inches(.05)
    _rect(slide, MARGIN, y, Inches(.04), Inches(.95), _rgb('#b9d3e8'), None)
    _text(slide, MARGIN + Inches(.2), y, CONTENT_W - Inches(.2), Inches(.25), 'Qué nos dice', 11, NAVY, True)
    _text(slide, MARGIN + Inches(.2), y + Inches(.28), CONTENT_W - Inches(.2), Inches(6.9) - y - Inches(.3),
          _short(reading, 420) + '\nNo se suman como personas únicas ni permiten estimar cuántos participantes tendría el programa en ' + ficha['brief']['pais'] + '.',
          10 if grid_rows == 1 else 9, MUTED, spacing=1.05)


def _empleabilidad(deck, index, key, label, weight):
    ficha = deck.ficha
    evidence = ficha['evidencia_visual'][key]
    slide = _dimension_slide(deck, index, key, label, weight)
    is_local = evidence.get('origen') == 'linkedin'
    title = 'Top 10 habilidades · participación en publicaciones' if is_local else evidence['titulo']
    _text(slide, MARGIN, Inches(1.65), CONTENT_W, Inches(.35), title, 14, NAVY, True)
    chart_x = MARGIN
    if is_local:
        summary = resumir_habilidades(evidence)
        metrics = [('Publicaciones identificadas', summary['total']), ('Organizaciones', summary['empresas']),
                   ('Habilidades analizadas', len(evidence.get('catalogo_habilidades', [])))]
        for i, (name, value) in enumerate(metrics):
            _metrics(deck, slide, [(name, value)], MARGIN, Inches(2.15) + Inches(1.15) * i, Inches(2.6))
        chart_x = MARGIN + Inches(2.9)
    if evidence.get('habilidades'):
        _picture(slide, grafico_dimension(ficha, key), chart_x, Inches(2.05), SLIDE_W - MARGIN - chart_x, Inches(4.25))
    else:
        _text(slide, chart_x, Inches(3.5), Inches(6), Inches(.5), 'No hay publicaciones para los filtros seleccionados.', 12, MUTED)
    legend_y = Inches(6.35)
    for i, (fill, text) in enumerate([('#3975b9', 'Habilidad explícita'), ('#a7c6e2', 'Habilidad homologada · asociación analítica sujeta a revisión curricular')]):
        x = chart_x + Inches(2.4) * i
        _rect(slide, x, legend_y + Inches(.05), Inches(.14), Inches(.14), _rgb(fill), None, MSO_SHAPE.OVAL)
        _text(slide, x + Inches(.22), legend_y, Inches(5.5) if i else Inches(2.1), Inches(.25), text, 9, MUTED)
    _caption(slide, 'Una publicación puede mencionar varias habilidades, por lo que las participaciones no suman 100%. Se usan habilidades descritas, no cantidad de vacantes.' if is_local else evidence.get('nota'), Inches(6.65), Inches(.35))


def _competencia(deck, index, key, label, weight, options):
    ficha = deck.ficha
    institution = INSTITUCIONES_EDCO[ficha['institucion_id']]['nombre']
    slide = _dimension_slide(deck, index, key, label, weight, ' · contenidos')
    declared = [o for o in ficha['ofertas'] if o.get('disponibilidad') == 'Inscripción declarada']
    metrics = [('Instituciones · inscripción declarada', len({o['institucion'] for o in declared if o['tipo'] == 'Institucional'})),
               ('Plataformas · sustitutos disponibles', len({o['institucion'].split(' · ')[0] for o in declared if o['tipo'] == 'Plataforma'})),
               ('Ofertas revisadas', len(ficha['ofertas']))]
    data = ficha.get('comparativa_contenidos')
    if not data:
        _metrics(deck, slide, metrics, MARGIN, Inches(1.7), CONTENT_W)
        _text(slide, MARGIN, Inches(3.1), CONTENT_W, Inches(.5), 'Esta propuesta aún no tiene una comparación de contenidos documentada.', 12, MUTED)
        return
    rows = filas_contenidos(ficha, options.get('tipos', TODOS_TIPOS), options.get('solo_inscripcion', False))
    summary_line = ' · '.join(f'{name}: {value}' for name, value in metrics)
    _text(slide, MARGIN, Inches(1.62), CONTENT_W, Inches(.3), summary_line, 11, MUTED)
    _text(slide, MARGIN, Inches(2.0), Inches(7), Inches(.3), '¿Qué contenidos declara cada programa?', 13, NAVY, True)
    _text(slide, Inches(7.8), Inches(2.02), SLIDE_W - MARGIN - Inches(7.8), Inches(.3), '✓ Declarado   · No identificado en la descripción', 9, MUTED, align=PP_ALIGN.RIGHT)
    topics = data['temas']
    proposed = dict(institucion=institution + ' · Programa propuesto', revision=data['propuesta'])
    visible = [proposed] + rows
    table_rows = [['Programa'] + [t['etiqueta'].replace('<br>', ' ') for t in topics]]
    for row in visible:
        values = [row['revision'].get('contenidos', {}).get(t['id']) for t in topics]
        table_rows.append([row['revision'].get('etiqueta', row['institucion'])] + ['✓' if v is True else '·' if v is False else '' for v in values])
    available = Inches(6.85) - Inches(2.4)
    row_h = min(Inches(.36), int(available / (len(table_rows) + 1)))
    size = 9 if len(table_rows) <= 11 else 8
    table = deck.table(slide, MARGIN, Inches(2.4), CONTENT_W, table_rows, [3.2] + [1] * len(topics), size, row_h,
                       align=[PP_ALIGN.LEFT] + [PP_ALIGN.CENTER] * len(topics))
    table.rows[0].height = row_h * 2
    for c in range(len(topics) + 1):
        cell = table.cell(1, c)
        cell.fill.fore_color.rgb = _rgb('#e3f0f2')
        cell.text_frame.paragraphs[0].runs[0].font.bold = True
    for r in range(1, len(table_rows)):
        for c in range(1, len(topics) + 1):
            run = table.cell(r, c).text_frame.paragraphs[0].runs[0]
            if run.text == '✓':
                table.cell(r, c).fill.fore_color.rgb = _rgb('#d4e6f4')
                run.font.color.rgb = _rgb('#23506e')
                run.font.size = Pt(12)
                run.font.bold = True
            else:
                run.font.color.rgb = SOFT
    deck.notes(slide, slide.notes_slide.notes_text_frame.text + '\n\nLa primera fila es la propuesta de ' + institution +
               '. Un tema no identificado no demuestra ausencia en el programa; la comparación se limita a las descripciones revisadas.\n\nCriterios:\n' +
               '\n'.join(f"- {t['etiqueta'].replace('<br>', ' ')}: {t['criterio']}" for t in topics))

    summary = resumen_contenidos(ficha, rows)
    slide = _dimension_slide(deck, index, key, label, weight, ' · lectura ejecutiva')
    if summary['total']:
        messages = lectura_ejecutiva(ficha, summary)
        columns = 3 if len(messages) != 4 else 2
        grid_rows = -(-len(messages) // columns)
        gap = Inches(.25)
        card_w = int((CONTENT_W - gap * (columns - 1)) / columns)
        card_h = int((Inches(4.6) - gap * (grid_rows - 1)) / grid_rows) if grid_rows > 1 else Inches(3)
        longest = max(len(m[1]) for m in messages)
        size = _fit('x' * longest, [13, 12, 11, 10], [150, 200, 260, 10_000]) if grid_rows == 1 else _fit('x' * longest, [11, 10, 9], [170, 240, 10_000])
        for i, (title, body) in enumerate(messages):
            x = MARGIN + (card_w + gap) * (i % columns)
            y = Inches(1.75) + (card_h + gap) * (i // columns)
            _rect(slide, x, y, card_w, card_h, WHITE, LINE)
            _rect(slide, x, y, Inches(.07), card_h, _rgb('#2879b4'), None)
            _text(slide, x + Inches(.3), y + Inches(.2), card_w - Inches(.5), Inches(.3), title.upper(), 10, BLUE, True)
            _text(slide, x + Inches(.3), y + Inches(.6), card_w - Inches(.5), card_h - Inches(.7), body, size, MUTED, spacing=1.1)
        _caption(slide, f"Base de la lectura: {summary['total']} descripciones externas revisadas. La propuesta y la oferta propia no cuentan como competencia externa; varios programas de un mismo oferente no son instituciones distintas.", Inches(1.75) + (card_h + gap) * grid_rows)
    else:
        _text(slide, MARGIN, Inches(2), CONTENT_W, Inches(.5), 'No hay descripciones externas verificadas con los filtros actuales.', 12, MUTED)

    map_ficha = deepcopy(ficha)
    if options.get('moneda_mapa'):
        map_ficha['evidencia_visual']['precio']['moneda'] = options['moneda_mapa']
    chart, missing = posicionamiento(map_ficha, rows)
    slide = _dimension_slide(deck, index, key, label, weight, ' · mapa de oferentes')
    currency = map_ficha['evidencia_visual']['precio'].get('moneda') or next(iter(monedas_precio(ficha)), 'USD')
    _text(slide, MARGIN, Inches(1.65), CONTENT_W, Inches(.35), f'Mapa de oferentes · precio frente a duración ({currency})', 14, NAVY, True)
    chart_w = CONTENT_W if not missing else Inches(7.9)
    if chart.data:
        _picture(slide, chart, MARGIN, Inches(2.05), chart_w, Inches(4.35))
    else:
        _text(slide, MARGIN, Inches(3.5), chart_w, Inches(.5), 'No hay programas con precio y horas publicados para ubicar en el mapa.', 12, MUTED)
    if missing:
        x = MARGIN + chart_w + Inches(.3)
        _text(slide, x, Inches(2.05), SLIDE_W - MARGIN - x, Inches(.3), 'Sin punto en el mapa', 11, NAVY, True)
        miss_rows = [['Oferente', 'Dato no publicado']] + [[_short(m['institucion'], 40), m['motivo']] for m in missing[:12]]
        deck.table(slide, x, Inches(2.4), SLIDE_W - MARGIN - x, miss_rows, [1.4, 1], 8, Inches(.3))
    _caption(slide, 'Cada punto representa un programa con precio y horas publicados. Derecha: más horas; arriba: mayor precio total. Las horas pueden ser académicas, de dedicación o de vídeo: el mapa no las convierte ni estima calidad o precio óptimo. Los precios en otras monedas no se convierten.')


def _precio(deck, index, key, label, weight):
    ficha = deck.ficha
    evidence = ficha['evidencia_visual'][key]
    slide = _dimension_slide(deck, index, key, label, weight)
    currency = evidence.get('moneda') or next(iter(monedas_precio(ficha)), 'USD')
    _text(slide, MARGIN, Inches(1.65), CONTENT_W, Inches(.35), f"{evidence.get('titulo', 'Precios publicados')} · {currency}", 14, NAVY, True)
    _picture(slide, grafico_dimension(ficha, key), MARGIN, Inches(2.05), Inches(5.6), Inches(4.4))
    crc = ficha['brief']['pais'] == 'Costa Rica'
    institutions = [o for o in ficha['ofertas'] if o['tipo'] == 'Institucional']
    header = ['Institución', 'Programa', 'USD'] + (['CRC'] if crc else []) + ['Horas']
    rows = [header]
    for o in institutions[:12]:
        rows.append([_short(o['institucion'], 38), _short(o['programa'], 48), '—' if o.get('precio_usd') is None else f"{o['precio_usd']:,.0f}"] +
                    (['—' if o.get('precio_crc') is None else f"{o['precio_crc']:,.0f}"] if crc else []) +
                    ['—' if o.get('horas') is None else f"{o['horas']:g}"])
    x = MARGIN + Inches(5.85)
    widths = [2.2, 2.6, 1, 1.1, .8] if crc else [2.3, 2.9, 1, .8]
    deck.table(slide, x, Inches(2.1), SLIDE_W - MARGIN - x, rows, widths, 8, Inches(.32),
               align=[PP_ALIGN.LEFT, PP_ALIGN.LEFT] + [PP_ALIGN.RIGHT] * (len(header) - 2))
    missing = [o['institucion'] for o in institutions if all(o.get('precio_' + c.lower()) is None for c in ('USD', 'CRC')) or not o.get('precio_verificado', True)]
    text = 'Precios observados en páginas consultadas; no son cotizaciones. Precio desconocido no equivale a cero.'
    if missing:
        text = 'Sin precio publicado: ' + ' · '.join(missing) + '. ' + text
    _caption(slide, text)
    platforms = [o for o in ficha['ofertas'] if o['tipo'] == 'Plataforma' and o.get('precio_usd') is not None]
    notes = slide.notes_slide.notes_text_frame.text
    if evidence.get('nota'):
        notes += '\n\n' + evidence['nota']
    if platforms:
        notes += '\n\nSustitutos introductorios · fuera del boxplot institucional:\n' + '\n'.join(f"- {o['institucion']}: USD {o['precio_usd']:,.2f} · {o['estado']}" for o in platforms)
    deck.notes(slide, notes)


def _sector(deck, index, key, label, weight):
    ficha = deck.ficha
    evidence = ficha['evidencia_visual'][key]
    slide = _dimension_slide(deck, index, key, label, weight)
    _text(slide, MARGIN, Inches(1.65), CONTENT_W, Inches(.35), evidence['titulo'], 14, NAVY, True)
    _picture(slide, grafico_dimension(ficha, key), MARGIN, Inches(2.05), CONTENT_W, Inches(4.3))
    if evidence.get('origen') == 'bccr':
        text = evidence['actividad'] + f" · IMAE, base {evidence.get('base', 2017)} = 100. " + evidence.get('alcance', '')
        if evidence.get('contexto_2026'):
            text += ' ' + evidence['contexto_2026']
    else:
        months = {r.get('meses', 12) for r in evidence.get('ventas', [])}
        text = ('2023–2025: enero–diciembre. 2026: enero–agosto, sin proyección. ' if len(months) > 1 else '') + \
               'Ventas SRI declaradas (casilleros 411 + 413) del CIIU exacto ' + str(ficha['brief']['ciiu']).replace('.', '') + '; no son transacciones de comercio electrónico ni recaudación tributaria.'
    _caption(slide, text)


def construir_pptx(ficha, resultado, opciones=None):
    """Bytes del .pptx del Diagnóstico EdCo para la ficha ya filtrada en la sesión."""
    options = opciones or {}
    deck = _Deck(ficha, resultado)
    _portada(deck)
    _perfil(deck)
    if ficha.get('recomendaciones'):
        _orientacion(deck)
    if ficha['brief'].get('diferenciadores'):
        _propuesta(deck)
    builders = {'demanda': _demanda, 'empleabilidad': _empleabilidad, 'precio': _precio, 'sector': _sector}
    for index, (key, label, weight) in enumerate(DIMENSIONES_EDCO, 1):
        if not ficha.get('evidencia_visual', {}).get(key):
            continue
        if key == 'competencia':
            _competencia(deck, index, key, label, weight, options)
        else:
            builders[key](deck, index, key, label, weight)
    output = BytesIO()
    deck.prs.save(output)
    return output.getvalue()


def nombre_archivo(ficha):
    text = unicodedata.normalize('NFKD', ficha['nombre']).encode('ascii', 'ignore').decode()
    slug = re.sub(r'[^A-Za-z0-9]+', '_', text).strip('_').lower()[:60] or ficha['id']
    return f'diagnostico_edco_{slug}.pptx'

# [Copia de Tendencias · presentation/charts/linkedin_requirements_slide.py; solo cambian las rutas de import]
# cambiado por samuel
"""Inserta requisitos de anuncios entre aptitudes y ubicación geográfica."""
from copy import deepcopy
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from presentaciones.graficos.linkedin import reemplazar_grafico
from presentaciones.graficos.linkedin_texto import resumir_requisitos


def insertar_requisitos(prs, detalle, region, habilidades_homologadas=None):
    # La plantilla de mercado tiene aptitudes en la diapositiva 10 y reserva
    # la 11 para habilidades solicitadas (índices en plantilla_mercado.py).
    from presentaciones import plantilla_mercado as PM
    existente = PM.es_plantilla_mercado(prs)
    origen = prs.slides[PM.APTITUDES] if existente else prs.slides[10]
    slide = prs.slides[PM.HABILIDADES] if existente else prs.slides.add_slide(origen.slide_layout)
    for shape in list(slide.shapes):
        slide.shapes._spTree.remove(shape._element)
    titulo_idx = 9 if existente else 8
    for idx in (0, 6, 7, titulo_idx):
        slide.shapes._spTree.insert_element_before(deepcopy(origen.shapes[idx]._element), 'p:extLst')
    footer, nota, resumen, titulo = list(slide.shapes)
    for shape, texto in ((footer, 'Fuente: anuncios de empleo de LinkedIn'),
                         (nota, 'Habilidades solicitadas en «Acerca del empleo» · ' + region),
                         (titulo.shapes[0], 'HABILIDADES MÁS SOLICITADAS')):
        shape.text_frame.paragraphs[0].runs[0].text = texto
        for run in shape.text_frame.paragraphs[0].runs[1:]:
            run.text = ''
    footer.left, footer.width = Inches(9.1), Inches(3.4)
    vacantes = detalle.get('vacantes', []) if detalle else []
    if habilidades_homologadas:
        top = [
            (str(row.get('nombre_normalizado') or row.get('nombre') or '').strip(),
             int(round(float(row.get('frecuencia_total') or row.get('profesionales') or 0))))
            for row in sorted(habilidades_homologadas,
                              key=lambda item: float(item.get('frecuencia_total') or item.get('profesionales') or 0),
                              reverse=True)[:6]
            if str(row.get('nombre_normalizado') or row.get('nombre') or '').strip()
        ]
    else:
        top = resumir_requisitos(vacantes, limite=6, solo_habilidades=True)
    placeholder = slide.shapes.add_textbox(Inches(.63), Inches(1.47), Inches(7.96), Inches(3.95))
    reemplazar_grafico(slide, placeholder, 'Habilidades repetidas en los anuncios',
                      [n if len(n) <= 60 else n[:57] + '…' for n, _ in top],
                      [('Anuncios que lo solicitan', [c for _, c in top])],
                      colores=('A6CAEC',))
    mensaje = ('Sin descripciones de vacantes disponibles para este estudio.'
               if not detalle else
               f"Se leyeron {len(vacantes)} de {detalle.get('enlaces_detectados', len(vacantes))} anuncios detectados. "
               'Cada habilidad cuenta una vez por anuncio. Se muestran las que aparecen al menos en dos. '
               'Se excluyen títulos, años de experiencia, residencia y disponibilidad.')
    if detalle and not top:
        mensaje += ' No se encontraron habilidades repetidas.'
    resumen.text_frame.paragraphs[0].runs[0].text = mensaje
    for paragraph in resumen.text_frame.paragraphs:
        for run in paragraph.runs:
            run.font.size = Pt(11)
    filas = top or [('Sin habilidades repetidas' if detalle else 'Sin datos disponibles', 'N/D')]
    tabla = slide.shapes.add_table(len(filas) + 1, 2, Inches(9), Inches(1.49), Inches(3.75),
                                   Inches(.35 + .65 * len(filas))).table
    tabla.rows[0].height = Inches(.35)
    for row in list(tabla.rows)[1:]:
        row.height = Inches(.65)
    tabla.columns[0].width = Inches(3.15)
    tabla.columns[1].width = Inches(.6)
    for i, datos in enumerate([('Habilidad', 'N.º')] + filas):
        for j, valor in enumerate(datos):
            celda = tabla.cell(i, j)
            celda.text = str(valor)
            celda.fill.solid()
            celda.fill.fore_color.rgb = RGBColor.from_string('006DBF' if i == 0 else 'E6F0F8')
            for paragraph in celda.text_frame.paragraphs:
                paragraph.font.size = Pt(11)
                paragraph.font.color.rgb = RGBColor.from_string('FFFFFF' if i == 0 else '222222')
    slide.notes_slide.notes_text_frame.text = '\n'.join(
        f"{v.get('titulo', '')}: {v['url']}\n" + '\n'.join(v.get('requisitos', [])) for v in vacantes)
    if not existente:
        orden = prs.slides._sldIdLst
        nuevo = orden[-1]
        orden.remove(nuevo)
        orden.insert(11, nuevo)
    return slide
#------------------------------------

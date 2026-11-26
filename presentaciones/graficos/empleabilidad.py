"""[Copia de Tendencias · presentation/charts, adaptada al observatorio] Diapositiva 16 · Empleabilidad: tarjetas por corte, composición y banda salarial.

Replica la vista "Empleo y salarios" del observatorio EMPLEABILIDAD_INV-DE-MERCADO
sobre la diapositiva existente de la plantilla, sin cambiar su geometría.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pptx.enum.shapes import MSO_SHAPE_TYPE

from presentaciones.formato import decimal, variaciones

BLUE, LIGHT, MUTED = "#087BCC", "#76BDED", "#B9C9DC"
NAVY, TEXT, CAPTION = "#123F70", "#617D99", "#7B91A8"
FONT = "Century Gothic"

# Índices de la diapositiva de la plantilla (base 0 dentro de la diapositiva).
TARJETAS = (  # (año, tasa, variación)
    (9, 10, 24),
    (13, 14, 25),
    (17, 18, 26),
    (21, 22, 27),
)
IMAGEN_COMPOSICION = 33
IMAGEN_BANDA = 0
FUENTE = 2


def _guardar(fig, ruta):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, format="png", dpi=200, facecolor="white")
    plt.close(fig)
    return str(ruta)


def _mensaje(ax, texto):
    ax.axis("off")
    ax.text(.5, .5, texto, ha="center", va="center", fontsize=13, color=CAPTION, family=FONT,
            transform=ax.transAxes)


def generar_composicion(fila, ruta):
    """Dona de dependientes / independientes / sin información (corte más reciente)."""
    # Proporción del marcador de la plantilla (3801005 x 2876951 EMU).
    fig, ax = plt.subplots(figsize=(5.3, 4.0))
    fig.subplots_adjust(0, 0, 1, 1)
    valores = [] if fila is None else [int(fila["dependent"]), int(fila["independent"]), int(fila["unknown"])]
    total = sum(valores)
    if not total:
        _mensaje(ax, "Sin graduados elegibles en este corte")
        return _guardar(fig, ruta)
    # Igual que la dona de Plotly del observatorio: desde las 12 en sentido
    # horario aparecen dependientes, sin información e independientes.
    orden = [valores[0], valores[2], valores[1]]
    wedges, _ = ax.pie(orden, colors=[BLUE, MUTED, LIGHT], startangle=90, counterclock=False,
                       radius=1, wedgeprops=dict(width=.27, edgecolor="white", linewidth=3))
    for wedge, valor in zip(wedges, orden):
        if not valor:
            continue
        angulo = np.deg2rad((wedge.theta1 + wedge.theta2) / 2)
        x, y = 1.16 * np.cos(angulo), 1.16 * np.sin(angulo)
        ax.text(x, y, f"{decimal(100 * valor / total)}%", ha="left" if x >= 0 else "right",
                va="center", fontsize=10, color=TEXT, family=FONT)
    ax.text(0, .08, f"{decimal(fila['rate'])}%", ha="center", va="center", fontsize=27,
            fontweight="bold", color=NAVY, family=FONT)
    ax.text(0, -.2, "empleo visible", ha="center", va="center", fontsize=11, color=CAPTION, family=FONT)
    ax.set_xlim(-1.55, 1.55)
    ax.set_ylim(-1.17, 1.17)
    ax.set_aspect("equal")
    ax.axis("off")
    return _guardar(fig, ruta)


def generar_banda_salarial(fila, ruta):
    """Rango intercuartílico (P25–P75) del ingreso mensual de dependientes."""
    # Proporción del marcador de la plantilla (5982535 x 1181265 EMU).
    fig, ax = plt.subplots(figsize=(8.0, 1.58))
    fig.subplots_adjust(0, 0, 1, 1)
    if fila is None or not fila["salary_n"] or pd.isna(fila["p25"]):
        _mensaje(ax, "Sin salarios válidos para calcular la banda")
        return _guardar(fig, ruta)
    p25, p75 = float(fila["p25"]), float(fila["p75"])
    span = max(p75 - p25, 100)
    ax.plot([p25, p75], [0, 0], color=BLUE, linewidth=7, solid_capstyle="butt", zorder=1)
    ax.scatter([p25, p75], [0, 0], s=260, color=BLUE, zorder=2)
    for x, valor, etiqueta, alinea in ((p25, p25, "PERCENTIL 25", "right"), (p75, p75, "PERCENTIL 75", "left")):
        ax.text(x, .42, f"${decimal(valor, 0)}", ha=alinea,
                va="bottom", fontsize=11, color=TEXT, family=FONT)
        ax.text(x, -.42, etiqueta, ha="center", va="top", fontsize=9.5, color=CAPTION, family=FONT)
    ax.set_xlim(max(0, p25 - span * .35), p75 + span * .35)
    ax.set_ylim(-1, 1)
    ax.axis("off")
    return _guardar(fig, ruta)


def _texto(shape, valor):
    """Reemplaza el texto conservando el formato del primer run."""
    if not getattr(shape, "has_text_frame", False):
        return
    parrafos = shape.text_frame.paragraphs
    runs = parrafos[0].runs
    if runs:
        runs[0].text = str(valor)
        for run in runs[1:]:
            run.text = ""
    else:
        parrafos[0].text = str(valor)
    for parrafo in parrafos[1:]:
        for run in parrafo.runs:
            run.text = ""


def validar_slide(slide):
    """Comprueba que la diapositiva tenga la estructura esperada de la plantilla."""
    shapes = slide.shapes
    if len(shapes) <= IMAGEN_COMPOSICION:
        raise ValueError(f"La diapositiva de empleabilidad tiene {len(shapes)} shapes; se esperaban al menos 34.")
    for indice in (IMAGEN_COMPOSICION, IMAGEN_BANDA):
        if shapes[indice].shape_type != MSO_SHAPE_TYPE.PICTURE:
            raise ValueError(f"El shape {indice} de la diapositiva de empleabilidad no es una imagen.")
    for anio, tasa, delta in TARJETAS:
        if not shapes[anio].has_text_frame or not shapes[anio].text_frame.text.strip().isdigit():
            raise ValueError(f"El shape {anio} no contiene el año de una tarjeta de empleabilidad.")


def actualizar_tarjetas(slide, summary):
    """Año, tasa de empleo visible y variación en puntos porcentuales."""
    textos_delta = variaciones(summary) if summary is not None else ["N/D"] * len(TARJETAS)
    for i, (anio, tasa, delta) in enumerate(TARJETAS):
        fila = summary.iloc[i] if summary is not None and i < len(summary) else None
        if fila is not None:
            _texto(slide.shapes[anio], int(fila["year"]))
        _texto(slide.shapes[tasa], "N/D" if fila is None or pd.isna(fila["rate"]) else f"{decimal(fila['rate'])}%")
        _texto(slide.shapes[delta], textos_delta[i] if fila is not None else "N/D")


# --- Tarjeta "Empleabilidad en <provincia>" (abajo a la derecha) -------------

# Debajo de la tarjeta "Banda Salarial" (termina en y=4633369) y alineada con su
# borde izquierdo (x=5865865) y derecho (x=11801277). Colores de la plantilla.
NAVY_PLANTILLA, AZUL_PLANTILLA, FONDO_TARJETA = "002060", "0D5898", "DCEAF7"
TERRITORIO_TITULO = (6150000, 4800000, 4600000, 320000)
TERRITORIO_CAJA = (6150000, 5250000, 2700000, 1080000)
TERRITORIO_LINEA_X, TERRITORIO_LINEA_Y = 9100000, (5200000, 6380000)
TERRITORIO_LISTA = (9280000, 5260000, 2550000, 1060000)


def _run(parrafo, texto, size, color, bold=False):
    from pptx.dml.color import RGBColor
    from pptx.util import Pt

    run = parrafo.add_run()
    run.text = texto
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)
    return run


def agregar_tarjeta_territorial(slide, territorio, provincia="Pichincha"):
    """Empleo visible y composición de los graduados domiciliados en la provincia."""
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Emu, Pt

    titulo = slide.shapes.add_textbox(*(Emu(v) for v in TERRITORIO_TITULO))
    titulo.name = "Empleabilidad territorial · título"
    p = titulo.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    _run(p, f"Empleabilidad en {provincia}", 14, AZUL_PLANTILLA, bold=True)

    caja = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, *(Emu(v) for v in TERRITORIO_CAJA))
    caja.name = "Empleabilidad territorial · tasa"
    caja.adjustments[0] = .18
    caja.shadow.inherit = False
    caja.fill.solid()
    caja.fill.fore_color.rgb = RGBColor.from_string(FONDO_TARJETA)
    caja.line.color.rgb = RGBColor.from_string(AZUL_PLANTILLA)
    caja.line.width = Pt(1.5)
    tf = caja.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.word_wrap = True
    tasa = "N/D" if not territorio else f"{decimal(territorio['rate'])}%"
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    _run(p, tasa, 24, NAVY_PLANTILLA, bold=True)
    p = tf.add_paragraph()
    p.alignment = PP_ALIGN.CENTER
    _run(p, "Empleo visible" if territorio else f"Sin graduados domiciliados en {provincia}", 12, AZUL_PLANTILLA)

    y0, y1 = TERRITORIO_LINEA_Y
    linea = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Emu(TERRITORIO_LINEA_X), Emu(y0),
                                       Emu(TERRITORIO_LINEA_X), Emu(y1))
    linea.name = "Empleabilidad territorial · separador"
    linea.line.color.rgb = RGBColor.from_string(AZUL_PLANTILLA)
    linea.line.width = Pt(1.5)

    lista = slide.shapes.add_textbox(*(Emu(v) for v in TERRITORIO_LISTA))
    lista.name = "Empleabilidad territorial · composición"
    tf = lista.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.word_wrap = True
    filas = [("dependent", "Dependientes"), ("independent", "Independientes"), ("unknown", "Sin información")]
    for i, (campo, etiqueta) in enumerate(filas):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(2)
        valor = "N/D" if not territorio else f"{decimal(100 * territorio[campo] / territorio['graduates'])}%"
        _run(p, "•  ", 14, AZUL_PLANTILLA, bold=True)
        _run(p, valor, 14, AZUL_PLANTILLA, bold=True)
        _run(p, f" {etiqueta}", 14, "404040")

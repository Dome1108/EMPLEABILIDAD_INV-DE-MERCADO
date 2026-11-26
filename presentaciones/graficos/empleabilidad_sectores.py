"""[Copia de Tendencias · presentation/charts, adaptada al observatorio]
Diapositiva «Empresas y Sectores»: principales empresas y macroindustrias.

Gráficos del observatorio EMPLEABILIDAD_INV-DE-MERCADO ("Top empresas por
graduados" y "Graduados empleados por macroindustria") con la composición de
la lámina "Empleabilidad Nacional": texto arriba a la izquierda, sectores abajo
a la izquierda y principales empresas en la columna derecha. Si hay proyecto de
Tendencias, debajo de las empresas van los cargos de LinkedIn (como en Tendencias);
sin proyecto, el gráfico de empresas ocupa toda la columna derecha.
"""
from __future__ import annotations

import copy
from pathlib import Path
from textwrap import wrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Pt

from presentaciones.formato import entero

BLUE, LIGHT = "#087BCC", "#76BDED"
TEXT, CAPTION = "#617D99", "#7B91A8"
FONT = "Century Gothic"
EMU_POR_PULGADA = 914400

# Geometría (EMU) sobre la diapositiva 16:9 de la plantilla (12192000 x 6858000).
# El logo de la plantilla ocupa la esquina superior derecha hasta ~1,1 M de alto.
PARRAFO = (575703, 1230000, 6950000, 1050000)
TITULO_EMPRESAS = (7750000, 1180000, 3900000, 277000)
GRAFICO_EMPRESAS = (7700000, 1460000, 4000000, 4920000)  # toda la columna derecha
# Con cargos de LinkedIn (geometría de Tendencias): empresas arriba y cinco cargos debajo.
GRAFICO_EMPRESAS_CON_CARGOS = (7700000, 1460000, 4000000, 1720000)
TITULO_CARGOS = (9113000, 3440000, 2430000, 277000)
CAJAS_CARGOS = dict(left=9113000, top=3790000, width=2430000, height=470000, gap=45000)
FILL_CARGO = "#DCEAF7"
TITULO_SECTORES = (575703, 2380000, 4000000, 277000)
GRAFICO_SECTORES = (400000, 2660000, 7250000, 3720000)
FUENTE_DERECHA = 11647859
FUENTE_ANCHO = 5600000

TEXTO_FUENTE = "Fuente: SENESCYT, IESS (SIM enero 2026) y catálogo RUC-CIIU"
TEXTO_FUENTE_CARGOS = "Fuente: SENESCYT, IESS (SIM enero 2026), catálogo RUC-CIIU y LinkedIn Talent Insights"


# --- Gráficos -------------------------------------------------------------

def _figura(caja):
    _, _, ancho, alto = caja
    return plt.subplots(figsize=(ancho / EMU_POR_PULGADA, alto / EMU_POR_PULGADA))


def _guardar(fig, ruta):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, format="png", dpi=300, facecolor="white")
    plt.close(fig)
    return str(ruta)


def _sin_datos(ax, texto):
    ax.axis("off")
    ax.text(.5, .5, texto, ha="center", va="center", fontsize=9, color=CAPTION,
            family=FONT, transform=ax.transAxes)


def _etiqueta(nombre, ancho, lineas=2):
    partes = wrap(str(nombre), ancho) or [""]
    if len(partes) > lineas:
        partes = partes[:lineas]
        partes[-1] = partes[-1][: ancho - 1].rstrip() + "…"
    return "\n".join(partes)


def _estilo_barras(ax):
    for lado in ("top", "right", "bottom"):
        ax.spines[lado].set_visible(False)
    ax.spines["left"].set_color("#D5DEE8")
    ax.tick_params(axis="y", length=0, labelsize=6.5, labelcolor=TEXT)
    ax.set_xticks([])


def generar_empresas(empresas, ruta, caja=GRAFICO_EMPRESAS):
    """Top empresas por graduados: barras horizontales con graduados y participación."""
    fig, ax = _figura(caja)
    if empresas is None or empresas.empty:
        _sin_datos(ax, "N/D: sin graduados con empleador identificado")
        return _guardar(fig, ruta)
    datos = empresas.iloc[::-1].reset_index(drop=True)
    posiciones = range(len(datos))
    ax.barh(posiciones, datos["Graduados"], color=BLUE, height=.66)
    maximo = float(datos["Graduados"].max()) or 1
    for y, (graduados, share) in enumerate(zip(datos["Graduados"], datos["Participación"])):
        texto = f"{entero(graduados)} · " + f"{share:.1f} %".replace(".", ",")
        ax.text(graduados + maximo * .02, y, texto, va="center", fontsize=6.5, color=TEXT, family=FONT)
    ax.set_yticks(list(posiciones), [_etiqueta(n, 30) for n in datos["Empresa"]], family=FONT)
    ax.set_xlim(0, maximo * 1.32)
    ax.set_ylim(-.6, len(datos) - .4)
    _estilo_barras(ax)
    fig.tight_layout(pad=.25)
    return _guardar(fig, ruta)


def generar_sectores(sectores, ruta, destacados=3):
    """Graduados únicos por macroindustria; las primeras ``destacados`` en azul."""
    fig, ax = _figura(GRAFICO_SECTORES)
    if sectores is None or sectores.empty or not sectores["Graduados"].sum():
        _sin_datos(ax, "N/D: sin graduados con sector (CIIU) identificado")
        return _guardar(fig, ruta)
    datos = (sectores.sort_values(["Graduados", "Macroindustria"], ascending=[False, True])
                     .reset_index(drop=True))
    colores = [BLUE if i < destacados and v > 0 else LIGHT for i, v in enumerate(datos["Graduados"])]
    datos, colores = datos.iloc[::-1].reset_index(drop=True), colores[::-1]
    posiciones = range(len(datos))
    ax.barh(posiciones, datos["Graduados"], color=colores, height=.68)
    maximo = float(datos["Graduados"].max()) or 1
    for y, valor in enumerate(datos["Graduados"]):
        ax.text(valor + maximo * .01, y, entero(valor), va="center", fontsize=6.5, color=TEXT, family=FONT)
    ax.set_yticks(list(posiciones), [_etiqueta(n, 42) for n in datos["Macroindustria"]], family=FONT)
    ax.set_xlim(0, maximo * 1.1)
    ax.set_ylim(-.6, len(datos) - .4)
    _estilo_barras(ax)
    ax.set_xlabel("Graduados únicos por macroindustria · corte laboral enero 2026",
                  fontsize=6.5, color=CAPTION, family=FONT, labelpad=4)
    fig.tight_layout(pad=.3)
    return _guardar(fig, ruta)


# --- Texto ------------------------------------------------------------------

def _lista(nombres):
    nombres = [n for n in nombres if n]
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


_MINUSCULAS = {"de", "del", "la", "las", "el", "los", "y", "e", "en", "para", "por", "a"}
_SIGLAS = {"sa", "s.a.", "s.a", "ca", "c.a.", "ltda", "ltda.", "cia", "cia.", "sas", "s.a.s.", "bp", "b.p.", "ep", "e.p."}


def _titulo_empresa(nombre):
    """'HOSPITAL DE ESPECIALIDADES S.A.' -> 'Hospital de Especialidades S.A.'."""
    palabras = []
    for i, palabra in enumerate(str(nombre).strip().split()):
        minuscula = palabra.lower()
        if minuscula in _SIGLAS:
            palabras.append(palabra.upper())
        elif i and minuscula in _MINUSCULAS:
            palabras.append(minuscula)
        else:
            palabras.append(palabra.capitalize())
    return " ".join(palabras)


def texto_resumen(nombre_programa, empresas, sectores, cargos=None):
    """Párrafo descriptivo construido solo con los datos de la lámina."""
    partes = []
    if sectores is not None and not sectores.empty and sectores["Graduados"].sum():
        top = sectores.sort_values("Graduados", ascending=False)
        top = top[top["Graduados"] > 0].head(3)["Macroindustria"].str.lower().tolist()
        partes.append(f"La empleabilidad de los profesionales en {nombre_programa} se vincula "
                      f"principalmente con los sectores de {_lista(top)}.")
    else:
        partes.append(f"No se identificaron sectores de empleo formal para los graduados de {nombre_programa}.")
    if empresas is not None and not empresas.empty:
        nombres = [_titulo_empresa(n) for n in empresas["Empresa"].head(3)]
        partes.append(f"Entre los principales empleadores de los graduados destacan {_lista(nombres)}.")
    if cargos:
        partes.append(f"En LinkedIn, los cargos más frecuentes son {_lista([c for c, _ in cargos[:3]])}.")
    return " ".join(partes)


# --- Diapositiva ------------------------------------------------------------

def _textos(slide):
    for shape in slide.shapes:
        if shape.has_text_frame:
            yield shape, shape.text_frame.text.strip()


def localizar_elementos(slide):
    """Elementos de la diapositiva "Empresas y Sectores" de la plantilla."""
    encabezado = next((s for s, t in _textos(slide) if t.lower() == "empresas y sectores"), None)
    fuente = next((s for s, t in _textos(slide) if t.lower().startswith("fuente")), None)
    parrafos = [(len(t), s) for s, t in _textos(slide) if s not in (encabezado, fuente)]
    parrafo = max(parrafos, key=lambda x: x[0])[1] if parrafos else None
    imagen = next((s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE), None)
    titulo = next((s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.GROUP), None)
    lineas = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.LINE]
    faltan = [n for n, v in (("encabezado", encabezado), ("fuente", fuente), ("párrafo", parrafo),
                             ("imagen", imagen)) if v is None]
    if faltan:
        raise RuntimeError("La diapositiva de empresas y sectores no tiene: " + ", ".join(faltan))
    return dict(encabezado=encabezado, fuente=fuente, parrafo=parrafo, imagen=imagen,
                titulo=titulo, lineas=lineas)


def _poner_texto(shape, texto):
    """Reemplaza el texto conservando el formato del primer run."""
    tf = shape.text_frame
    p = tf.paragraphs[0]
    if p.runs:
        p.runs[0].text = texto
        for run in p.runs[1:]:
            run._r.getparent().remove(run._r)
    else:
        p.text = texto
    for extra in list(tf.paragraphs)[1:]:
        extra._p.getparent().remove(extra._p)


def _mover(shape, caja):
    shape.left, shape.top, shape.width, shape.height = (Emu(v) for v in caja)


def _encabezado(shape, caja, texto):
    """El encabezado de la plantilla está girado 270°; aquí va horizontal."""
    shape.rotation = 0
    _mover(shape, caja)
    _poner_texto(shape, texto)
    for p in shape.text_frame.paragraphs:
        p.alignment = PP_ALIGN.LEFT
        for run in p.runs:
            run.font.italic = False


def _clonar(shape, caja, texto):
    elemento = copy.deepcopy(shape._element)
    shape._element.addnext(elemento)
    nuevo = next(s for s in shape.part.slide.shapes if s._element is elemento)
    _encabezado(nuevo, caja, texto)
    return nuevo


def _cajas_cargos(slide, cargos):
    """Copia de Tendencias: cinco cuadritos con los cargos más frecuentes de LinkedIn."""
    c = CAJAS_CARGOS
    nombres = [n for n, _ in (cargos or [])[:5]] or ["N/D: sin cargos de LinkedIn"]
    for i, nombre in enumerate(nombres):
        caja = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Emu(c["left"]), Emu(c["top"] + i * (c["height"] + c["gap"])), Emu(c["width"]), Emu(c["height"]))
        caja.name = f"Cargo {i + 1}"
        caja.adjustments[0] = .22
        caja.shadow.inherit = False
        caja.fill.solid()
        caja.fill.fore_color.rgb = RGBColor.from_string(FILL_CARGO[1:])
        caja.line.color.rgb = RGBColor.from_string(BLUE[1:])
        caja.line.width = Pt(1.5)
        tf = caja.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        for margen in ("margin_left", "margin_right"):
            setattr(tf, margen, Emu(60000))
        tf.margin_top = tf.margin_bottom = Emu(20000)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = str(nombre)
        run.font.name = FONT
        run.font.size = Pt(11.5 if len(str(nombre)) <= 22 else 10.5)
        run.font.bold = True
        run.font.color.rgb = RGBColor.from_string(BLUE[1:])


def actualizar_slide(slide, nombre_programa, empresas, sectores, ruta_empresas, ruta_sectores, cargos=None):
    """Compone la lámina con los dos gráficos y el párrafo; ``cargos`` (LinkedIn) es opcional:
    None = sin proyecto de Tendencias; lista (aunque vacía) = cuadritos de cargos como en Tendencias."""
    e = localizar_elementos(slide)
    if e["titulo"] is not None:
        titulo = next((s for s in e["titulo"].shapes
                       if s.has_text_frame and s.text_frame.text.strip().upper() == "EMPLEABILIDAD"), None)
        if titulo is not None:
            _poner_texto(titulo, "EMPLEABILIDAD NACIONAL")
    for linea in e["lineas"]:
        linea._element.getparent().remove(linea._element)

    # Párrafo como texto corrido (sin la caja redondeada del ejemplo).
    parrafo = e["parrafo"]
    _mover(parrafo, PARRAFO)
    _poner_texto(parrafo, texto_resumen(nombre_programa, empresas, sectores, cargos))
    parrafo.fill.background()
    parrafo.line.fill.background()
    parrafo.text_frame.word_wrap = True
    for p in parrafo.text_frame.paragraphs:
        p.alignment = PP_ALIGN.JUSTIFY
        for run in p.runs:
            run.font.size = Pt(10.5)
            run.font.bold = False

    # Encabezados con el mismo estilo (azul, negrita) del encabezado de la plantilla.
    _clonar(e["encabezado"], TITULO_EMPRESAS, "Principales Empresas")
    if cargos is not None:
        _clonar(e["encabezado"], TITULO_CARGOS, "Principales Cargos")
    _encabezado(e["encabezado"], TITULO_SECTORES, "Principales Sectores")

    imagen = e["imagen"]
    for ruta, caja, descripcion in (
        (ruta_sectores, GRAFICO_SECTORES, "Graduados empleados por macroindustria (SIM enero 2026)"),
        (ruta_empresas, GRAFICO_EMPRESAS if cargos is None else GRAFICO_EMPRESAS_CON_CARGOS,
         f"Top {10 if cargos is None else 5} empresas por graduados (SIM enero 2026)"),
    ):
        nueva = slide.shapes.add_picture(ruta, *(Emu(v) for v in caja))
        nueva._element.nvPicPr.cNvPr.set("descr", descripcion)
    imagen._element.getparent().remove(imagen._element)
    if cargos is not None:
        _cajas_cargos(slide, cargos)

    fuente = e["fuente"]
    fuente.left, fuente.width = Emu(FUENTE_DERECHA - FUENTE_ANCHO), Emu(FUENTE_ANCHO)
    fuente.text_frame.word_wrap = True
    _poner_texto(fuente, TEXTO_FUENTE if cargos is None else TEXTO_FUENTE_CARGOS)
    for p in fuente.text_frame.paragraphs:
        p.alignment = PP_ALIGN.RIGHT

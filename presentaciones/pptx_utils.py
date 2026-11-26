"""Utilidades de python-pptx copiadas del proyecto Tendencias (presentation/pptx_utils.py y
presentation/generator.py) para editar la plantilla sin perder su formato."""
import copy
import os
import unicodedata

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches


def normalizar(texto):
    """Minúsculas, sin tildes ni espacios repetidos (para buscar textos de la plantilla)."""
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.casefold().split())


def iterar_shapes(shapes):
    """Recorre shapes directos y los que estén dentro de grupos."""
    for shape in shapes:
        yield shape
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from iterar_shapes(shape.shapes)


def texto_de_slide(slide):
    return " ".join(normalizar(s.text_frame.text) for s in iterar_shapes(slide.shapes)
                    if getattr(s, "has_text_frame", False))


def reemplazar_texto_en_shape(shape, viejo, nuevo):
    """Reemplaza una cadena dentro de un shape (y sus grupos) manteniendo los runs y su formato."""
    if getattr(shape, "shape_type", None) == MSO_SHAPE_TYPE.GROUP:
        for subshape in shape.shapes:
            reemplazar_texto_en_shape(subshape, viejo, nuevo)
        return
    if not getattr(shape, "has_text_frame", False):
        return
    for paragraph in shape.text_frame.paragraphs:
        for run in paragraph.runs:
            if viejo in run.text:
                run.text = run.text.replace(viejo, nuevo)


def reemplazar_en_presentacion(prs, variantes, nuevo):
    for slide in prs.slides:
        for shape in slide.shapes:
            for variante in variantes:
                reemplazar_texto_en_shape(shape, variante, nuevo)


def poner_texto_completo(shape, texto):
    """Reemplaza el contenido de un cuadro de texto conservando el formato del primer run."""
    if not getattr(shape, "has_text_frame", False):
        return
    tf = shape.text_frame
    if not tf.paragraphs:
        tf.text = str(texto)
        return
    p = tf.paragraphs[0]
    if p.runs:
        p.runs[0].text = str(texto)
        for run in p.runs[1:]:
            run._r.getparent().remove(run._r)
    else:
        p.text = str(texto)
    for paragraph in list(tf.paragraphs)[1:]:
        paragraph._p.getparent().remove(paragraph._p)


def poner_etiqueta_valor(shape, etiqueta, valor):
    """«Etiqueta: valor» en un cuadro de la plantilla: etiqueta con el formato del primer run
    y el valor con el formato del último run (como reemplazar_texto_preservando_formato)."""
    if not getattr(shape, "has_text_frame", False):
        return
    p = shape.text_frame.paragraphs[0]
    runs = list(p.runs)
    if not runs:
        p.text = f"{etiqueta}: {valor}"
        return
    base, ultimo = runs[0], runs[-1]
    base.text = f"{etiqueta}:"
    for run in runs[1:]:
        run._r.getparent().remove(run._r)
    nuevo = copy.deepcopy(base._r)
    base._r.addnext(nuevo)
    run_valor = p.runs[1]
    run_valor.text = f" {valor}"
    run_valor.font.bold = False if ultimo is base else ultimo.font.bold
    for paragraph in list(shape.text_frame.paragraphs)[1:]:
        paragraph._p.getparent().remove(paragraph._p)
    shape.text_frame.word_wrap = True
    p.alignment = PP_ALIGN.LEFT  # justificado estira «etiqueta: valor» cuando pasa a dos líneas


def poner_parrafos(shape, filas):
    """Varios párrafos «Título: texto» con el título en negrita, copiando el formato del
    primer párrafo de la plantilla. ``filas`` = [(titulo, texto), ...]; título None = solo texto."""
    tf = shape.text_frame
    plantilla = copy.deepcopy(tf.paragraphs[0]._p)
    for paragraph in list(tf.paragraphs):
        paragraph._p.getparent().remove(paragraph._p)
    contenedor = tf._txBody
    for titulo, texto in filas:
        nuevo = copy.deepcopy(plantilla)
        contenedor.append(nuevo)
        p = tf.paragraphs[-1]
        runs = list(p.runs)
        for run in runs[1:]:
            run._r.getparent().remove(run._r)
        base = p.runs[0] if p.runs else p.add_run()
        if titulo:
            base.text = f"{titulo}: "
            base.font.bold = True
            cuerpo = copy.deepcopy(base._r)
            base._r.addnext(cuerpo)
            p.runs[1].text = texto
            p.runs[1].font.bold = False
        else:
            base.text = texto
            base.font.bold = False


def reemplazar_imagen(slide, shape_or_index, ruta_imagen, conservar_proporcion=False, factor_tamano=1.0, caja=None):
    """Reemplaza la imagen del shape indicado conservando su capa (copiado de Tendencias).

    ``caja`` = (izquierda, arriba, ancho, alto) en pulgadas: espacio que debe ocupar la imagen.
    """
    if not ruta_imagen or not os.path.exists(ruta_imagen):
        raise FileNotFoundError(f"No existe la imagen para reemplazar: {ruta_imagen}")
    shape = slide.shapes[shape_or_index] if isinstance(shape_or_index, int) else shape_or_index
    if shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
        raise ValueError(f"El shape {shape.name!r} no es una imagen.")
    left, top, width, height = shape.left, shape.top, shape.width, shape.height
    if caja is not None:
        left, top, width, height = (int(Inches(valor)) for valor in caja)
    if conservar_proporcion:
        from PIL import Image
        with Image.open(ruta_imagen) as imagen:
            ancho, alto = imagen.size
        escala = min(width / ancho, height / alto)
        nuevo_ancho, nuevo_alto = round(ancho * escala), round(alto * escala)
        left += (width - nuevo_ancho) // 2
        top += (height - nuevo_alto) // 2
        width, height = nuevo_ancho, nuevo_alto
    if factor_tamano != 1.0:
        nuevo_ancho, nuevo_alto = round(width * factor_tamano), round(height * factor_tamano)
        left += (width - nuevo_ancho) // 2
        top += (height - nuevo_alto) // 2
        width, height = nuevo_ancho, nuevo_alto
    parent = shape._element.getparent()
    index = parent.index(shape._element)
    nueva = slide.shapes.add_picture(ruta_imagen, left, top, width, height)
    # Mantener la misma capa del elemento original: add_picture agrega al final
    # y podría tapar textos, marcos o logos de la plantilla.
    parent.remove(nueva._element)
    parent.remove(shape._element)
    parent.insert(index, nueva._element)
    return nueva


def imagen_mayor(slide):
    """La imagen más grande de la diapositiva (el gráfico de ejemplo de la plantilla)."""
    imagenes = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
    if not imagenes:
        raise ValueError("La diapositiva no tiene imágenes para reemplazar.")
    return max(imagenes, key=lambda s: s.width * s.height)


def colorear(shape, hex_color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string(hex_color.lstrip("#"))


def quitar_diapositivas(prs, indices):
    """Elimina diapositivas por índice (de mayor a menor para no mover los demás)."""
    lista = prs.slides._sldIdLst
    elementos = list(lista)
    for indice in sorted(set(indices), reverse=True):
        elemento = elementos[indice]
        prs.part.drop_rel(elemento.rId)
        lista.remove(elemento)


def guardar(prs, ruta):
    ruta = str(ruta)
    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    prs.save(ruta)
    return ruta

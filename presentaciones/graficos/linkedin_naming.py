# [Copia de Tendencias · presentation/charts/linkedin_naming.py; solo cambian las rutas de import]
# cambiado por samuel
"""Validación y renderizado del naming de la diapositiva visible 23."""

import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from presentaciones.graficos.linkedin_template_graphs import insertar_figura


CRITERIOS_NAMING = (
    "claridad",
    "pertinencia",
    "atractivo_comercial",
    "profesionalismo_academico",
    "internacionalizacion",
)

# Celeste de la serie LATAM en los gráficos de aptitudes.
CELESTE_PLANTILLA = "#A6CAEC"


def _limpiar_privado(texto):
    texto = str(texto or "")
    texto = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "", texto)
    texto = re.sub(r"https?://\S+", "", texto)
    texto = re.sub(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\b", "", texto)
    return " ".join(texto.split())


def construir_contexto_naming(nombre_original, requisitos, homologaciones,
                              datos_raw=None, datos_homologados=None, solicitud=None):
    def resumen_mercado(datos):
        if not isinstance(datos, dict):
            return {}
        return {
            tipo: [
                {"nombre": _limpiar_privado(row.get("nombre_normalizado") or row.get("nombre")),
                 "frecuencia": row.get("frecuencia_total") or row.get("profesionales") or row.get("cantidad") or 0}
                for row in (datos.get(tipo) or [])
                if _limpiar_privado(row.get("nombre_normalizado") or row.get("nombre"))
            ]
            for tipo in ("aptitudes", "cargos", "empresas", "sectores", "habilidades")
        }

    return {
        "nombre_original": _limpiar_privado(nombre_original),
        "requisitos": [_limpiar_privado(r) for r in (requisitos or {}).get("requisitos", []) if _limpiar_privado(r)],
        "mercado_homologado": [
            _limpiar_privado(row.get("nombre_normalizado"))
            for row in homologaciones or []
            if _limpiar_privado(row.get("nombre_normalizado"))
        ],
        "mercado_raw": resumen_mercado(datos_raw),
        "mercado_homologado_detalle": resumen_mercado(datos_homologados),
        "solicitud": {
            key: _limpiar_privado(value)
            for key, value in (solicitud or {}).items()
            if key in ("nombre_programa", "facultad_propuesta", "duracion", "modalidad") and _limpiar_privado(value)
        },
    }


def _puntaje(criterios):
    valores = {}
    for criterio in CRITERIOS_NAMING:
        try:
            valor = int(round(float((criterios or {}).get(criterio, 1))))
        except (TypeError, ValueError):
            valor = 1
        valores[criterio] = min(max(valor, 1), 7)
    total = sum(valores.values())
    return valores, total, round(total / 35 * 100, 2)


def validar_nombres(data):
    original = data.get("original") if isinstance(data, dict) else None
    alternativas = data.get("alternativas") if isinstance(data, dict) else None
    original = original if isinstance(original, dict) else {"nombre": "N/D", "criterios": {}}
    alternativas = alternativas if isinstance(alternativas, list) else []
    filas = []
    for tipo, item in [("original", original)] + [("alternativa", item) for item in alternativas]:
        if not isinstance(item, dict) or not str(item.get("nombre", "")).strip():
            continue
        criterios, total, porcentaje = _puntaje(item.get("criterios"))
        filas.append({"tipo": tipo, "nombre": " ".join(str(item["nombre"]).split()), "criterios": criterios,
                      "total": total, "porcentaje": porcentaje})
    if not filas:
        filas = [{"tipo": "original", "nombre": "N/D", "criterios": {c: 1 for c in CRITERIOS_NAMING}, "total": 5, "porcentaje": round(5 / 35 * 100, 2)}]
    while len(filas) < 5:
        filas.append({"tipo": "alternativa", "nombre": "N/D", "criterios": {c: 1 for c in CRITERIOS_NAMING}, "total": 5, "porcentaje": round(5 / 35 * 100, 2)})
    return filas[:5]


def grafico_nombres(filas):
    fig, ax = plt.subplots(figsize=(11, 6))
    etiquetas = [row["nombre"] for row in filas]
    valores = [row["porcentaje"] for row in filas]
    # La diapositiva 23 es una imagen renderizada por Matplotlib: sus barras
    # son rectángulos de la gráfica, no shapes editables de python-pptx.
    # Todas usan el celeste de la plantilla para mantener una sola lectura
    # visual sin alterar posiciones, textos ni valores.
    colores = [CELESTE_PLANTILLA for _ in filas]
    posiciones = list(range(len(filas)))[::-1]
    ax.barh(posiciones, valores[::-1], color=colores[::-1], height=.58)
    ax.set_yticks(posiciones, etiquetas[::-1], fontsize=12)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Evaluación combinada (%)", fontsize=11)
    ax.grid(axis="x", linestyle=(0, (3, 3)), color="#D9D9D9", alpha=.7)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", length=0)
    for y, value in zip(posiciones, valores[::-1]):
        ax.text(min(value + 1, 96), y, f"{value:.0f}%", va="center", fontsize=11, color="#555555")
    ax.set_title("Alternativas de nombre evaluadas", fontsize=16, fontweight="bold", pad=16)
    fig.subplots_adjust(left=.30, right=.97, top=.86, bottom=.16)
    return fig


def actualizar_slide_naming(slide, filas):
    filas = validar_nombres({"original": filas[0], "alternativas": filas[1:]})
    pictures = [shape for shape in slide.shapes if shape.shape_type == 13]
    if pictures:
        insertar_figura(slide, pictures[0], grafico_nombres(filas), "Evaluación de nombres de programa")
    if len(slide.shapes) > 0 and hasattr(slide.shapes[0], "text_frame"):
        mejor = max(filas, key=lambda row: row["total"])
        slide.shapes[0].text_frame.text = (
            f"{mejor['nombre']} presenta la mayor valoración ({mejor['porcentaje']:.0f}%), "
            "según claridad, pertinencia, atractivo comercial, profesionalismo académico e internacionalización."
        )
    for shape in slide.shapes:
        if getattr(shape, "text", "").strip() == "API":
            shape.text_frame.text = "Análisis IA"
    return filas
#------------------------------------

"""[Copia de Tendencias · presentation/charts, adaptada al observatorio] Diapositiva 6 · Instituciones educativas (Nacional y Privadas Sierra).

Réplica de ``education_visuals.education_figure`` del proyecto
EMPLEABILIDAD_INV-DE-MERCADO: dos gráficos de puntos unidos (recién titulados
y profesionales históricos) con el top 10 de cada grupo. Imagen estática con
el tamaño exacto de la imagen de la plantilla.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter, MaxNLocator

BLUE, LIGHT, LINEA = "#087BCC", "#76BDED", "#CFDEEC"
TITULO, ETIQUETA, GRID = "#123F70", "#476783", "#EEF3F8"
TAMANO = (13.333, 5.15)  # Imagen de la diapositiva 6 de la plantilla (pulgadas)
TITULOS = ("Nacional · top 10", "Privadas Sierra · top 10")


def _miles(valor, _=None):
    return f"{valor:,.0f}".replace(",", ".")


def _panel(ax, data, titulo):
    ax.set_title(titulo, loc="left", fontsize=13, color=TITULO, pad=14)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", length=0, labelcolor=ETIQUETA, pad=8)
    if data is None or data.empty or not data["professionals"].sum():
        ax.set_xticks([])
        ax.set_yticks([])
        ax.text(0.5, 0.5, "N/D: sin graduados registrados", transform=ax.transAxes,
                ha="center", va="center", fontsize=12, color=ETIQUETA)
        return None
    data = data.iloc[::-1]
    y = np.arange(len(data))
    ax.hlines(y, data["recent"], data["professionals"], color=LINEA, linewidth=2.2, zorder=1)
    recientes = ax.scatter(data["recent"], y, color=LIGHT, s=46, zorder=3, label="Recién titulados")
    historicos = ax.scatter(data["professionals"], y, color=BLUE, s=46, zorder=3,
                            label="Profesionales históricos")
    ax.set_yticks(y, data["label"], fontsize=10.5)
    ax.set_ylim(-0.7, max(len(data) - 0.3, 0.7))
    maximo = max(float(data["professionals"].max()), float(data["recent"].max()), 1)
    ax.set_xlim(-maximo * 0.025, maximo * 1.08)
    ax.set_axisbelow(True)
    ax.grid(axis="x", color=GRID)
    ax.xaxis.set_major_locator(MaxNLocator(4, integer=True))
    ax.xaxis.set_major_formatter(FuncFormatter(_miles))
    ax.tick_params(axis="x", labelsize=10)
    return recientes, historicos


def generar_instituciones(paneles, ruta):
    """``paneles`` = (nacional, privadas_sierra) de
    ``analytics.empleabilidad_instituciones.instituciones_educativas``."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    nacional, privadas = paneles if paneles else (None, None)
    # Fuente solo para esta figura: no altera los demás gráficos del proceso.
    with plt.rc_context({"font.family": ["Arial", "DejaVu Sans"]}):
        fig = plt.figure(figsize=TAMANO, facecolor="white")
        # Marco del panel, como en el tablero de empleabilidad.
        fig.patches.append(FancyBboxPatch(
            (0.012, 0.03), 0.976, 0.94, boxstyle="round,pad=0,rounding_size=0.012",
            transform=fig.transFigure, facecolor="none", edgecolor="#D9DEE4", linewidth=1, zorder=-1))
        fig.text(0.03, 0.9, "Instituciones educativas", fontsize=15, weight="bold", color=TITULO,
                 va="center")
        # Margen izquierdo algo mayor que en Tendencias: los nombres largos no se cortan.
        ejes = (fig.add_axes([0.205, 0.2, 0.285, 0.58]), fig.add_axes([0.665, 0.2, 0.30, 0.58]))
        marcadores = None
        for ax, data, titulo in zip(ejes, (nacional, privadas), TITULOS):
            marcadores = _panel(ax, data, titulo) or marcadores
        if marcadores:
            fig.legend(handles=list(marcadores), loc="lower center", bbox_to_anchor=(0.5, 0.045),
                       ncol=2, frameon=False, fontsize=11, handletextpad=0.6, columnspacing=2.5)
        fig.savefig(ruta, dpi=220, facecolor="white")
        plt.close(fig)
    return str(ruta)

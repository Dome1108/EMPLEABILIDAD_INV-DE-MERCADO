"""[Copia de Tendencias · presentation/charts/education.py, adaptada al observatorio]

Matriculados, titulados y aranceles con el estilo de la plantilla de Tendencias.
A diferencia de Tendencias, no recalcula nada: recibe las tablas que ya calcula el
observatorio con sus filtros (financiamiento, provincia, método de proyección 2025*
y semestre de precios), así la presentación coincide con lo que se ve en la app.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator

SERIES = (("PUBLICO", "Pública", "#DCEAF7", "#555555", 1.0),
          ("PRIVADO", "Privada", "#CAEEFB", "#0070C0", 1.8),
          ("NO CLASIFICADO", "No clasificado", "#EEF1F4", "#9AA6B2", 1.0))


def _guardar(fig, ruta) -> str:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, format="png", dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(ruta)


def _vacio(titulo, ruta, texto="N/D"):
    fig, ax = plt.subplots(figsize=(10, 6), dpi=130)
    ax.axis("off")
    ax.text(.5, .55, texto, ha="center", va="center", fontsize=20, color="#777777", wrap=True)
    ax.set_title(titulo, fontsize=15, fontweight="bold", color="#222222")
    _guardar(fig, ruta)


def _formato(valor: float) -> str:
    return f"{int(round(float(valor))):,}".replace(",", ".")


def generar_serie(tabla, titulo, eje_y, ruta, proyectados=(2025,)):
    """Barras apiladas por financiamiento y línea del total (tabla de enrollment/graduates_table).

    ``tabla``: filas PUBLICO/PRIVADO/NO CLASIFICADO/TOTAL y columnas por año; los años de
    ``proyectados`` se marcan con «*» y barras punteadas.
    """
    if tabla is None or tabla.empty or not tabla.loc["TOTAL"].sum():
        _vacio(titulo, ruta, "N/D: sin registros para los filtros elegidos")
        return
    anios = [int(a) for a in tabla.columns]
    x = np.arange(len(anios))
    fig, ax = plt.subplots(figsize=(10, 6), dpi=130)
    base = np.zeros(len(anios))
    for clave, etiqueta, relleno, borde, grosor in SERIES:
        if clave not in tabla.index or not tabla.loc[clave].sum():
            continue
        valores = tabla.loc[clave].to_numpy(dtype=float)
        barras = ax.bar(x, valores, .62, bottom=base, color=relleno, edgecolor=borde, linewidth=grosor,
                        label=etiqueta)
        for barra, anio in zip(barras, anios):
            if anio in proyectados:
                barra.set_linestyle("--")
        base += valores
    total = tabla.loc["TOTAL"].to_numpy(dtype=float)
    ax.plot(x, total, color="#0070C0", marker="s", linewidth=2.4, zorder=3, label="Total")
    margen = max(float(np.nanmax(total)) * .03, 1)
    for xi, valor in zip(x, total):
        ax.text(xi, valor + margen, _formato(valor), ha="center", va="bottom", fontsize=9, color="#0070C0",
                fontweight="bold")
    ax.set_xticks(x, [f"{a}*" if a in proyectados else str(a) for a in anios])
    ax.set_ylabel(eje_y)
    ax.set_title(titulo, fontsize=13, fontweight="bold")
    ax.grid(axis="y", alpha=.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left")
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.set_ylim(0, max(float(np.nanmax(total)) * 1.15, 1))
    fig.tight_layout()
    _guardar(fig, ruta)


def generar_precios(tabla, ruta, propio=None, propio_etiqueta="UDLA"):
    """Caja y puntos por institución (arancel promedio del semestre), como en Tendencias.

    ``tabla`` = aggregate_prices del observatorio; ``propio`` = arancel UDLA real o estimado.
    """
    titulo = "Distribución de aranceles del mercado"
    datos = (tabla.dropna(subset=["ARANCEL_PROMEDIO"]) if tabla is not None else pd.DataFrame())
    if datos.empty:
        _vacio(titulo, ruta, "N/D: sin aranceles válidos para los filtros elegidos")
        return
    datos = datos.sort_values("ARANCEL_PROMEDIO", kind="stable").reset_index(drop=True)
    vals = datos["ARANCEL_PROMEDIO"].to_numpy(dtype=float)
    rango = max(float(vals.max() - vals.min()), 1)
    fig, ax = plt.subplots(figsize=(9.8, 6.1), dpi=160)
    ax.boxplot([vals], positions=[1], tick_labels=[""], showfliers=False, patch_artist=True,
               boxprops=dict(color="#0070C0", facecolor="#0070C0", alpha=.20, linewidth=2),
               medianprops=dict(color="#0070C0", linewidth=1.8), whiskerprops=dict(color="#0070C0"),
               capprops=dict(color="#0070C0"), widths=.38)
    colores = plt.get_cmap("tab20")(np.linspace(0, 1, max(len(datos), 1)))
    xs = 1 + np.random.default_rng(7).normal(0, .035, len(datos))
    for x, (_, fila), color in zip(xs, datos.iterrows(), colores):
        sigla = str(fila["SIGLA"])
        es_propio = sigla.upper() == propio_etiqueta.upper()
        color_punto = "#006EBF" if es_propio else color
        ax.scatter(x, float(fila["ARANCEL_PROMEDIO"]), s=92 if es_propio else 70, color=color_punto,
                   edgecolor="#004B80" if es_propio else "#444444", linewidth=1.0 if es_propio else .7, zorder=4)
        ax.annotate(sigla, xy=(x, float(fila["ARANCEL_PROMEDIO"])), xytext=(14, 0), textcoords="offset points",
                    fontsize=10, fontweight="bold" if es_propio else "normal", va="center", color=color_punto)
    minimo, maximo = float(vals.min()), float(vals.max())
    if propio is not None and np.isfinite(propio):
        # Línea de referencia UDLA (real o estimada), igual que en la pestaña de precios.
        ax.axhline(propio, color="#C65F6B", linestyle=":", linewidth=1.8, zorder=2)
        ax.text(1.53, propio, f"{propio_etiqueta} ${_formato(propio)}", color="#C65F6B", fontsize=10,
                fontweight="bold", ha="right", va="bottom")
        minimo, maximo = min(minimo, propio), max(maximo, propio)
    rango = max(maximo - minimo, 1)
    ax.set_ylim(max(minimo - rango * .08, 0.0), maximo + rango * .10)
    ax.set_xlim(.45, 1.55)
    ax.set_xticks([])
    ax.set_ylabel("Arancel (USD)", fontsize=11, fontweight="semibold")
    ax.set_title(titulo, fontsize=14, fontweight="bold", pad=14)
    ax.grid(axis="y", alpha=.22)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines["left"].set_color("#999999")
    ax.spines["bottom"].set_color("#999999")
    ax.yaxis.set_major_locator(MaxNLocator(nbins=9, min_n_ticks=8))
    fig.subplots_adjust(left=.15, right=.98, top=.90, bottom=.10)
    _guardar(fig, ruta)

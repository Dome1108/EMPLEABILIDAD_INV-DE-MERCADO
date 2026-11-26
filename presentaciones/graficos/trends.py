"""[Copia de Tendencias · presentation/charts/trends.py, adaptada al observatorio]

Google Trends para la diapositiva 7. Conserva el estilo de Tendencias (áreas, línea de
tendencia punteada y pendiente en puntos/año) pero dibuja exactamente las series que muestra
la pestaña «Demanda e interés académico» (trends_analysis.regional_series): promedio anual
del índice en español para Ecuador, LATAM y todo el mundo, con su tendencia lineal.

El mapa comparativo de Tendencias necesita cartopy; aquí el desglose español frente a
inglés se dibuja como barras por país (los mismos porcentajes del mapa de la app).
"""
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

GRIS = "#727A84"
COLOR_ESPANOL = "#9CCBF4"
COLOR_INGLES = "#006EBF"
COLORES = {"Ecuador": "#9CCBF4", "LATAM": "#438BE3", "Todo el mundo": "#AEB6BE"}
COLOR_TEND_LATAM = "#249BAE"


def _formatear_pendiente(valor):
    signo = "+" if valor >= 0 else "−"
    return f"{signo}{abs(valor):.2f}".replace(".", ",") + " pts/año"


def _guardar(fig, ruta):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, dpi=220, facecolor="white")
    plt.close(fig)
    return str(ruta)


def _vacio(figsize, texto, ruta):
    fig, ax = plt.subplots(figsize=figsize, facecolor="white")
    ax.axis("off")
    ax.text(.5, .5, texto, ha="center", va="center", fontsize=16, color=GRIS)
    return _guardar(fig, ruta)


def generar_tendencia_regional(series, tendencias, ruta_salida):
    """``series`` y ``tendencias`` = trends_analysis.regional_series(regional)."""
    if series is None or series.empty:
        return _vacio((12, 5.5), "N/D\nSin datos regionales de Google Trends", ruta_salida)
    fig, ax = plt.subplots(figsize=(12, 5.5), facecolor="white")
    anios = np.asarray(series.index, dtype=float)
    valores = series.to_numpy(dtype=float)
    finitos = valores[np.isfinite(valores)]
    ymin = max(0, min(20, int(np.floor(finitos.min() / 5) * 5))) if finitos.size else 0
    ymax = max(60, int(np.ceil(finitos.max() / 5) * 5)) if finitos.size else 100
    if finitos.size and ymax - finitos.max() < 8:
        ymax += 10
    parcial = int(anios[-1]) >= date.today().year
    for nombre in series.columns:
        serie = series[nombre].to_numpy(dtype=float)
        validos = np.isfinite(serie)
        if not validos.any():
            continue
        color = COLORES.get(nombre, "#438BE3")
        ax.fill_between(anios[validos], ymin, serie[validos], color=color, alpha=.22, linewidth=0, zorder=1)
        ax.plot(anios[validos], serie[validos], marker="o", markersize=3.8, linewidth=2.1, color=color,
                label=nombre, zorder=4)
        tendencia = tendencias.get(nombre, {})
        if tendencia.get("slope") is not None:
            color_tend = COLOR_TEND_LATAM if nombre == "LATAM" else color
            ax.plot(anios, tendencia["line"], linestyle=(0, (5, 3)), linewidth=1.55, color=color_tend,
                    label=f"Tendencia {nombre}", zorder=3)
            ax.text(anios[-1] + .10, tendencia["line"][-1], _formatear_pendiente(tendencia["slope"]),
                    color=color_tend, fontsize=8.3, ha="left", va="center", weight="bold")
    if parcial:
        ax.axvline(anios[-1], color="#D9DDE1", linestyle=":", linewidth=.8, zorder=0)
        ax.text(anios[-1] + .05, ymax - 1.2, f"{int(anios[-1])}* dato parcial", color="#8D9399",
                fontsize=8.5, ha="left", va="top")
    ax.set_xlim(anios[0] - .18, anios[-1] + .78)
    ax.set_ylim(ymin, ymax)
    ax.set_ylabel("Índice relativo (0–100)", fontsize=9.5, color="#31383F")
    ax.set_title("Evolución del interés por el programa a nivel regional", loc="left", fontsize=15,
                 weight="bold", color="#20242A")
    ax.set_xticks(anios, [f"{int(a)}*" if parcial and a == anios[-1] else str(int(a)) for a in anios],
                  fontsize=8.5, color="#4D555D")
    ax.tick_params(axis="y", labelsize=8.5, colors="#4D555D", length=0)
    ax.grid(axis="y", color="#E5E8EB", linewidth=.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#D5D9DD")
    ax.legend(frameon=False, ncol=3, loc="upper left", fontsize=8.0, handlelength=2.3, columnspacing=1.25)
    fig.subplots_adjust(left=.055, right=.92, bottom=.12, top=.88)
    return _guardar(fig, ruta_salida)


def generar_comparacion(tabla, palabras, ruta_salida, top=10):
    """Barras 100 % por país: porcentaje de búsquedas en español frente a inglés.

    ``tabla`` = trends_analysis.comparison_table; se muestran los ``top`` países con más
    búsquedas en español (mismo orden que la tabla de la app). Tamaño de la imagen de la plantilla.
    """
    figsize = (4.0 * 1.6, 2.6 * 1.6)
    if tabla is None or tabla.empty:
        return _vacio(figsize, "N/D\nSin desglose comparativo\nespañol frente a inglés", ruta_salida)
    datos = tabla.head(top).iloc[::-1].reset_index(drop=True)
    esp = datos["% español"].fillna(0).to_numpy(dtype=float)
    ing = datos["% inglés"].fillna(0).to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=figsize, facecolor="white")
    y = np.arange(len(datos))
    ax.barh(y, esp, color=COLOR_ESPANOL, height=.68, label=f"{palabras[0]} (español)")
    ax.barh(y, ing, left=esp, color=COLOR_INGLES, height=.68, label=f"{palabras[1]} (inglés)")
    for yi, (e, i) in enumerate(zip(esp, ing)):
        if e >= 12:
            ax.text(e / 2, yi, f"{e:.0f} %", ha="center", va="center", fontsize=8, color="#123F70")
        if i >= 12:
            ax.text(e + i / 2, yi, f"{i:.0f} %", ha="center", va="center", fontsize=8, color="white")
    ax.set_yticks(y, datos["País"], fontsize=9, color="#4D555D")
    ax.set_xlim(0, 100)
    ax.set_xticks([])
    ax.spines[["top", "right", "bottom", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    # Sin leyenda: la plantilla ya tiene los cuadritos «término español / término inglés».
    fig.tight_layout(pad=.4)
    return _guardar(fig, ruta_salida)

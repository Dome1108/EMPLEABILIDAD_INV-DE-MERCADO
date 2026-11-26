"""Gráficos de la pestaña «Viabilidad de carreras» para la presentación.

- ``generar_radar_bloques``: perfil de 5 dimensiones del dashboard (viabilidad/app.py · radar)
  con el trazo suave y la paleta del radar de Tendencias (graficos/radar.py).
- ``generar_cuadrante``: «Demanda vs. competencia» (viabilidad/app.py · market_chart):
  mismas zonas, umbrales, carrera elegida y carrera de referencia.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

AZUL, CELESTE = "#006EBF", "#A6CAEC"
COLORES_CUADRANTE = {"Mercado atractivo": "#248064", "Mercado competido": "#c18b37",
                     "Baja tracción": "#c46d79", "Mercado débil": "#6b8194"}


def _guardar(fig, ruta, **kwargs):
    os.makedirs(os.path.dirname(str(ruta)) or ".", exist_ok=True)
    fig.savefig(str(ruta), format="png", dpi=300, **kwargs)
    plt.close(fig)
    return str(ruta)


def generar_radar_bloques(etiquetas, valores, ruta):
    """Radar suave (interpolación de Hermite, como Tendencias) con valores 0–100."""
    m = len(etiquetas)
    r = np.array([min(max(float(v), 0) / 100, 1.0) for v in valores])
    theta = np.linspace(0, 2 * np.pi, m, endpoint=False)
    delta = 2 * np.pi / m
    pendientes = np.array([(r[(k + 1) % m] - r[(k - 1) % m]) / (2 * delta) for k in range(m)])
    theta_d, r_d = [], []
    for k in range(m):
        th0 = theta[k]
        dth = (theta[k + 1] if k < m - 1 else 2 * np.pi) - th0
        r0, r1, s0, s1 = r[k], r[(k + 1) % m], pendientes[k], pendientes[(k + 1) % m]
        t = np.linspace(0, 1, 80, endpoint=False)
        theta_d.append(th0 + t * dth)
        r_d.append((2 * t**3 - 3 * t**2 + 1) * r0 + (t**3 - 2 * t**2 + t) * dth * s0
                   + (-2 * t**3 + 3 * t**2) * r1 + (t**3 - t**2) * dth * s1)
    theta_d = np.concatenate(theta_d + [np.array([2 * np.pi])])
    r_d = np.clip(np.concatenate(r_d + [np.array([r[0]])]), 0, None)

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.plot(theta_d, r_d, linewidth=2, color=AZUL)
    ax.fill(theta_d, r_d, color=CELESTE, alpha=0.45)
    ax.plot(theta, r, "o", color=AZUL)
    ax.set_xticks(theta)
    ax.set_xticklabels([""] * m)
    for angulo in theta:
        ax.plot([angulo, angulo], [0, 1.0], linestyle=":", color="gray", linewidth=1)
    for angulo, etiqueta in zip(theta, etiquetas):
        x = np.sin(angulo)  # con offset π/2 y sentido horario: + a la derecha, − a la izquierda
        ha = "center" if abs(x) < .2 else ("left" if x > 0 else "right")
        ax.text(angulo, 1.27, etiqueta, ha=ha, va="center", fontsize=12)
    for angulo, radio, valor in zip(theta, r, valores):
        ax.text(angulo, radio, f"{valor:.0f}%", ha="center", va="center", fontsize=9, fontweight="bold",
                color=AZUL, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=AZUL, alpha=1.0))
    ax.set_ylim(0, 1.20)
    ticks = [0.0, 0.20, 0.40, 0.60, 0.80, 1.0]
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{int(y * 100)}%" for y in ticks])
    return _guardar(fig, ruta, bbox_inches="tight", pad_inches=0.2)


def generar_cuadrante(resultados, actual, referencia, umbral_busquedas, umbral_competidores, ruta,
                      ancho=6.7, alto=4.5):
    """Búsquedas relativas (x) frente a competidores (y), con las cuatro zonas del dashboard."""
    fig, ax = plt.subplots(figsize=(ancho, alto))
    ymax = max([r["competidores"] for r in resultados] + [umbral_competidores]) * 1.25
    xmax = max(r["busquedas"] for r in resultados) * 1.12
    t, c = umbral_busquedas, umbral_competidores
    for x0, x1, y0, y1, color in ((0, t, 0, c, "#fcf0f2"), (t, xmax, 0, c, "#eaf6ef"),
                                  (0, t, c, ymax, "#edf2f6"), (t, xmax, c, ymax, "#fcf6e9")):
        ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color=color, zorder=0, linewidth=0))
    ax.axvline(t, color="#9cadbb", linestyle="--", linewidth=1)
    ax.axhline(c, color="#9cadbb", linestyle="--", linewidth=1)
    for x, y, texto, color in ((t / 2, ymax * .95, "MERCADO DÉBIL", "#70869b"),
                               ((t + xmax) / 2, ymax * .95, "MERCADO COMPETIDO", "#b68b4b"),
                               (t / 2, ymax * .04, "BAJA TRACCIÓN", "#bd7b86"),
                               ((t + xmax) / 2, ymax * .04, "MERCADO ATRACTIVO", "#468870")):
        ax.text(x, y, texto, ha="center", va="center", fontsize=8, color=color, fontweight="bold")
    ax.scatter([r["busquedas"] for r in resultados], [r["competidores"] for r in resultados],
               s=40, color="#9db6cb", edgecolor="white", linewidth=1, zorder=3)
    ax.scatter([referencia["busquedas"]], [referencia["competidores"]], marker="D", s=80, color="#153954",
               edgecolor="white", linewidth=1.5, zorder=4, label=f"Referencia: {referencia['carrera']}")
    ax.scatter([actual["busquedas"]], [actual["competidores"]], s=230, alpha=.9,
               color=COLORES_CUADRANTE.get(actual["cuadrante"], AZUL), edgecolor="white", linewidth=2.5,
               zorder=5, label=actual["carrera"])
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)
    ax.set_xlabel(f"Búsquedas relativas · {referencia['carrera']} = 100%", fontsize=9, color="#71869a")
    ax.set_ylabel("Número de competidores", fontsize=9, color="#71869a")
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.tick_params(colors="#71869a", labelsize=8, length=0)
    for lado in ax.spines.values():
        lado.set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.14), ncol=2, frameon=False, fontsize=8)
    fig.tight_layout()
    return _guardar(fig, ruta, facecolor="white")

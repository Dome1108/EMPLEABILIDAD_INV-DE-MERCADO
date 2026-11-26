# [Copia de Tendencias · presentation/charts/radar.py; solo cambian las rutas de import]
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os


def generar_grafico_radar(valores, ruta_salida):
    if not valores:
        print("No hay datos de gráfico radar")
        return
    # Reemplazar None por 0 para evitar errores
    if isinstance(valores, dict):
        valor_busqueda = float(valores.get("valor_busqueda") or 0.0)
        valor_competencia_presencialidad = float(valores.get("valor_competencia_presencialidad") or 0.0)
        valor_competencia_virtualidad = float(valores.get("valor_competencia_virtualidad") or 0.0)
        valor_linkedin = float(valores.get("valor_linkedin") or 0.0)
        valor_mercado = float(valores.get("valor_mercado") or 0.0)
    else:
        valor_busqueda = float(valores[0]) if valores[0] is not None else 0.0
        valor_competencia_presencialidad = float(valores[1]) if valores[1] is not None else 0.0
        valor_competencia_virtualidad = float(valores[2]) if valores[2] is not None else 0.0
        valor_linkedin = float(valores[3]) if valores[3] is not None else 0.0
        valor_mercado = float(valores[4]) if valores[4] is not None else 0.0

    # Los valores en BD ya son porcentajes (máximos: Búsqueda 26.07%, Competencia 12.93%, LinkedIn 38.48%, Mercado 22.51%)
    # Normalizar a escala 0-100% para el gráfico
    competencia_avg = (
        valor_competencia_presencialidad + valor_competencia_virtualidad
    ) / 2

    # Convertir de porcentaje con peso a porcentaje normalizado (0-100)
    busqueda_pct = round((valor_busqueda / 26.07) * 100)
    competencia_pct = round((competencia_avg / 12.93) * 100)
    linkedin_pct = round((valor_linkedin / 38.48) * 100)
    mercado_pct = round((valor_mercado / 22.51) * 100)

    # Calcular viabilidad como suma directa de los valores con peso
    viabilidad = valor_busqueda + competencia_avg + valor_linkedin + valor_mercado
    print(
        f"[DEBUG RADAR] Valores desde BD: busqueda={valor_busqueda:.2f}%, competencia_avg={competencia_avg:.2f}%, linkedin={valor_linkedin:.2f}%, mercado={valor_mercado:.2f}%"
    )
    print(
        f"[DEBUG RADAR] Valores normalizados (0-100): busqueda={busqueda_pct}%, competencia={competencia_pct}%, linkedin={linkedin_pct}%, mercado={mercado_pct}%, viabilidad={viabilidad:.2f}%"
    )
    labels = ["Busqueda", "Competencia", "LinkedIn", "Mercado"]
    valores_grafico = [busqueda_pct, competencia_pct, linkedin_pct, mercado_pct]
    m = len(labels)
    # Normalizar al rango [0, 1] para graficar
    r = np.array([min(v / 100, 1.0) for v in valores_grafico], dtype=float)
    theta = np.linspace(0, 2 * np.pi, m, endpoint=False)
    delta = 2 * np.pi / m
    slopes = np.array(
        [(r[(k + 1) % m] - r[(k - 1) % m]) / (2 * delta) for k in range(m)]
    )
    theta_dense = []
    r_dense = []
    for k in range(m):
        th0 = theta[k]
        th1 = theta[(k + 1) % m] if k < m - 1 else 2 * np.pi
        r0, r1 = r[k], r[(k + 1) % m]
        s0, s1 = slopes[k], slopes[(k + 1) % m]
        dth = (th1 - th0) if k < m - 1 else (2 * np.pi - th0)
        t = np.linspace(0, 1, 80, endpoint=False)
        h00 = 2 * t**3 - 3 * t**2 + 1
        h10 = t**3 - 2 * t**2 + t
        h01 = -2 * t**3 + 3 * t**2
        h11 = t**3 - t**2
        theta_dense.append(th0 + t * dth)
        r_dense.append(h00 * r0 + h10 * dth * s0 + h01 * r1 + h11 * dth * s1)
    theta_dense = np.concatenate(theta_dense + [np.array([2 * np.pi])])
    r_dense = np.concatenate(r_dense + [np.array([r[0]])])

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 4)
    ax.set_theta_direction(-1)
    # cambiado por samuel
    # Paleta de resultados de viabilidad: azul para la serie y celeste para
    # el área del radar, consistente con los gráficos del reporte.
    color_azul = "#006EBF"
    color_celeste = "#A6CAEC"
    ax.plot(theta_dense, r_dense, linewidth=2, color=color_azul)
    ax.fill(theta_dense, r_dense, color=color_celeste, alpha=0.45)
    ax.plot(theta, r, "o", color=color_azul)
    #------------------------------------
    ax.set_xticks(theta)
    ax.set_xticklabels([""] * len(labels))
    # Líneas radiales internas como puntitos
    for angle in theta:
        ax.plot([angle, angle], [0, 1.0], linestyle=":", color="gray", linewidth=1)
    for angle, label in zip(theta, labels):
        if label in ["Busqueda", "LinkedIn"]:
            rot = 315
        elif label in ["Mercado", "Competencia"]:
            rot = 405
        else:
            rot = 0
        ax.text(
            angle,
            1.28,
            label,
            rotation=rot,
            ha="center",
            va="center",
            fontsize=12,
            rotation_mode="anchor",
        )

    # Agregar porcentajes en los puntos
    for angle, rad, val in zip(theta, r, valores_grafico):
        ax.text(
            angle,
            rad,
            f"{int(val)}%",
            ha="center",
            va="center",
            fontsize=9,
            fontweight="bold",
            color=color_azul,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=color_azul, alpha=1.0),
        )
    ax.set_ylim(0, 1.20)
    yticks = [0.0, 0.20, 0.40, 0.60, 0.80, 1.0]
    ax.set_yticks(yticks)
    ax.set_yticklabels([f"{int(y*100)}%" for y in yticks])

    # Crear directorio de salida si no existe
    output_path = ruta_salida.replace(".jpg", ".png")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    plt.savefig(output_path, format="png", bbox_inches="tight", pad_inches=0.2, dpi=300)
    plt.close(fig)
    return viabilidad

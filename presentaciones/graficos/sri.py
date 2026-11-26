"""Copia del proyecto Tendencias (presentation/charts) adaptada al observatorio."""
import re
# cambiado por samuel
import unicodedata
#------------------------------------
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
# cambiado por samuel
_MESES_NORMALIZADOS = {
    "enero": 1, "ene": 1,
    "febrero": 2, "feb": 2,
    "marzo": 3, "mar": 3,
    "abril": 4, "abr": 4,
    "mayo": 5, "may": 5,
    "junio": 6, "jun": 6,
    "julio": 7, "jul": 7,
    "agosto": 8, "ago": 8,
    "septiembre": 9, "sept": 9, "sep": 9,
    "setiembre": 9, "set": 9,
    "octubre": 10, "oct": 10,
    "noviembre": 11, "nov": 11,
    "diciembre": 12, "dic": 12,
}
#------------------------------------
AZUL = "#0878BE"
CELESTE = "#75B9E6"
# Celeste ya utilizado por los rectángulos de la plantilla oficial.
CELESTE_PLANTILLA = "#DCEAF7"
GRIS = "#5E6670"
BORDE = "#AEB8C2"


# cambiado por samuel
def _formatear_monto_eje(valor, _pos=None):
    """Formato compacto para el eje Y: $5M, $850K o $500."""
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return "N/D"
    if not np.isfinite(valor):
        return "N/D"
    signo = "-" if valor < 0 else ""
    valor = abs(valor)
    if valor >= 1_000_000:
        millones = valor / 1_000_000
        texto = f"{millones:.1f}".rstrip("0").rstrip(".")
        return f"{signo}${texto}M"
    if valor >= 1_000:
        miles = valor / 1_000
        texto = f"{miles:.1f}".rstrip("0").rstrip(".")
        return f"{signo}${texto}K"
    return f"{signo}${valor:,.0f}"
#------------------------------------


# cambiado por samuel
def _formatear_monto_card(valor):
    """Formato monetario completo usado en el cuadro Overview."""
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return "N/D"
    if not np.isfinite(valor):
        return "N/D"
    if abs(valor) >= 1e6:
        # Los montos de varios CIIU llegan a miles de millones: en millones para que quepan.
        return f"${valor / 1e6:,.1f}M".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"${valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
#------------------------------------


# cambiado por samuel
def _formatear_velocidad(valor):
    """Presenta la pendiente en dólares por mes, con el signo explícito."""
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return "N/D"
    if not np.isfinite(valor):
        return "N/D"
    signo = "+" if valor > 0 else "−" if valor < 0 else ""
    return f"{signo}{_formatear_monto_eje(abs(valor))}/mes"
#------------------------------------


# cambiado por samuel
def _pendiente_lineal(valores, periodos):
    """Calcula la pendiente lineal de una serie en dólares por mes."""
    valores = np.asarray(valores, dtype=float)
    periodos = np.asarray(periodos, dtype=float)
    validos = np.isfinite(valores) & np.isfinite(periodos)
    if validos.sum() == 0:
        return np.nan, np.full(periodos.shape, np.nan, dtype=float)
    if validos.sum() < 2 or np.ptp(periodos[validos]) == 0:
        base = valores[validos][0] if validos.any() else 0.0
        return 0.0, np.full(periodos.shape, base, dtype=float)
    coeficientes = np.polyfit(periodos[validos], valores[validos], 1)
    return float(coeficientes[0]), np.polyval(coeficientes, periodos)
#------------------------------------


def _codigos(valor):
    if isinstance(valor, (list, tuple, set)):
        return [str(codigo).strip() for codigo in valor if str(codigo).strip()]
    return [codigo.strip() for codigo in re.split(r"[,;\n]+", str(valor or "")) if codigo.strip()]


def _prefijo_ciiu(valor):
    coincidencia = re.match(r"\s*([A-Za-z]?\d+)", str(valor or ""))
    return coincidencia.group(1).upper() if coincidencia else str(valor or "").strip().upper()


def preparar_datos_sri(codigos, filas):
    return _codigos(codigos), pd.DataFrame(
        filas,
        columns=["ciiu", "anio", "mes", "personas_naturales", "sociedades"],
    )


# cambiado por samuel
def _normalizar_mes(valor):
    if pd.isna(valor):
        return pd.NA
    if isinstance(valor, (int, np.integer)):
        return int(valor) if 1 <= int(valor) <= 12 else pd.NA
    if isinstance(valor, (float, np.floating)) and np.isfinite(valor):
        entero = int(valor)
        return entero if valor == entero and 1 <= entero <= 12 else pd.NA
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    texto = texto.strip().lower().rstrip(".")
    if texto.isdigit():
        entero = int(texto)
        return entero if 1 <= entero <= 12 else pd.NA
    return _MESES_NORMALIZADOS.get(texto, pd.NA)


def ajustar_personas_naturales(datos):
    if datos.empty:
        return datos.copy()
    df = datos.copy()
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df["mes"] = df["mes"].map(_normalizar_mes)
    df["personas_naturales"] = pd.to_numeric(df["personas_naturales"], errors="coerce")
    df["sociedades"] = pd.to_numeric(df["sociedades"], errors="coerce")
    df = df.dropna(subset=["anio", "mes"]).copy()
    df["anio"] = df["anio"].astype(int)
    df["mes"] = df["mes"].astype(int)
    df["personas_ajustadas"] = df["personas_naturales"]
    return df.sort_values(["anio", "mes"], kind="stable").reset_index(drop=True)


def _agrupar_mensual(datos):
    """Agrupa solo por año y mes, sin completar ni recortar meses."""
    ajustados = ajustar_personas_naturales(datos)
    if ajustados.empty:
        return pd.DataFrame(columns=["anio", "mes", "personas_ajustadas", "sociedades"])
    mensual = ajustados.groupby(["anio", "mes"], as_index=False, sort=True)[
        ["personas_ajustadas", "sociedades"]
    ].sum(min_count=1)
    return mensual.sort_values(["anio", "mes"], kind="stable").reset_index(drop=True)
#------------------------------------


def _distribuir_eje_mensual(mensual):
    """Asigna 12 posiciones uniformes por año sin crear valores de ventas.

    Las filas de ``mensual`` permanecen intactas para dibujar las series. La
    cuadrícula adicional solo sirve para que el eje X muestre siempre Ene–Dic
    bajo cada año, aunque algún mes no tenga un registro en la base.
    """

    if mensual is None or mensual.empty:
        return mensual.copy() if mensual is not None else mensual, [], {}

    anios = sorted(int(anio) for anio in mensual["anio"].unique())
    inicio_por_anio = {anio: indice * 12 for indice, anio in enumerate(anios)}
    distribuido = mensual.copy()
    distribuido["x"] = [
        inicio_por_anio[int(anio)] + int(mes) - 1
        for anio, mes in zip(distribuido["anio"], distribuido["mes"])
    ]
    marcas = [
        (anio, mes, inicio_por_anio[anio] + mes - 1)
        for anio in anios
        for mes in range(1, 13)
    ]
    return distribuido, marcas, inicio_por_anio
#------------------------------------


def generar_grafico_desestacionalidad(codigos, datos, ruta_salida, mes_acumulado=None, anio_acumulado=None):
    """``mes_acumulado``/``anio_acumulado``: filtro «Acumulado comparable hasta el mes» de la app;
    el cuadro Overview suma enero–ese mes. Sin filtro se usa el último mes disponible (Tendencias)."""
    ruta = Path(ruta_salida)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # La figura tiene el tamaño exacto de su espacio en la diapositiva 23:
    # Overview a la izquierda (toda la altura) y el gráfico a la derecha.
    from presentaciones.plantilla_mercado import CAJA_SRI
    fig = plt.figure(figsize=CAJA_SRI[2:], facecolor="white")
    ax_info = fig.add_axes([0.0, 0.01, 0.285, 0.98])
    ax = fig.add_axes([0.355, 0.255, 0.635, 0.665])
    ax_info.axis("off")

    if datos.empty:
        ax.axis("off")
        ax.text(0.5, 0.5, "N/D\nSin ventas mensuales para los CIIU seleccionados",
                ha="center", va="center", fontsize=18, color=GRIS)
        ax_info.text(0.05, 0.8, "CIIU", fontsize=13, weight="bold", color=AZUL)
        ax_info.text(0.05, 0.68, ", ".join(codigos) or "N/D", fontsize=12, color=GRIS)
        fig.savefig(ruta, dpi=220, facecolor="white")
        plt.close(fig)
        return {"codigos": codigos, "anios": [], "ultimo_mes": None, "meses_eje": []}

    # cambiado por samuel
    mensual = _agrupar_mensual(datos)
    ultimo_anio = int(anio_acumulado or mensual["anio"].max())
    ultimo_mes = int(mes_acumulado or mensual.loc[mensual["anio"] == ultimo_anio, "mes"].max())
    anual = mensual[mensual["mes"] <= ultimo_mes].groupby("anio", as_index=False)[
        ["personas_ajustadas", "sociedades"]
    ].sum(min_count=1)
    #------------------------------------

    mensual, marcas_mensuales, inicio_por_anio = _distribuir_eje_mensual(mensual)
    anio_inicial = int(mensual["anio"].min())
    mensual["periodo"] = (
        (mensual["anio"].astype(int) - anio_inicial) * 12
        + mensual["mes"].astype(int) - 1
    )
    pendiente_pn, tendencia_pn = _pendiente_lineal(
        mensual["personas_ajustadas"], mensual["periodo"]
    )
    pendiente_soc, tendencia_soc = _pendiente_lineal(
        mensual["sociedades"], mensual["periodo"]
    )

    actual = anual[anual["anio"] == ultimo_anio].iloc[0]
    # El cuadro conserva la composición de la plantilla: marco redondeado,
    # pastilla azul de Overview, dos filas de datos y separador. Los nuevos
    # indicadores de velocidad se muestran en la parte inferior del mismo
    # cuadro, sin alterar su estructura exterior.
    ax_info.add_patch(FancyBboxPatch(
        (0.012, 0.012), 0.976, 0.976,
        boxstyle="round,pad=0.0,rounding_size=0.04",
        transform=ax_info.transAxes, facecolor="white", edgecolor="#D4D9DE",
        linewidth=1.0, clip_on=False,
    ))
    ax_info.add_patch(FancyBboxPatch(
        (0.045, 0.85), 0.91, 0.11,
        boxstyle="round,pad=0.0,rounding_size=0.035",
        transform=ax_info.transAxes, facecolor=CELESTE_PLANTILLA, edgecolor="none",
        clip_on=False,
    ))
    ax_info.text(0.08, 0.905, "Overview", transform=ax_info.transAxes,
                 fontsize=13, weight="bold", color=AZUL, va="center")
    for y, etiqueta, monto, color in (
        (0.745, "Personas naturales", actual["personas_ajustadas"], AZUL),
        (0.635, "Sociedades", actual["sociedades"], CELESTE),
    ):
        ax_info.scatter([0.095], [y], transform=ax_info.transAxes,
                        s=34, color=color, zorder=5, clip_on=False)
        ax_info.text(0.14, y, etiqueta, transform=ax_info.transAxes,
                     fontsize=10, color=GRIS, va="center")
        ax_info.text(0.93, y, _formatear_monto_card(monto), transform=ax_info.transAxes,
                     fontsize=10.5, weight="bold", color="#20242A", ha="right", va="center")
    ax_info.plot([0.08, 0.93], [0.545, 0.545], transform=ax_info.transAxes,
                 color="#E0E3E6", linewidth=1.0, clip_on=False)
    ax_info.text(0.08, 0.465,
                 f"Acumulado enero-{MESES[ultimo_mes - 1].lower()} {ultimo_anio}",
                 transform=ax_info.transAxes, fontsize=9.5, color="#8A9199", va="center")
    ax_info.text(0.08, 0.335, "Velocidad de crecimiento", transform=ax_info.transAxes,
                 fontsize=10.5, weight="bold", color="#20242A", va="center")
    for y, etiqueta, pendiente, color in (
        (0.215, "Personas naturales", pendiente_pn, AZUL),
        (0.105, "Sociedades", pendiente_soc, CELESTE),
    ):
        ax_info.text(0.08, y, etiqueta, transform=ax_info.transAxes,
                     fontsize=10, color=GRIS, va="center")
        ax_info.text(0.93, y, _formatear_velocidad(pendiente), transform=ax_info.transAxes,
                     fontsize=10.5, weight="bold", color=color, ha="right", va="center")

    x = mensual["x"].to_numpy()
    ax.plot(x, mensual["personas_ajustadas"], marker="o", markersize=4.5, linewidth=2.6,
            color=AZUL, label="Personas naturales")
    ax.plot(x, mensual["sociedades"], marker="o", markersize=4.5, linewidth=2.6,
            color=CELESTE, label="Sociedades")
    ax.plot(x, tendencia_pn, linewidth=1.6, linestyle=(0, (5, 3)), color=AZUL,
            alpha=0.9, label="Pendiente personas naturales")
    ax.plot(x, tendencia_soc, linewidth=1.6, linestyle=(0, (5, 3)), color=CELESTE,
            alpha=0.95, label="Pendiente sociedades")
    ax.set_title("Evolución anual", loc="left", pad=8,
                 fontsize=14, weight="bold", color="#20242A")
    # cambiado por samuel
    margen_x = 0.5
    # El eje debe conservar los doce meses aunque la base solo tenga datos
    # para algunos de ellos; los puntos ausentes no se inventan.
    ax.set_xlim(float(marcas_mensuales[0][2]) - margen_x,
                float(marcas_mensuales[-1][2]) + margen_x)
    #------------------------------------

    # Eje Y monetario compacto y visible.
    ax.yaxis.set_major_formatter(FuncFormatter(_formatear_monto_eje))
    ax.set_ylabel("Ventas declaradas (USD)", fontsize=10, color=GRIS, labelpad=8)
    ax.grid(axis="y", color="#E6E9ED", linewidth=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BORDE)
    ax.spines["bottom"].set_color(BORDE)
    ax.tick_params(axis="y", labelcolor=GRIS, labelsize=10, length=3, color=BORDE)

    # Eje X jerárquico: todos los meses del calendario abajo y cada año en
    # una caja centrada debajo de sus doce meses. Las marcas adicionales no
    # agregan ni inventan datos de las series.
    ax.set_xticks([x for _, _, x in marcas_mensuales])
    # Con la figura a tamaño real los 12 meses de cada año no caben en
    # horizontal; se escriben en vertical para que se lean sin encimarse.
    ax.set_xticklabels(
        [MESES[mes - 1] for _, mes, _ in marcas_mensuales],
        fontsize=8, color=GRIS, rotation=90
    )
    ax.tick_params(axis="x", which="major", length=3, color=BORDE, pad=4)
    for anio, inicio in inicio_por_anio.items():
        ax.annotate(
            str(anio), xy=(inicio + 5.5, 0), xycoords=("data", "axes fraction"),
            xytext=(0, -42), textcoords="offset points",
            ha="center", va="center", fontsize=10, weight="bold", color=GRIS,
            annotation_clip=False,
            bbox={
                "boxstyle": "round,pad=0.3",
                "facecolor": CELESTE_PLANTILLA,
                "edgecolor": "#C2D8EA",
                "linewidth": 0.8,
            },
        )
    ax.annotate("Periodo", xy=(0.5, 0), xycoords="axes fraction", xytext=(0, -62),
                textcoords="offset points", ha="center", va="center",
                fontsize=9.5, color=GRIS, annotation_clip=False)
    ax.legend(frameon=False, loc="upper left", ncol=2, fontsize=9.5,
              handlelength=2.5, columnspacing=1.4)
    fig.savefig(ruta, dpi=220, facecolor="white")
    plt.close(fig)
    return {
        "codigos": codigos,
        "anios": [int(a) for a in anual["anio"]],
        "ultimo_mes": ultimo_mes,
        "meses_eje": [(int(anio), int(mes)) for anio, mes, _ in marcas_mensuales],
        "pendiente_personas_naturales": pendiente_pn,
        "pendiente_sociedades": pendiente_soc,
    }

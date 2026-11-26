"""Indicadores de Google Trends a partir de los datos guardados por Tendencias. Sin acceso a bases.

Reproduce las mismas reglas que usa el proyecto Tendencias para su presentación:
- Interés de búsqueda: promedio de las 6 palabras con mayor promedio frente al promedio de
  las palabras base de la carrera de referencia (`analytics/web.py`, peso 8,57 puntos).
- Evolución regional: promedio anual del índice en español para Ecuador, LATAM y todo el
  mundo, con una recta del primer al último año en puntos por año (`presentation/charts/trends.py`).
- Desglose comparativo por región (vista `vw_google_trends`): porcentaje de la palabra
  en español y en inglés por país, de una misma descarga comparativa.
"""
import unicodedata

import numpy as np
import pandas as pd

from paises_iso3 import PAISES_ISO3

TRENDS_WEIGHT = 8.57  # puntos máximos de Google Trends en el puntaje web de Tendencias
TOP_KEYWORDS = 6
LATAM = {
    "argentina", "bolivia", "brazil", "brasil", "chile", "colombia", "costa rica", "cuba",
    "dominican republic", "republica dominicana", "ecuador", "el salvador", "guatemala", "haiti",
    "honduras", "mexico", "nicaragua", "panama", "paraguay", "peru", "puerto rico", "uruguay", "venezuela",
}
# Países que guarda Tendencias (en español) → código ISO-3 para el mapa.
ISO3 = {
    "alemania": "DEU", "argentina": "ARG", "bolivia": "BOL", "brasil": "BRA", "brazil": "BRA",
    "canada": "CAN", "chile": "CHL", "colombia": "COL", "corea del sur": "KOR", "costa rica": "CRI",
    "cuba": "CUB", "ecuador": "ECU", "el salvador": "SLV", "espana": "ESP", "estados unidos": "USA",
    "francia": "FRA", "guatemala": "GTM", "haiti": "HTI", "honduras": "HND", "italia": "ITA",
    "mexico": "MEX", "nicaragua": "NIC", "panama": "PAN", "paraguay": "PRY", "peru": "PER",
    "puerto rico": "PRI", "reino unido": "GBR", "republica dominicana": "DOM", "uruguay": "URY",
    "venezuela": "VEN", "vietnam": "VNM", "portugal": "PRT", "japon": "JPN", "china": "CHN",
    "india": "IND", "australia": "AUS", "paises bajos": "NLD", "suiza": "CHE", "rusia": "RUS",
}


def country_code(name):
    """Código ISO-3 del país tal como lo escribe Google Trends en español."""
    key = normalize(name).lower()
    return PAISES_ISO3.get(key) or ISO3.get(key)


def normalize(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).upper().split())


def folder_level(folder):
    """Nivel de carreras_facultad que corresponde a la carpeta del proyecto."""
    folder = normalize(folder)
    if "POSGRADO" in folder:
        return "Posgrado"
    return "Pregrado CR" if folder.endswith(" CR") else "Pregrado"


def project_label(row):
    """Texto de un proyecto de Tendencias en los selectores: id · programa · referencia · fecha."""
    created = row["creado"].strftime("%d/%m/%Y") if pd.notna(row["creado"]) else "sin fecha"
    regional = " · con serie regional" if row["filas_regionales"] else ""
    return (f"{row['id']} · {str(row['carrera_estudio']).title()} · ref. {str(row['carrera_referencia']).title()}"
            f" · {created}{regional}")


def best_project(projects, career, level=None):
    """Proyecto más afín a la carrera elegida en el observatorio; None si ninguno coincide.

    Prioridad: nombre del programa en estudio igual a la carrera > carrera de referencia igual >
    coincidencia parcial. En empate, el que tiene serie regional y luego el más reciente.
    """
    if projects is None or projects.empty or not career:
        return None
    target = normalize(career)
    posgrado = normalize(level) == "CUARTO NIVEL"

    def score(row):
        study, reference = normalize(row["carrera_estudio"]), normalize(row["carrera_referencia"])
        points = 0
        if study == target:
            points = 4
        elif reference == target:
            points = 3
        elif target and (target in study or study in target):
            points = 2
        elif target and (target in reference or reference in target):
            points = 1
        if points and posgrado == ("POSGRADO" in normalize(row["tipo_carpeta"])):
            points += .5
        return points

    ranked = projects.assign(_score=projects.apply(score, axis=1),
                             _regional=projects["filas_regionales"].gt(0).astype(int))
    ranked = ranked[ranked["_score"] > 0]
    if ranked.empty:
        return None
    return int(ranked.sort_values(["_score", "_regional", "id"], ascending=False).iloc[0]["id"])


def reference_base(base, project):
    """Palabras base de la carrera de referencia del proyecto (mismo nivel si existe)."""
    if base is None or base.empty:
        return pd.DataFrame(columns=["palabra", "cantidad"])
    names = base["carrera"].map(normalize)
    same = base[names.eq(normalize(project["carrera_referencia"]))]
    level = same[same["nivel"].eq(folder_level(project["tipo_carpeta"]))]
    chosen = level if not level.empty else same
    return chosen[["palabra", "cantidad"]].reset_index(drop=True)


def search_interest(keywords, base):
    """Promedio de las 6 palabras más buscadas frente a la base de la carrera de referencia."""
    values = keywords["promedio"].dropna().sort_values(ascending=False) if keywords is not None else pd.Series(dtype=float)
    top = values.head(TOP_KEYWORDS)
    top_mean = float(top.mean()) if len(top) else None
    base_mean = float(base["cantidad"].mean()) if base is not None and len(base) else None
    ratio = 100 * top_mean / base_mean if top_mean is not None and base_mean else None
    points = min(ratio / 100 * TRENDS_WEIGHT, TRENDS_WEIGHT) if ratio is not None else None
    return {"top_mean": top_mean, "top_n": len(top), "base_mean": base_mean, "base_n": 0 if base is None else len(base),
            "ratio": ratio, "points": points}


def _slope(years, values, until=None):
    """Recta del primer punto al último punto (igual que la diapositiva de Tendencias).

    La pendiente es (último valor − primer valor) / años transcurridos; la recta pasa
    exactamente por ambos puntos, incluido el año en curso. ``until`` permite, si se
    pide, terminar la recta en un año anterior.
    """
    mask = np.isfinite(years) & np.isfinite(values)
    if until is not None and (mask & (years <= until)).sum() >= 2:
        mask = mask & (years <= until)
    if mask.sum() < 2:
        return np.full(years.shape, np.nan), None
    x0, x1 = years[mask][0], years[mask][-1]
    y0, y1 = values[mask][0], values[mask][-1]
    slope = float((y1 - y0) / (x1 - x0))
    line = np.where(years >= x0, y0 + slope * (years - x0), np.nan)
    return line, slope


MIN_PANEL_COUNTRIES = 10


def _countries_in_all_years(data):
    """Filas de los países con valor en todos los años (si quedan al menos 10)."""
    presence = data.groupby("pais_norm")["anio"].nunique()
    panel = presence[presence.eq(data["anio"].nunique())].index
    return data[data["pais_norm"].isin(panel)] if len(panel) >= MIN_PANEL_COUNTRIES else data


MIN_MONTHS_PER_YEAR = 3


def world_from_timeline(timeline, years):
    """Promedio anual de la serie de tiempo mundial, o ``None`` si no cubre todos los años."""
    if timeline is None or timeline.empty:
        return None
    data = timeline.dropna(subset=["fecha", "valor_espanol"]).copy()
    data["anio"] = pd.to_datetime(data["fecha"]).dt.year
    months = data.groupby("anio")["fecha"].apply(lambda f: pd.to_datetime(f).dt.month.nunique())
    covered = set(months[months >= MIN_MONTHS_PER_YEAR].index)
    if not set(years) <= covered:
        return None
    result = data.groupby("anio")["valor_espanol"].mean().reindex(years)
    return result if result.mean() > 0 else None


def regional_series(regional, timeline=None):
    """Índice anual (escala 0-100) corregido entre años, con recta primer-último año.

    Igual que la diapositiva de Tendencias (`presentation/charts/trends.py`): cada CSV
    anual da 100 al país con más interés de ese año, así que si ese país cambia todos
    los demás se reescalan. Cada año se lleva a una misma escala con su mediana:
    valor × (mediana de referencia ÷ mediana del año), con la mediana de las medianas
    anuales como referencia. Ecuador = su valor; LATAM = promedio de sus países;
    Todo el mundo = promedio de todos los países (todos corregidos). Mediana, LATAM y
    Todo el mundo usan solo los países con dato en todos los años.

    Si hay serie de tiempo mundial (``timeline``: fecha y valor_espanol de la descarga
    comparativa) que cubra todos los años, su promedio anual da la forma real de
    "Todo el mundo", ubicada al nivel del promedio corregido de los países: los CSV
    anuales solo dicen cómo se reparte el interés entre países, no si sube o baja.
    """
    if regional is None or regional.empty:
        return pd.DataFrame(), {}
    data = regional.dropna(subset=["anio"]).copy()
    data["valor_espanol"] = pd.to_numeric(data["valor_espanol"], errors="coerce")
    data = data.dropna(subset=["valor_espanol"])
    data["anio"] = data["anio"].astype(int)
    data["pais_norm"] = data["pais"].map(lambda p: normalize(p).lower())
    years = sorted(data["anio"].unique())
    panel = _countries_in_all_years(data)
    median = panel.groupby("anio")["valor_espanol"].median().reindex(years).replace(0, np.nan)
    factor = float(median.median()) / median
    series = pd.DataFrame({
        "Ecuador": data[data["pais_norm"].eq("ecuador")].groupby("anio")["valor_espanol"].mean().reindex(years) * factor,
        "LATAM": panel[panel["pais_norm"].isin(LATAM)].groupby("anio")["valor_espanol"].mean().reindex(years) * factor,
        "Todo el mundo": panel.groupby("anio")["valor_espanol"].mean().reindex(years) * factor,
    }, index=years)
    world = world_from_timeline(timeline, years)
    if world is not None:
        series["Todo el mundo"] = world * (series["Todo el mundo"].mean() / world.mean())
    trends = {}
    x = np.asarray(years, dtype=float)
    for name in series.columns:
        line, slope = _slope(x, series[name].to_numpy(dtype=float))
        trends[name] = {"line": line, "slope": slope}
    return series, trends


def country_table(regional):
    """Índice por país: promedio del período, último año y idioma con más interés."""
    if regional is None or regional.empty:
        return pd.DataFrame(columns=["País", "ISO3", "Promedio español", "Promedio inglés", "Último año", "Valor último año", "Idioma"])
    data = regional.dropna(subset=["anio"]).copy()
    for column in ("valor_espanol", "valor_ingles"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    last = int(data["anio"].max())
    grouped = data.groupby("pais").agg(esp=("valor_espanol", "mean"), ing=("valor_ingles", "mean"))
    latest = data[data["anio"].eq(last)].groupby("pais")["valor_espanol"].mean()
    table = grouped.assign(ultimo=latest.reindex(grouped.index)).reset_index()

    def language(row):
        if pd.isna(row["ing"]):
            return "Español (sin dato en inglés)"
        return "Español" if (row["esp"] or 0) >= row["ing"] else "Inglés"

    return pd.DataFrame({
        "País": table["pais"],
        "ISO3": table["pais"].map(country_code),
        "Promedio español": table["esp"].round(1),
        "Promedio inglés": table["ing"].round(1),
        "Último año": last,
        "Valor último año": table["ultimo"].round(1),
        "Idioma": table.apply(language, axis=1),
    }).sort_values("Promedio español", ascending=False, na_position="last").reset_index(drop=True)



def comparison_table(comparison):
    """Desglose comparativo por región: porcentaje de cada palabra por país y cuál predomina.

    Igual que Google Trends, cada país se asigna a la palabra con mayor porcentaje;
    con 50 % y 50 % queda como empate.
    """
    columns = ["País", "ISO3", "% español", "% inglés", "Predomina"]
    if comparison is None or comparison.empty:
        return pd.DataFrame(columns=columns)
    data = comparison.dropna(subset=["valor_espanol", "valor_ingles"], how="all")
    spanish, english = data["valor_espanol"].fillna(0), data["valor_ingles"].fillna(0)
    return pd.DataFrame({
        "País": data["pais"].to_numpy(),
        "ISO3": data["pais"].map(country_code).to_numpy(),
        "% español": data["valor_espanol"].round(1).to_numpy(),
        "% inglés": data["valor_ingles"].round(1).to_numpy(),
        "Predomina": np.select([spanish > english, english > spanish], ["Español", "Inglés"], "Empate"),
    }, columns=columns).sort_values(["% español", "País"], ascending=[False, True]).reset_index(drop=True)

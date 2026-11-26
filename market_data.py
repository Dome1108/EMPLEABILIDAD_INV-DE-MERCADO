"""Cálculos de mercado académico: matriculados, titulados y precios.

No depende de Streamlit ni de SQL Server; las consultas viven en data_access.py.
Reproduce la lógica del notebook MATRICULAS_TITULOS_Y_PRECIOS_MASTER_BDD_IDM_v2.
"""
import re
import unicodedata

import numpy as np
import pandas as pd

from analytics import institution_key

YEARS = list(range(2020, 2025))
PROJECTION_YEAR = 2025
PROJECTION_METHODS = {"LINEAL": "Proyección lineal", "CRECIMIENTO": "Tasa de crecimiento"}
FINANCING = ["PUBLICO", "PRIVADO"]
UNCLASSIFIED = "NO CLASIFICADO"
NO_PRICE = "SIN INFORMACIÓN DE PRECIO"
PRICE_COLUMNS = ["SIGLA", "SEMESTRE_POS", "FINANCIAMIENTO", "OFERTAS", "ARANCEL_MINIMO",
                 "ARANCEL_PROMEDIO", "ARANCEL_MAXIMO", "ESTADO_PRECIO"]

# Graduados conserva nombres anteriores de algunas IES; Matriculados usa los actuales.
INSTITUTION_ALIASES = {
    "UNIVERSIDAD TECNOLOGICA EQUINOCCIAL": "UNIVERSIDAD UTE",
    "ESCUELA POLITECNICA DEL EJERCITO": "UNIVERSIDAD DE LAS FUERZAS ARMADAS ESPE",
}


def normalize_text(value):
    if value is None or pd.isna(value):
        return pd.NA
    text = str(value).strip().upper()
    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    return " ".join(text.split())


def parse_currency(value):
    if value is None or pd.isna(value):
        return float("nan")
    if isinstance(value, (int, float)):
        return float(value)

    text = re.sub(r"[^0-9,.-]", "", str(value).strip().replace("$", ""))
    if not text:
        return float("nan")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return float("nan")


def career_sources(catalog, level):
    """Carrera normalizada → {fuente: [textos originales]} para el nivel elegido.

    Cada fuente se filtra con sus propios textos, así una carrera escrita con
    tildes o espacios distintos se aplica igual a matriculados, titulados y precios.
    """
    data = catalog[catalog["NIVEL"].eq(level)].dropna(subset=["CARRERA"]).copy()
    data["CLAVE"] = data["CARRERA"].map(normalize_text)
    result = {}
    for (key, source), rows in data.groupby(["CLAVE", "FUENTE"]):
        result.setdefault(key, {})[source] = sorted(rows["CARRERA"].unique())
    return result


# Una misma carrera escrita distinto en cada tabla: (nombre que se muestra, nombres equivalentes).
# Ej.: Graduados_nueva dice SOFTWARE, Matriculados INGENIERIA DE SOFTWARE y Precios INGENIERIA EN SOFTWARE.
CAREER_EQUIVALENTS = (
    ("INGENIERIA EN SOFTWARE", ("SOFTWARE", "INGENIERIA DE SOFTWARE", "INGENIERIA EN SOFTWARE")),
)


def career_with_equivalents(sources, career):
    """Nombre a mostrar y textos originales por fuente, sumando los nombres equivalentes."""
    name, keys = next(((n, k) for n, k in CAREER_EQUIVALENTS if career in k), (career, (career,)))
    found = {}
    for key in keys:
        for source, texts in sources.get(key, {}).items():
            found[source] = sorted({*found.get(source, []), *texts})
    return name, found


def institution_match_key(value):
    key = institution_key(value).replace("INSTITUTO TECNOLOGICO SUPERIOR", "INSTITUTO SUPERIOR TECNOLOGICO")
    return INSTITUTION_ALIASES.get(key, key)


def financing_map(institutions):
    """IES → PUBLICO/PRIVADO. Las IES con financiamiento contradictorio quedan sin clasificar."""
    data = institutions.dropna().copy()
    data["CLAVE"] = data["NOMBRE_IES"].map(institution_match_key)
    unique = data.groupby("CLAVE")["FINANCIAMIENTO"].agg(lambda values: set(values))
    return {key: next(iter(values)) for key, values in unique.items() if len(values) == 1}


def _growth(table):
    growth = pd.DataFrame(index=table.index)
    columns = list(table.columns)
    for previous, current in zip(columns, columns[1:]):
        base = table[previous].replace(0, np.nan)
        growth[f"CREC_{current}"] = (table[current] / base - 1) * 100
    return growth


def project(table, method="LINEAL"):
    """Añade 2025 a cada fila (sin valores negativos).

    LINEAL: tendencia lineal 2020-2024. CRECIMIENTO: 2024 × (2024 / 2023); si 2023 es 0
    la tasa no está definida y se mantiene el valor de 2024.
    """
    for row in table.index:
        if method == "CRECIMIENTO":
            previous, last = table.loc[row, 2023], table.loc[row, 2024]
            value = last * last / previous if previous else last
        else:
            slope, intercept = np.polyfit(YEARS, table.loc[row, YEARS].to_numpy(dtype=float), 1)
            value = slope * PROJECTION_YEAR + intercept
        table.loc[row, PROJECTION_YEAR] = max(0.0, value)
    return table


def enrollment_table(raw, financing=None, method="LINEAL"):
    """Matriculados por financiamiento y año: suma de TOTAL_MATRICULADOS y proyección 2025."""
    data = raw.copy()
    data["ANIO"] = pd.to_numeric(data["ANIO"], errors="coerce")
    data["TOTAL_MATRICULADOS"] = pd.to_numeric(data["TOTAL_MATRICULADOS"], errors="coerce").fillna(0)
    rows = [financing] if financing in FINANCING else FINANCING
    table = (
        data[data["FINANCIAMIENTO"].isin(rows)]
        .groupby(["FINANCIAMIENTO", "ANIO"])["TOTAL_MATRICULADOS"].sum()
        .unstack(fill_value=0)
        .reindex(index=rows, columns=YEARS, fill_value=0)
        .astype(float)
    )
    table = project(table, method)
    table.loc["TOTAL"] = table.sum(axis=0)
    return table, _growth(table)


def graduates_table(raw, institutions, financing=None, method="LINEAL"):
    """Titulados (registros) por financiamiento de la IES y año, con proyección 2025.

    Graduados_nueva no informa financiamiento: se toma de Matriculados por nombre de IES
    normalizado. Las IES sin correspondencia se reportan como NO CLASIFICADO.
    """
    data = raw.copy()
    data["ANIO"] = pd.to_numeric(data["ANIO"], errors="coerce")
    data["TITULADOS"] = pd.to_numeric(data["TITULADOS"], errors="coerce").fillna(0)
    mapping = financing_map(institutions)
    data["FINANCIAMIENTO"] = data["INSTITUCION"].map(institution_match_key).map(mapping).fillna(UNCLASSIFIED)
    rows = [financing] if financing in FINANCING else [*FINANCING, UNCLASSIFIED]
    table = (
        data[data["FINANCIAMIENTO"].isin(rows)]
        .groupby(["FINANCIAMIENTO", "ANIO"])["TITULADOS"].sum()
        .unstack(fill_value=0)
        .reindex(index=rows, columns=YEARS, fill_value=0)
        .astype(float)
    )
    table = project(table, method)
    table.loc["TOTAL"] = table.sum(axis=0)
    return table, _growth(table)


def price_semesters(prices):
    return sorted(pd.to_numeric(prices["SEMESTRE_POS"], errors="coerce").dropna().astype(int).unique(), reverse=True)


def aggregate_prices(prices, careers=None, level=None, semester=None, financing=None):
    """Una fila por institución (SIGLA) con arancel mínimo, promedio y máximo.

    Usa el semestre indicado o, si no se indica, el último con algún arancel válido.
    Los aranceles nulos o <= 0 no entran en las estadísticas; las instituciones que
    solo tienen esos valores se conservan como SIN INFORMACIÓN DE PRECIO.
    """
    data = prices.copy()
    required = {
        "SEMESTRE_POS",
        "SIGLA",
        "CARRERA_HOMOLOGADA_FINAL",
        "HOMOLOGADOS_NIVEL_ACADEMICO",
        "ARANCEL",
    }
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Faltan columnas de precios: {sorted(missing)}")

    for column in ("SIGLA", "CARRERA_HOMOLOGADA_FINAL", "HOMOLOGADOS_NIVEL_ACADEMICO"):
        data[column] = data[column].astype("string").map(normalize_text)
    if "HOMOLOGADOS_FINANCIAMIENTO" in data:
        data["FINANCIAMIENTO"] = data["HOMOLOGADOS_FINANCIAMIENTO"].astype("string").map(normalize_text)
    else:
        data["FINANCIAMIENTO"] = pd.NA
    data["SEMESTRE_POS"] = pd.to_numeric(data["SEMESTRE_POS"], errors="coerce")
    data["ARANCEL"] = data["ARANCEL"].map(parse_currency)
    data["ARANCEL_VALIDO"] = data["ARANCEL"].where(data["ARANCEL"] > 0)

    if careers:
        wanted = {normalize_text(career) for career in careers if career}
        data = data[data["CARRERA_HOMOLOGADA_FINAL"].isin(wanted)]
    if level and normalize_text(level) not in ("TODOS LOS NIVELES", "TODOS"):
        data = data[data["HOMOLOGADOS_NIVEL_ACADEMICO"].eq(normalize_text(level))]
    if financing in FINANCING:
        data = data[data["FINANCIAMIENTO"].eq(financing)]
    data = data.dropna(subset=["SIGLA"])

    if semester is None:
        valid = data.dropna(subset=["ARANCEL_VALIDO"])["SEMESTRE_POS"].dropna()
        available = valid if not valid.empty else data["SEMESTRE_POS"].dropna()
        semester = int(available.max()) if not available.empty else None
    else:
        semester = int(semester)
    if semester is None:
        return pd.DataFrame(columns=PRICE_COLUMNS)

    data = data[data["SEMESTRE_POS"].eq(semester)]
    if data.empty:
        return pd.DataFrame(columns=PRICE_COLUMNS)

    result = (
        data.groupby("SIGLA", as_index=False)
        .agg(
            FINANCIAMIENTO=("FINANCIAMIENTO", lambda values: values.dropna().mode().iat[0] if values.notna().any() else pd.NA),
            OFERTAS=("SIGLA", "size"),
            ARANCEL_MINIMO=("ARANCEL_VALIDO", "min"),
            ARANCEL_PROMEDIO=("ARANCEL_VALIDO", "mean"),
            ARANCEL_MAXIMO=("ARANCEL_VALIDO", "max"),
        )
        .sort_values(["ARANCEL_PROMEDIO", "SIGLA"], na_position="last")
        .reset_index(drop=True)
    )
    result.insert(1, "SEMESTRE_POS", semester)
    result["ESTADO_PRECIO"] = np.where(result["ARANCEL_PROMEDIO"].notna(), "CON PRECIO", NO_PRICE)
    return result[PRICE_COLUMNS]


def _udla_label(value):
    """CARRERA_UDLA o FACULTAD utilizable; NULL, vacío y SIN REGISTRO no lo son."""
    text = normalize_text(value)
    return None if pd.isna(text) or text in ("", "SIN REGISTRO") else text


def _udla_rows(prices):
    data = prices.copy()
    for column in ("CARRERA_UDLA", "FACULTAD"):
        data[column] = data[column].map(_udla_label) if column in data else None
    data["CARRERA"] = data["CARRERA_HOMOLOGADA_FINAL"].map(normalize_text)
    data["SEMESTRE_POS"] = pd.to_numeric(data["SEMESTRE_POS"], errors="coerce")
    data["ARANCEL"] = data["ARANCEL"].map(parse_currency)
    return data


def _representative(rows):
    """Un arancel por carrera UDLA (promedio de sus filas válidas): cada carrera pesa una vez."""
    rows = rows.assign(REFERENCIA=rows["CARRERA_UDLA"].fillna(rows["CARRERA"]))
    return (rows.groupby("REFERENCIA", as_index=False)
            .agg(ARANCEL_REPRESENTATIVO=("ARANCEL", "mean"), REGISTROS=("ARANCEL", "size"))
            .sort_values("REFERENCIA").reset_index(drop=True))


def obtener_arancel_udla(career_prices, udla_prices, table, level, semester, own="UDLA"):
    """Arancel UDLA de la carrera, real o estimado por facultad, con su trazabilidad.

    1. Real: la oferta UDLA de la carrera en el semestre (lo que ya mostraba el tablero) o,
       si no existe, la carrera UDLA indicada en CARRERA_UDLA con arancel en ese semestre.
    2. Estimado: promedio de los aranceles representativos de las carreras UDLA de la misma
       FACULTAD y nivel, en el semestre; si no hay ninguna, el semestre anterior más
       reciente (marcado como histórico). Solo usa ofertas UDLA, nunca competidores.
    3. Sin información: sin facultad identificable o sin aranceles UDLA válidos.
    """
    semester = int(semester)
    level = normalize_text(level)
    base = dict(nivel=level, periodo=semester)
    own_row = table[table["SIGLA"].eq(own) & table["ARANCEL_PROMEDIO"].notna()]
    career = _udla_rows(career_prices) if len(career_prices) else pd.DataFrame(
        columns=["CARRERA_UDLA", "FACULTAD", "CARRERA", "SEMESTRE_POS", "ARANCEL"])
    mapped = sorted(career["CARRERA_UDLA"].dropna().unique())
    if len(own_row):
        return dict(base, arancel=float(own_row["ARANCEL_PROMEDIO"].iat[0]), tipo="real",
                    carrera_udla=", ".join(mapped) or None, fuente="Oferta UDLA de la carrera")

    udla = _udla_rows(udla_prices) if len(udla_prices) else _udla_rows(pd.DataFrame(
        columns=["SEMESTRE_POS", "CARRERA_UDLA", "CARRERA_HOMOLOGADA_FINAL", "FACULTAD", "ARANCEL"]))
    if "HOMOLOGADOS_NIVEL_ACADEMICO" in udla:
        udla = udla[udla["HOMOLOGADOS_NIVEL_ACADEMICO"].map(normalize_text).eq(level)]
    valid = udla[udla["ARANCEL"] > 0]

    real = valid[valid["CARRERA_UDLA"].isin(mapped) & valid["SEMESTRE_POS"].eq(semester)]
    if len(real):
        detail = _representative(real)
        return dict(base, arancel=float(detail["ARANCEL_REPRESENTATIVO"].mean()), tipo="real",
                    carrera_udla=", ".join(detail["REFERENCIA"]), fuente="Carrera UDLA indicada en CARRERA_UDLA",
                    detalle=detail)

    # Facultad de la carrera; si sus filas no la traen, la de su carrera UDLA (CARRERA_UDLA).
    faculties = career["FACULTAD"].dropna()
    if faculties.empty and mapped:
        faculties = udla.loc[udla["CARRERA_UDLA"].isin(mapped), "FACULTAD"].dropna()
    if faculties.empty:
        return dict(base, arancel=None, tipo="sin_informacion", carrera_udla=None, facultad=None,
                    motivo="La carrera no tiene una facultad identificable.")
    counts = faculties.value_counts()
    faculty = sorted(counts[counts.eq(counts.max())].index)[0]
    related = valid[valid["FACULTAD"].eq(faculty)]
    periods = related.loc[related["SEMESTRE_POS"].le(semester), "SEMESTRE_POS"]
    if periods.empty:
        return dict(base, arancel=None, tipo="sin_informacion", carrera_udla=None, facultad=faculty,
                    facultades_detectadas=sorted(counts.index),
                    motivo="No hay carreras UDLA de la misma facultad y nivel con arancel válido.")
    period = semester if periods.eq(semester).any() else int(periods.max())
    detail = _representative(related[related["SEMESTRE_POS"].eq(period)])
    return dict(base, arancel=float(detail["ARANCEL_REPRESENTATIVO"].mean()), tipo="estimado",
                carrera_udla=None, facultad=faculty, facultades_detectadas=sorted(counts.index),
                periodo=period, periodo_solicitado=semester, historico=period != semester,
                numero_carreras=len(detail), carreras_referencia=list(detail["REFERENCIA"]), detalle=detail)


def price_metrics(table, own="UDLA", own_info=None):
    """Indicadores de mercado; cada institución pesa una vez (su arancel promedio).

    own_info es el resultado de obtener_arancel_udla: real, estimado o sin información (NaN).
    """
    priced = table.dropna(subset=["ARANCEL_PROMEDIO"])
    is_own = table["SIGLA"].eq(own)
    competitors = priced[~priced["SIGLA"].eq(own)]
    if own_info is not None:
        own_price = np.nan if own_info.get("arancel") is None else float(own_info["arancel"])
    else:
        own_price = priced.loc[priced["SIGLA"].eq(own), "ARANCEL_PROMEDIO"]
        own_price = float(own_price.iat[0]) if len(own_price) else np.nan
    competitor_mean = float(competitors["ARANCEL_PROMEDIO"].mean()) if len(competitors) else np.nan
    offering = len(table)
    return dict(
        offering=offering,
        competitors=int((~is_own).sum()),
        priced=len(priced),
        without_price=offering - len(priced),
        coverage=100 * len(priced) / offering if offering else np.nan,
        market_min=float(priced["ARANCEL_MINIMO"].min()) if len(priced) else np.nan,
        market_mean=float(priced["ARANCEL_PROMEDIO"].mean()) if len(priced) else np.nan,
        market_max=float(priced["ARANCEL_MAXIMO"].max()) if len(priced) else np.nan,
        own_price=own_price,
        competitor_mean=competitor_mean,
        own_gap=own_price - competitor_mean,
        own_gap_pct=100 * (own_price / competitor_mean - 1) if competitor_mean else np.nan,
    )

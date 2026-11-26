"""Resultados de Google Trends guardados por el proyecto Tendencias (PostgreSQL, solo lectura).

No consulta Google Trends: lee lo que el proyecto Tendencias ya extrajo y guardó en
sus tablas `proyectos_tendencias`, `tendencias`, `tendencias_regional`,
`tendencias_carrera` y `carreras_facultad`, y en la vista `vw_google_trends`
(desglose comparativo por región: palabra en español frente a inglés).
La vista existe desde la migración 9 de Tendencias; si falta, ese desglose
queda vacío y el resto sigue funcionando.
"""
import os
from contextlib import closing

import pandas as pd


def database_url():
    """URL de PostgreSQL de Tendencias: secrets [tendencias] o TENDENCIAS_DATABASE_URL.

    TENDENCIAS_DESACTIVADO=1 la anula (lo usan las pruebas para no tocar la base real).
    """
    if os.environ.get("TENDENCIAS_DESACTIVADO") == "1":
        return None
    url = None
    try:
        import streamlit as st
        url = dict(st.secrets.get("tendencias", {})).get("database_url")
    except Exception:
        url = None
    return (url or os.environ.get("TENDENCIAS_DATABASE_URL") or "").strip() or None


def _connect(url):
    import psycopg2

    connection = psycopg2.connect(url, connect_timeout=10)
    connection.set_session(readonly=True)  # nunca escribe en la base de Tendencias
    return connection


def _frame(cursor):
    return pd.DataFrame(cursor.fetchall(), columns=[column[0] for column in cursor.description])


def load_trend_projects(url):
    """Un registro por proyecto, con cuántas palabras y filas regionales tiene."""
    with closing(_connect(url)) as connection, connection.cursor() as cursor:
        cursor.execute("""
            SELECT p.id, p.tipo_carpeta, p.carrera_referencia, p.carrera_estudio,
                   p.created_at::date AS creado,
                   (SELECT COUNT(*) FROM tendencias t WHERE t.proyecto_id = p.id) AS palabras,
                   (SELECT COUNT(*) FROM tendencias_regional r WHERE r.proyecto_id = p.id) AS filas_regionales
            FROM proyectos_tendencias p
            ORDER BY p.id""")
        return _frame(cursor)


def load_trend_project(url, project_id):
    """Palabras clave, serie regional y palabras base de todas las carreras de referencia."""
    with closing(_connect(url)) as connection, connection.cursor() as cursor:
        cursor.execute("""SELECT palabra, palabra_ingles, promedio FROM tendencias
                          WHERE proyecto_id = %s ORDER BY id""", (int(project_id),))
        keywords = _frame(cursor)
        cursor.execute("""SELECT palabra_espanol, palabra_ingles, anio, pais, valor_espanol, valor_ingles
                          FROM tendencias_regional WHERE proyecto_id = %s
                          ORDER BY anio, pais""", (int(project_id),))
        regional = _frame(cursor)
        cursor.execute("""SELECT c.carrera, c.nivel, b.palabra, b.cantidad
                          FROM tendencias_carrera b JOIN carreras_facultad c ON c.id = b.id_carrera
                          ORDER BY c.id, b.palabra""")
        base = _frame(cursor)
        comparison, timeline = _load_comparison(cursor, int(project_id))
    for frame, columns in ((keywords, ["promedio"]), (regional, ["anio", "valor_espanol", "valor_ingles"]),
                           (base, ["cantidad"]), (comparison, ["valor_espanol", "valor_ingles"]),
                           (timeline, ["valor_espanol"])):
        for column in columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    timeline["fecha"] = pd.to_datetime(timeline["fecha"], errors="coerce")
    return {"keywords": keywords, "regional": regional, "base": base, "comparison": comparison,
            "timeline": timeline}


COMPARISON_COLUMNS = ["palabra_espanol", "palabra_ingles", "periodo", "pais", "valor_espanol",
                      "valor_ingles", "extraido_en"]


TIMELINE_COLUMNS = ["fecha", "valor_espanol"]


def _load_comparison(cursor, project_id):
    """Desglose por región y serie de tiempo mundial (vw_google_trends).

    La serie de tiempo (palabra en español, todo el mundo) da la forma real de la
    línea "Todo el mundo" del gráfico regional. Ambas quedan vacías si la vista no existe.
    """
    cursor.execute("SELECT to_regclass('public.vw_google_trends') IS NOT NULL")
    if not cursor.fetchone()[0]:
        return pd.DataFrame(columns=COMPARISON_COLUMNS), pd.DataFrame(columns=TIMELINE_COLUMNS)
    cursor.execute(f"""SELECT {", ".join(COMPARISON_COLUMNS)} FROM vw_google_trends
                       WHERE proyecto_id = %s AND tipo = %s ORDER BY pais""", (project_id, "comparacion_pais"))
    comparison = _frame(cursor)
    cursor.execute(f"""SELECT {", ".join(TIMELINE_COLUMNS)} FROM vw_google_trends
                       WHERE proyecto_id = %s AND tipo = %s ORDER BY fecha""", (project_id, "interes_en_el_tiempo"))
    return comparison, _frame(cursor)

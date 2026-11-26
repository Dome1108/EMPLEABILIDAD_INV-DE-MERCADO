"""Lecturas parametrizadas. No modifica las bases de origen."""
from contextlib import closing

import pandas as pd
import pyodbc

from analytics import SNAPSHOTS, institution_key

EMPLOYER_SCHEMA_VERSION = 3

ACADEMIC_LEVELS = ("Tecnológico", "Tercer nivel", "Cuarto nivel, especialidades y doctorados")


def academic_level(value):
    text = institution_key(value)
    if any(word in text for word in ("CUARTO", "MAESTR", "MAGISTER", "ESPECIAL", "DOCTOR", "PHD", "POSGRADO", "POSTGRADO")):
        return ACADEMIC_LEVELS[2]
    if any(word in text for word in ("TECNOLOG", "TECNIC", "SUPERIOR NO UNIVERSITARIO")):
        return ACADEMIC_LEVELS[0]
    if any(word in text for word in ("TERCER", "PREGRADO", "GRADO", "LICENCI", "INGENIER")):
        return ACADEMIC_LEVELS[1]
    return None


def level_column(cursor):
    cursor.execute("SELECT COLUMN_NAME FROM BDD_IDM.INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'senescyt' AND TABLE_NAME = 'Graduados_nueva'")
    columns = {institution_key(row[0]): row[0] for row in cursor.fetchall()}
    for candidate in ("NIVEL FORMACION", "NIVEL DE FORMACION", "NIVEL ACADEMICO", "NIVEL DE TITULO", "NIVEL TITULO", "NIVEL"):
        if candidate in columns:
            return "[" + columns[candidate].replace("]", "]]") + "]"
    raise RuntimeError("No se encontró la columna de nivel académico en Graduados_nueva. Revisa el nombre del campo de nivel en la fuente.")


def career_catalog(config):
    with closing(connect(config)) as connection:
        cursor = connection.cursor()
        column = level_column(cursor)
        cursor.execute(f"""SELECT DISTINCT LTRIM(RTRIM(CARRERA_HOMOLOGADA)) AS carrera,
            LTRIM(RTRIM(CONVERT(nvarchar(1000), {column}))) AS nivel_origen
            FROM [BDD_IDM].[senescyt].[Graduados_nueva]
            WHERE NULLIF(LTRIM(RTRIM(CARRERA_HOMOLOGADA)), '') IS NOT NULL""")
        catalog = frame(cursor)
        catalog["nivel"] = catalog.nivel_origen.map(academic_level)
        return catalog


def connect(config):
    server = str(config.get('server', 'SNBI03'))
    # Configuración del servidor institucional; otros servidores validan su certificado.
    trust_certificate = config.get('trust_server_certificate', server.casefold() == 'snbi03')
    available = pyodbc.drivers()
    driver = config.get("driver") or next((d for d in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server") if d in available), None)
    if not driver:
        raise RuntimeError("Instala Microsoft ODBC Driver 17 o 18 for SQL Server.")
    def escape(value):
        return "{" + str(value).replace("}", "}}") + "}"
    parts = [f"DRIVER={escape(driver)}", f"SERVER={escape(server)}",
             f"DATABASE={escape(config.get('database', 'BDD_IDM'))}",
             f"Encrypt={'yes' if config.get('encrypt', True) else 'no'}",
             f"TrustServerCertificate={'yes' if trust_certificate else 'no'}",
             "APP=Observatorio Empleabilidad"]
    if config.get("trusted_connection", True):
        parts.append("Trusted_Connection=yes")
    else:
        parts += [f"UID={escape(config['username'])}", f"PWD={escape(config['password'])}"]
    connection = pyodbc.connect(";".join(parts), timeout=8)
    connection.timeout = 180
    return connection


def frame(cursor):
    return pd.DataFrame.from_records(cursor.fetchall(), columns=[col[0] for col in cursor.description])


def salary_sql(column):
    # Las fuentes reales mezclan punto decimal (2023/24/26) y coma decimal (2025).
    text = f"REPLACE(LTRIM(RTRIM(CONVERT(varchar(100), e.[{column}]))), ' ', '')"
    number = f"CASE WHEN CHARINDEX(',', {text}) > 0 THEN REPLACE(REPLACE({text}, '.', ''), ',', '.') ELSE {text} END"
    return f"NULLIF(TRY_CONVERT(float, {number}), 0)"


def careers(config):
    with closing(connect(config)) as connection:
        cursor = connection.cursor()
        cursor.execute("""SELECT DISTINCT LTRIM(RTRIM(CARRERA_HOMOLOGADA)) AS carrera
            FROM [BDD_IDM].[senescyt].[Graduados_nueva]
            WHERE NULLIF(LTRIM(RTRIM(CARRERA_HOMOLOGADA)), '') IS NOT NULL
            ORDER BY carrera""")
        return [row[0] for row in cursor.fetchall()]


def load(config, selected, progress=None, levels=None):
    """Reinicia la lectura completa una vez si se pierde la conexión.

    Cada intento usa su propia conexión y tablas temporales. Nunca devuelve
    cortes incompletos ni reutiliza una conexión rota.
    """
    for attempt in range(2):
        try:
            return _load_once(config,selected,progress=progress,levels=levels)
        except pyodbc.Error as exc:
            state=str(exc.args[0]) if exc.args else ''
            if state not in ('08S01','08001','08003','08007') or attempt:
                raise
            if progress:
                progress('Se interrumpió la conexión con SQL Server. Reintentando la consulta con una conexión nueva…')


def _load_once(config, selected, progress=None, levels=None):
    if not selected:
        raise ValueError("Selecciona al menos una carrera.")
    progress = progress or (lambda message: None)
    progress("Preparando graduados de las carreras seleccionadas…")
    with closing(connect(config)) as connection:
        cursor = connection.cursor()
        level_filter = ""
        if levels is not None:
            column = level_column(cursor)
            cursor.execute("CREATE TABLE #levels (name nvarchar(1000) COLLATE DATABASE_DEFAULT)")
            if levels:
                cursor.executemany("INSERT INTO #levels (name) VALUES (?)", [(x,) for x in levels])
            level_filter = f" AND EXISTS (SELECT 1 FROM #levels l WHERE l.name = LTRIM(RTRIM(CONVERT(nvarchar(1000), g.{column}))) COLLATE DATABASE_DEFAULT)"
        # Tabla temporal en tempdb; las fuentes solo se consultan.
        cursor.execute("CREATE TABLE #careers (name nvarchar(1000) COLLATE DATABASE_DEFAULT)")
        cursor.executemany("INSERT INTO #careers (name) VALUES (?)", [(c,) for c in selected])
        cursor.execute(f"""SELECT CONVERT(varchar(100), g.IDENTIFICACION) AS IDENTIFICACION,
            COALESCE(TRY_CONVERT(date, g.FECHA_REGISTRO, 23), TRY_CONVERT(date, g.FECHA_REGISTRO, 103)) AS FECHA_REGISTRO,
            g.INSTITUCION_EDUCACION_SUPERIOR, LTRIM(RTRIM(g.CARRERA_HOMOLOGADA)) AS CARRERA_HOMOLOGADA
            INTO #graduates FROM [BDD_IDM].[senescyt].[Graduados_nueva] g
            WHERE EXISTS (SELECT 1 FROM #careers c
                WHERE c.name = LTRIM(RTRIM(g.CARRERA_HOMOLOGADA)) COLLATE DATABASE_DEFAULT){level_filter}""")
        cursor.execute("""SELECT DISTINCT RIGHT('0000000000' + LTRIM(RTRIM(IDENTIFICACION)), 10) AS person
            INTO #people FROM #graduates
            WHERE LEN(LTRIM(RTRIM(IDENTIFICACION))) BETWEEN 1 AND 10
              AND LTRIM(RTRIM(IDENTIFICACION)) NOT LIKE '%[^0-9]%'
            """)
        cursor.execute("CREATE UNIQUE CLUSTERED INDEX ix_person ON #people(person)")
        cursor.execute("SELECT * FROM #graduates")
        graduates = frame(cursor)
        employment = {}
        for snapshot in SNAPSHOTS:
            progress(f"Cruzando graduados con empleo · {snapshot.label}…")
            salary = ", ".join(salary_sql(column) for column in snapshot.salary_columns)
            salary = f"COALESCE({salary})" if len(snapshot.salary_columns) > 1 else salary
            # Nombres de tablas/columnas proceden exclusivamente de constantes locales.
            cursor.execute(f"""SELECT CONVERT(varchar(100), e.NUMAFI) AS NUMAFI,
                CONVERT(varchar(100), e.RUCEMP) AS RUCEMP, {salary} AS salary
                FROM [Northwind].[dbo].[{snapshot.table}] e
                WHERE LEN(LTRIM(RTRIM(CONVERT(varchar(100), e.NUMAFI)))) BETWEEN 1 AND 10
                  AND LTRIM(RTRIM(CONVERT(varchar(100), e.NUMAFI))) NOT LIKE '%[^0-9]%'
                  AND EXISTS (SELECT 1 FROM #people p WHERE p.person COLLATE DATABASE_DEFAULT =
                    RIGHT('0000000000' + LTRIM(RTRIM(CONVERT(varchar(100), e.NUMAFI))), 10) COLLATE DATABASE_DEFAULT)""")
            employment[snapshot.year] = frame(cursor)
        progress("Cruzando cédula + 001 con el catastro SRI…")
        cursor.execute("""SELECT CONVERT(varchar(100), s.NUMERO_RUC) AS NUMERO_RUC,
            s.ESTADO_CONTRIBUYENTE,
            COALESCE(TRY_CONVERT(date, s.FECHA_INICIO_ACTIVIDADES, 23), TRY_CONVERT(date, s.FECHA_INICIO_ACTIVIDADES, 103)) AS FECHA_INICIO_ACTIVIDADES,
            COALESCE(TRY_CONVERT(date, s.FECHA_SUSPENSION_DEFINITIVA, 23), TRY_CONVERT(date, s.FECHA_SUSPENSION_DEFINITIVA, 103)) AS FECHA_SUSPENSION_DEFINITIVA,
            COALESCE(TRY_CONVERT(date, s.FECHA_REINICIO_ACTIVIDADES, 23), TRY_CONVERT(date, s.FECHA_REINICIO_ACTIVIDADES, 103)) AS FECHA_REINICIO_ACTIVIDADES,
            COALESCE(TRY_CONVERT(date, s.FECHA_CARGA, 23), TRY_CONVERT(date, s.FECHA_CARGA, 103)) AS FECHA_CARGA,
            COALESCE(TRY_CONVERT(date, s.FECHA_ACTUALIZACION, 23), TRY_CONVERT(date, s.FECHA_ACTUALIZACION, 103)) AS FECHA_ACTUALIZACION
            FROM [BDD_IDM].[dbo].[SRI_CATASTRO] s
            WHERE EXISTS (SELECT 1 FROM #people p WHERE
                (p.person + '001') COLLATE DATABASE_DEFAULT =
                LTRIM(RTRIM(CONVERT(varchar(100), s.NUMERO_RUC))) COLLATE DATABASE_DEFAULT)""")
        sri = frame(cursor)
        return graduates, employment, sri


def insertar_personas(cursor,table,people):
    """Inserta hasta 500 IDs por viaje, sin fast_executemany sobre tablas temporales."""
    if table not in ('#industry_people','#geo_people'):
        raise ValueError('Tabla temporal no permitida.')
    ids=sorted(set(str(p) for p in people))
    for offset in range(0,len(ids),500):
        batch=ids[offset:offset+500]
        cursor.execute(f"INSERT INTO {table} (person) VALUES "+','.join('(?)' for _ in batch),*batch)


def load_employers(config, people):
    """Relaciones persona-empleador del último corte SIM."""
    if not people:return pd.DataFrame(columns=['person','RUCEMP','NOMEMP'])
    with closing(connect(config)) as connection:
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE #industry_people (person varchar(10) COLLATE DATABASE_DEFAULT PRIMARY KEY)")
        insertar_personas(cursor,'#industry_people',people)
        cursor.execute("""SELECT DISTINCT RIGHT('0000000000' + LTRIM(RTRIM(CONVERT(varchar(100), e.NUMAFI))), 10) AS person,
            LTRIM(RTRIM(CONVERT(varchar(100), e.RUCEMP))) AS RUCEMP,
            LTRIM(RTRIM(CONVERT(nvarchar(500), e.NOMEMP))) AS NOMEMP
            FROM [Northwind].[dbo].[SIM_Y_ENE_26] e
            WHERE LEN(LTRIM(RTRIM(CONVERT(varchar(100), e.NUMAFI)))) BETWEEN 1 AND 10
            AND LTRIM(RTRIM(CONVERT(varchar(100), e.NUMAFI))) NOT LIKE '%[^0-9]%'
            AND EXISTS (SELECT 1 FROM #industry_people p WHERE p.person =
                RIGHT('0000000000' + LTRIM(RTRIM(CONVERT(varchar(100), e.NUMAFI))), 10) COLLATE DATABASE_DEFAULT)""")
        return frame(cursor)


def load_atlas(config, people):
    """Lee únicamente cédula y domicilio de la cohorte; fuentes de solo lectura."""
    with closing(connect(config)) as connection:
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE #geo_people (person varchar(10) COLLATE DATABASE_DEFAULT PRIMARY KEY)")
        insertar_personas(cursor,'#geo_people',people)
        cursor.execute("""SELECT DISTINCT CONVERT(varchar(100), a.cedula) AS cedula,
            a.provincia, a.canton, a.parroquia
            FROM [BDD_IDM].[modelo].[03_ATLAS_Universo] a
            WHERE LEN(LTRIM(RTRIM(CONVERT(varchar(100), a.cedula)))) BETWEEN 1 AND 10
            AND LTRIM(RTRIM(CONVERT(varchar(100), a.cedula))) NOT LIKE '%[^0-9]%'
            AND EXISTS (SELECT 1 FROM #geo_people p WHERE p.person =
                RIGHT('0000000000' + LTRIM(RTRIM(CONVERT(varchar(100), a.cedula))), 10) COLLATE DATABASE_DEFAULT)""")
        return frame(cursor)


# --- Mercado académico: matriculados, titulados y precios (solo SELECT) ---

MARKET_LEVELS = ("TERCER NIVEL", "CUARTO NIVEL", "TECNOLOGIA")
MARKET_FINANCING = ("PUBLICO", "PRIVADO")
MARKET_YEARS = (2020, 2024)


def market_level_sql(column):
    """Homologa en SQL los niveles de Matriculados/Graduados a las categorías de precios.

    Matriculados usa p. ej. 'TERCER NIVEL DE GRADO' o 'TERCER NIVEL TECNOLOGICO SUPERIOR';
    Graduados usa 'Título(s) de cuarto nivel o posgrado' o códigos como 'TITULS_4T_NVL_PSGRD'.
    """
    text = f"UPPER(CONVERT(nvarchar(400), {column})) COLLATE Latin1_General_CI_AI"
    return f"""CASE
        WHEN {text} LIKE '%CUARTO%' OR {text} LIKE '%POSGRADO%' OR {text} LIKE '%PSGRD%' THEN 'CUARTO NIVEL'
        WHEN {text} LIKE '%TECNIC%' OR {text} LIKE '%TECNOLOG%' OR {text} LIKE '%[_]TEC%' THEN 'TECNOLOGIA'
        WHEN {text} LIKE '%TERCER NIVEL%' OR {text} LIKE '%3ER[_]NVL[_]GRD%' THEN 'TERCER NIVEL'
    END"""


def market_financing_sql(column):
    text = f"UPPER(CONVERT(nvarchar(200), {column})) COLLATE Latin1_General_CI_AI"
    return f"""CASE
        WHEN {text} LIKE '%PARTICULAR%' OR {text} LIKE '%PRIVAD%' THEN 'PRIVADO'
        WHEN {text} LIKE '%PUBLIC%' THEN 'PUBLICO'
    END"""


def placeholders(values):
    if not values:
        raise ValueError("Se requiere al menos un valor de filtro.")
    return ", ".join("?" for _ in values)


def market_catalog(config):
    """Carreras disponibles por fuente y nivel homologado, con su texto original."""
    with closing(connect(config)) as connection:
        cursor = connection.cursor()
        cursor.execute(f"""
            SELECT 'MATRICULADOS' AS FUENTE, LTRIM(RTRIM(CARRERA_HOMOLOGADA)) AS CARRERA,
                {market_level_sql('NIVEL_FORMACION')} AS NIVEL
            FROM [BDD_IDM].[senescyt].[Matriculados_Senescyt]
            WHERE NULLIF(LTRIM(RTRIM(CARRERA_HOMOLOGADA)), '') IS NOT NULL
            GROUP BY LTRIM(RTRIM(CARRERA_HOMOLOGADA)), {market_level_sql('NIVEL_FORMACION')}
            UNION ALL
            SELECT 'TITULADOS', LTRIM(RTRIM(CARRERA_HOMOLOGADA)), {market_level_sql('NIVEL_ACADEMICO')}
            FROM [BDD_IDM].[senescyt].[Graduados_nueva]
            WHERE NULLIF(LTRIM(RTRIM(CARRERA_HOMOLOGADA)), '') IS NOT NULL
            GROUP BY LTRIM(RTRIM(CARRERA_HOMOLOGADA)), {market_level_sql('NIVEL_ACADEMICO')}
            UNION ALL
            SELECT 'PRECIOS', LTRIM(RTRIM(CARRERA_HOMOLOGADA_FINAL)), LTRIM(RTRIM(HOMOLOGADOS_NIVEL_ACADEMICO))
            FROM [BDD_IDM].[senescyt].[Precios_Homologados]
            WHERE NULLIF(LTRIM(RTRIM(CARRERA_HOMOLOGADA_FINAL)), '') IS NOT NULL
            GROUP BY LTRIM(RTRIM(CARRERA_HOMOLOGADA_FINAL)), LTRIM(RTRIM(HOMOLOGADOS_NIVEL_ACADEMICO))""")
        return frame(cursor)


def enrollment_provinces(config):
    with closing(connect(config)) as connection:
        cursor = connection.cursor()
        cursor.execute("""SELECT DISTINCT LTRIM(RTRIM(PROVINCIA_IES)) AS PROVINCIA
            FROM [BDD_IDM].[senescyt].[Matriculados_Senescyt]
            WHERE NULLIF(LTRIM(RTRIM(PROVINCIA_IES)), '') IS NOT NULL ORDER BY PROVINCIA""")
        return [row[0] for row in cursor.fetchall()]


def load_enrollment(config, careers, level, province=None):
    """SUM(TOTAL_MATRICULADOS) por año y financiamiento; nunca cuenta filas."""
    params = [*careers, level, *MARKET_YEARS]
    province_filter = ""
    if province:
        province_filter = " AND LTRIM(RTRIM(m.PROVINCIA_IES)) = ?"
        params.append(province)
    financing = market_financing_sql("m.TIPO_FINANCIAMIENTO")
    with closing(connect(config)) as connection:
        cursor = connection.cursor()
        cursor.execute(f"""
            SELECT m.PERIODO AS ANIO, {financing} AS FINANCIAMIENTO,
                SUM(CAST(m.TOTAL_MATRICULADOS AS bigint)) AS TOTAL_MATRICULADOS
            FROM [BDD_IDM].[senescyt].[Matriculados_Senescyt] m
            WHERE LTRIM(RTRIM(m.CARRERA_HOMOLOGADA)) IN ({placeholders(careers)})
              AND {market_level_sql('m.NIVEL_FORMACION')} = ?
              AND m.PERIODO BETWEEN ? AND ?{province_filter}
            GROUP BY m.PERIODO, {financing}""", *params)
        return frame(cursor)


def institution_financing(config):
    """Relación IES → financiamiento tomada de Matriculados (Graduados no la trae)."""
    financing = market_financing_sql("TIPO_FINANCIAMIENTO")
    with closing(connect(config)) as connection:
        cursor = connection.cursor()
        cursor.execute(f"""SELECT LTRIM(RTRIM(NOMBRE_IES)) AS NOMBRE_IES, {financing} AS FINANCIAMIENTO
            FROM [BDD_IDM].[senescyt].[Matriculados_Senescyt]
            WHERE NULLIF(LTRIM(RTRIM(NOMBRE_IES)), '') IS NOT NULL
            GROUP BY LTRIM(RTRIM(NOMBRE_IES)), {financing}""")
        return frame(cursor)


def load_graduates_by_year(config, careers, level):
    """Registros de Graduados_nueva por IES y año (año desde FECHA_REGISTRO d/m/aaaa)."""
    date = "COALESCE(TRY_CONVERT(date, g.FECHA_REGISTRO, 103), TRY_CONVERT(date, g.FECHA_REGISTRO, 23))"
    with closing(connect(config)) as connection:
        cursor = connection.cursor()
        cursor.execute(f"""
            WITH g AS (
                SELECT LTRIM(RTRIM(g.INSTITUCION_EDUCACION_SUPERIOR)) AS INSTITUCION, YEAR({date}) AS ANIO
                FROM [BDD_IDM].[senescyt].[Graduados_nueva] g
                WHERE LTRIM(RTRIM(g.CARRERA_HOMOLOGADA)) IN ({placeholders(careers)})
                  AND {market_level_sql('g.NIVEL_ACADEMICO')} = ?)
            SELECT INSTITUCION, ANIO, COUNT_BIG(*) AS TITULADOS
            FROM g WHERE ANIO BETWEEN ? AND ?
            GROUP BY INSTITUCION, ANIO""", *careers, level, *MARKET_YEARS)
        return frame(cursor)


def load_prices(config, careers, level):
    """Filas de precios de la carrera y nivel ya homologados en SQL Server.

    Usa HOMOLOGADOS_FINANCIAMIENTO cuando la columna existe. Si aún no está en la
    tabla, deriva PUBLICO/PRIVADO de FINANCIAMIENTO (PUBLICA/PARTICULAR).
    """
    with closing(connect(config)) as connection:
        cursor = connection.cursor()
        cursor.execute("""SELECT 1 FROM BDD_IDM.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'senescyt' AND TABLE_NAME = 'Precios_Homologados'
              AND COLUMN_NAME = 'HOMOLOGADOS_FINANCIAMIENTO'""")
        has_financing = cursor.fetchone() is not None
        financing = ("LTRIM(RTRIM(p.HOMOLOGADOS_FINANCIAMIENTO))" if has_financing
                     else market_financing_sql("p.FINANCIAMIENTO"))
        cursor.execute(f"""
            SELECT LTRIM(RTRIM(p.SEMESTRE_POS)) AS SEMESTRE_POS, LTRIM(RTRIM(p.SIGLA)) AS SIGLA,
                LTRIM(RTRIM(p.CARRERA_HOMOLOGADA_FINAL)) AS CARRERA_HOMOLOGADA_FINAL,
                LTRIM(RTRIM(p.HOMOLOGADOS_NIVEL_ACADEMICO)) AS HOMOLOGADOS_NIVEL_ACADEMICO,
                {financing} AS HOMOLOGADOS_FINANCIAMIENTO, p.ARANCEL,
                LTRIM(RTRIM(p.CARRERA_UDLA)) AS CARRERA_UDLA, LTRIM(RTRIM(p.FACULTAD)) AS FACULTAD
            FROM [BDD_IDM].[senescyt].[Precios_Homologados] p
            WHERE LTRIM(RTRIM(p.CARRERA_HOMOLOGADA_FINAL)) IN ({placeholders(careers)})
              AND LTRIM(RTRIM(p.HOMOLOGADOS_NIVEL_ACADEMICO)) = ?""", *careers, level)
        prices = frame(cursor)
        prices.attrs["financing_source"] = "HOMOLOGADOS_FINANCIAMIENTO" if has_financing else "FINANCIAMIENTO"
        return prices


def load_udla_prices(config, level):
    """Ofertas UDLA (SIGLA = 'UDLA') de un nivel, para el arancel real o estimado por facultad.

    Se filtra en SQL por institución y nivel (unas cientos de filas). La facultad y el
    periodo se eligen después, porque la facultad puede derivarse de estas mismas filas
    y la estimación histórica necesita el periodo anterior disponible.
    """
    with closing(connect(config)) as connection:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT LTRIM(RTRIM(p.SEMESTRE_POS)) AS SEMESTRE_POS,
                LTRIM(RTRIM(p.CARRERA_UDLA)) AS CARRERA_UDLA,
                LTRIM(RTRIM(p.CARRERA_HOMOLOGADA_FINAL)) AS CARRERA_HOMOLOGADA_FINAL,
                LTRIM(RTRIM(p.FACULTAD)) AS FACULTAD,
                LTRIM(RTRIM(p.HOMOLOGADOS_NIVEL_ACADEMICO)) AS HOMOLOGADOS_NIVEL_ACADEMICO, p.ARANCEL
            FROM [BDD_IDM].[senescyt].[Precios_Homologados] p
            WHERE LTRIM(RTRIM(p.SIGLA)) = 'UDLA'
              AND LTRIM(RTRIM(p.HOMOLOGADOS_NIVEL_ACADEMICO)) = ?""", level)
        return frame(cursor)


def load_reference_prices(config):
    """Histórico completo para modelo_referencia_precios, con los nombres de columna que espera.

    Solo lectura. ARANCEL y TOTAL llegan como texto; el modelo los convierte a número.
    """
    with closing(connect(config)) as connection:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT LTRIM(RTRIM(p.NIVEL_ACADEMICO)) AS [NIVEL ACADEMICO],
                LTRIM(RTRIM(p.CARRERA_UDLA)) AS [CARRERA UDLA],
                LTRIM(RTRIM(p.SEMESTRE_POS)) AS [Semestre Pos],
                LTRIM(RTRIM(p.SIGLA)) AS SIGLA, p.ARANCEL, p.TOTAL
            FROM [BDD_IDM].[senescyt].[Precios_Homologados] p""")
        return frame(cursor)


def demo_atlas(people):
    rows = []
    zones = [('PICHINCHA', 'QUITO', 'IÑAQUITO'), ('PICHINCHA', 'QUITO', 'CALDERON'),
             ('PICHINCHA', 'RUMIÑAHUI', 'SANGOLQUI'), ('GUAYAS', 'GUAYAQUIL', 'TARQUI')]
    for i, person in enumerate(sorted(people)):
        if i % 11:
            province, canton, parish = zones[i % len(zones)]
            rows.append(dict(cedula=person, provincia=province, canton=canton, parroquia=parish))
    return pd.DataFrame(rows, columns=['cedula', 'provincia', 'canton', 'parroquia'])


def demo_data():
    """Datos sintéticos reproducibles; nunca se presentan como cifras reales."""
    import numpy as np
    rng = np.random.default_rng(42)
    names = ["Economía", "Administración de Empresas", "Finanzas", "Ingeniería de Software"]
    universities = ["Universidad de Las Américas", "Universidad Central del Ecuador", "Universidad de Guayaquil", "Universidad de Cuenca", "Escuela Politécnica Nacional", "Universidad Técnica de Ambato"]
    n = 3600
    ids = [str(i).zfill(10) for i in range(100000000, 100000000+n)]
    dates = pd.to_datetime(rng.integers(pd.Timestamp('2013-01-01').value//10**9, pd.Timestamp('2026-02-01').value//10**9, n), unit='s')
    grads = pd.DataFrame(dict(IDENTIFICACION=ids, FECHA_REGISTRO=dates,
        INSTITUCION_EDUCACION_SUPERIOR=rng.choice(universities, n), CARRERA_HOMOLOGADA=rng.choice(names, n, p=[.4,.28,.18,.14])))
    grads["NIVEL_ACADEMICO"] = rng.choice(ACADEMIC_LEVELS, n, p=[.2, .6, .2])
    # Duplicados y titulaciones múltiples para ejercitar las reglas.
    grads = pd.concat([grads, grads.iloc[:80]], ignore_index=True)
    employment = {}
    for snapshot in SNAPSHOTS:
        mask = (dates <= snapshot.date) & (rng.random(n) < (.62+(snapshot.year-2023)*.025))
        chosen = np.array(ids)[mask]
        employment[snapshot.year] = pd.DataFrame(dict(NUMAFI=chosen, RUCEMP=rng.choice(['1790000001001','1790000002001','1790000003001'],len(chosen)), salary=np.round(rng.lognormal(7.05,.45,len(chosen)),2)))
    mask = rng.random(n) < .42
    chosen = np.array(ids)[mask]
    starts = dates[mask] + pd.to_timedelta(rng.integers(10,500,len(chosen)),unit='D')
    inactive = rng.random(len(chosen)) < .16
    sri = pd.DataFrame(dict(NUMERO_RUC=[x+'001' for x in chosen], ESTADO_CONTRIBUYENTE=np.where(inactive,'SUSPENDIDO','ACTIVO'),
        FECHA_INICIO_ACTIVIDADES=starts, FECHA_SUSPENSION_DEFINITIVA=[pd.Timestamp('2024-09-01') if x else pd.NaT for x in inactive],
        FECHA_REINICIO_ACTIVIDADES=pd.NaT, FECHA_CARGA=pd.Timestamp('2026-02-01'), FECHA_ACTUALIZACION=pd.Timestamp('2026-02-01')))
    return grads, employment, sri

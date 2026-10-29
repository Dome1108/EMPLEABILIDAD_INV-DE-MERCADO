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

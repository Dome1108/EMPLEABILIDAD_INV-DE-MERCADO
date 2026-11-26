"""Cola de presentaciones .pptx del observatorio (SQLite local).

Mismo funcionamiento que ``presentation_queue`` del proyecto Tendencias, pero en un archivo
del propio proyecto (``presentaciones/trabajo/cola.sqlite3``): no escribe en la base de
Tendencias ni en SQL Server.

- La app encola un trabajo con los filtros vigentes (``encolar``). Si ya hay uno igual en cola
  o generándose, devuelve ese mismo (como ``ON CONFLICT ... DO NOTHING`` de Tendencias).
- El worker toma el trabajo con un *lease* (``tomar``): un token y un vencimiento que renueva
  con un latido (``renovar``). Solo quien tiene el token publica el archivo o el error.
- Si un worker se cae, su lease vence y otro worker vuelve a tomar el trabajo (hasta 3 intentos).
"""
import json
import os
import sqlite3
import time
import uuid
from contextlib import closing
from pathlib import Path

RUTA = Path(__file__).resolve().parent / "trabajo" / "cola.sqlite3"


def ruta_cola():
    """PRESENTACIONES_COLA permite otra ubicación (las pruebas usan una cola temporal)."""
    return Path(os.getenv("PRESENTACIONES_COLA") or RUTA)
LEASE_SEGUNDOS = 600
MAX_INTENTOS = 3
ACTIVOS = ("queued", "running")
ESQUEMA = """
CREATE TABLE IF NOT EXISTS trabajos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clave TEXT NOT NULL,
    filtros TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'queued' CHECK (estado IN ('queued', 'running', 'finished', 'error')),
    intentos INTEGER NOT NULL DEFAULT 0,
    creado REAL NOT NULL,
    iniciado REAL,
    terminado REAL,
    error TEXT,
    archivo_nombre TEXT,
    archivo BLOB,
    lease_token TEXT,
    lease_vence REAL,
    progreso TEXT
);
-- Un solo trabajo activo por combinación de filtros.
CREATE UNIQUE INDEX IF NOT EXISTS trabajos_activo_unico ON trabajos(clave) WHERE estado IN ('queued', 'running');
CREATE INDEX IF NOT EXISTS trabajos_clave ON trabajos(clave, id);
CREATE TABLE IF NOT EXISTS workers (
    nombre TEXT PRIMARY KEY,
    pid INTEGER,
    latido REAL NOT NULL
);
"""


def conectar(ruta=None):
    ruta = Path(ruta or ruta_cola())
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(str(ruta), timeout=30, isolation_level=None)  # transacciones explícitas
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA journal_mode=WAL")
    conexion.executescript(ESQUEMA)
    return conexion


def _fila(row):
    if row is None:
        return None
    datos = dict(row)
    datos["filtros"] = json.loads(datos["filtros"])
    datos["tiene_archivo"] = bool(datos.pop("archivo_presente", 0))
    return datos


COLUMNAS = ("id, clave, filtros, estado, intentos, creado, iniciado, terminado, error, archivo_nombre, "
            "progreso, archivo IS NOT NULL AS archivo_presente")


def encolar(clave, filtros, ruta=None):
    """Encola los filtros; devuelve (id, es_nuevo). No duplica un trabajo activo igual."""
    with closing(conectar(ruta)) as c:
        cursor = c.execute("INSERT OR IGNORE INTO trabajos (clave, filtros, creado) VALUES (?, ?, ?)",
                           (clave, json.dumps(filtros, ensure_ascii=False, sort_keys=True), time.time()))
        if cursor.rowcount:
            return cursor.lastrowid, True
        row = c.execute("SELECT id FROM trabajos WHERE clave = ? AND estado IN ('queued', 'running')",
                        (clave,)).fetchone()
        return (row["id"] if row else None), False


def ultimo(clave, ruta=None):
    """Último trabajo de estos filtros, sin leer el archivo."""
    with closing(conectar(ruta)) as c:
        return _fila(c.execute(f"SELECT {COLUMNAS} FROM trabajos WHERE clave = ? ORDER BY id DESC LIMIT 1",
                               (clave,)).fetchone())


def archivo(trabajo_id, ruta=None):
    """(nombre, bytes) del .pptx terminado."""
    with closing(conectar(ruta)) as c:
        row = c.execute("SELECT archivo_nombre, archivo FROM trabajos WHERE id = ? AND estado = 'finished'",
                        (int(trabajo_id),)).fetchone()
    return (row["archivo_nombre"], bytes(row["archivo"])) if row and row["archivo"] is not None else (None, b"")


def tomar(lease=LEASE_SEGUNDOS, ruta=None):
    """El worker reclama el trabajo más antiguo en cola (o uno cuyo lease venció)."""
    ahora = time.time()
    token = uuid.uuid4().hex
    with closing(conectar(ruta)) as c:
        c.execute("BEGIN IMMEDIATE")
        try:
            # Trabajos de un worker caído que ya agotaron sus intentos: se cierran con error.
            c.execute("""UPDATE trabajos SET estado = 'error', terminado = ?, lease_token = NULL,
                         error = 'El worker se detuvo varias veces mientras generaba esta presentación.'
                         WHERE estado = 'running' AND lease_vence < ? AND intentos >= ?""",
                      (ahora, ahora, MAX_INTENTOS))
            row = c.execute("""SELECT id FROM trabajos
                               WHERE estado = 'queued' OR (estado = 'running' AND lease_vence < ?)
                               ORDER BY id LIMIT 1""", (ahora,)).fetchone()
            if row is None:
                c.execute("COMMIT")
                return None
            c.execute("""UPDATE trabajos SET estado = 'running', intentos = intentos + 1, iniciado = ?,
                         lease_token = ?, lease_vence = ?, error = NULL WHERE id = ?""",
                      (ahora, token, ahora + lease, row["id"]))
            trabajo = _fila(c.execute(f"SELECT {COLUMNAS} FROM trabajos WHERE id = ?", (row["id"],)).fetchone())
            c.execute("COMMIT")
        except Exception:
            c.execute("ROLLBACK")
            raise
    trabajo["lease_token"] = token
    return trabajo


def renovar(trabajo_id, token, lease=LEASE_SEGUNDOS, progreso=None, ruta=None):
    """Latido del worker: extiende el lease solo si el trabajo sigue siendo suyo."""
    with closing(conectar(ruta)) as c:
        cursor = c.execute("""UPDATE trabajos SET lease_vence = ?, progreso = COALESCE(?, progreso)
                              WHERE id = ? AND estado = 'running' AND lease_token = ?""",
                           (time.time() + lease, progreso, int(trabajo_id), token))
        return cursor.rowcount == 1


def publicar(trabajo_id, token, nombre, datos, ruta=None):
    """Guarda el .pptx y marca el trabajo como terminado (solo con el token vigente)."""
    with closing(conectar(ruta)) as c:
        cursor = c.execute("""UPDATE trabajos SET estado = 'finished', terminado = ?, archivo_nombre = ?,
                              archivo = ?, lease_token = NULL, progreso = NULL
                              WHERE id = ? AND estado = 'running' AND lease_token = ?""",
                           (time.time(), nombre, sqlite3.Binary(datos), int(trabajo_id), token))
        return cursor.rowcount == 1


def fallar(trabajo_id, token, mensaje, ruta=None):
    with closing(conectar(ruta)) as c:
        cursor = c.execute("""UPDATE trabajos SET estado = 'error', terminado = ?, error = ?, lease_token = NULL,
                              progreso = NULL WHERE id = ? AND estado = 'running' AND lease_token = ?""",
                           (time.time(), str(mensaje)[:4000], int(trabajo_id), token))
        return cursor.rowcount == 1


def latido_worker(nombre, ruta=None):
    with closing(conectar(ruta)) as c:
        c.execute("INSERT INTO workers (nombre, pid, latido) VALUES (?, ?, ?) "
                  "ON CONFLICT(nombre) DO UPDATE SET pid = excluded.pid, latido = excluded.latido",
                  (nombre, os.getpid(), time.time()))


def worker_activo(maximo_segundos=60, ruta=None):
    """True si algún worker dio señales de vida en el último minuto."""
    with closing(conectar(ruta)) as c:
        row = c.execute("SELECT MAX(latido) AS latido FROM workers").fetchone()
    return bool(row and row["latido"] and time.time() - row["latido"] <= maximo_segundos)

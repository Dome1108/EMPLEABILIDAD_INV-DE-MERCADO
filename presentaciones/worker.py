"""Worker de presentaciones .pptx del observatorio.

Copia de ``workers/presentation_worker.py`` del proyecto Tendencias (lease con latido, archivo
temporal, publicación solo con el token vigente y bucle de espera), adaptada a este proyecto:
- Lee la cola local ``presentaciones/cola.py`` en lugar de ``presentation_queue`` de Tendencias.
- Cada trabajo trae los filtros de la app (no un proyecto de Tendencias): carreras, nivel,
  corte, financiamiento, provincia, proyección, semestre, CIIU, mes acumulado, zona y proyecto
  de Google Trends.
- Genera con ``presentaciones.datos`` + ``presentaciones.generador``.

Iniciar: ``python run_worker_presentaciones.py`` (o iniciar_worker_presentaciones.bat).
"""
import os
import socket
import sys
import tempfile
import threading
import time
import traceback

# Consolas con codepage clásica (cp1252): evita UnicodeEncodeError en los print.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from presentaciones import cola

NOMBRE = f"{socket.gethostname()}:{os.getpid()}"
ESPERA_SIN_TRABAJOS = 5


class OwnershipLostError(RuntimeError):
    """El worker ya no puede publicar resultados de su trabajo."""


class LeaseHeartbeat:
    """Renueva el lease del trabajo en segundo plano (igual que en Tendencias)."""

    def __init__(self, job_id, lease_token, renew_fn, interval_seconds=60):
        self.job_id = job_id
        self.lease_token = lease_token
        self.renew_fn = renew_fn
        self.interval_seconds = max(0.1, float(interval_seconds))
        self.stop_event = threading.Event()
        self.loss_event = threading.Event()
        self.thread = None
        self.progreso = None

    @property
    def ownership_lost(self):
        return self.loss_event.is_set()

    def tick(self):
        if self.stop_event.is_set() or self.ownership_lost:
            return False
        try:
            renewed = self.renew_fn(self.job_id, self.lease_token, progreso=self.progreso)
        except Exception:
            self.loss_event.set()
            return False
        if not renewed:
            self.loss_event.set()
            return False
        return True

    def _run(self):
        while not self.stop_event.wait(self.interval_seconds):
            latido()
            if not self.tick():
                return

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self._run, name=f"pptx-lease-{self.job_id}", daemon=True)
            self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread is not None and self.thread is not threading.current_thread():
            self.thread.join(timeout=max(1.0, self.interval_seconds))


def latido():
    try:
        cola.latido_worker(NOMBRE)
    except Exception as error:  # un latido perdido no detiene el trabajo
        print(f"No se pudo registrar el latido del worker: {error}")


def _ensure_ownership(heartbeat):
    if heartbeat.ownership_lost:
        raise OwnershipLostError("Se perdió el trabajo: el latido no pudo renovar el lease")


def procesar(trabajo, generar=None):
    """Genera un trabajo ya reclamado y publica el resultado solo con su token."""
    from presentaciones import datos as D
    from presentaciones import generador as G

    trabajo_id, token, filtros = trabajo["id"], trabajo["lease_token"], trabajo["filtros"]
    heartbeat = LeaseHeartbeat(trabajo_id, token, cola.renovar, interval_seconds=cola.LEASE_SEGUNDOS / 6)
    heartbeat.start()

    def avisar(mensaje):
        print(mensaje, flush=True)
        heartbeat.progreso = mensaje.split("] ", 1)[-1][:200]

    carpeta = tempfile.mkdtemp(prefix="pptx_trabajo_")
    temporal = os.path.join(carpeta, G.nombre_archivo(filtros))
    try:
        if generar is None:
            datos = D.recopilar(filtros, avisar=avisar)
            _ensure_ownership(heartbeat)
            salida = G.generar(datos, temporal, avisar=avisar)
        else:
            salida = generar(filtros, temporal)
        _ensure_ownership(heartbeat)
        if not salida or not os.path.exists(temporal):
            raise FileNotFoundError(f"El generador no creó el archivo temporal: {temporal}")
        with open(temporal, "rb") as archivo:
            contenido = archivo.read()
        if not cola.publicar(trabajo_id, token, os.path.basename(temporal), contenido):
            raise OwnershipLostError("El trabajo perdió el lease antes de guardar el archivo")
        print(f"PRESENTACIÓN {trabajo_id} GUARDADA ({len(contenido):,} bytes)".replace(",", "."), flush=True)
        return True
    except OwnershipLostError as error:
        print(f"No se publica la presentación {trabajo_id}: {error}", flush=True)
        return False
    except Exception as error:
        print(f"PRESENTACIÓN {trabajo_id} FALLÓ: {error}", flush=True)
        traceback.print_exc()
        if not heartbeat.ownership_lost:
            try:
                cola.fallar(trabajo_id, token, error)
            except Exception as failure:
                print(f"No se pudo registrar el fallo del trabajo {trabajo_id}: {failure}", flush=True)
        return False
    finally:
        heartbeat.stop()
        try:
            if os.path.exists(temporal):
                os.unlink(temporal)
            os.rmdir(carpeta)
        except OSError as limpieza:
            print(f"No se pudo limpiar {carpeta}: {limpieza}", flush=True)


def ejecutar(una_vez=False):
    print("Worker de presentaciones .pptx iniciado")
    print(f"   Inicio: {time.strftime('%Y-%m-%d %H:%M:%S')} · cola: {cola.ruta_cola()}")
    print("   Esperando pedidos del botón «Generar .pptx» (Ctrl+C para detener)…", flush=True)
    ultimo_aviso = 0
    try:
        while True:
            latido()
            trabajo = cola.tomar()
            if trabajo is None:
                if una_vez:
                    return
                if time.time() - ultimo_aviso > 300:
                    print("No hay presentaciones en cola, esperando…", flush=True)
                    ultimo_aviso = time.time()
                time.sleep(ESPERA_SIN_TRABAJOS)
                continue
            f = trabajo["filtros"]
            print(f"\nNuevo trabajo {trabajo['id']} (intento {trabajo['intentos']}): "
                  f"{', '.join(f['carreras'])} · {f['nivel_academico']} · corte {f['corte']}", flush=True)
            procesar(trabajo)
            ultimo_aviso = 0
    except KeyboardInterrupt:
        print("\nWorker de presentaciones detenido por el usuario.")


def main():
    ejecutar(una_vez="--una-vez" in sys.argv)


if __name__ == "__main__":
    main()

"""Botones «Generar .pptx» y «Descargar .pptx» del recuadro «Área de análisis» de Empleabilidad.

Al pulsar «Generar .pptx» se guardan los filtros vigentes de la app en la cola local
(presentaciones/cola.py) y el worker del observatorio (run_worker_presentaciones.py) arma la
presentación con esos filtros. «Descargar .pptx» entrega la presentación de los filtros que
están puestos ahora; si se cambian, hay que volver a generarla.
"""
from datetime import datetime

import streamlit as st

from presentaciones import cola
from presentaciones import filtros as F

PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
POLL_SECONDS = 5


def hora(valor):
    return datetime.fromtimestamp(valor).strftime("%d/%m/%Y %H:%M") if valor else "—"


def estado_texto(trabajo):
    if trabajo is None:
        return "Aún no se ha generado con los filtros actuales"
    estado = trabajo["estado"]
    if estado == "queued":
        return f"⏳ En cola desde {hora(trabajo['creado'])} · se actualiza solo"
    if estado == "running":
        paso = f" · {trabajo['progreso']}" if trabajo.get("progreso") else ""
        return f"🟡 Generándose desde {hora(trabajo['iniciado'])}{paso}"
    if estado == "finished" and trabajo["tiene_archivo"]:
        return f"✅ Lista · {hora(trabajo['terminado'])}"
    if estado == "error":
        return "⚠️ Falló la última generación · vuelve a generarla"
    return f"Estado: {estado}"


def draw(filtros, clave):
    trabajo = cola.ultimo(clave)
    activo = trabajo is not None and trabajo["estado"] in cola.ACTIVOS
    lista = trabajo is not None and trabajo["estado"] == "finished" and trabajo["tiene_archivo"]
    generar, descargar = st.columns(2)
    with generar:
        if st.button("Generar .pptx", disabled=activo, width="stretch", type="primary", key="pptx_generar",
                     icon=":material/slideshow:",
                     help="Genera la presentación de mercado con los filtros puestos en el observatorio."
                     if not activo else "Ya hay una presentación con estos filtros en cola o generándose."):
            cola.encolar(clave, filtros)
            st.rerun()
    with descargar:
        if lista:
            st.download_button("Descargar .pptx", data=lambda: cola.archivo(trabajo["id"])[1],
                               file_name=trabajo["archivo_nombre"] or "presentacion_mercado.pptx", mime=PPTX_MIME,
                               on_click="ignore", width="stretch", icon=":material/download:", key="pptx_descargar")
        else:
            st.button("Descargar .pptx", disabled=True, width="stretch", icon=":material/download:",
                      key="pptx_descargar_inactivo", help="Se activa cuando la presentación de estos filtros está lista.")
    st.caption("Presentación de mercado — " + estado_texto(trabajo))
    if (trabajo is None or activo) and not cola.worker_activo():
        st.caption("⚠️ El worker de presentaciones no está encendido: ejecuta **iniciar_worker_presentaciones.bat** "
                   "(o `python run_worker_presentaciones.py`) en la carpeta del proyecto.")
    if trabajo is not None and trabajo["estado"] == "error" and trabajo["error"]:
        with st.expander("Detalle del error"):
            st.code(str(trabajo["error"]))
    return trabajo


@st.fragment(run_every=POLL_SECONDS)
def live(filtros, clave):
    """Consulta la cola cada pocos segundos mientras el trabajo está en cola o generándose."""
    trabajo = draw(filtros, clave)
    if trabajo is None or trabajo["estado"] not in cola.ACTIVOS:
        st.rerun()  # terminó: se dibuja la página completa y deja de consultar


def render():
    """Dibuja los botones en el lugar actual (esquina del recuadro «Área de análisis»)."""
    filtros = F.desde_estado(st.session_state)
    clave = F.clave(filtros)
    try:
        trabajo = cola.ultimo(clave)
    except Exception as exc:
        st.caption("Presentación .pptx: no fue posible abrir la cola local de presentaciones.")
        with st.expander("Detalle técnico"):
            st.code(str(exc))
        return
    if trabajo is not None and trabajo["estado"] in cola.ACTIVOS:
        live(filtros, clave)
    else:
        draw(filtros, clave)

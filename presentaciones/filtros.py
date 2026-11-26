"""Filtros del observatorio que definen una presentación .pptx.

``desde_estado`` toma la selección vigente de la app (st.session_state) en el momento de
pulsar «Generar .pptx». Se guardan en la cola como JSON, así el worker genera exactamente lo
que se veía, aunque después se cambien los filtros. La paleta de colores no se incluye: la
presentación usa siempre los colores de la plantilla.
"""
import hashlib
import json
import os

from analytics import SNAPSHOTS
from presentaciones.formato import titulo

NIVELES_MERCADO = {"TERCER NIVEL": "Tercer nivel", "CUARTO NIVEL": "Cuarto nivel", "TECNOLOGIA": "Tecnología"}
# Nivel de Empleabilidad → nivel homologado de mercado (igual que market_filters.EMPLOYMENT_LEVELS).
NIVEL_EMPLEO_A_MERCADO = {"Tecnológico": "TECNOLOGIA", "Tercer nivel": "TERCER NIVEL",
                          "Cuarto nivel, especialidades y doctorados": "CUARTO NIVEL"}
FINANCIAMIENTO = {"TODOS": "Público y privado", "PUBLICO": "Público", "PRIVADO": "Privado"}
PROYECCION = {"LINEAL": "Proyección lineal", "CRECIMIENTO": "Tasa de crecimiento"}
NACIONAL = "NACIONAL"


def _valor(estado, clave, validos, defecto):
    valor = estado.get(clave)
    return valor if valor in validos else defecto


PESOS_VIABILIDAD = [30, 22, 28, 12, 8]  # viabilidad/app.py: pesos por defecto de los 5 bloques
PESTANA_VIABILIDAD = "negocios"  # primera pestaña de referencia (Negocios Internacionales)


def viabilidad(estado):
    """Configuración de «Viabilidad de carreras» (pestaña de referencia por defecto)."""
    k = PESTANA_VIABILIDAD
    pesos = [estado.get(f"weight{i}_{k}", p) for i, p in enumerate(PESOS_VIABILIDAD)]
    pesos = [int(p) for p in pesos] if all(isinstance(p, (int, float)) for p in pesos) else PESOS_VIABILIDAD
    umbral = estado.get(f"busquedas_{k}", 75)
    return {"pesos": pesos, "umbral_busquedas": int(umbral) if isinstance(umbral, (int, float)) else 75,
            "nivel": _valor(estado, f"nivel_{k}", ("Pregrado", "Posgrado"), "Pregrado")}


def desde_estado(estado, demo=None):
    """Filtros normalizados a partir de st.session_state (o cualquier diccionario)."""
    carreras = [str(c) for c in estado.get("selected_careers", []) if c] or ["ECONOMIA"]
    nivel = estado.get("academic_level") or "Todos los niveles"
    cortes = [s.year for s in SNAPSHOTS]
    nivel_mercado = _valor(estado, "market_level", NIVELES_MERCADO,
                           NIVEL_EMPLEO_A_MERCADO.get(nivel, "TERCER NIVEL"))
    semestre = estado.get("market_semester")
    mes = estado.get("industry_month")
    ciiu = estado.get("industry_ciiu")
    proyectos = {k.removeprefix("trends_project_"): int(v) for k, v in estado.items()
                 if str(k).startswith("trends_project_") and v is not None}
    return {
        "carreras": carreras,
        "nivel_academico": nivel,
        "corte": _valor(estado, "employment_cutoff", cortes, cortes[-1]),
        "mercado_nivel": nivel_mercado,
        "financiamiento": _valor(estado, "market_financing", FINANCIAMIENTO, "TODOS"),
        "provincia": estado.get("market_province") or NACIONAL,
        "proyeccion": _valor(estado, "market_projection", PROYECCION, "LINEAL"),
        "semestre": int(semestre) if semestre is not None else None,
        "ciiu": sorted(str(c) for c in ciiu) if ciiu else None,
        "mes_acumulado": int(mes) if mes is not None else None,
        "territorio": {
            "provincia": estado.get("geo_provincia") or "PICHINCHA",
            "canton": estado.get("geo_canton") or "",
            "parroquia": estado.get("geo_parroquia") or "",
        },
        "proyectos_tendencias": proyectos,
        "viabilidad": viabilidad(estado),
        "demo": (os.getenv("DASHBOARD_DEMO", "0") == "1") if demo is None else bool(demo),
    }


def clave(filtros):
    """Huella estable de los filtros: identifica la presentación pedida."""
    texto = json.dumps(filtros, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()


def etiqueta_corte(anio):
    return next((s.label for s in SNAPSHOTS if s.year == anio), str(anio))


def descripcion(filtros):
    """Filtros en texto, para la diapositiva «Filtros aplicados» y el nombre del archivo."""
    t = filtros["territorio"]
    zona = " · ".join(titulo(x) for x in (t["provincia"], t["canton"], t["parroquia"] if t["canton"] else "") if x)
    return {
        "Carreras": ", ".join(titulo(c) for c in filtros["carreras"]),
        "Nivel académico": filtros["nivel_academico"],
        "Corte de análisis": etiqueta_corte(filtros["corte"]),
        "Nivel de mercado": NIVELES_MERCADO[filtros["mercado_nivel"]],
        "Financiamiento": FINANCIAMIENTO[filtros["financiamiento"]],
        "Provincia (matriculados)": "Nacional" if filtros["provincia"] == NACIONAL else titulo(filtros["provincia"]),
        "Proyección 2025": PROYECCION[filtros["proyeccion"]],
        "Semestre de precios": str(filtros["semestre"]) if filtros["semestre"] else "Último disponible",
        "Zona territorial": zona,
    }

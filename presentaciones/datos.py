"""Datos de la presentación con los filtros del observatorio (sin Streamlit).

Cada sección usa las mismas funciones y en el mismo orden que su pestaña, para que la
presentación coincida con lo que se ve en la app:
- Empleabilidad: views/empleabilidad.py (data_access.load + analytics.calculate).
- Industrias y ventas SRI: industry_view.py.
- Matriculados, titulados y precios: market_filters.py, views/demanda_interes.py y
  views/posicionamiento_competencia_precios.py.
- Google Trends: views/demanda_interes.py (base del proyecto Tendencias, solo lectura).

Las fuentes solo se leen. Si una sección falla se registra una nota y la diapositiva
queda en N/D; solo la empleabilidad es obligatoria.
"""
import os
import tomllib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def configuracion():
    """[sql] y [tendencias] de .streamlit/secrets.toml, como la app."""
    ruta = ROOT / ".streamlit" / "secrets.toml"
    secretos = tomllib.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    url = (secretos.get("tendencias", {}).get("database_url") or os.getenv("TENDENCIAS_DATABASE_URL") or "").strip()
    if os.getenv("TENDENCIAS_DESACTIVADO") == "1":
        url = ""
    return dict(secretos.get("sql", {})), url or None


def empleabilidad(config, f):
    """Resumen de los 4 cortes, cohortes por persona e instituciones (pestaña Empleo y salarios)."""
    from analytics import calculate
    from data_access import career_catalog, demo_data, load

    carreras = tuple(sorted(f["carreras"]))
    nivel = f["nivel_academico"]
    if f["demo"]:
        grads, jobs, sri = demo_data()
        if nivel != "Todos los niveles":
            grads = grads[grads.NIVEL_ACADEMICO.eq(nivel)]
        resultado = calculate(grads[grads.CARRERA_HOMOLOGADA.isin(carreras)], jobs, sri)
    else:
        levels = None
        if nivel != "Todos los niveles":
            catalogo = career_catalog(config)
            levels = tuple(sorted(catalogo.loc[catalogo.nivel.eq(nivel), "nivel_origen"].dropna().unique()))
        resultado = calculate(*load(config, carreras, levels=levels))
    summary, institutions, cohorts, quality = resultado
    if summary.empty or not summary["graduates"].sum():
        raise ValueError("Las carreras seleccionadas no tienen graduados para el nivel académico elegido.")
    return dict(summary=summary, institutions=institutions, cohorts=cohorts, quality=quality)


def instituciones(emp, f):
    from education_visuals import education_panels

    inst = emp["institutions"]
    inst = inst[inst.year.eq(f["corte"])].sort_values("professionals", ascending=False)
    private = pd.DataFrame(emp["quality"]["private_institutions"])
    if not private.empty:
        private = private[private.year.eq(f["corte"])].sort_values(["professionals", "code"], ascending=[False, True])
    return education_panels(inst, private)


def territorio(config, emp, f):
    """Empleo georreferenciado de la zona elegida (corte enero 2026, como la app)."""
    from analytics import SNAPSHOTS
    from data_access import demo_atlas, load_atlas
    from geography import locations, territorial_summary
    from presentaciones.formato import titulo

    cohort = emp["cohorts"][SNAPSHOTS[-1].year]
    ids = tuple(sorted(cohort.person.unique()))
    geo, _ = locations(demo_atlas(ids) if f["demo"] else load_atlas(config, ids))
    located = cohort.merge(geo, on="person", how="left", validate="one_to_one")
    t = f["territorio"]
    provincias = set(geo.provincia.dropna())
    provincia = t["provincia"] if t["provincia"] in provincias else ("PICHINCHA" if "PICHINCHA" in provincias else None)
    if provincia is None:
        return None
    canton = t["canton"] if provincia == t["provincia"] else ""
    nombre = " · ".join(titulo(x) for x in (provincia, canton, t["parroquia"] if canton else "") if x)
    return dict(nombre=nombre, resumen=territorial_summary(located, provincia, canton,
                                                           t["parroquia"] if canton else ""))


def sector(config, emp, f):
    """Empresas, macroindustrias y ventas SRI de los CIIU elegidos (Industrias y ventas SRI)."""
    from analytics import SNAPSHOTS
    from data_access import load_employers
    from company_ranking import graduate_distribution
    from industry import (growth_summary, macroindustry_summary, match_employers, monthly_sales,
                          read_sources)

    if f["demo"]:
        raise ValueError("En modo demostración no hay empleadores ni ventas SRI reales.")
    mapping, sales, _ = read_sources(DATA / "validación.txt", DATA / "consulta_sri_1.xlsx")
    cohort = emp["cohorts"][SNAPSHOTS[-1].year]
    jobs = load_employers(config, tuple(sorted(cohort.loc[cohort.dependent, "person"].unique())))
    catalogo, con_ciiu, con_empleador = match_employers(jobs, mapping)
    # Igual que «Top 10 empresas por graduados» (company_ranking_view): personas únicas por RUC y
    # participación sobre todos los graduados con empleador identificado.
    companies = graduate_distribution(jobs, mapping)[0]
    empresas = (companies.sort_values(["sim_graduates", "SIM_company"], ascending=[False, True]).head(10)
                .rename(columns={"SIM_company": "Empresa", "sim_graduates": "Graduados", "share": "Participación"})
                [["Empresa", "Graduados", "Participación"]].reset_index(drop=True))
    resultado = dict(empresas=empresas, catalogo=catalogo, con_ciiu=int(con_ciiu),
                     con_empleador=int(con_empleador), macro=None, mensual=pd.DataFrame(), codigos=[],
                     mes=None, anio=None, crecimiento=None)
    if catalogo.empty:
        return resultado
    elegidos = [c for c in (f["ciiu"] or []) if c in set(catalogo.CIIU)] or catalogo.CIIU.tolist()
    mensual = monthly_sales(sales, elegidos)
    resultado.update(codigos=elegidos, mensual=mensual)
    if mensual.empty:
        return resultado
    mes_maximo = int(mensual.groupby("Año").Mes.max().min())
    mes = f["mes_acumulado"] if f["mes_acumulado"] and 1 <= f["mes_acumulado"] <= mes_maximo else mes_maximo
    anio = int(mensual[mensual.Mes.le(mes)]["Año"].max())
    resultado.update(mes=mes, anio=anio, crecimiento=growth_summary(sales, elegidos, anio, mes),
                     macro=macroindustry_summary(jobs, mapping, sales, elegidos, anio, mes))
    return resultado


def carrera_mercado(catalogo, f):
    """Primera carrera de Empleabilidad con datos de mercado en el nivel (como market_filters.render)."""
    from market_data import career_sources, career_with_equivalents, normalize_text

    fuentes = career_sources(catalogo, f["mercado_nivel"])
    for carrera in f["carreras"]:
        nombre, encontrado = career_with_equivalents(fuentes, normalize_text(carrera))
        if encontrado:
            return nombre, encontrado
    return None, {}


def mercado(config, f):
    """Matriculados, titulados y precios de la carrera de mercado con los filtros de mercado."""
    import data_access
    from market_data import (aggregate_prices, enrollment_table, graduates_table, obtener_arancel_udla,
                             price_metrics, price_semesters)

    if f["demo"]:
        raise ValueError("En modo demostración no hay datos de matriculados, titulados ni precios.")
    nombre, fuentes = carrera_mercado(data_access.market_catalog(config), f)
    if nombre is None:
        raise ValueError("Ninguna carrera elegida aparece en matriculados, titulados ni precios para "
                         f"{f['mercado_nivel'].lower()}.")
    nivel = f["mercado_nivel"]
    financiamiento = None if f["financiamiento"] == "TODOS" else f["financiamiento"]
    provincia = None if f["provincia"] == "NACIONAL" else f["provincia"]
    resultado = dict(carrera=nombre, fuentes=fuentes, matriculados=None, titulados=None, precios=None)
    if "MATRICULADOS" in fuentes:
        raw = data_access.load_enrollment(config, fuentes["MATRICULADOS"], nivel, provincia)
        resultado["matriculados"] = enrollment_table(raw, financiamiento, f["proyeccion"])[0]
    if "TITULADOS" in fuentes:
        raw = data_access.load_graduates_by_year(config, fuentes["TITULADOS"], nivel)
        resultado["titulados"] = graduates_table(raw, data_access.institution_financing(config),
                                                 financiamiento, f["proyeccion"])[0]
    if "PRECIOS" in fuentes:
        precios = data_access.load_prices(config, fuentes["PRECIOS"], nivel)
        semestre = f["semestre"] if f["semestre"] in price_semesters(precios) else None
        tabla = aggregate_prices(precios, financing=financiamiento, semester=semestre)
        if not tabla.empty:
            usado = int(tabla["SEMESTRE_POS"].iat[0])
            propio = obtener_arancel_udla(precios, data_access.load_udla_prices(config, nivel),
                                          aggregate_prices(precios, semester=usado), nivel, usado)
            resultado["precios"] = dict(tabla=tabla, semestre=usado, propio=propio,
                                        metricas=price_metrics(tabla, own_info=propio))
    return resultado


def google_trends(url, f, carrera):
    """Proyecto de Tendencias elegido en la app (o el más afín) y sus indicadores."""
    import tendencias_data
    import trends_analysis
    from presentaciones.formato import titulo

    if not url:
        raise ValueError("Falta [tendencias] database_url en .streamlit/secrets.toml.")
    proyectos = tendencias_data.load_trend_projects(url)
    proyectos = proyectos[proyectos["palabras"].gt(0) | proyectos["filas_regionales"].gt(0)].reset_index(drop=True)
    ids = proyectos["id"].astype(int).tolist()
    # Igual que la pestaña Demanda e interés académico: el proyecto elegido en su lista; si no se
    # eligió, el más afín a la carrera (también probando las demás carreras elegidas).
    elegido = next((f["proyectos_tendencias"][k] for k in (trends_analysis.normalize(c) for c in [carrera, *f["carreras"]])
                    if f["proyectos_tendencias"].get(k) in ids), None)
    if elegido is None:
        elegido = next((p for p in (trends_analysis.best_project(proyectos, c, f["mercado_nivel"])
                                    for c in [carrera, *f["carreras"]]) if p is not None), None)
    if elegido is None:
        raise ValueError(f"ningún proyecto de Tendencias coincide con {titulo(carrera)}; elige uno en la lista "
                         "«Proyecto de Google Trends» de la pestaña Demanda e interés académico")
    proyecto = proyectos.set_index("id").loc[elegido].copy()
    proyecto["id"] = elegido
    datos = tendencias_data.load_trend_project(url, elegido)
    keywords, regional, comparison = datos["keywords"], datos["regional"], datos["comparison"]
    serie, tendencias = trends_analysis.regional_series(regional, datos.get("timeline"))
    interes = trends_analysis.search_interest(keywords, trends_analysis.reference_base(datos["base"], proyecto))
    palabras = None
    for tabla, esp, ing in ((comparison, "palabra_espanol", "palabra_ingles"),
                            (regional, "palabra_espanol", "palabra_ingles"),
                            (keywords, "palabra", "palabra_ingles")):
        if tabla is not None and not tabla.empty:
            fila = tabla[[esp, ing]].dropna(how="all").head(1)
            if len(fila):
                palabras = (str(fila.iat[0, 0] or "—"), str(fila.iat[0, 1] or "—"))
                break
    return dict(proyecto=proyecto, serie=serie, tendencias=tendencias, interes=interes,
                comparacion=trends_analysis.comparison_table(comparison), palabras=palabras or ("—", "—"))


def _modelo_viabilidad():
    """viabilidad/modelo.py (sin Streamlit), cargado por ruta para no chocar con otros «modelo»."""
    import importlib.util
    import sys

    nombre = "viabilidad_modelo_pptx"
    if nombre not in sys.modules:
        spec = importlib.util.spec_from_file_location(nombre, ROOT / "viabilidad" / "modelo.py")
        modulo = importlib.util.module_from_spec(spec)
        sys.modules[nombre] = modulo  # dataclass Config necesita su módulo registrado
        spec.loader.exec_module(modulo)
    return sys.modules[nombre]


def viabilidad_carreras(f):
    """Resultado de la pestaña «Viabilidad de carreras» (viabilidad/app.py · render_dashboard).

    Misma carrera (la primera elegida en Empleabilidad que esté entre las 12 del modelo), misma
    referencia por defecto (primera pestaña), mismos pesos, umbral y nivel.
    """

    M = _modelo_viabilidad()
    programas = M.cargar_datos()
    carrera = next((m for m in map(M.carrera_modelo, f["carreras"]) if m), None)
    if carrera is None:
        raise ValueError("ninguna carrera elegida está entre las 12 del modelo de viabilidad ("
                         + ", ".join(p["carrera"] for p in programas) + ")")
    v = f.get("viabilidad") or {}
    pesos = v.get("pesos") or [30, 22, 28, 12, 8]
    if sum(pesos) != 100:
        raise ValueError(f"los pesos de Viabilidad de carreras suman {sum(pesos)}%, no 100%")
    referencia = programas[0]
    config = M.Config(pesos, v.get("umbral_busquedas", 75), nivel=v.get("nivel", "Pregrado"))
    resultados = [M.evaluar(p, referencia, config) for p in programas]
    actual = next(r for r in resultados if r["carrera"] == carrera)
    crudo = next(p for p in programas if p["carrera"] == carrera)
    return dict(fuente="dashboard", carrera=carrera, referencia=referencia["carrera"], config=config,
                pesos=pesos, bloques=M.BLOQUES, resultados=resultados, actual=actual,
                base=next(r for r in resultados if r["carrera"] == referencia["carrera"]),
                recomendaciones=M.recomendaciones(crudo, actual, config), crudo=crudo)


def linkedin(url, trends, f, carrera):
    """LinkedIn e IA de un proyecto de Tendencias.

    Primero el mismo proyecto de Google Trends; si ese proyecto no tiene datos de LinkedIn, el
    proyecto más afín a la carrera que sí los tenga (misma regla que la pestaña de Demanda).
    """
    import trends_analysis
    from presentaciones import tendencias_linkedin
    from presentaciones.formato import titulo

    if not url:
        raise ValueError("Falta [tendencias] database_url en .streamlit/secrets.toml.")
    proyectos = tendencias_linkedin.proyectos_con_linkedin(url)
    con_linkedin = set(proyectos["id"].astype(int))
    elegido = int(trends["proyecto"]["id"]) if trends and trends.get("proyecto") is not None else None
    if elegido not in con_linkedin:
        elegido = next((p for p in (trends_analysis.best_project(proyectos, c, f["mercado_nivel"])
                                    for c in [carrera, *f["carreras"]]) if p is not None), None)
    if elegido is None:
        raise ValueError(f"ningún proyecto de Tendencias con datos de LinkedIn coincide con {titulo(carrera)}")
    return tendencias_linkedin.recopilar(url, elegido)


def recopilar(f, avisar=print):
    """Todas las secciones; ``notas`` explica las que quedaron en N/D."""
    config, url = configuracion()
    notas = []

    def seccion(nombre, funcion, *args):
        avisar(f"[DATOS] {nombre}…")
        try:
            return funcion(*args)
        except Exception as error:
            notas.append(f"{nombre}: {error}")
            avisar(f"[DATOS] {nombre} no disponible: {error}")
            return None

    avisar("[DATOS] Empleabilidad (graduados, empleo, SRI)…")
    emp = empleabilidad(config, f)  # obligatoria: sin graduados no hay presentación
    resultado = dict(filtros=f, empleabilidad=emp, notas=notas)
    resultado["instituciones"] = seccion("Instituciones educativas", instituciones, emp, f)
    resultado["territorio"] = seccion("Empleo georreferenciado", territorio, config, emp, f)
    resultado["sector"] = seccion("Empresas, sectores y ventas SRI", sector, config, emp, f)
    resultado["mercado"] = seccion("Matriculados, titulados y precios", mercado, config, f)
    carrera = (resultado["mercado"] or {}).get("carrera") or f["carreras"][0]
    resultado["trends"] = seccion("Google Trends", google_trends, url, f, carrera)
    resultado["linkedin"] = seccion("LinkedIn e IA (proyecto Tendencias)", linkedin, url, resultado["trends"], f,
                                    carrera)
    resultado["viabilidad"] = seccion("Viabilidad de carreras", viabilidad_carreras, f)
    return resultado

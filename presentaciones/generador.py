"""Presentación de mercado (.pptx) con los filtros del observatorio.

Basado en ``generar_reporte_mercado`` del proyecto Tendencias (presentation/generator.py):
misma plantilla, las mismas 27 diapositivas y los mismos gráficos. Cada sección sale de este
dashboard con sus filtros (Empleabilidad, Demanda, Precios, Industrias y Viabilidad de carreras).
Lo que el dashboard no tiene (LinkedIn y nombres evaluados con IA) se busca como en Tendencias:
en su base, para el proyecto de Tendencias de la carrera (solo lectura).
"""
import tempfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

from presentaciones import filtros as F
from presentaciones import plantilla_mercado as PM
from presentaciones import pptx_utils as U
from presentaciones.formato import (decimal, dinero, entero, lista, mayuscula_inicial, mes_anio, porcentaje,
                                    titulo, variacion)
from presentaciones.graficos import education as G_EDU
from presentaciones.graficos import empleabilidad as G_EMP
from presentaciones.graficos import empleabilidad_instituciones as G_INST
from presentaciones.graficos import empleabilidad_sectores as G_SEC
from presentaciones.graficos import sri as G_SRI
from presentaciones.graficos import linkedin as G_LI
from presentaciones.graficos import linkedin_naming as G_NAMING
from presentaciones.graficos import linkedin_requirements_slide as G_REQ
from presentaciones.graficos import map_latam as G_MAPA
from presentaciones.graficos import radar as G_RADAR
from presentaciones.graficos import trends as G_TR
from presentaciones.graficos import viabilidad as G_VIA

PLANTILLA = Path(__file__).resolve().parent / "plantillas" / "Plantilla mercado.pptx"
VARIANTES_NOMBRE = ("‘Nombre del programa propuesto’", "'Nombre del programa propuesto'", "Nombre del programa propuesto",
                    "‘Nombre programa propuesto’", "'Nombre programa propuesto'", "Nombre programa propuesto")
PROYECCION_NOTA = {"LINEAL": "2025*: proyección lineal 2020–2024 por financiamiento.",
                   "CRECIMIENTO": "2025*: valor 2024 × tasa de crecimiento 2023–2024, por financiamiento."}


def nombre_programa(carreras):
    nombres = [titulo(c) for c in carreras]
    return lista(nombres) if len(nombres) <= 3 else f"{', '.join(nombres[:3])} y {len(nombres) - 3} más"


def nombre_archivo(filtros):
    base = "_".join(c.title().replace(" ", "") for c in filtros["carreras"][:3])
    base = "".join(ch for ch in base if ch.isalnum() or ch in "_-")[:80] or "Presentacion"
    return f"{base}_{filtros['corte']}_mercado.pptx"


def validar_plantilla(prs):
    if not PM.es_plantilla_mercado(prs):
        raise ValueError(f"La plantilla debe tener {PM.TOTAL_DIAPOSITIVAS} diapositivas; tiene {len(prs.slides)}.")
    for indice, texto in PM.TEXTOS_CLAVE.items():
        if texto not in U.texto_de_slide(prs.slides[indice]):
            raise ValueError(f"La diapositiva {indice + 1} de la plantilla no contiene «{texto}».")


def _shape_con_texto(slide, inicio):
    inicio = U.normalizar(inicio)
    return next(s for s in slide.shapes if getattr(s, "has_text_frame", False)
                and U.normalizar(s.text_frame.text).startswith(inicio))


# --- Diapositivas -----------------------------------------------------------------

def portada(prs, nombre):
    slide = prs.slides[PM.PORTADA]
    shape = next(s for s in slide.shapes if getattr(s, "has_text_frame", False)
                 and "investigacion de mercados" in U.normalizar(s.text_frame.text))
    fecha = mes_anio(date.today())
    for p in shape.text_frame.paragraphs:
        if "2026" in p.text and "investig" not in U.normalizar(p.text):
            # El párrafo de la fecha puede venir partido en varios runs.
            p.runs[0].text = fecha
            for run in p.runs[1:]:
                run.text = ""
    for variante in ("‘", "’"):
        U.reemplazar_texto_en_shape(shape, variante, "")


def diapositiva_filtros(prs, f, datos):
    slide = prs.slides[PM.FILTROS]
    texto = F.descripcion(f)
    U.poner_texto_completo(_shape_con_texto(slide, "propuesta"), "FILTROS APLICADOS")
    U.poner_texto_completo(_shape_con_texto(slide, "datos de solicitud"), "Filtros elegidos:")
    # Cuadro de la plantilla de Tendencias → filtro del observatorio que muestra.
    for inicio, etiqueta in (("nombre del programa", "Carreras"), ("facultad propuesta", "Nivel académico"),
                             ("duracion", "Corte de análisis"), ("modalidad", "Financiamiento"),
                             ("nombre del proponente", "Provincia (matriculados)"),
                             ("facultad proponente", "Proyección 2025"), ("cargo proponente", "Semestre de precios")):
        U.poner_etiqueta_valor(_shape_con_texto(slide, inicio), etiqueta, texto[etiqueta])
    mercado = datos.get("mercado") or {}
    lineas = [f"Nivel de mercado: {texto['Nivel de mercado']}",
              f"Carrera en matriculados, titulados y precios: {titulo(mercado['carrera'])}" if mercado.get("carrera")
              else "Carrera en matriculados, titulados y precios: sin datos",
              f"Zona territorial: {(datos.get('territorio') or {}).get('nombre') or texto['Zona territorial']}"]
    if (datos.get("trends") or {}).get("proyecto") is not None:
        p = datos["trends"]["proyecto"]
        lineas.append(f"Google Trends: proyecto {int(p['id'])} de Tendencias · {titulo(p['carrera_estudio'])}")
    li = datos.get("linkedin")
    if li:
        lineas.append(f"LinkedIn: proyecto {li['proyecto_id']} de Tendencias · {titulo(li['carrera'] or '')}")
    via = datos.get("viabilidad")
    if via:
        lineas.append(f"Viabilidad: {via['carrera']} frente a {via['referencia']} "
                      f"(pesos {'/'.join(str(x) for x in via['pesos'])}, {via['config'].nivel.lower()})")
    caja = slide.shapes.add_textbox(Inches(.8), Inches(6.98), Inches(11.8), Inches(.45))
    caja.name = "Filtros adicionales"
    caja.text_frame.word_wrap = True
    p = caja.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = " · ".join(lineas) + (("\nSin datos: " + " | ".join(datos["notas"])) if datos["notas"] else "")
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor.from_string("617D99")


def _texto_serie(tabla, carrera, sustantivo, f):
    anios = [int(a) for a in tabla.columns]
    reales = [a for a in anios if a != 2025]
    primero, ultimo = reales[0], reales[-1]
    total = tabla.loc["TOTAL"]
    cambio = variacion(total[primero], total[ultimo])
    partes = [f"{sustantivo.capitalize()} de {carrera}: {entero(total[primero])} en {primero} y "
              f"{entero(total[ultimo])} en {ultimo}"
              + (f" ({porcentaje(cambio, signo=True)})." if cambio is not None else ".")]
    if 2025 in anios:
        partes.append(f"Para 2025* se estiman {entero(total[2025])} "
                      f"({F.PROYECCION[f['proyeccion']].lower()}).")
    if "PUBLICO" in tabla.index and "PRIVADO" in tabla.index:
        partes.append(f"En {ultimo}, {entero(tabla.loc['PUBLICO', ultimo])} corresponden a instituciones públicas "
                      f"y {entero(tabla.loc['PRIVADO', ultimo])} a privadas.")
    partes.append(f"Financiamiento: {F.FINANCIAMIENTO[f['financiamiento']].lower()}.")
    return " ".join(partes)


def diapositiva_serie(prs, indice, tabla, carrera, f, carpeta, tipo):
    slide = prs.slides[indice]
    ruta = carpeta / f"{tipo}.png"
    if tipo == "matriculados":
        G_EDU.generar_serie(tabla, "Evolución de matriculados por tipo de institución", "Estudiantes", ruta)
        sustantivo = "la matrícula"
        texto = (_texto_serie(tabla, carrera, sustantivo, f)
                 + (f" Provincia de la IES: {titulo(f['provincia'])}." if f["provincia"] != F.NACIONAL else "")
                 if tabla is not None and tabla.loc["TOTAL"].sum() else
                 "N/D: no existen matriculados para la carrera y los filtros elegidos.")
        caja = _shape_con_texto(slide, "la matricula")
    else:
        G_EDU.generar_serie(tabla, "Evolución de titulados por tipo de institución", "Títulos registrados", ruta)
        texto = (_texto_serie(tabla, carrera, "los titulados", f)
                 if tabla is not None and tabla.loc["TOTAL"].sum() else
                 "N/D: no existen titulados para la carrera y los filtros elegidos.")
        caja = _shape_con_texto(slide, "la evolucion de titulados")
    U.reemplazar_imagen(slide, U.imagen_mayor(slide), str(ruta))
    U.poner_texto_completo(caja, texto)
    U.poner_texto_completo(_shape_con_texto(slide, "**valores proyectados"), PROYECCION_NOTA[f["proyeccion"]])


def diapositiva_instituciones(prs, paneles, carpeta):
    slide = prs.slides[PM.INSTITUCIONES]
    ruta = carpeta / "instituciones.png"
    G_INST.generar_instituciones(paneles, ruta)
    U.reemplazar_imagen(slide, U.imagen_mayor(slide), str(ruta))


def diapositiva_trends(prs, tr, carpeta):
    slide = prs.slides[PM.GOOGLE_TRENDS]
    imagenes = sorted((s for s in slide.shapes if s.shape_type == 13), key=lambda s: s.left)
    regional, comparativo = imagenes[0], imagenes[-1]
    ruta_regional, ruta_comparacion = carpeta / "trends_regional.png", carpeta / "trends_comparacion.png"
    if tr is None:
        G_TR.generar_tendencia_regional(None, {}, ruta_regional)
        G_TR.generar_comparacion(None, ("—", "—"), ruta_comparacion)
        texto = "N/D: no hay resultados de Google Trends para esta carrera en el proyecto Tendencias."
        palabras = ("Término español", "Término inglés")
    else:
        G_TR.generar_tendencia_regional(tr["serie"], tr["tendencias"], ruta_regional)
        G_TR.generar_comparacion(tr["comparacion"], tr["palabras"], ruta_comparacion)
        palabras = tr["palabras"]
        i = tr["interes"]
        partes = [f"Búsquedas de «{palabras[0]}» en Google Trends (proyecto {int(tr['proyecto']['id'])} de Tendencias)."]
        if i["top_mean"] is not None:
            partes.append(f"Promedio de las palabras clave: {decimal(i['top_mean'])}, frente a "
                          f"{decimal(i['base_mean'])} de las palabras base de la carrera de referencia "
                          f"(interés relativo {porcentaje(i['ratio'])}).")
        pendientes = [f"{nombre} {'+' if t['slope'] >= 0 else '−'}{decimal(abs(t['slope']), 2)} pts/año"
                      for nombre, t in tr["tendencias"].items() if t.get("slope") is not None]
        if pendientes:
            partes.append("Tendencia anual del índice: " + "; ".join(pendientes) + ".")
        texto = " ".join(partes)
    U.reemplazar_imagen(slide, regional, str(ruta_regional))
    U.reemplazar_imagen(slide, comparativo, str(ruta_comparacion))
    U.poner_texto_completo(_shape_con_texto(slide, "el comportamiento de busquedas"), texto)
    U.poner_texto_completo(_shape_con_texto(slide, "interes a nivel mundial"), "Español frente a inglés · top 10 países")
    U.poner_texto_completo(_shape_con_texto(slide, "termino espanol"), palabras[0])
    U.poner_texto_completo(_shape_con_texto(slide, "termino ingles"), palabras[1])
    cuadritos = sorted((s for s in slide.shapes if s.shape_type == 1 and s.width < Inches(.3)), key=lambda s: s.left)
    for cuadrito, color in zip(cuadritos, (G_TR.COLOR_ESPANOL, G_TR.COLOR_INGLES)):
        U.colorear(cuadrito, color)


# Tarjetas de la diapositiva de empleabilidad: rectángulo y etiqueta «Tasa de empleo visible»
# (año, tasa y variación están en graficos/empleabilidad.TARJETAS). La plantilla resalta la última.
RECTANGULOS_TARJETA = (8, 12, 16, 20)
ETIQUETAS_TARJETA = (11, 15, 19, 23)


def _partes_tarjeta(slide, i):
    return [slide.shapes[RECTANGULOS_TARJETA[i]], *(slide.shapes[j] for j in G_EMP.TARJETAS[i]),
            slide.shapes[ETIQUETAS_TARJETA[i]]]


def _estilo(forma):
    """Relleno/borde del shape y formato del primer run de texto (copias independientes)."""
    import copy
    relleno = [copy.deepcopy(h) for h in forma._element.spPr if not h.tag.endswith(("}xfrm", "}prstGeom"))]
    run = next((r for p in forma.text_frame.paragraphs for r in p.runs), None) if forma.has_text_frame else None
    texto = copy.deepcopy(run._r.rPr) if run is not None and run._r.rPr is not None else None
    return relleno, texto


def _aplicar_estilo(forma, estilo):
    import copy
    relleno, texto = estilo
    sp = forma._element.spPr
    for hijo in [h for h in sp if not h.tag.endswith(("}xfrm", "}prstGeom"))]:
        sp.remove(hijo)
    for hijo in relleno:
        sp.append(copy.deepcopy(hijo))
    if texto is not None and forma.has_text_frame:
        for p in forma.text_frame.paragraphs:
            for run in p.runs:
                if run._r.rPr is not None:
                    run._r.remove(run._r.rPr)
                run._r.insert(0, copy.deepcopy(texto))


def resaltar_tarjeta(slide, indice):
    """Pasa el resaltado (fondo azul) de la última tarjeta a la del corte elegido."""
    ultima = len(RECTANGULOS_TARJETA) - 1
    if indice == ultima:
        return
    corte, final = _partes_tarjeta(slide, indice), _partes_tarjeta(slide, ultima)
    estilos_corte, estilos_final = [_estilo(s) for s in corte], [_estilo(s) for s in final]
    for forma, estilo in zip(corte, estilos_final):
        _aplicar_estilo(forma, estilo)
    for forma, estilo in zip(final, estilos_corte):
        _aplicar_estilo(forma, estilo)


def diapositiva_empleabilidad(prs, emp, territorio, f, carpeta):
    slide = prs.slides[PM.EMPLEABILIDAD]
    G_EMP.validar_slide(slide)
    summary = emp["summary"].reset_index(drop=True)
    fila = summary[summary.year.eq(f["corte"])]
    fila = fila.iloc[0] if len(fila) else summary.iloc[-1]
    ruta_comp, ruta_banda = carpeta / "composicion.png", carpeta / "banda.png"
    G_EMP.generar_composicion(fila, ruta_comp)
    G_EMP.generar_banda_salarial(fila, ruta_banda)
    G_EMP.actualizar_tarjetas(slide, summary)
    resaltar_tarjeta(slide, int(summary.index[summary.year.eq(int(fila["year"]))][0]))
    U.reemplazar_imagen(slide, G_EMP.IMAGEN_COMPOSICION, str(ruta_comp))
    U.reemplazar_imagen(slide, G_EMP.IMAGEN_BANDA, str(ruta_banda))
    U.poner_texto_completo(slide.shapes[G_EMP.FUENTE], "Fuente: SENESCYT, IESS y SRI")
    corte = F.etiqueta_corte(int(fila["year"]))
    U.poner_texto_completo(_shape_con_texto(slide, "composicion del empleo"), f"Composición del empleo · {int(fila['year'])}")
    U.poner_texto_completo(_shape_con_texto(slide, "banda salarial"), f"Banda Salarial · {int(fila['year'])}")
    zona = territorio["nombre"] if territorio else titulo(f["territorio"]["provincia"])
    G_EMP.agregar_tarjeta_territorial(slide, territorio["resumen"] if territorio else None, zona)
    return fila


def diapositiva_empresas(prs, sector, nombre, carpeta, cargos=None):
    """Empresas y sectores del observatorio; con proyecto de Tendencias, también cargos de LinkedIn."""
    slide = prs.slides[PM.EMPRESAS_SECTORES]
    ruta_emp, ruta_sec = carpeta / "empresas.png", carpeta / "sectores.png"
    empresas = sector["empresas"] if sector else None
    macro = sector["macro"] if sector else None
    if cargos is None:
        G_SEC.generar_empresas(empresas, ruta_emp)
    else:
        G_SEC.generar_empresas(None if empresas is None else empresas.head(5), ruta_emp,
                               caja=G_SEC.GRAFICO_EMPRESAS_CON_CARGOS)
    G_SEC.generar_sectores(macro, ruta_sec)
    G_SEC.actualizar_slide(slide, nombre, empresas, macro, str(ruta_emp), str(ruta_sec), cargos=cargos)


def diapositiva_precios(prs, mercado, carpeta):
    slide = prs.slides[PM.PRECIOS]
    ruta = carpeta / "precios.png"
    precios = (mercado or {}).get("precios")
    if precios is None:
        G_EDU.generar_precios(None, ruta)
        texto = "N/D: no existen aranceles válidos en Precios_Homologados para la carrera y los filtros elegidos."
    else:
        m, propio = precios["metricas"], precios["propio"]
        G_EDU.generar_precios(precios["tabla"], ruta, propio=m["own_price"])
        texto = (f"Semestre {precios['semestre']}: {m['offering']} universidades ofertan {titulo(mercado['carrera'])} "
                 f"({m['competitors']} competidores). Los aranceles promedio por institución van de "
                 f"{dinero(m['market_min'])} a {dinero(m['market_max'])}, con un promedio de {dinero(m['market_mean'])}.")
        if not pd.isna(m["own_price"]):
            tipo = "estimado" if propio["tipo"] == "estimado" else "real"
            texto += (f" El arancel UDLA ({tipo}) es {dinero(m['own_price'])}, "
                      f"{porcentaje(m['own_gap_pct'], signo=True)} frente al promedio de la competencia "
                      f"({dinero(m['competitor_mean'])}).")
        else:
            texto += " Sin información suficiente para el arancel UDLA."
    U.reemplazar_imagen(slide, U.imagen_mayor(slide), str(ruta), factor_tamano=1.12)
    U.poner_texto_completo(_shape_con_texto(slide, "la comparacion de aranceles"), texto)


def diapositiva_sri(prs, sector, carpeta):
    slide = prs.slides[PM.SRI]
    ruta = carpeta / "sri.png"
    mensual = (sector or {}).get("mensual", pd.DataFrame())
    codigos = (sector or {}).get("codigos") or []
    datos = pd.DataFrame(columns=["ciiu", "anio", "mes", "personas_naturales", "sociedades"])
    if mensual is not None and not mensual.empty:
        datos = pd.DataFrame({"ciiu": "TOTAL", "anio": mensual["Año"], "mes": mensual["Mes"],
                              "personas_naturales": mensual["Personas naturales"], "sociedades": mensual["Sociedades"]})
    resumen = G_SRI.generar_grafico_desestacionalidad(codigos, datos, ruta, sector.get("mes") if sector else None,
                                                      sector.get("anio") if sector else None)
    if datos.empty:
        texto = "N/D: no hay ventas SRI para los CIIU de los empleadores de los graduados."
    else:
        c = sector["crecimiento"]
        partes = [f"Ventas declaradas al SRI (formularios 411 y 413) de los {len(codigos)} CIIU donde trabajan los "
                  f"graduados, acumulado enero–{G_SRI.MESES[sector['mes'] - 1].lower()} {sector['anio']}: "
                  f"{dinero(c['total'])}."]
        if not pd.isna(c["growth"]):
            partes.append(f"Variación frente al mismo periodo de {sector['anio'] - 1}: {porcentaje(c['growth'], signo=True)}.")
        if c["top"]:
            partes.append(f"CIIU con mayor crecimiento: {c['top']['CIIU']} ({porcentaje(c['top']['growth'], signo=True)}).")
        macro = sector.get("macro")
        if macro is not None and macro["Ventas totales"].notna().any() and c["total"]:
            lider = macro.sort_values("Ventas totales", ascending=False).iloc[0]
            partes.append(f"Macroindustria con más ventas: {lider['Macroindustria'].lower()} "
                          f"({porcentaje(100 * lider['Ventas totales'] / c['total'])}).")
        texto = " ".join(partes)
    U.reemplazar_imagen(slide, U.imagen_mayor(slide), str(ruta), caja=PM.CAJA_SRI)
    U.poner_texto_completo(_shape_con_texto(slide, "el comportamiento financiero"), texto)
    return resumen


def diapositiva_conclusiones(prs, datos, nombre, fila):
    slide = prs.slides[PM.CONCLUSIONES]
    f = datos["filtros"]
    mercado, sector, tr = datos.get("mercado") or {}, datos.get("sector") or {}, datos.get("trends")
    corte = F.etiqueta_corte(int(fila["year"]))
    hallazgos = []
    demanda = []
    for clave, sustantivo in (("matriculados", "matrícula"), ("titulados", "titulados")):
        tabla = mercado.get(clave)
        if tabla is not None and tabla.loc["TOTAL"].sum():
            reales = [int(a) for a in tabla.columns if int(a) != 2025]
            cambio = variacion(tabla.loc["TOTAL", reales[0]], tabla.loc["TOTAL", reales[-1]])
            if cambio is not None:
                demanda.append(f"{sustantivo} {porcentaje(cambio, signo=True)} entre {reales[0]} y {reales[-1]}")
    if tr is not None and tr["tendencias"].get("Ecuador", {}).get("slope") is not None:
        demanda.append(f"interés en Google Trends en Ecuador "
                       f"{'+' if tr['tendencias']['Ecuador']['slope'] >= 0 else '−'}"
                       f"{decimal(abs(tr['tendencias']['Ecuador']['slope']), 2)} pts/año")
    hallazgos.append(("Demanda e Interés Académico", (mayuscula_inicial(lista(demanda)) + ".") if demanda else "N/D."))
    empleo = (f"{decimal(fila['rate'])} % de empleo visible en {corte} "
              f"({entero(fila['employed'])} de {entero(fila['graduates'])} graduados)")
    if fila["salary_n"] and not pd.isna(fila["p25"]):
        empleo += f"; banda salarial de dependientes entre {dinero(fila['p25'])} y {dinero(fila['p75'])}"
    hallazgos.append(("Oferta de Valor-Empleabilidad", empleo + "."))
    precios = mercado.get("precios")
    if precios:
        m = precios["metricas"]
        texto = (f"{m['competitors']} competidores con arancel promedio de {dinero(m['market_mean'])} "
                 f"(semestre {precios['semestre']})")
        if not pd.isna(m["own_price"]):
            texto += f"; UDLA {dinero(m['own_price'])} ({porcentaje(m['own_gap_pct'], signo=True)} frente a la competencia)"
        hallazgos.append(("Posicionamiento, Competencia y Precios", texto + "."))
    else:
        hallazgos.append(("Posicionamiento, Competencia y Precios", "N/D."))
    if sector.get("macro") is not None and sector["macro"]["Graduados"].sum():
        top = sector["macro"].sort_values("Graduados", ascending=False).head(2)["Macroindustria"].str.lower().tolist()
        texto = f"los graduados trabajan sobre todo en {lista(top)}"
        crecimiento = (sector.get("crecimiento") or {}).get("growth")
        if crecimiento is not None and not pd.isna(crecimiento):
            texto += f"; ventas SRI de sus CIIU {porcentaje(crecimiento, signo=True)} interanual"
        hallazgos.append(("Sector Económico", mayuscula_inicial(texto) + "."))
    else:
        hallazgos.append(("Sector Económico", "N/D."))
    resultado = resultado_viabilidad(datos.get("viabilidad"), datos.get("linkedin"))
    li = datos.get("linkedin")
    if li and li.get("estudio"):
        local = li["estudio"].get(li["region"]) or {}
        profesionales = G_LI.numero_linkedin(local.get("profesionales"))
        anuncios = G_LI.numero_linkedin(local.get("anuncios"))
        if profesionales is not None:
            texto = f"{entero(profesionales)} profesionales en LinkedIn ({li['region']})"
            if anuncios is not None:
                texto += f" y {entero(anuncios)} anuncios de empleo"
            hallazgos.insert(2, ("LinkedIn", mayuscula_inicial(texto) + "."))
    encabezado = (f"{nombre}: indicadores del observatorio con los filtros aplicados "
                  f"(corte {corte}, nivel {f['nivel_academico'].lower()})")
    if resultado:
        encabezado += f"; {resultado[0]}: {resultado[1].lower()}"
    U.poner_texto_completo(slide.shapes[0], encabezado + ".")
    U.poner_parrafos(slide.shapes[1], hallazgos)
    U.poner_texto_completo(_shape_con_texto(slide, "razones clave"), "Hallazgos:")
    U.poner_parrafos(_shape_con_texto(slide, "conclusion final"), [(
        "Conclusión final",
        (f"con los filtros elegidos, el {resultado[0]} da como resultado: {resultado[1].lower()}. "
         "Revisar las dimensiones más débiles antes de decidir; el índice no es una autorización de apertura.")
        if resultado else
        "esta presentación resume la evidencia del observatorio para los filtros elegidos; no hay un resultado "
        "de viabilidad para esta carrera.")])


# --- LinkedIn e IA (proyecto Tendencias, como generar_reporte_mercado) --------------------

def _imagen_nd(ruta, texto, ancho=8, alto=4.5):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(ancho, alto))
    ax.axis("off")
    ax.text(.5, .5, texto, ha="center", va="center", fontsize=13, color="#7B91A8", wrap=True,
            transform=ax.transAxes)
    fig.savefig(str(ruta), dpi=200, facecolor="white")
    plt.close(fig)
    return str(ruta)


def diapositiva_aptitudes(prs, li):
    """Diapositiva 10: competencias del programa, alineación (IA) y aptitudes LinkedIn local vs LATAM."""
    slide = prs.slides[PM.APTITUDES]
    region = li["region"] if li else "Ecuador"
    top = li["aptitudes"] if li else []
    tarjetas = []
    if li:
        calculo = li["alineacion"].get("calculo", {}) if isinstance(li["alineacion"], dict) else {}
        puntajes = {G_LI.clave_aptitud(fila.get("competencia")): fila.get("puntaje")
                    for fila in calculo.get("competencias", []) if fila.get("competencia")}
        tarjetas = [(c, puntajes.get(G_LI.clave_aptitud(c))) for c in li["competencias"][:5]]
    G_LI.actualizar_tarjetas_competencias(slide, tarjetas)
    for shape in slide.shapes:
        if getattr(shape, "text", "").strip() == "API":
            shape.text_frame.text = "Análisis IA"
            shape.text_frame.word_wrap = False
    if li and top:
        conjunto = len(li["homologados"]["aptitudes"]) + len(li["homologados"]["habilidades"])
        texto = (f"Las competencias existentes del programa ({len(tarjetas)}) se comparan contra todo el conjunto "
                 f"homologado relevante de LinkedIn ({conjunto} elementos entre aptitudes y habilidades). "
                 "Aptitudes más habituales entre los profesionales del programa de estudio: "
                 + ", ".join(str(r[0]) for r in top) + ". "
                 "Los porcentajes de las tarjetas corresponden al cálculo de alineación reproducible.")
    elif li:
        texto = "No hay aptitudes registradas para este programa en LinkedIn."
    else:
        texto = "N/D: no hay proyecto de Tendencias con datos de LinkedIn para esta carrera."
    U.poner_texto_completo(slide.shapes[7], texto)
    for run in slide.shapes[7].text_frame.paragraphs[0].runs:
        run.font.size = Pt(11)
    G_LI.actualizar_graficos_linkedin(
        prs, top, region, li["estudio"] if li else {},
        aptitudes_regionales=li["aptitudes_region"] if li else {region: [], "América Latina": []})


def diapositiva_habilidades(prs, li):
    """Diapositiva 11: habilidades repetidas en los anuncios (se arma con la diapositiva 10)."""
    G_REQ.insertar_requisitos(prs, li["requisitos"] if li else None, li["region"] if li else "Ecuador",
                              habilidades_homologadas=li["homologados"]["habilidades"] if li else None)


def diapositiva_ubicacion(prs, li, carpeta):
    """Diapositiva 12: mapa LATAM con las ubicaciones de profesionales en LinkedIn."""
    slide = prs.slides[PM.UBICACION]
    ruta = carpeta / "mapa_latam.png"
    top = G_MAPA.generar_mapa_latam(li["ubicaciones"] if li else (), str(ruta))
    U.poner_texto_completo(slide.shapes[1], (
        "Principales países en las ubicaciones extraídas de LinkedIn: "
        + "; ".join(f"{pais}: {entero(total)} profesionales" for pais, total in top) + ". "
        "La distribución corresponde a las ubicaciones disponibles del reporte de América Latina.")
        if top else "Sin ubicaciones registradas para este programa en América Latina.")
    U.reemplazar_imagen(slide, 3, str(ruta), conservar_proporcion=True, caja=PM.CAJA_MAPA)


def _pintar_rectangulos_celestes(slide):
    """Copia de Tendencias: rectángulos nativos de la diapositiva de nombres en celeste."""
    from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_SHAPE_TYPE
    for shape in U.iterar_shapes(slide.shapes):
        if shape.shape_type != MSO_SHAPE_TYPE.AUTO_SHAPE:
            continue
        try:
            rectangulo = shape.auto_shape_type in (MSO_AUTO_SHAPE_TYPE.RECTANGLE,
                                                   MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE)
        except ValueError:
            rectangulo = False
        if rectangulo:
            U.colorear(shape, "DCEAF7")


def diapositiva_naming(prs, li, carpeta):
    """Diapositiva 19: alternativas de nombre evaluadas por IA en el proyecto de Tendencias."""
    slide = prs.slides[PM.NAMING]
    filas = (li["naming"].get("nombres") if li and isinstance(li["naming"], dict) else None)
    if filas:
        G_NAMING.actualizar_slide_naming(slide, filas)
    else:
        # Tendencias deja la gráfica de ejemplo; aquí se marca N/D para no mostrar nombres ficticios.
        imagen = next(s for s in slide.shapes if s.shape_type == 13)
        U.reemplazar_imagen(slide, imagen, _imagen_nd(carpeta / "naming.png",
                                                      "N/D: sin evaluación de nombres con IA", 11, 6))
        U.poner_texto_completo(slide.shapes[0], (
            "N/D: el proyecto de Tendencias de esta carrera no tiene alternativas de nombre evaluadas con IA."
            if li else "N/D: no hay proyecto de Tendencias para evaluar alternativas de nombre."))
    _pintar_rectangulos_celestes(slide)


# --- Viabilidad (pestaña «Viabilidad de carreras»; si no, radar de Tendencias) -------------

ETIQUETAS_RADAR = ["Demanda", "Empleabilidad", "Competencia", "Precio", "Sector económico"]
RANGOS_DASHBOARD = (("0%–<60%", "Puntaje bajo"), ("60%–<75%", "Requiere ajustes"),
                    ("75%–100%", "Resultado intermedio o alto"))


def viabilidad_tendencias(li):
    """generator._obtener_viabilidad_existente de Tendencias (grafico_radar_datos)."""
    fila = (li or {}).get("radar")
    if not fila:
        return None
    n = [float(v or 0) for v in fila]
    competencia = (n[1] + n[2]) / 2
    valores = dict(busqueda=n[0], competencia=competencia, linkedin=n[3], mercado=n[4])
    total = n[0] + competencia + n[3] + n[4]
    clasificacion = "Definitivamente no viable" if total <= 60 else "Para revisión adicional" if total <= 70 else "Viable"
    return dict(fuente="tendencias", fila=fila, valores=valores, total=total, clasificacion=clasificacion)


def _items_porcentaje(shape, items, vacio):
    U.poner_parrafos(shape, [(None, f"{etiqueta} ({decimal(valor)}%)") for etiqueta, valor in items] or [(None, vacio)])


def _total_y_lectura(slide, total, lectura):
    """Total y clasificación en una sola línea dentro de sus cuadros de la plantilla."""
    U.poner_texto_completo(slide.shapes[1], f"{decimal(total)}/100")
    U.poner_texto_completo(slide.shapes[5], lectura)
    for indice in (1, 5):
        slide.shapes[indice].text_frame.word_wrap = False
    if len(lectura) > 10:
        for run in slide.shapes[5].text_frame.paragraphs[0].runs:
            run.font.size = Pt(16 if len(lectura) <= 16 else 14)


def diapositiva_cuadrante(prs, via, carpeta):
    """Diapositiva 18: «Demanda vs. competencia» de Viabilidad de carreras."""
    slide = prs.slides[PM.CUADRANTE]
    imagen = next(s for s in slide.shapes if s.shape_type == 13)
    ruta = carpeta / "cuadrante.png"
    if via and via["fuente"] == "dashboard":
        a, cfg = via["actual"], via["config"]
        G_VIA.generar_cuadrante(via["resultados"], a, via["base"], cfg.umbral_busquedas, cfg.umbral_competidores, ruta)
        texto = (f"La carrera de {via['carrera']} se ubica en el cuadrante «{a['cuadrante'].lower()}», con búsquedas "
                 f"equivalentes al {decimal(a['busquedas'])}% de {via['referencia']} y {a['competidores']:g} "
                 f"competidores. Zona objetivo: búsquedas de al menos {cfg.umbral_busquedas:g}% y hasta "
                 f"{cfg.umbral_competidores:g} competidores ({cfg.nivel.lower()}). "
                 + dict(via["recomendaciones"]).get("Competencia y posición de mercado", ""))
    else:
        _imagen_nd(ruta, "N/D: carrera fuera del modelo de Viabilidad de carreras", 6.7, 4.5)
        texto = "N/D: la carrera no está entre las 12 del modelo de «Viabilidad de carreras»."
    U.reemplazar_imagen(slide, imagen, str(ruta))
    U.poner_texto_completo(slide.shapes[0], texto)


def diapositiva_metodo(prs, via):
    """Diapositiva 23: rangos de evaluación del modelo que dio el resultado."""
    if not via or via["fuente"] != "dashboard":
        return  # Tendencias: se conserva su tabla (0–60, 61–70, 71–100)
    slide = prs.slides[PM.METODO]
    tabla = next(s for s in slide.shapes if s.has_table).table
    celdas = [fila.cells[0] for fila in tabla.rows][1:]
    for i, (rango, lectura) in enumerate(RANGOS_DASHBOARD):
        for celda, texto in ((celdas[2 * i], rango), (celdas[2 * i + 1], lectura)):
            p = celda.text_frame.paragraphs[0]
            if p.runs:
                p.runs[0].text = texto
                for run in p.runs[1:]:
                    run._r.getparent().remove(run._r)
            else:
                p.text = texto


def diapositiva_resumen(prs, via, li, carpeta):
    """Diapositiva 24: radar, total, clasificación, fortalezas, debilidades y recomendaciones."""
    slide = prs.slides[PM.RESUMEN_RESULTADOS]
    ruta = carpeta / "radar.png"
    if via and via["fuente"] == "dashboard":
        a = via["actual"]
        G_VIA.generar_radar_bloques(ETIQUETAS_RADAR, a["bloques"], ruta)
        ordenados = sorted(zip(via["bloques"], a["bloques"]), key=lambda x: x[1], reverse=True)
        U.reemplazar_imagen(slide, 0, str(ruta))
        _total_y_lectura(slide, a["total"], a["clasificacion"])
        _items_porcentaje(slide.shapes[8], [x for x in ordenados if x[1] >= 75][:2], "Ningún bloque alcanza el 75%.")
        _items_porcentaje(slide.shapes[9], sorted(ordenados[-2:], key=lambda x: x[1]), "N/D")
        U.poner_parrafos(slide.shapes[3], via["recomendaciones"])
        return
    tend = viabilidad_tendencias(li)
    if tend:
        v = tend["valores"]
        G_RADAR.generar_grafico_radar(tend["fila"], str(ruta))
        U.reemplazar_imagen(slide, 0, str(ruta))
        _total_y_lectura(slide, tend["total"], "No viable" if tend["total"] <= 60 else
                         "En revisión" if tend["total"] <= 70 else "Viable")
        dimensiones = [(nombre, v[clave]) for nombre, clave in (
            ("Demanda e interés académico", "busqueda"), ("Oferta de valor y empleabilidad", "linkedin"),
            ("Posicionamiento, competencia y precios", "competencia"), ("Dinámica del sector económico", "mercado"))]
        dimensiones.sort(key=lambda x: x[1], reverse=True)
        _items_porcentaje(slide.shapes[8], dimensiones[:2], "N/D")
        _items_porcentaje(slide.shapes[9], list(reversed(dimensiones[-2:])), "N/D")
        U.poner_parrafos(slide.shapes[3], [(None, "Resultado de viabilidad guardado en el proyecto "
                                                  f"{li['proyecto_id']} de Tendencias.")])
        return
    U.reemplazar_imagen(slide, 0, _imagen_nd(ruta, "N/D", 4, 4))
    for indice in (1, 5, 8, 9):
        U.poner_texto_completo(slide.shapes[indice], "N/D")
    U.poner_texto_completo(slide.shapes[3], "N/D\nNo existen resultados de viabilidad para esta carrera.")


def resultado_viabilidad(via, li):
    """(texto corto, clasificación) del resultado usado en la presentación, o None."""
    if via and via["fuente"] == "dashboard":
        a = via["actual"]
        return (f"índice de viabilidad {decimal(a['total'])}/100 (pestaña Viabilidad de carreras, referencia "
                f"{via['referencia']})", a["clasificacion"])
    tend = viabilidad_tendencias(li)
    if tend:
        return f"resultado de viabilidad {decimal(tend['total'])}% (proyecto {li['proyecto_id']} de Tendencias)", tend["clasificacion"]
    return None


# --- Entrada principal ---------------------------------------------------------------

def generar(datos, ruta_salida, avisar=print):
    """Llena la plantilla con ``datos`` (presentaciones.datos.recopilar) y guarda el .pptx."""
    f = datos["filtros"]
    nombre = nombre_programa(f["carreras"])
    prs = Presentation(str(PLANTILLA))
    validar_plantilla(prs)
    with tempfile.TemporaryDirectory(prefix="pptx_mercado_") as temporal:
        carpeta = Path(temporal)
        U.reemplazar_en_presentacion(prs, VARIANTES_NOMBRE, nombre)
        avisar("[PPTX] Portada y filtros")
        portada(prs, nombre)
        diapositiva_filtros(prs, f, datos)
        mercado = datos.get("mercado") or {}
        carrera = titulo(mercado.get("carrera") or f["carreras"][0])
        avisar("[PPTX] Matriculados y titulados")
        diapositiva_serie(prs, PM.MATRICULADOS, mercado.get("matriculados"), carrera, f, carpeta, "matriculados")
        diapositiva_serie(prs, PM.TITULADOS, mercado.get("titulados"), carrera, f, carpeta, "titulados")
        avisar("[PPTX] Instituciones y Google Trends")
        diapositiva_instituciones(prs, datos.get("instituciones"), carpeta)
        diapositiva_trends(prs, datos.get("trends"), carpeta)
        li, via = datos.get("linkedin"), datos.get("viabilidad")
        avisar("[PPTX] LinkedIn: aptitudes, habilidades y ubicación")
        diapositiva_aptitudes(prs, li)
        diapositiva_habilidades(prs, li)
        diapositiva_ubicacion(prs, li, carpeta)
        avisar("[PPTX] Empleabilidad, empresas y sectores")
        fila = diapositiva_empleabilidad(prs, datos["empleabilidad"], datos.get("territorio"), f, carpeta)
        diapositiva_empresas(prs, datos.get("sector"), nombre, carpeta, li["cargos"] if li else None)
        avisar("[PPTX] Precios, cuadrante y nombres")
        diapositiva_precios(prs, mercado, carpeta)
        diapositiva_cuadrante(prs, via, carpeta)
        diapositiva_naming(prs, li, carpeta)
        avisar("[PPTX] Sector económico, viabilidad y conclusiones")
        diapositiva_sri(prs, datos.get("sector"), carpeta)
        diapositiva_metodo(prs, via)
        diapositiva_resumen(prs, via, li, carpeta)
        diapositiva_conclusiones(prs, datos, nombre, fila)
        return U.guardar(prs, ruta_salida)

"""LinkedIn, IA y radar de un proyecto de Tendencias (solo lectura).

El observatorio no tiene LinkedIn ni nombres evaluados con IA. Estas consultas son copia de
``database/repositories/presentation_data.py`` y ``report.py`` del proyecto Tendencias, es
decir, se buscan igual que en su presentación. La conexión se abre con
``tendencias_data._connect`` (``readonly=True``): nunca escribe en la base de Tendencias.
"""
import json
from contextlib import closing


class LinkedinTendencias:
    def __init__(self, url, proyecto_id):
        self.url, self.proyecto_id = url, int(proyecto_id)

    def _uno(self, sql, parametros, todos=False):
        import tendencias_data

        with closing(tendencias_data._connect(self.url)) as conexion, conexion.cursor() as cursor:
            cursor.execute(sql, parametros)
            return cursor.fetchall() if todos else cursor.fetchone()

    # --- PresentationDataRepository --------------------------------------------------------

    def region_local(self):
        """generator._obtener_region_local: «pregrado cr» → Costa Rica; si no, Ecuador."""
        fila = self._uno("SELECT tipo_carpeta FROM proyectos_tendencias WHERE id=%s", (self.proyecto_id,))
        return "Costa Rica" if "pregrado cr" in str((fila or [""])[0] or "").lower() else "Ecuador"

    def carrera(self):
        fila = self._uno("SELECT carrera_estudio FROM proyectos_tendencias WHERE id=%s", (self.proyecto_id,))
        return fila[0] if fila else None

    def estudio(self, region):
        filas = self._uno("""
            SELECT Tipo, Region, Profesionales, AnunciosEmpleo,
                   PorcentajeAnunciosProfesionales, DemandaContratacion
            FROM linkedin
            WHERE proyecto_id=%s AND LOWER(Tipo)=LOWER('Estudio')
            ORDER BY CASE WHEN Region=%s THEN 0 ELSE 1 END, id DESC""", (self.proyecto_id, region), todos=True)
        resultado = {}
        for fila in filas:
            resultado.setdefault(fila[1], {"tipo": fila[0], "region": fila[1], "profesionales": fila[2],
                                           "anuncios": fila[3], "porcentaje": fila[4], "demanda": fila[5]})
        return resultado

    def aptitudes(self, region, limite=5):
        filas = self._uno("""
            SELECT DISTINCT ON (a.ubicacion, LOWER(TRIM(a.nombre)))
                   a.nombre, a.porcentaje, a.cantidad, a.ubicacion
            FROM linkedin_aptitudes a
            JOIN proyectos_tendencias p ON p.id=a.proyecto_id
            WHERE a.proyecto_id=%s
              AND LOWER(TRIM(a.carrera_estudio))=LOWER(TRIM(p.carrera_estudio))
              AND a.ubicacion IN (%s, 'América Latina')
            ORDER BY a.ubicacion, LOWER(TRIM(a.nombre)), a.id DESC""", (self.proyecto_id, region), todos=True)

        def porcentaje(valor):
            try:
                return float(str(valor).replace("%", "").replace(",", ".").strip())
            except (TypeError, ValueError):
                return 0.0

        def cantidad(valor):
            try:
                return float(valor)
            except (TypeError, ValueError):
                return 0.0

        local = [f for f in filas if f[3] == region]
        latam = [f for f in filas if f[3] == "América Latina"]
        if limite is None:
            return {region: local, "América Latina": latam}
        return sorted(local or latam, key=lambda f: (porcentaje(f[1]), cantidad(f[2])), reverse=True)[:limite]

    def ubicaciones_latam(self):
        return self._uno("""
            SELECT DISTINCT ON (LOWER(TRIM(u.nombre))) u.nombre, u.cantidad
            FROM linkedin_ubicaciones u
            JOIN proyectos_tendencias p ON p.id = u.proyecto_id
            WHERE u.proyecto_id=%s
              AND u.ubicacion='América Latina'
              AND LOWER(TRIM(u.carrera_estudio))=LOWER(TRIM(p.carrera_estudio))
            ORDER BY LOWER(TRIM(u.nombre)), u.id DESC""", (self.proyecto_id,), todos=True)

    def detalle(self, region, tipo):
        try:
            fila = self._uno("""
                SELECT d.datos FROM linkedin_detalles d
                JOIN proyectos_tendencias p ON p.id=d.proyecto_id
                WHERE d.proyecto_id=%s AND d.region=%s AND d.tipo=%s
                  AND LOWER(TRIM(d.carrera_estudio))=LOWER(TRIM(p.carrera_estudio))
                ORDER BY d.updated_at DESC LIMIT 1""", (self.proyecto_id, region, tipo))
        except Exception:
            return None
        return fila[0] if fila else None

    def homologados(self, region, tipo):
        carrera = self.carrera()
        if not carrera:
            return []
        filas = self._uno("""
            SELECT nombre_normalizado, variantes_originales, frecuencia_total,
                   confianza, familia_cargo, seniority, metadata
            FROM linkedin_ai_homologaciones
            WHERE proyecto_id=%s AND carrera_estudio=%s AND region=%s
              AND tipo_reporte='Estudio' AND tipo_fuente=%s
            ORDER BY frecuencia_total DESC, id""", (self.proyecto_id, carrera, region, tipo), todos=True)
        return [{"nombre_normalizado": f[0], "variantes_originales": f[1], "frecuencia_total": float(f[2] or 0),
                 "confianza": f[3], "familia_cargo": f[4], "seniority": f[5], "metadata": f[6] or {}} for f in filas]

    def resultado_ia(self, region, tipo):
        carrera = self.carrera()
        if not carrera:
            return None
        fila = self._uno("""
            SELECT resultado FROM linkedin_ai_analisis
            WHERE proyecto_id=%s AND carrera_estudio=%s AND region=%s
              AND tipo_reporte='Estudio' AND tipo_analisis=%s
              AND estado IN ('ok','fallback_no_key','fallback_error','fallback_sdk_missing')
            ORDER BY updated_at DESC, id DESC LIMIT 1""", (self.proyecto_id, carrera, region, tipo))
        return fila[0] if fila else None

    def aptitudes_formulario(self):
        try:
            fila = self._uno("SELECT aptitudes_programa FROM proyectos_tendencias WHERE id=%s", (self.proyecto_id,))
        except Exception:
            return []
        valores = fila[0] if fila else []
        if isinstance(valores, str):
            valores = json.loads(valores)
        return [str(v).strip() for v in (valores or [])]

    def radar(self):
        """ReportRepository.get_radar_values: último resultado de viabilidad de Tendencias."""
        return self._uno("""
            SELECT valor_busqueda, valor_competencia_presencialidad,
                   valor_competencia_virtualidad, valor_linkedin, valor_mercado
            FROM grafico_radar_datos
            WHERE proyecto_id=%s ORDER BY updated_at DESC LIMIT 1""", (self.proyecto_id,))


def proyectos_con_linkedin(url):
    """Proyectos de Tendencias con aptitudes o ubicaciones de LinkedIn (para elegir el más afín)."""
    import pandas as pd
    import tendencias_data

    with closing(tendencias_data._connect(url)) as conexion, conexion.cursor() as cursor:
        cursor.execute("""
            SELECT p.id, p.tipo_carpeta, p.carrera_referencia, p.carrera_estudio,
                   (SELECT COUNT(*) FROM linkedin_aptitudes a WHERE a.proyecto_id = p.id) AS aptitudes,
                   (SELECT COUNT(*) FROM linkedin_ubicaciones u WHERE u.proyecto_id = p.id) AS ubicaciones
            FROM proyectos_tendencias p ORDER BY p.id""")
        tabla = pd.DataFrame(cursor.fetchall(), columns=[c[0] for c in cursor.description])
    tabla = tabla[tabla["aptitudes"].gt(0) | tabla["ubicaciones"].gt(0)].reset_index(drop=True)
    return tabla.assign(filas_regionales=tabla["aptitudes"])


def recopilar(url, proyecto_id):
    """Todo lo que la presentación de Tendencias lee de LinkedIn e IA para un proyecto."""
    t = LinkedinTendencias(url, proyecto_id)
    region = t.region_local()
    homologados = {tipo: t.homologados(region, tipo)
                   for tipo in ("aptitudes", "habilidades", "cargos", "sectores")}
    cargos = ([(f["nombre_normalizado"], f["frecuencia_total"]) for f in homologados["cargos"]]
              or [(f["nombre"], f["profesionales"]) for f in (t.detalle(region, "cargos") or [])])
    return dict(
        proyecto_id=int(proyecto_id), carrera=t.carrera(), region=region,
        estudio=t.estudio(region),
        aptitudes=t.aptitudes(region, 5),
        aptitudes_region=t.aptitudes(region, None),
        homologados=homologados,
        competencias=t.aptitudes_formulario(),
        alineacion=t.resultado_ia(region, "alineacion") or {},
        naming=t.resultado_ia(region, "naming") or {},
        requisitos=t.detalle(region, "requisitos"),
        ubicaciones=t.ubicaciones_latam(),
        cargos=cargos,
        radar=t.radar(),
    )

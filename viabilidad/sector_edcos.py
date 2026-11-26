"""Puntuacion absoluta de sector para Educacion Continua con ventas SRI."""
import math
import re
from collections import defaultdict
import openpyxl


def puntaje_evolucion(tasa):
    if not math.isfinite(tasa):
        raise ValueError('La tasa debe ser finita.')
    return max(0.0, min(100.0, 50 + 250 * tasa))


def calcular_sector_sri(archivo, ciiu, anio=2026, mes_corte=8):
    normalizar = lambda v: re.sub(r'[^A-Z0-9]', '', str(v).upper())
    objetivo = normalizar(ciiu)
    if not re.fullmatch(r'[A-U]\d{6}', objetivo) or not 1 <= mes_corte <= 12:
        raise ValueError('CIIU o corte no valido.')
    datos = defaultdict(dict)
    libro = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
    try:
        for fila in libro['Ventas SRI'].iter_rows(min_row=2, values_only=True):
            codigo = normalizar(fila[0])
            if not re.fullmatch(objetivo[0] + r'\d{6}', codigo):
                continue
            year, month = int(fila[1]), int(fila[2])
            if year not in (anio-1, anio) or not 1 <= month <= mes_corte:
                continue
            clave = (year, month)
            if clave in datos[codigo]:
                raise ValueError('CIIU y mes duplicados.')
            celdas = fila[3:7]
            datos[codigo][clave] = None if len(celdas)!=4 or any(v is None for v in celdas) else sum(float(v) for v in celdas)
    finally:
        libro.close()
    esperados = {(y,m) for y in (anio-1,anio) for m in range(1,mes_corte+1)}
    completos = {c:d for c,d in datos.items() if set(d)==esperados and all(v is not None and math.isfinite(v) and v>=0 for v in d.values())}
    if objetivo not in completos:
        raise ValueError('El sector requiere ventas completas en ambos periodos.')
    totales = {c:sum(v for (y,m),v in d.items() if y==anio) for c,d in completos.items()}
    universo = [v for v in totales.values() if v>0]
    actual = totales[objetivo]
    anterior = sum(v for (y,m),v in completos[objetivo].items() if y==anio-1)
    if anterior<=0 or actual<=0 or len(universo)<2:
        raise ValueError('No hay base suficiente para calcular crecimiento y percentil.')
    # Rango medio de empates sobre N: posicion porcentual en el universo elegible.
    tamano = 100 * (sum(v<actual for v in universo) + .5*sum(v==actual for v in universo)) / len(universo)
    crecimiento = actual/anterior-1
    evolucion = puntaje_evolucion(crecimiento)
    return dict(puntaje=.4*tamano+.6*evolucion, tamano=tamano, evolucion=evolucion,
                crecimiento=crecimiento, ventas_actual=actual, ventas_anterior=anterior,
                anio=anio, mes_corte=mes_corte, ciiu=objetivo, seccion=objetivo[0],
                universo=len(universo), codigos_comparables=sorted(c for c,v in totales.items() if v>0),
                peso_tamano=40, peso_evolucion=60,
                metodo_percentil='100 * (actividades con ventas menores + 0,5 * actividades empatadas) / actividades elegibles')

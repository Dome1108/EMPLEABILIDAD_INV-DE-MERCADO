"""Extrae el CIIU exacto del Excel SRI aportado, sin mezclar períodos."""
from collections import defaultdict
from decimal import Decimal
import re
import openpyxl


def extraer_ventas_sri(archivo,ciiu):
    normalize=lambda value:re.sub(r'[^A-Z0-9]','',str(value).upper())
    target=normalize(ciiu)
    workbook=openpyxl.load_workbook(archivo,read_only=True,data_only=True)
    monthly=[]
    seen=set()
    try:
        sheet=workbook['Ventas SRI']
        for row in sheet.iter_rows(min_row=2,values_only=True):
            if normalize(row[0])!=target:
                continue
            year,month=int(row[1]),int(row[2])
            if not 1<=month<=12 or (year,month) in seen:
                raise ValueError('Mes inválido o registro duplicado del CIIU.')
            seen.add((year,month))
            values=[None if v is None else Decimal(str(v)) for v in row[3:7]]
            if len(values)!=4:raise ValueError('Faltan las cuatro columnas de ventas.')
            monthly.append(dict(anio=year,mes=month,ciiu=ciiu,**{k:None if v is None else float(v) for k,v in zip(['naturales_411','sociedades_411','naturales_413','sociedades_413'],values)}))
    finally:
        workbook.close()
    if not monthly:raise ValueError('CIIU exacto no encontrado en el Excel.')
    by_year=defaultdict(set)
    for r in monthly:by_year[r['anio']].add(r['mes'])
    common=set.intersection(*by_year.values())
    if not common or common!=set(range(1,max(common)+1)):
        raise ValueError('Los años no tienen meses consecutivos comparables desde enero.')
    def summarize(months):
        result=[]
        for year,available in sorted(by_year.items()):
            if not months<=available:continue
            selected=[r for r in monthly if r['anio']==year and r['mes'] in months]
            def total(keys):
                cells=[r[k] for r in selected for k in keys]
                return None if any(v is None for v in cells) else float(sum((Decimal(str(v)) for v in cells),Decimal(0)))
            result.append(dict(anio=year,meses=len(months),ciiu=ciiu,naturales=total(['naturales_411','naturales_413']),sociedades=total(['sociedades_411','sociedades_413']),fuente='sri_excel'))
        return result
    return dict(mensual=sorted(monthly,key=lambda r:(r['anio'],r['mes'])),ventas=summarize(common),ventas_anuales=summarize(set(range(1,13))),mes_corte=max(common))

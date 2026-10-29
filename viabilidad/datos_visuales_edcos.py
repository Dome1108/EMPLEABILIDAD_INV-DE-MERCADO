"""Importación de evidencia para gráficos; independiente de la rúbrica."""
from datetime import date
import pandas as pd

PLANTILLAS={
    'demanda':['fecha','termino','indice','territorio','consulta','fuente'],
    'competencia':['programa','busquedas','competidores','territorio','consulta','fuente'],
    'sector':['anio','naturales','sociedades','ciiu','meses','fuente'],
}


def leer_evidencia(archivo,dimension,ciiu):
    table=pd.read_csv(archivo,dtype=str,keep_default_na=False)
    required=PLANTILLAS[dimension]
    if not set(required)<=set(table.columns) or table.empty:
        raise ValueError('Se necesitan registros y las columnas de la plantilla.')
    table=table[required].copy()
    if table.apply(lambda col:col.str.strip().eq('')).any().any():
        raise ValueError('Cada registro debe identificar sus valores, contexto y fuente.')
    keys={'demanda':['fecha','termino'],'competencia':['programa'],'sector':['anio']}[dimension]
    if table.duplicated(keys).any():
        raise ValueError('Hay registros duplicados para el mismo período o programa.')
    for col in ['territorio','consulta'] if dimension!='sector' else ['ciiu','meses']:
        if table[col].nunique()!=1:
            raise ValueError('Los registros deben compartir territorio y consulta o CIIU y meses comparables.')
    numeric={'demanda':['indice'],'competencia':['busquedas','competidores'],'sector':['anio','naturales','sociedades','meses']}[dimension]
    for col in numeric:
        table[col]=pd.to_numeric(table[col],errors='raise')
        if not table[col].map(lambda n:pd.notna(n) and 0<=n<float('inf')).all():
            raise ValueError('Los valores deben ser finitos y no negativos.')
    if dimension=='demanda':
        table['fecha']=pd.to_datetime(table['fecha'],format='%Y-%m-%d',errors='raise')
        if (table['fecha'].dt.day!=1).any() or table.duplicated(['fecha','termino']).any():
            raise ValueError('Usa el primer día de cada mes, sin duplicados.')
        counts=table.groupby('termino')['fecha'].apply(lambda values:set(values))
        if any(values!=counts.iloc[0] for values in counts):
            raise ValueError('Los términos deben tener los mismos meses observados.')
        table['fecha']=table['fecha'].dt.strftime('%Y-%m-%d')
        if (table['indice']>100).any():raise ValueError('El índice de Trends debe estar entre 0 y 100.')
        return 'serie',table.to_dict('records')
    if dimension=='competencia':
        if (table['busquedas']>100).any() or (table['competidores']%1!=0).any():
            raise ValueError('Búsquedas debe estar entre 0 y 100 y competidores debe ser entero.')
        return 'matriz',table.to_dict('records')
    if table['ciiu'].iloc[0]!=ciiu:
        raise ValueError('El CIIU debe coincidir con la actividad declarada del programa.')
    if (table['anio']%1!=0).any() or (table['meses']%1!=0).any() or not table['meses'].between(1,12).all():
        raise ValueError('Años enteros y meses acumulados entre 1 y 12.')
    today=date.today()
    if ((table['anio']>today.year)|((table['anio']==today.year)&(table['meses']>=today.month))).any():
        raise ValueError('Solo se admiten períodos cerrados; el año actual no está completo.')
    return 'ventas',table.sort_values('anio').to_dict('records')

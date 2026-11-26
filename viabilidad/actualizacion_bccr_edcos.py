"""Descarga anónima y lectura del IMAE vigente publicado por el BCCR.

No necesita cuenta ni credenciales. El token CSRF sólo vive en la sesión HTTP.
Se conserva la respuesta original para auditar la extracción.
"""
import json
import math
import re
from pathlib import Path

BASE=Path(__file__).parent
API='https://apim.bccr.fi.cr/SDDE/api/Bccr.GE.SDDE.IndicadoresSitioExterno.'
URL='https://sdd.bccr.fi.cr/es/IndicadoresEconomicos/Inicio/Contenedor/1581?Cuadro=939'
ARCHIVO=BASE/'edcos_fuentes/bccr_imae_grupo_939.json'
MESES={name:i for i,name in enumerate(['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'],1)}
MESES['setiembre']=9


def extraer_serie(documento,indicador,desde='2023-01-01'):
    info=documento['informacionDelCuadro']
    if info['codGrupoVariablePublicado']!=939 or '2022=100' not in info['subTituloEspanol'].replace(' ',''):
        raise ValueError('Se requiere el grupo 939 de la serie original base 2022=100.')
    nivel=next(r for r in documento['indicadoresRaiz'] if r['nombreEspanol']=='Nivel')
    row=next(r for r in nivel['indicadores'] if r['idIndicador']==indicador)
    records=[]
    for col in documento['columnas']:
        if not re.fullmatch(r'serie\d+',col['field']):continue
        month,year=(p.strip().lower() for p in col['tituloEspanol'].split('/'))
        fecha=f'{int(year):04}-{MESES[month]:02}-01'
        if fecha<desde:continue
        value=row['series'].get(col['field'])
        if value in (None,'','n.d.','-'):continue
        numero=float(value) if isinstance(value,(int,float)) and not isinstance(value,bool) else float(str(value).replace('.','').replace(',','.'))
        if not math.isfinite(numero):raise ValueError('Observación IMAE no finita.')
        records.append(dict(fecha=fecha,valor=numero,fuente='bccr_imae'))
    records.sort(key=lambda r:r['fecha'])
    if not records or len({r['fecha'] for r in records})!=len(records):
        raise ValueError('Serie vacía o con fechas duplicadas.')
    return dict(actividad=row['nombreEspanol'],base=2022,serie_indice=records,periodo_hasta=records[-1]['fecha'],indicador=indicador,url=URL)


def descargar(fecha_corte):
    import requests
    session=requests.Session()
    session.trust_env=False
    session.headers.update({'User-Agent':'Mozilla/5.0','Origin':'https://sdd.bccr.fi.cr','Referer':'https://sdd.bccr.fi.cr/'})
    token=session.get(API+'ServiciosUsuario.API/Token/GenereCSRF',timeout=30)
    token.raise_for_status()
    session.headers['Token_CSRF']=token.text.strip('"')
    response=session.get(API+'GrupoVariables.API/CuadroGrupoVariables/ObtenerDatosCuadro',params=dict(IdGrupoVariable=939,FechaInicio='2023-01-01',FechaFin=fecha_corte,CantidadSeriesAMostrar=48),timeout=30)
    response.raise_for_status()
    data=response.json()
    for indicador in (94984,94986):extraer_serie(data,indicador)
    ARCHIVO.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def cargar_sector(people):
    data=json.loads(ARCHIVO.read_text(encoding='utf-8'))
    return extraer_serie(data,94984 if people else 94986)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--fecha-corte',required=True,help='Fecha de consulta AAAA-MM-DD')
    args=parser.parse_args()
    descargar(args.fecha_corte)
    for people in (False,True):
        row=cargar_sector(people)
        print(row['actividad']+': '+row['periodo_hasta']+' · '+str(len(row['serie_indice']))+' meses')

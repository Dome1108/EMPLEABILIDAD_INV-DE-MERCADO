"""Viabilidad EdCo independiente del comparativo de carreras."""
import json
import math
from pathlib import Path
from modelo import BLOQUES

INSTITUCIONES_EDCO={
    'udla_ec':{'nombre':'UDLA','pais':'Ecuador','etiqueta':'UDLA · Ecuador'},
    'ulatina_cr':{'nombre':'ULatina','pais':'Costa Rica','etiqueta':'ULatina · Costa Rica'},
}


def programas_institucion(fichas,institucion_id):
    if institucion_id not in INSTITUCIONES_EDCO:
        raise ValueError('Institución no reconocida.')
    return [f for f in fichas if f.get('institucion_id')==institucion_id]

DIMENSIONES_EDCO=[
    ('demanda',BLOQUES[0],30),
    ('empleabilidad',BLOQUES[1],22),
    ('competencia',BLOQUES[2],28),
    ('precio',BLOQUES[3],12),
    ('sector',BLOQUES[4],8),
]

def cargar_edcos():
    folder=Path(__file__).with_name('edcos_data')
    return [json.loads(p.read_text(encoding='utf-8')) for p in sorted(folder.glob('*.json'))]

def evaluar_edco(ficha):
    filas=[]
    for key,label,weight in DIMENSIONES_EDCO:
        criterion=ficha['evaluacion'][key]
        score=criterion.get('puntaje')
        if score is not None:
            if isinstance(score,bool) or not isinstance(score,(int,float)) or not math.isfinite(score) or not 0<=score<=100:
                raise ValueError(f'Puntaje no válido en {label}.')
            if not criterion.get('justificacion') or not criterion.get('fuentes'):
                raise ValueError(f'{label} necesita justificación y fuente para recibir puntaje.')
        filas.append(dict(id=key,dimension=label,peso=weight,puntaje=score,aporte=None if score is None else score*weight/100))
    coverage=sum(r['peso'] for r in filas if r['puntaje'] is not None)
    complete=all(r['puntaje'] is not None for r in filas)
    total=sum(r['aporte'] for r in filas) if complete else None
    status='En evaluación' if total is None else 'Viabilidad favorable' if total>=75 else 'Viabilidad condicionada' if total>=55 else 'Viabilidad desfavorable'
    return dict(filas=filas,cobertura=coverage,evaluados=sum(r['puntaje'] is not None for r in filas),total=total,estado=status)

def validar_ficha(ficha):
    """Rechaza fuentes inexistentes y mezcla de oferta propia con competencia."""
    if ficha.get('institucion_id') not in INSTITUCIONES_EDCO:
        raise ValueError('La ficha debe indicar UDLA Ecuador o ULatina Costa Rica.')
    if ficha['brief'].get('pais')!=INSTITUCIONES_EDCO[ficha['institucion_id']]['pais']:
        raise ValueError('El país del brief debe corresponder a la institución seleccionada.')
    if set(ficha['evaluacion'])!={row[0] for row in DIMENSIONES_EDCO}:
        raise ValueError('La ficha debe usar las cinco dimensiones del pentágono.')
    source_ids={s['id'] for s in ficha['fuentes']}
    for criterion in ficha['evaluacion'].values():
        if not set(criterion.get('fuentes',[]))<=source_ids:
            raise ValueError('La evaluación referencia una fuente no registrada.')
    for item in ficha['ofertas']:
        if item['tipo']=='Oferta propia' and item.get('competidor_directo'):
            raise ValueError('La oferta propia no debe contarse como competidor externo.')
    return evaluar_edco(ficha)

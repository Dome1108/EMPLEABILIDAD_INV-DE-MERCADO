"""Regla de tres ponderada: cada variable aporta como máximo su peso."""
from dataclasses import dataclass, field
import json
from pathlib import Path

BLOQUES = ['Demanda e interés', 'Empleabilidad y valor', 'Competencia', 'Precio frente al mercado', 'Sector económico']
PESOS_VARIABLES = [6.3, 4.2, 13.65, 5.85, 9.9, 5.5, 28, 12, 8, 6.6]
VARIABLES = ['Crecimiento de matriculados', 'Crecimiento de titulados', 'Búsquedas del programa', 'Evaluación del nombre', 'Alineación con el mercado laboral (mayor es mejor)', 'Salario del campo', 'Competencia (menos es mejor)', 'Precio frente a la media', 'Ventas de sectores vinculados', 'Cantidad de profesionales del campo']

@dataclass
class Config:
    pesos: list = field(default_factory=lambda: [30,22,28,12,8])
    umbral_busquedas: float = 75
    umbral_competidores: float | None = None
    nivel: str = 'Pregrado'

    def __post_init__(self):
        if self.nivel not in ['Pregrado','Posgrado']:
            raise ValueError('El nivel debe ser Pregrado o Posgrado.')
        if self.umbral_competidores is None:
            self.umbral_competidores=5 if self.nivel=='Pregrado' else 3

def cargar_datos():
    return json.loads(Path(__file__).with_name('datos.json').read_text(encoding='utf-8'))

def limitar(x):
    return max(0.0,min(100.0,x))

def relativo(x, referencia):
    if referencia <= 0:
        raise ValueError('La referencia debe ser mayor que cero.')
    return max(0.0,100*x/referencia)

def precio(brecha):
    """Rango [-15%,+10%]; -25% y +25% equivalen a 50 puntos."""
    return limitar(100-500*max(0,-.15-brecha)-(50/.15)*max(0,brecha-.10))

def cuadrante(busquedas_indice, competidores, config):
    alta=busquedas_indice>=config.umbral_busquedas
    baja=competidores<=config.umbral_competidores
    if alta and baja:
        return 'Mercado atractivo'
    if alta:
        return 'Mercado competido'
    if baja:
        return 'Baja tracción'
    return 'Mercado débil'

def evaluar(carrera, referencia, config=None):
    cfg=config or Config()
    if abs(sum(cfg.pesos)-100)>1e-8 or any(v<0 for v in cfg.pesos):
        raise ValueError('Los pesos deben sumar 100%.')
    if not 0<cfg.umbral_busquedas<100 or cfg.umbral_competidores<=0:
        raise ValueError('Revisa los umbrales del cuadrante.')
    for a in [carrera,referencia]:
        if a.get('profesionales') is None or a['profesionales']<0:
            raise ValueError('Cantidad de profesionales debe ser un dato no negativo.')
        if a['competidores']<0:
            raise ValueError('Competidores no puede ser negativo.')
        if min(a['matriculados'],a['titulados']) < -1:
            raise ValueError('Una tasa de crecimiento no puede ser inferior a -100%.')
    sales=carrera['ventas_naturales']+carrera['ventas_sociedades']
    basesales=referencia['ventas_naturales']+referencia['ventas_sociedades']
    indices=[
        relativo(1+carrera['matriculados'],1+referencia['matriculados']),
        relativo(1+carrera['titulados'],1+referencia['titulados']),
        relativo(carrera['busquedas'],referencia['busquedas']),
        relativo(carrera['nombre'],referencia['nombre']),
        relativo(carrera['alineacion'],referencia['alineacion']),
        relativo(carrera['salario'],referencia['salario']),
    ]
    quadrant=cuadrante(indices[2],carrera['competidores'],cfg)
    # Regla absoluta: hasta el límite, aporte completo; luego penalización inversa.
    competition=100 if carrera['competidores']<=cfg.umbral_competidores else relativo(cfg.umbral_competidores,carrera['competidores'])
    indices += [competition,precio(carrera['brecha_precio']),relativo(sales,basesales),relativo(carrera['profesionales'],referencia['profesionales'])]
    indices_sin_tope=indices.copy()
    indices=[limitar(value) for value in indices]
    es_referencia=carrera['carrera']==referencia['carrera']
    if es_referencia:
        # Ancla del comparativo por definición, incluida competencia y precio.
        indices=[100.0]*len(indices)
    blocks=[.65*(.7*indices[2]+.3*indices[3])+.35*(.6*indices[0]+.4*indices[1]), .3*indices[9]+.45*indices[4]+.25*indices[5],indices[6],indices[7],indices[8]]
    total_sin_tope=sum(v*p/100 for v,p in zip(blocks,cfg.pesos))
    total=limitar(total_sin_tope)
    label='Carrera de referencia' if es_referencia else 'Puntaje máximo' if total>=100 else 'Puntaje alto' if total>=90 else 'Resultado intermedio' if total>=75 else 'Requiere ajustes' if total>=60 else 'Puntaje bajo'
    return dict(carrera=carrera['carrera'],es_referencia=es_referencia,bloques=blocks,indices=indices,indices_sin_tope=indices_sin_tope,total=total,total_sin_tope=total_sin_tope,clasificacion=label,cuadrante=quadrant,busquedas=indices_sin_tope[2],busquedas_sin_tope=indices_sin_tope[2],competidores=carrera['competidores'],brecha_precio=carrera['brecha_precio'])

def recomendaciones(carrera, resultado, config):
    demand,employ,competition,cost,sector=resultado['bloques']
    rec=[]
    rec.append(('Demanda e interés','Priorizar la validación de interesados y su conversión a matrícula.' if resultado['busquedas']>=config.umbral_busquedas else 'Validar el interés con prospectos antes de dimensionar la apertura.'))
    rec.append(('Empleabilidad y valor','Revisar el tamaño del campo, la alineación de competencias y el valor salarial frente a la referencia.' if employ<75 else 'Sustentar la propuesta con el tamaño del campo profesional, las competencias demandadas y su remuneración.'))
    texts={'Mercado atractivo':'Priorizar la validación de esta oportunidad y avanzar si los demás componentes son favorables.', 'Mercado competido':'Definir una diferenciación concreta antes de entrar al mercado.', 'Baja tracción':'Validar la demanda con el público objetivo antes de avanzar.', 'Mercado débil':'Revisar el público objetivo y la propuesta de valor antes de avanzar.'}
    rec.append(('Competencia y posición de mercado',texts[resultado['cuadrante']]))
    gap=carrera['brecha_precio']
    price_advice='Mantener un precio coherente con el posicionamiento y la propuesta de valor.' if -.15<=gap<=.10 else 'Revisar el precio para acercarlo al rango aceptable frente a la media del mercado.'
    if resultado['cuadrante']=='Baja tracción':
        price_advice+=' La poca oferta acompañada de una baja demanda no garantiza una oportunidad.'
    rec.append(('Precio frente al mercado',price_advice))
    rec.append(('Sector económico','Dimensionar la apertura de forma prudente, considerando el tamaño del sector vinculado al programa.'))
    return rec

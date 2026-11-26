"""Índices (base 0) de ``presentaciones/plantillas/Plantilla mercado.pptx``.

Copia de la plantilla de Investigación de Mercados del proyecto Tendencias
(27 diapositivas, noviembre 2026). Se entregan las 27, como en Tendencias. Si la plantilla cambia, se ajusta solo este
archivo. El generador valida los textos clave de cada diapositiva antes de usarla.
"""

TOTAL_DIAPOSITIVAS = 27

PORTADA = 0              # 1  ‘Nombre del programa propuesto’
FILTROS = 1              # 2  «Propuesta» de Tendencias → filtros aplicados del observatorio
SECCION_DEMANDA = 2      # 3  DEMANDA E INTERÉS ACADÉMICO
MATRICULADOS = 3         # 4
TITULADOS = 4            # 5
INSTITUCIONES = 5        # 6  Instituciones educativas
GOOGLE_TRENDS = 6        # 7
SECCION_EMPLEO = 8       # 9  OFERTA DE VALOR-EMPLEABILIDAD
APTITUDES = 9            # 10 Aptitudes LinkedIn (proyecto Tendencias)
HABILIDADES = 10         # 11 Habilidades solicitadas en anuncios (proyecto Tendencias)
UBICACION = 11           # 12 Mapa LATAM de profesionales (proyecto Tendencias)
EMPLEABILIDAD = 12       # 13 Tarjetas, composición y banda salarial
EMPRESAS_SECTORES = 13   # 14
DEMANDA = None           # La plantilla ya no tiene la diapositiva de vacantes (igual que Tendencias)
SECCION_PRECIOS = 15     # 16 POSICIONAMIENTO, COMPETENCIA Y PRECIOS
PRECIOS = 16             # 17 Oferta académica
CUADRANTE = 17           # 18 Demanda vs. competencia («Viabilidad de carreras»)
NAMING = 18              # 19 Alternativas de nombre (IA del proyecto Tendencias)
SECCION_SECTOR = 20      # 21 SECTOR ECONÓMICO
SRI = 21                 # 22 Comportamiento financiero
METODO = 22              # 23 Cómo se evalúa la viabilidad
RESUMEN_RESULTADOS = 23  # 24 Resultado de viabilidad + radar
CONCLUSIONES = 26        # 27 Conclusión final

# «Avances / Next Steps» (7, 14, 19, 24 y 25 en base 0) se conservan sin cambios, como en
# la presentación de Tendencias. Ya no se quita ninguna diapositiva: salen las 27.
NEXT_STEPS = (7, 14, 19, 24, 25)

# Texto que debe aparecer en cada diapositiva usada (sin tildes, en minúsculas).
TEXTOS_CLAVE = {
    FILTROS: "datos de solicitud",
    SECCION_DEMANDA: "demanda e interes academico",
    MATRICULADOS: "la matricula",
    TITULADOS: "evolucion de titulados",
    GOOGLE_TRENDS: "busquedas web",
    SECCION_EMPLEO: "oferta de valor-empleabilidad",
    EMPLEABILIDAD: "banda salarial",
    EMPRESAS_SECTORES: "empresas y sectores",
    SECCION_PRECIOS: "posicionamiento, competencia y precios",
    PRECIOS: "comparacion de aranceles",
    APTITUDES: "fuente: linkedin",
    CUADRANTE: "cuadrante",
    NAMING: "presenta la mayor valoracion",
    SECCION_SECTOR: "sector economico",
    METODO: "analisis de tendencias para programas",
    RESUMEN_RESULTADOS: "recomendaciones",
    SRI: "comportamiento financiero",
    CONCLUSIONES: "conclusion final",
}


def es_plantilla_mercado(prs):
    return len(prs.slides) == TOTAL_DIAPOSITIVAS


# Espacio (izquierda, arriba, ancho, alto) en pulgadas que ocupa cada gráfico.
# Los gráficos se dibujan con este mismo tamaño para que las letras se vean
# en su tamaño real en la diapositiva (sin reducirse al insertarlos).
CAJA_SRI = (0.60, 1.25, 11.75, 3.92)     # Diapositiva 22, encima del texto
CAJA_MAPA = (0.40, 1.50, 6.30, 4.75)     # Diapositiva 12, a la izquierda del texto

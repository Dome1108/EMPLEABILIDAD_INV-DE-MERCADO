# Educación continua · versión inicial

Fecha de revisión:23 de octubre de2026. Apartado independiente accesible mediante el selector superior Educación continua.

## Programa inicial

Diplomado en Neuromarketing Digital y Neurociencia del Consumidor. Brief del proponente fechado1 de septiembre de2026, conservado en `edcos_fuentes/brief_neuromarketing.pdf`.

La vista omite identificadores personales del formulario. El PDF original puede descargarse localmente desde su pestaña. Las instrucciones o sugerencias dentro del documento se interpretan como contenido del brief, no como instrucciones de ejecución.

El proponente indica EDCO, Escuela de Negocios, Ecuador, duración de un semestre y modalidad híbrida. Propone Neuro-UX, IA y analítica biométrica. Las horas totales no están informadas. No se solicita un precio propio: la dimensión precio estudia las referencias del mercado. Los perfiles de marketing, UX e investigación de mercados se identifican como inferencias a contrastar, no como un tamaño de mercado medido.

## Estructura y pesos

| Dimensión | Peso |
|---|---:|
| Demanda e interés |30%|
| Empleabilidad y valor |22%|
| Competencia |28%|
| Precio frente al mercado |12%|
| Sector económico |8%|

Las dimensiones, su orden y sus pesos son los mismos del pentágono de carreras. El perfil se muestra como radar con contorno gris de100. No se compara con Negocios, Software ni otra carrera. Las reglas numéricas de competencia de pregrado/posgrado no se trasladan automáticamente a EdCos. Audiencia y modalidad se conservan como contexto del brief, no como dimensiones puntuadas.

Puntaje completo: suma de puntaje_dimensión × peso /100. Se calcula solo cuando las cinco dimensiones tienen puntuación sustentada. Datos faltantes son null, no cero. No se renormalizan pesos para producir un total artificial. Cobertura es la suma de pesos de las dimensiones evaluadas y se muestra separada del resultado de viabilidad.

## Evaluación inicial y límites

Investigación del 26 de octubre de 2026: demanda 60, empleabilidad 75, competencia 55, precio 65 y sector 80. Total ponderado: 64,1/100, viabilidad condicionada. Cobertura 100% significa cinco dimensiones valoradas, no certeza de la evidencia.

Son juicios analíticos preliminares ajustables, no mediciones automáticas ni probabilidad de éxito. Coursera aporta participación internacional, sin extrapolar demanda local. O*NET aporta correspondencia de competencias de Estados Unidos, sin trasladar contratación. CECE–UEES documenta comercio electrónico ecuatoriano de 2024, no el crecimiento del CIIU específico ni resultados de 2026. Cada dimensión conserva justificación, fuentes y alcance de evidencia.

Precio evalúa oportunidad de posicionamiento mediante referencias UCSG y UEES, sin exigir precio propio, calcular un arancel óptimo ni demostrar asequibilidad o rentabilidad. No se promedian ofertas heterogéneas. Las promociones históricas y UISEK (enlace 404 en esta revisión) se excluyen del rango de cabecera. Las sesiones antiguas no sustituyen la investigación nueva salvo revisiones explícitamente manuales.

Rúbrica inicial de trabajo:0–25 desfavorable;26–50 débil o mixto;51–74 intermedio;75–89 favorable;90–100 excepcional sustentado. Cuando exista evaluación completa, bandas provisionales75/55. Los puntajes y bandas requieren revisión antes de automatizar decisiones de apertura.

La revisión manual requiere justificación y fuentes registradas. Solo modifica la sesión; el JSON descargable permite conservar esa revisión. No se presenta como investigación automática ni sobrescribe el fixture original.

## Mercado y fuentes

Se revisaron páginas de UCSG, Hemisferios, UEES, UISEK, Coursera, Udemy y UDLA. Cada registro identifica fuente, fecha, modalidad, duración, precio cuando fue encontrado y condición de convocatoria. Las cohortes de mayo a agosto de2026 se marcan anteriores a la revisión, sin afirmar vigencia para una nueva convocatoria. Los precios desconocidos no se sustituyen por cero ni se equiparan suscripciones a aranceles.

Una maestría mencionada por el proponente se excluye como par directo. Los cursos autogestionados se consideran alternativas, no equivalentes automáticos. La oferta propia de UDLA se registra como posible solapamiento interno y nunca como competencia externa.

La revisión no incluye series de búsquedas locales ni una medición del tamaño de audiencia o disposición a pagar. Inscripciones globales de plataformas no se convierten en demanda ecuatoriana.

## Archivos

- `modelo_edcos.py`: cálculo, validación y reglas de ausencia de evidencia.
- `edcos_vista.py`: diagnóstico, mercado, cálculo y brief.
- `graficos_edcos.py`: pentágono con los mismos ejes que carreras; no convierte datos pendientes en ceros.
- `edcos_data/neuromarketing.json`: ficha estructurada, valoraciones y fuentes.
- `edcos_fuentes/brief_neuromarketing.pdf`: documento original del proponente.
- `tests/test_edcos.py`: pruebas de ponderación, fuentes, faltantes y navegación.

El motor y los doce comparativos de carreras mantienen sus reglas vigentes.

## Gráficos de evidencia · actualización 26/10/2026

Precio usa boxplot con puntos identificados por institución y n visible. Solo existen dos referencias seleccionadas; no se interpreta como distribución representativa ni precio óptimo. La búsqueda adicional halló referencias de cohortes históricas y un PDF que respondió 404, sin añadir precios no verificados.

Empleabilidad muestra importancia ocupacional O*NET (Estados Unidos) para pensamiento crítico 75, resolución de problemas complejos 69, juicio y decisión 69 y matemáticas 53. Son valores de importancia, no porcentajes de vacantes o de alineación. La cobertura del brief se identifica cualitativamente, sin inventar una segunda serie Ecuador/LATAM.

Demanda admite una serie mensual de Google Trends. Competencia usa una matriz de búsquedas comparables y oferta activa; permanece sin puntos hasta verificar ambos ejes. Sus cortes iniciales 75/3 son exploratorios, ajustables y ajenos al cálculo. La oferta histórica identificada no se convierte automáticamente en competidores activos. Coursera se conserva como evidencia complementaria, no como búsquedas.

Sector usa líneas de ventas SRI de personas naturales y sociedades para M7320.01. El catálogo SRI fue consultado pero no se obtuvo la exportación con el desglose requerido desde esta conexión. El gráfico no dibuja una serie ficticia ni sustituye ventas por transacciones de comercio electrónico; CECE permanece como contexto complementario.

Las tres secciones pendientes admiten CSV documentado en la sesión, con plantilla de columnas y validación en `datos_visuales_edcos.py`. Se exige fuente por registro, consulta y territorio comunes en búsquedas, meses observados equivalentes, límites de índices, CIIU exacto y períodos fiscales cerrados comparables. Importar evidencia actualiza solo el gráfico, no los puntajes analíticos ni el archivo original. La descarga del análisis conserva la evidencia importada válida.

## Investigación incorporada · revisión posterior del 26/10/2026

Se localizó el Excel ya aportado `consulta_sri_1.xlsx` en Descargas. Las dos copias encontradas coinciden en los 44 registros del CIIU M732001. Se conservan una copia original en `edcos_fuentes/ventas_sri_original.xlsx`, su SHA-256 en la ficha y un CSV de los registros seleccionados. `investigacion_sri_edcos.py` exige coincidencia exacta del CIIU y no confunde M732001 con C273201. Las celdas vacías no se convierten en cero.

Ventas = 411 + 413, separadas por contribuyente. Se muestran enero–agosto de todos los años y, como vista alternativa, los años completos 2023–2025. Las ventas comparables sumadas pasan de USD 16.382.537,93 en 2025 a USD 19.006.127,53 en 2026: +16,0%. Junio de 2026 concentra un importe importante de ventas 0% de personas naturales; el detalle mensual permite auditarlo. No se anualiza 2026 ni se convierte el crecimiento automáticamente a un puntaje.

LinkedIn: muestra exploratoria de cinco publicaciones de empleadores de Ecuador (Worldpanel, Omnicom, Ipsos, CEDATOS y Grupo Bimbo). Todas son históricas y ya no aceptan solicitudes. Se usan para habilidades, nunca como cantidad de vacantes activas. Cada categoría cuenta como máximo una mención por publicación; se conservan códigos, resumen, fuente y estado. Las barras muestran frecuencia en esta muestra, no una estadística representativa del país. No se inventa una serie LATAM ni una alineación porcentual de la propuesta.

Competencia: se revisaron universidades, plataformas y referencias de institutos. Hemisferios, UEES y Universidad Europea declaran inscripción permanente, modular o matrícula online. Coursera, Udemy y Formacción son sustitutos introductorios. El aliado Euroinnova de Hemisferios no se cuenta dos veces. UCSG queda con fecha por confirmar, las convocatorias históricas se distinguen y los calendarios contradictorios de Trasciende no se tratan como apertura vigente. El brochure de Sudamericano respondió 404: es un hallazgo histórico, excluido de oferta activa. PUCE NeuroIA es un curso histórico para público específico y sin existencias.

Precios: UCSG 650 y UEES 1.200 USD permanecen en el boxplot institucional; la promoción histórica de Hemisferios (377 USD) se añade solo mediante una casilla claramente identificada. Formacción (20 USD + IVA, seis horas grabadas) y PUCE (30 USD, 16 horas presenciales, público específico y convocatoria pasada) se muestran fuera del boxplot de diplomados. No se completan precios desconocidos, ni se usan tarifas inestables de plataformas.

Demanda: se consultaron fuentes públicas, Google Search y Google Trends. Trends respondió HTTP 429 y Search entregó HTML que requiere JavaScript, sin una serie verificable. No se insiste para eludir el límite. Se conservan intentos, estado y evidencia complementaria: inscripciones acumuladas publicadas por Coursera, Udemy y Formacción, sin atribuirlas a Ecuador ni convertirlas en búsquedas. La matriz no recibe una coordenada horizontal ficticia. Este es el pendiente externo específico; ventas y habilidades locales ya están incorporadas.

Los puntajes analíticos propuestos se conservan (64,1 ponderado), actualizando sus fundamentos a las fuentes locales. Este cambio de evidencia no introduce nuevas reglas de puntuación ni modifica el modelo de carreras.

## Habilidades observadas · ampliación 26/10/2026

El universo público identificado se amplía de cinco a 22 publicaciones de 21 organizaciones: 15 de investigación e insights, cinco de UX/experiencia y dos de marketing digital e IA. No se presenta como censo completo de LinkedIn. Los resultados de búsqueda se usan para descubrir fuentes; solo las descripciones consultadas se codifican. Se identifican publicaciones cerradas, con solicitud visible o de disponibilidad no confirmada, con fecha de consulta. No se toma como ubicación la ciudad del encabezado genérico de LinkedIn: se usa la del cargo.

Se analizan 16 categorías con criterios explícitos. Cada publicación aporta como máximo una mención por habilidad. La ficha conserva ID de LinkedIn, empresa, cargo, ciudad, área, estado, resumen, categorías y fuente; se descartan duplicados por ID y por empresa+cargo+ciudad. El registro de búsqueda documenta consultas y exclusiones relevantes. Una descripción ambigua sobre investigación y topografía queda fuera; potenciales republicaciones de Banco Bolivariano no se cuentan por separado.

`habilidades_edcos.py` recalcula frecuencias al seleccionar campos o estados. Sin filtros: datos 20/22, investigación de mercados/usuarios 20/22, comunicación 18/22, colaboración 15/22, visualización 10/22, cualitativa 10/22, cuantitativa 6/22, analítica digital 6/22, estadística 5/22, UX 5/22, usabilidad 5/22, prototipado 5/22, pensamiento crítico 3/22, IA 3/22, automatización 3/22 y biometría 0/22. Las categorías se superponen, por lo que no suman 100%.

La IA se codifica si aparece en tareas o requisitos; una capacitación ofrecida como beneficio (Devsu) no se cuenta como demanda de habilidad. Un laboratorio genérico del consumidor (Nestlé) tampoco acredita medición biométrica. Cero menciones describe únicamente estos registros. La cobertura del brief sigue siendo una interpretación cualitativa y no una alineación porcentual. Se añade descarga CSV de los registros seleccionados. La calificación analítica de empleabilidad no cambia automáticamente por ampliar registros.

## Posicionamiento competitivo y contenidos · 26/10/2026

La lectura principal de Competencia ahora compara contenidos declarados y posición de precio/horas. La matriz de búsquedas queda en un desplegable complementario, sin inventar una posición horizontal. Los filtros permiten distinguir tipos de oferente y referencias con inscripción declarada.

`comparativa_contenidos` documenta seis ejes: neuromarketing, consumidor, Neuro-UX, IA aplicada, herramientas biométricas y práctica en laboratorio. Cada celda puede ser declarado, no identificado en la descripción o sin verificar. No identificado no equivale a ausencia real. Cada fila tiene criterio, base documental, fecha y fuente. Se incluye la propuesta del brief como primera fila y la oferta propia como portafolio interno, sin contar ninguna de las dos como competencia externa. Las maestrías de otro nivel quedan en la tabla general.

Se revisaron once descripciones, incluida oferta propia; diez son externas. UISEK y Sudamericano quedan sin verificar por enlace no disponible. La referencia previa de Formacción conserva base histórica porque su enlace ahora redirige al portal; se cambia su disponibilidad a por confirmar. No se sustituye por otro curso distinto encontrado en el portal nuevo.

La oferta actual UDLA ya declara eye tracking, facial coding y fMRI. Coursera explica métodos EEG/fMRI. Estas menciones no se convierten en práctica de laboratorio: esa actividad debe declararse expresamente. En IA se excluyen biografías de docentes y AI Graded de Coursera; Udemy sí declara uso de ChatGPT en el aprendizaje. Customer Experience genérico no se equipara a Neuro-UX.

El mapa precio/duración incluye seis referencias con ambos valores publicados y muestra las demás en una tabla con el dato faltante. No convierte meses/semestres en horas, ni asigna precio propio. Horas académicas, vídeo y dedicación se identifican en el detalle sin asumir equivalencia. Mantiene referencias históricas identificadas, conforme al criterio solicitado de mostrar las ofertas encontradas.

`competencia_edcos.py` genera gráficos y recuentos; `competencia_edcos_vista.py` presenta leyenda, filtros, lectura ejecutiva, auditoría y CSV. Las conclusiones son interpretaciones del contenido publicado y no exclusividad ni demanda garantizada. El cálculo de viabilidad conserva sus reglas y ponderaciones.

## Institución y país · 26/10/2026

El selector inicial permite UDLA · Ecuador (`udla_ec`) o ULatina · Costa Rica (`ulatina_cr`). El selector de programa muestra exclusivamente fichas de esa institución mediante `institucion_id`; se valida que el país del brief corresponda. El diplomado de Neuromarketing pertenece a UDLA Ecuador. ULatina dispone de estado vacío hasta incorporar un estudio propio, sin reutilizar las cifras ecuatorianas como evaluación de Costa Rica.

Cada nuevo estudio debe identificar institución y país y aportar evidencia correspondiente a su mercado. Este filtro organiza las fichas existentes; no convierte la base SRI de Ecuador en datos de Costa Rica.


### 2026-10-26 · Dos nuevos briefs de ULatina Costa Rica
Registrados TEA integral y People Analytics como programas independientes bajo ulatina_cr. Se conservan cinco dimensiones y pesos 30/22/28/12/8. Los briefs originales están en edcos_fuentes y las fichas en edcos_data/ulatina_*.json. No se trasladaron cifras, puntajes ni fuentes de Ecuador. Las referencias competitivas son declaraciones del proponente pendientes de verificación; CRC 38.300 de UNED se conserva en colones, sin conversión. Las cinco notas quedan pendientes hasta investigar mercado local. Al cambiar programa se restablecen filtros y campos de edición para evitar mezclar evaluaciones; las revisiones manuales se conservan por ID.


### 2026-10-26 · Aplicación del modelo a los dos programas de Costa Rica
Se reemplazó el registro pendiente por una evaluación documentada de las cinco dimensiones, con los pesos EdCo 30/22/28/12/8 y los mismos umbrales del modelo. Los puntajes son juicios analíticos preliminares; no son porcentajes de matrícula ni se deducen mecánicamente de contadores internacionales.

| Programa | Demanda | Empleabilidad | Competencia | Precio | Sector | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Abordaje Integral del TEA | 65 | 75 | 60 | 55 | 70 | 65,0 |
| People Analytics y talent strategy | 65 | 80 | 50 | 65 | 75 | 64,9 |

Ambos resultados son de viabilidad condicionada. Cada ficha contiene las justificaciones y fuentes por dimensión. La investigación se mantiene separada de Ecuador y es reproducible mediante investigacion_cr_edcos.py.

- Demanda: consultas Google Trends para CR intentadas sin serie verificable. Se muestran participaciones acumuladas publicadas en Coursera y Udemy como señales internacionales, sin convertirlas en búsquedas locales. TEA: 55.812 (Colorado), 13.989 (Ginebra) y 75 (Udemy); People Analytics: 159.605 (Wharton) y 643 (Udemy). No se suman como personas únicas.
- Empleabilidad: cinco publicaciones de Costa Rica para TEA y cuatro para People Analytics, con descripción, país, identificador y fuente por publicación. Se distinguen cerradas y de vigencia no confirmada. Las habilidades se calculan por publicación; se muestran las diez más frecuentes. La oferta de educación continua no sustituye requisitos profesionales o experiencia.
- Competencia: comparación propia de contenidos y mapa de precio/duración para cada tema, incluyendo proveedores institucionales y plataformas. Las referencias sin descripción verificable siguen en la tabla de oferta; no se inventa su contenido. Los múltiples programas de un oferente no incrementan el número de instituciones.
- Precio: TEA utiliza CRC 15.000, 16.000 y 60.000 de páginas oficiales indexadas de Mundo de Colores, con condición histórica/promocional visible y limitación de un solo proveedor. CRC 38.300 de UNED está declarado en el brief, pero no se verificó en su página y queda fuera del boxplot. People Analytics utiliza USD 145, 250, 290, 450 y 1.000; CEDESO es precio base antes de 2% IVA y TTU corresponde a cohorte histórica. Monedas separadas, sin tipo de cambio supuesto. Se incluyen todos los precios institucionales documentados en cada moneda, no solo universidades.
- Sector: BCCR IMAE por industria, serie original base 2017=100 de octubre de 2024 a septiembre de 2025, ventana accesible del cuadro 5914. TEA usa el agregado enseñanza/salud; People Analytics usa profesionales/científicas/técnicas/administrativas/apoyo. No se identifican como ventas ni como CIIU específico. El informe oficial de agosto de 2026 se muestra como contexto separado: IMAE nacional 2,2% interanual, sin agregarlo a la serie sectorial.

Fuentes destacadas:
- UNED: https://uabierta.uned.ac.cr/Home/ActividadesEducativasDetalle?IdActividadEducativa=116
- San Marcos: https://internacional.usanmarcos.ac.cr/product/diplomado-en-people-analytics/
- BCCR serie sectorial: https://gee.bccr.fi.cr/indicadoreseconomicos/cuadros/frmvercatcuadro.aspx?codcuadro=+5914&idioma=1
- BCCR contexto 2026: https://www.bccr.fi.cr/cr/es/noticias/listado-de-noticias/2026/indice-mensual-de-actividad-economica-para-agosto-de-2026.html

Se conservan los cinco ejes del pentágono, el formato ejecutivo y el fondo blanco. Los campos y filtros de Streamlit se restablecen también cuando cambia la versión de investigación, para que una sesión abierta no mantenga puntajes vacíos del registro anterior. Las revisiones manuales siguen separadas por programa.


### 2026-10-26 · Actualidad de datos y leyenda de competencia
Se descargó el IMAE vigente directamente desde el portal estadístico BCCR: grupo 939, serie original base 2022=100, indicadores 94984 (profesionales y apoyo) y 94986 (educación, salud y asistencia social). Ambos gráficos utilizan 44 meses, enero 2023–agosto 2026. Se sustituyó la totalidad de la base 2017; no se empalmaron bases ni se añadieron cifras nacionales a los sectores. Respuesta original: edcos_fuentes/bccr_imae_grupo_939.json. Informe oficial de agosto: edcos_fuentes/bccr_imae_agosto_2026.pdf. Extracción y descarga reproducibles: actualizacion_bccr_edcos.py. El índice no es ventas; las notas analíticas se mantienen y se actualiza su explicación sectorial.
Cada dimensión de CR muestra fecha de consulta y alcance temporal/tipo de evidencia. Participaciones Udemy People Analytics actualizadas de 643 a 655; demás contadores revisados se conservan. La revisión confirma que Lakeside ya no acepta solicitudes, por lo que se marca cerrada. Se incorpora Omnidian People Analytics Manager, Costa Rica, con botón Solicitar visible; se recalculan participaciones sobre cinco publicaciones distintas, sin duplicar republicaciones. Se mantienen referencias históricas de cursos y precios porque describen ofertas encontradas, con condición explícita; no se atribuye vigencia actual a una cohorte pasada ni a precios indexados sin convocatoria confirmada. El registro revision_fuentes_cr_2026-10-26.json distingue intentos HTTP limitados y consultas web alternativas. Google Trends sigue sin una serie verificable para CR; no se inventan datos locales.
Se retiró «? Sin verificar» de la leyenda de competencia y los signos de interrogación en las celdas. Los valores desconocidos siguen siendo None en la evidencia y no se transforman en contenido declarado o ausente. Se mantienen el fondo blanco y el margen vertical corregido.

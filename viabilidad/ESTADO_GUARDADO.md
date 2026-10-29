# Estado del proyecto · 21 de octubre de 2026

Actualización del23 de octubre de2026: se añadió el apartado independiente Educación continua. Su estado, rúbrica y datos se documentan en `EDCOS_METODOLOGIA.md`. El modelo de carreras conserva las reglas descritas a continuación.

## Aplicación

Tablero Streamlit local con doce pestañas, una por carrera de referencia. Cada pestaña tiene filtro de carrera y selector de nivel independientes. Fondo blanco, diseño ejecutivo, radar con pentágono gris de100 como marco, sin leyenda de Negocios. Fortalezas muestra hasta dos bloques con puntaje real >=75; el título no muestra ese umbral.

## Reglas definitivas de esta sesión

- Cada variable aporta por regla de tres, hasta su peso máximo. No se permiten compensaciones por encima del peso asignado.
- **La carrera de referencia contra sí misma obtiene siempre100 en indicadores, bloques y total.** Es una convención comparativa. Para las otras carreras se aplican las reglas siguientes.
- Indicadores relativos: mínimo entre100 y valor del programa / valor de referencia *100. Mayor es mejor para búsquedas, evaluación del nombre, profesionales, alineación y salario.
- Matriculados y titulados comparan factores `(1+tasa)` para manejar caídas. No se dividen directamente tasas negativas.
- Sector: suma de ventas de personas naturales y sociedades. Se compara frente a la referencia, con máximo100. Mide tamaño económico, no crecimiento.
- Competencia no se compara contra la carrera base. Hasta5 competidores en pregrado o3 en posgrado obtiene100, inclusive. Por encima: límite / competidores *100. Cero competidores obtiene100 sin dividir.
- Precio no se compara contra la carrera base. Usa brecha frente a la media: de−15% a+10% obtiene100. Por debajo resta5 puntos por punto porcentual adicional; por encima resta3,333333. Precio−25% y+25% obtienen50; mínimo0.
- El cuadrante no añade puntos. Verde: búsquedas>=75% de la referencia y competidores dentro del límite del nivel. La referencia puede quedar fuera del verde aunque su puntaje sea100 por definición.
- Vacantes y palabras clave no entran al cálculo. Profesionales sí entra, como tamaño del campo. Modalidad y capacidad de implementación quedan pendientes para después.

## Pesos

Bloques: demanda30%; empleabilidad22%; competencia28%; precio12%; sector8%.

Demanda: nombre65% del bloque y educativa35%. Nombre: búsquedas70%, evaluación30%. Educativa: matriculados60%, titulados40%.

Empleabilidad: profesionales30%, alineación45%, salario25%.

| Variable | Peso total |
|---|---:|
| Búsquedas | 13,65% |
| Evaluación del nombre | 5,85% |
| Crecimiento matriculados | 6,30% |
| Crecimiento titulados | 4,20% |
| Profesionales | 6,60% |
| Alineación laboral | 9,90% |
| Salario | 5,50% |
| Competencia | 28,00% |
| Precio frente a media | 12,00% |
| Ventas del sector | 8,00% |
| Total | 100,00% |

## Visual de precio

Reporte simulado de sensibilidad Van Westendorp: cuatro curvas azules, rango sombreado, límites punteados y resumen ejecutivo. Línea Barato en azul claro. Línea roja vertical punteada UDLA usa precios de pregrado de `PRECIO!C15:C26` del archivo original. En posgrado se identifica como precio base de pregrado; no se inventa un arancel de posgrado.

OPP: cruce demasiado barato/demasiado caro. IPP: cruce barato/caro. Límites del rango: demasiado barato frente a complemento de barato; demasiado caro frente a complemento de caro. Todos los cruces se interpolan linealmente. El resumen se deriva de las curvas, sin depender de metadatos opcionales del gráfico.

Curvas y rango son ficticios, no estiman matrícula, equilibrio económico ni precio para llenar una cohorte. No afectan calificaciones.

## Recomendaciones

Sin cifras introductorias ni sugerencias de rellenar o completar información. En precio, cuando coinciden poca oferta y baja demanda, indicar que esa combinación no garantiza oportunidad.

## Archivos y procedencia

`datos.json` contiene los doce registros extraídos de Hoja1 y los precios UDLA de PRECIO del archivo `Tabla de valores tendencias.xlsx`. Se acepta comparabilidad según confirmación del usuario. El archivo `pesos tendencias.xlsx` se usó para entender la lógica anterior, conservando las variables y pesos nuevos.

`comparativos_todas_referencias.csv` contiene288 resultados:12 programas por12 referencias por2 niveles. Los otros dos CSV conservan vistas de pregrado con referencia Negocios y Software.

Los Excel y scripts de versiones anteriores en la carpeta superior son históricos y no representan necesariamente las reglas vigentes. El código de `modelo.py` y este documento describen la versión actual.

Los valores predeterminados acordados están guardados en código. Los ajustes manuales de pesos, nivel y selección dentro de una sesión de navegador son temporales y no sobrescriben los archivos.

## Educación continua · investigación incorporada 26/10/2026

Se incorporó el Excel SRI aportado (`consulta_sri_1.xlsx`), con respaldo original, hash y CSV mensual del CIIU exacto M732001. El gráfico permite enero–agosto 2023–2026 o años completos 2023–2025; suma 411 + 413 por tipo de contribuyente. LinkedIn aporta una muestra documentada de cinco publicaciones históricas para frecuencia de habilidades, sin contar vacantes activas.

Oferta revisada: universidades, plataformas y referencias de institutos. Precio usa boxplot institucional, promoción histórica opcional y cursos cortos separados. El JSON conserva fuentes, fechas, disponibilidad y exclusiones. Demanda presenta señales indirectas publicadas; Google Trends respondió 429 y no se obtuvo una serie, por lo que la matriz no inventa una posición de búsquedas. El total EdCo sigue siendo una valoración analítica preliminar de 64,1/100. Véase `EDCOS_METODOLOGIA.md` para alcance y procedencia.


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

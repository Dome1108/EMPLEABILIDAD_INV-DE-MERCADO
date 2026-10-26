# Observatorio de empleabilidad

Dashboard ejecutivo en Streamlit con paleta de azules. Filtros de nivel académico y carreras homologadas, cuatro tarjetas de empleo visible y detalle por corte de empleo, salarios e instituciones.

La pestaña Educación reúne el top 10 nacional y el top 10 de Privadas Sierra en una sola figura, en dos columnas con leyenda compartida. Los nombres abreviados conservan su nombre completo al pasar el cursor. El botón **Descargar educación para diapositiva · PNG 16:9** genera una imagen de 2560 × 1440 para insertar en PowerPoint, con ambos gráficos y las carreras seleccionadas. Las tablas completas quedan dentro de los desplegables.

Los controles están en el área principal de la página. El catálogo consulta todas las carreras homologadas no vacías de SENESCYT, sin limitarse a las utilizadas en las pruebas. El gráfico **Privadas Sierra** muestra el **top 10** por volumen histórico dentro de las 18 IES definidas por la usuaria; el detalle tabular conserva el grupo completo. Los nombres equivalentes y siglas se deduplican por persona e institución. El gráfico general también muestra el **top 10** de instituciones por volumen histórico.

La tarjeta **Recién titulados · 2026**, los gráficos de instituciones de 2026 y el conteo de recién titulados del CSV usan desde el 01/01/2026 hasta la última fecha disponible de 2026 para las carreras seleccionadas, excluyendo fechas posteriores a hoy en Ecuador. El histórico de instituciones de 2026 también incorpora todos los registros hasta esa fecha. Los denominadores y resultados laborales conservan el corte de empleo de enero de 2026. El CSV muestra por separado la fecha laboral y la académica. Para 2023–2025 educación conserva el corte correspondiente.

## Ejecutar

El selector **Paleta de colores** permite alternar entre Azul (predeterminada) y Vino: `#A5133D`, rosa `#E4B6C2` y gris `#F2F2F2`. Se aplica a las tarjetas, gráficos y descarga PNG de educación, conservando los filtros y resultados.

Desde esta carpeta, con Python 3.11 o superior:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

También puedes abrir `iniciar_dashboard.bat`. La aplicación estará en http://localhost:8501. Activa **Vista de demostración** para explorar datos sintéticos sin conexión. La aplicación nunca sustituye automáticamente datos reales por datos de ejemplo.

## SQL Server

Conexión predeterminada: servidor **SNBI03**, autenticación de Windows, base inicial **BDD_IDM**. El usuario de Windows que ejecute Streamlit debe tener lectura en las cinco tablas compartidas de SENESCYT/SIM/APOR y en SRI_CATASTRO, en BDD_IDM y Northwind. Ambos catálogos deben estar accesibles en la misma instancia. Se requiere Microsoft ODBC Driver 17 o 18 for SQL Server.

Al clonar en otro equipo, la conexión predeterminada a **SNBI03** mantiene el cifrado y acepta su certificado interno (`trust_server_certificate = true`), sin necesitar un archivo local de configuración. Se requiere red institucional o VPN, ODBC Driver 17/18 y permisos de Windows sobre las bases. Si ya existe `.streamlit/secrets.toml`, sus valores tienen prioridad: cambiar `trust_server_certificate = false` a `true` para SNBI03 y reiniciar Streamlit.

Para personalizar, copiar `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml`. La plantilla también incluye el ajuste de SNBI03. El archivo local de credenciales se excluye de Git. Para servidores distintos de SNBI03, se valida el certificado por defecto; utilizar `trust_server_certificate = false` cuando exista una cadena de confianza válida. Si hay errores de autenticación integrada, ejecutar desde una sesión institucional con acceso al servidor.

Solo se leen las fuentes; las tablas temporales de trabajo se crean en tempdb y desaparecen al cerrar la conexión. Las carreras se pasan como parámetros, nunca se concatenan al SQL. La aplicación no muestra ni exporta cédulas, teléfonos, correos o registros individuales. El CSV contiene exclusivamente resultados agregados y las carreras seleccionadas. La caché en memoria tiene vigencia de 15 minutos; el botón de actualización la invalida.

## Reglas

- **Industrias y ventas SRI:** la pestaña usa la cohorte de carreras y nivel académico seleccionados, y los empleadores de SIM de enero de 2026. Cruza el RUC del empleador con `validación.txt` (RUCEMP, NOMEMP, CIUU), normaliza CIIU con y sin punto y consulta las ventas sectoriales de `consulta_sri_1.xlsx`. Los archivos se incluyen en la carpeta `data/` del repositorio y se leen desde ella; las rutas pueden cambiarse en el desplegable de fuentes. La tabla muestra 411 y 413 por personas naturales y sociedades; los gráficos suman 411 + 413 y cada CIIU una sola vez. El gráfico anual compara los mismos meses de todos los años; el mensual conserva la serie completa. Los valores vacíos permanecen sin dato. La selección territorial no cambia esta pestaña. Las ventas pertenecen al conjunto de cada actividad económica, no únicamente a los empleadores identificados. Una persona puede pertenecer a varias industrias si tiene varios empleadores. Catálogos con RUC asociados a CIIU contradictorios se excluyen del cruce. La demostración usa únicamente datos sintéticos.

- **Panel territorial:** cruza por cédula la cohorte de enero de 2026 con `[BDD_IDM].[modelo].[03_ATLAS_Universo]`, leyendo solo cédula, provincia, cantón y parroquia. Pichincha es la selección inicial cuando tiene registros; provincia, cantón y parroquia solo cambian este panel. La tasa usa empleo visible SIM/SRI sobre graduados de la misma zona. La banda P25–P75 usa los salarios SIM y las reglas nacionales, sin ingresos imputados Atlas. El domicilio disponible en Atlas no garantiza la ubicación histórica ni el lugar de trabajo. Se deduplican domicilios equivalentes; personas con ubicaciones contradictorias se excluyen del panel y se informa la cobertura. Se requiere permiso de lectura en la tabla Atlas. Si falla esa lectura, el nacional continúa disponible.

- **Cortes:** 28/02/2023, 31/05/2024, 31/01/2025 y 31/01/2026. Se asume fin de mes porque las tablas solo identifican el mes. Si la extracción fue anterior, ajustar `Snapshot.date` en `analytics.py`. Los datos no son promedios anuales ni cortes del mismo mes.
- **Denominador:** personas únicas de las carreras seleccionadas con FECHA_REGISTRO <= corte. La fecha de registro aproxima la fecha de titulación. Identificaciones inválidas y fechas no interpretables se excluyen y se reportan. Se aceptan fechas SQL nativas, ISO y dd/mm/aaaa en las lecturas SQL.
- **SIM/APOR:** presencia en la tabla correspondiente = dependiente, como se acordó. No se reaplica un filtro de fechas de entrada/salida sobre la foto entregada.
- **SRI:** buscar exactamente cédula normalizada a diez dígitos + `001`. Deduplicar por RUC, conservar carga más reciente y última actualización. Inferir actividad por inicio, suspensión y reinicio. Si no puede establecerse, clasificar como indeterminado. SRI inactivo no aporta empleo visible. SIM siempre tiene prioridad.
- **Limitación SRI:** un catastro actual no conserva necesariamente todos los ciclos de actividad. Las cifras independientes y de empleo visible son estimaciones históricas inferidas; requieren catastros históricos para validarse definitivamente. La ausencia de suspensión en una fila ACTIVO se interpreta como actividad desde el inicio; puede existir historial no conservado. Los casos indeterminados sin SIM aparecen en Sin información laboral y en calidad del corte.
- **Empleo visible:** (dependientes + independientes) / graduados al corte. Si no hay graduados, mostrar sin dato, sin dividir por cero. Profesionales ejerciendo = numerador; no implica afinidad ocupacional con la carrera.
- **Salarios:** SALARIO en 2023/2026; SALARIO_TOTAL con respaldo de SALARIO_FIJO vacío/cero en 2024/2025. Máximo por persona y RUC de empleador, suma entre empleadores y exclusión de ingresos no positivos. Si falta RUCEMP, sus filas se agrupan como un único empleador desconocido. Percentiles 25 y 75 con interpolación lineal por persona; no mezclar ingreso mensual con SalarioPromedio12M. No hay ingresos SRI en la fuente proporcionada.
- **Educación:** recién titulados = personas con registro de ese año, aunque tengan títulos anteriores. En 2026, la ventana se extiende hasta la última fecha disponible sin superar hoy; en años anteriores, hasta el corte. Profesionales históricos = personas acumuladas hasta el corte académico, con o sin empleo. Una persona cuenta una vez en el total y una vez dentro de cada institución; instituciones no sumables entre sí cuando existen múltiples titulaciones.
- **Nivel académico:** permite todos los niveles, Tecnológico (incluye técnico superior), Tercer nivel y Cuarto nivel, especialidades y doctorados. Se clasifica el campo de nivel de la fuente, sin inferirlo por el nombre de la carrera. El filtro limita el catálogo de carreras y los registros de titulación antes de calcular cohortes, empleo, salarios e instituciones. Los valores no reconocidos solo se incluyen en Todos los niveles. El CSV identifica el nivel seleccionado. La columna se detecta entre NIVEL_FORMACION, NIVEL_DE_FORMACION, NIVEL_ACADEMICO, NIVEL_DE_TITULO, NIVEL_TITULO o NIVEL; si no existe, se informa el problema para revisar el esquema.
- No se aplican filtros adicionales de nacionalidad, edad o país de institución.

La normalización espera identificaciones compuestas por dígitos, representadas como texto o enteros; permite completar ceros a la izquierda, pero no convierte formatos decimales o notación científica. Revisar los conteos de calidad al conectar las fuentes reales. Se admiten salarios con punto decimal y con coma decimal, incluido separador de miles con punto (`1.234,56`). La tabla real de 2025 usa coma decimal.

## Validación

La sección **Empresas donde trabajan los graduados · SIM enero 2026**, dentro de Industrias y ventas SRI, toma todos los empleadores de los graduados de las carreras y nivel académico seleccionados. El gráfico muestra el top 10 de empresas, ordenado por **graduados únicos en SIM**: eje X en cantidad de graduados y etiqueta en participación porcentual. El denominador es el total de graduados únicos empleados con un RUC válido en la SIM de esa selección, sin limitarlo al top 10 ni a coincidencias con el ranking. Una persona con varios empleadores cuenta una vez dentro de cada empresa. Las participaciones de categorías distintas pueden sumar más de 100 % por personas con varios empleadores. Se conservan los empleadores sin coincidencia en el ranking y los sectores no identificados.

El Excel `data/ranking_2025.xlsx` (hoja Ranking2025, encabezados en la segunda fila) es complementario y su ruta se puede cambiar en la fuente. Se busca `NOMEMP` en el ranking para obtener **Cant. Empleados** de 2025, disponible en tablas y descargas, sin usar ese tamaño como eje de los gráficos principales. La actividad se toma del catálogo por RUC; si falta, se aprovecha el CIIU de una coincidencia unívoca con el ranking. El filtro CIIU de ventas se mantiene independiente. Sin el archivo del ranking, los gráficos de graduados siguen disponibles con SIM y el catálogo.

El ranking no contiene RUC: se enlaza por coincidencia exacta del nombre tras normalizar tildes, mayúsculas, puntuación, espacios y formas jurídicas equivalentes. No se aceptan automáticamente coincidencias aproximadas, nombres con varios expedientes ni un expediente asociado a varios RUC distintos; estos casos y los nombres sin coincidencia se muestran en una tabla de revisión descargable, sin asignar cero empleados. El RUC agrupa a los empleadores dentro de SIM. Se deduplica el ranking por expediente y año; duplicados contradictorios se excluyen y se reportan. Cantidades ausentes, negativas o fraccionarias de empleados se conservan sin dato, y los ceros explícitos son válidos. Cada expediente coincidente se suma una vez. El total corresponde a empleados reportados de todas las ocupaciones: no mide graduados de la carrera, vacantes ni personas únicas entre empresas. El ranking mantiene su año 2025 y no multiplica las ventas SRI. Se usan solo año, expediente, nombre, actividad y empleados del Excel.

La serie mensual de **Industrias y ventas SRI** incorpora un diagnóstico guiado:

1. Serie original en USD, niveles de la serie seleccionada, media y desviación estándar móviles de 12 meses, y ACF hasta 24 rezagos.
2. ADF (constante o constante y tendencia, rezagos elegidos por AIC dentro de un máximo prudente para la muestra) y KPSS (misma especificación determinística, rezagos automáticos). Se muestran estadísticos, p-valores, rezagos y lectura conjunta al 5 %. Los p-valores acotados de KPSS se identifican como límites.
3. Transformación opcional a logaritmo o Box-Cox con lambda por máxima verosimilitud; ambas exigen valores positivos, sin sumar constantes a los ceros.
4. Diferencias regulares `d = 0, 1, 2` y estacionales `D = 0, 1`, con `s = 12`. Como alternativa, se permite quitar una tendencia lineal sin diferenciar.
5. Nueva gráfica, ACF y pruebas sobre el resultado; comparación explícita con diferencia estacional sola, regular sola y ambas. La segunda diferencia se ofrece en la comparación únicamente si la primera arroja resultados no estacionarios o inconclusos.
6. Avisos orientativos de posible sobrediferenciación por ACF(1) muy negativa o aumento de varianza al agregar la última diferencia, comparando fechas comunes en la misma escala.
7. Registro de transformación, lambda, `d`, `D` y `s`, y descarga CSV con las series originales, base transformada y resultado. Este paso no estima ARIMA/SARIMA ni pronósticos.

El diagnóstico permite elegir ventas totales, personas naturales o sociedades y dos métodos de cobertura. El predeterminado, **Panel fijo comparable**, conserva únicamente las casillas CIIU/campo informadas en todos los meses; una casilla ausente en algún mes se excluye del período completo. Esto permite analizar sectores con casillas sistemáticamente vacías sin convertirlas en cero ni cambiar la composición mensual. Se muestra el número de casillas incluidas/excluidas y se permite descargar el detalle. La suma del panel representa un subconjunto de ventas informadas, no el total completo del sector. La alternativa **Cobertura completa de todos los CIIU** exige todas las casillas de todos los códigos cada mes. Los huecos no se imputan ni se comprimen. Cuando hay huecos se informa y se analiza el mayor tramo mensual continuo, con preferencia por el más reciente ante empate. Se requieren al menos 20 observaciones para las pruebas y se advierte sobre historias cortas. ADF y KPSS aportan evidencia, no una prueba concluyente del orden de integración ni de raíces estacionales; resultados discordantes quedan como inconclusos.

Documentación de referencia: [ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html), [KPSS](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.kpss.html) y [estacionariedad y eliminación de tendencia](https://www.statsmodels.org/stable/examples/notebooks/generated/stationarity_detrending_adf_kpss.html).

```powershell
python -m unittest discover -s tests -v
```

Las pruebas verifican deduplicación, cédula + 001, prioridad SIM/SRI, denominadores por fecha, titulaciones múltiples, suma por empleador, percentiles y suspensión/reinicio. La interfaz puede validarse con `streamlit.testing.v1.AppTest` usando `DASHBOARD_DEMO=1`.

Referencias técnicas: [Streamlit: conexión a datos](https://docs.streamlit.io/develop/concepts/connections/connecting-to-data) y [gestión de caché](https://docs.streamlit.io/develop/concepts/architecture/caching).

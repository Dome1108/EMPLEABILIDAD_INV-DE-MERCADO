# Diseño: pestaña Demanda e interés académico

## Intención

Añadir una cuarta opción en la navegación superior del dashboard, junto a las
tres vistas existentes, para preparar el espacio de análisis de demanda e
interés académico.

## Alcance de esta etapa

- La pestaña se llamará `Demanda e interés académico`.
- Se abrirá como una vista independiente mediante `st.navigation`.
- Mostrará una cabecera coherente con la paleta visual existente.
- Incluirá dos paneles preparados para los futuros gráficos de matriculados y
  titulados.
- No leerá CSV, no consultará SQL y no calculará todavía datos reales.

## Fuera de alcance

- No se implementan aún los gráficos ni la lógica del notebook.
- No se incorporan precios, oferta, competencia ni empleabilidad.
- No se reorganizan ni refactorizan las tres vistas actuales.

## Enfoque elegido

Se creará `views/demanda_interes.py` como una vista nueva e independiente y
se añadirá únicamente su registro en la lista `st.navigation` de `app.py`.
Esto es necesario para que la pestaña aparezca en la barra superior; el resto
de la lógica y de las vistas actuales permanecerá sin cambios.

## Apariencia y ubicación

La nueva pestaña quedará al lado de las opciones existentes en la navegación
superior. Dentro de ella tendrá un título, una breve descripción y dos tarjetas
visuales con los rótulos `Matriculados` y `Titulados`, listas para conectar
posteriormente con los datos del notebook.

## Decisiones para la implementación

- Reutilizar los colores y tipografías ya definidos por el frontend.
- Mantener la vista aislada para que la futura lógica de datos pueda crecer sin
  modificar `views/empleabilidad.py`, `views/carreras.py` ni
  `views/educacion_continua.py`.
- Validar que la app pueda importar y renderizar la nueva ruta sin datos
  externos.

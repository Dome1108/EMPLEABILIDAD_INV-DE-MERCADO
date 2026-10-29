# Tablero de viabilidad académica

Aplicación local en Streamlit con12 carreras de referencia, filtro de programa y niveles pregrado/posgrado.

Incluye un apartado independiente **Educación continua**, con el brief y la investigación inicial del Diplomado en Neuromarketing Digital y Neurociencia del Consumidor. Ver `EDCOS_METODOLOGIA.md` para criterios, fuentes y alcance del resultado preliminar.

## Abrir

Desde esta carpeta:

```powershell
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Abrir http://localhost:8501. También se puede ejecutar `abrir_tablero.bat`.

Para instalar en otro equipo:

```powershell
python -m pip install -r requirements.txt
```

## Contenido

- `ESTADO_GUARDADO.md`: reglas y decisiones vigentes.
- `modelo.py`: cálculo ponderado; la referencia contra sí misma siempre obtiene100.
- `datos.json`: datos de las doce carreras y precios de pregrado UDLA del archivo original.
- `app.py`: interfaz con fondo blanco y formato ejecutivo.
- `graficos_simulados.py`: sensibilidad de precio ilustrativa, fuera del cálculo.
- `comparativos_todas_referencias.csv`:288 comparaciones, incluidos ambos niveles.
- `resultados_actualizados.csv`: pregrado con Negocios como referencia.
- `resultados_referencia_software.csv`: pregrado con Software como referencia.
- `tests/`: pruebas del cálculo y la interfaz.
- `modelo_edcos.py`, `edcos_vista.py` y `graficos_edcos.py`: módulo EdCo con las mismas cinco dimensiones del pentágono de carreras y pesos30/22/28/12/8.
- `edcos_data/` y `edcos_fuentes/`: ficha investigada y brief original del proponente.

Los pesos predeterminados y reglas están guardados en los archivos. Cambios de controles en el navegador son temporales. El tablero no necesita acceso a Excel ni a servicios externos para calcular. Google Fonts tiene fuente local de respaldo.

## Verificar

```powershell
python -m unittest discover -s tests -v
```

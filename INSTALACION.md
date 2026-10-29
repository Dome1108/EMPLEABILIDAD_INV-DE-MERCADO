# Instalar en otra computadora

Requisitos: Windows, Python 3.11 y Git. Para consultar empleo institucional también se necesita Microsoft ODBC Driver 17 o 18 para SQL Server, acceso a la red institucional/VPN y permisos de lectura en SNBI03 (BDD_IDM y Northwind). Las bases SQL permanecen en el servidor; no se copian a GitHub.

En PowerShell:

```powershell
git clone --branch integrar-viabilidad-academica https://github.com/Dome1108/EMPLEABILIDAD_INV-DE-MERCADO.git
cd EMPLEABILIDAD_INV-DE-MERCADO
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Abrir http://localhost:8501. No es necesario activar el entorno virtual ni cambiar la política de ejecución de PowerShell.

El proyecto está en la rama `integrar-viabilidad-academica`; aún no se ha fusionado con `main`.

## Datos y configuración

- `data/`: ventas SRI, catálogo RUC–CIIU y ranking de empresas.
- `viabilidad/`: modelo de carreras, estudios de Educación Continua, fuentes públicas y briefs originales.
- `archivo_historico/`: versiones Excel y scripts originales para reconstrucción. Estos scripts leen `Tabla de valores tendencias.xlsx` desde la raíz del repositorio.
- SQL Server utiliza autenticación de Windows de forma predeterminada. Si necesitas personalizarla, usa la plantilla de configuración del repositorio y crea localmente `.streamlit/secrets.toml`. Las credenciales nunca se versionan.
- El modo normal consulta datos institucionales. Para pruebas con datos sintéticos puede establecerse explícitamente `$env:DASHBOARD_DEMO="1"`; la interfaz identifica esa vista. Para volver al modo normal: `Remove-Item Env:DASHBOARD_DEMO` y reiniciar Streamlit.

Los filtros se conservan durante la sesión de Streamlit. Las consultas y selecciones temporales de una sesión no se transfieren a otro equipo.

## Verificación

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m unittest discover -s viabilidad/tests
```

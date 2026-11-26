@echo off
rem Worker de presentaciones .pptx: dejar esta ventana abierta mientras se usan los botones.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" run_worker_presentaciones.py
) else (
  python run_worker_presentaciones.py
)
pause

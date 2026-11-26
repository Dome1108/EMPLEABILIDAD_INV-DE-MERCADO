"""Inicia el worker de presentaciones .pptx (equivalente a run_workers.py de Tendencias).

Uso: python run_worker_presentaciones.py          (queda escuchando la cola)
     python run_worker_presentaciones.py --una-vez (procesa lo pendiente y termina)
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)  # data/, .streamlit/secrets.toml y la plantilla se buscan desde aquí

from presentaciones.worker import main

if __name__ == "__main__":
    main()

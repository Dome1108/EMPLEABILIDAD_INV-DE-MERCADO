"""Entrada única del Observatorio de empleabilidad y viabilidad académica."""
from pathlib import Path
import sys
import streamlit as st

ROOT=Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
st.set_page_config(page_title='Observatorio · Empleabilidad y viabilidad',page_icon='◈',layout='wide')
page=st.navigation([
    st.Page('views/empleabilidad.py',title='Empleabilidad y mercado',url_path='empleabilidad',default=True),
    st.Page('views/carreras.py',title='Viabilidad de carreras',url_path='viabilidad-carreras'),
    st.Page('views/educacion_continua.py',title='Viabilidad Educación Continua',url_path='educacion-continua'),
],position='top')
page.run()

"""Entrada única del Observatorio de empleabilidad y viabilidad académica."""
from pathlib import Path
import sys
import streamlit as st

ROOT=Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
st.set_page_config(page_title='Observatorio · Empleabilidad y viabilidad',page_icon='◈',layout='wide')
# Conserva estos filtros aunque sus widgets no se rendericen en otra página.
# La reasignación desde la entrada común evita la limpieza de estado de widgets.
for key in ('selected_careers','academic_level','color_palette','employment_cutoff'):
    if key in st.session_state:
        st.session_state[key]=st.session_state[key]
page=st.navigation([
    st.Page('views/empleabilidad.py',title='Empleabilidad y mercado',url_path='empleabilidad',default=True),
    st.Page('views/carreras.py',title='Viabilidad de carreras',url_path='viabilidad-carreras'),
    st.Page('views/educacion_continua.py',title='Viabilidad Educación Continua',url_path='educacion-continua'),
],position='top')
page.run()

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
# Todos son filtros que usa también la presentación .pptx (presentaciones/filtros.py).
PERSISTENT_KEYS=('selected_careers','academic_level','color_palette','employment_cutoff',
                 'market_career','market_level','market_financing','market_province','market_projection',
                 'market_semester','industry_ciiu','industry_month','geo_provincia','geo_canton','geo_parroquia')
for key in (*PERSISTENT_KEYS,*(k for k in list(st.session_state) if str(k).startswith('trends_project_'))):
    if key in st.session_state:
        st.session_state[key]=st.session_state[key]
if st.session_state.get('color_palette')=='Vino':
    from palettes import VINO_CSS
    st.markdown(VINO_CSS,unsafe_allow_html=True)
page=st.navigation([
    st.Page('views/empleabilidad.py',title='Oferta de valor-empleabilidad',url_path='empleabilidad',default=True),
    st.Page('views/demanda_interes.py',title='Demanda e interés académico',url_path='demanda-interes-academico'),
    st.Page('views/posicionamiento_competencia_precios.py',title='Posicionamiento-competencia y precios',url_path='posicionamiento-competencia-precios'),
    st.Page('views/carreras.py',title='Viabilidad de carreras',url_path='viabilidad-carreras'),
    st.Page('views/educacion_continua.py',title='Viabilidad Educación Continua',url_path='educacion-continua'),
],position='top')
page.run()

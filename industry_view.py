"""Pestaña de industrias y ventas sectoriales."""
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from data_access import load_employers
from industry import read_sources, match_employers, monthly_sales, macroindustry_summary, growth_summary, compact_usd, SECTIONS, SALES
from palettes import PALETTES, theme_figure


@st.cache_data(ttl=900, show_spinner=False, max_entries=8)
def employers(config, people):
    return load_employers(config, people)


@st.cache_data(ttl=900, show_spinner=False, max_entries=2)
def sources(mapping_path, sales_path, mapping_stamp, sales_stamp):
    return read_sources(mapping_path, sales_path)


def render(config, cohort, demo, palette):
    st.markdown('### Industrias y ventas sectoriales')
    try:
        if demo:
            codes = ['M711022', 'K641901', 'J620101']
            ids = cohort.loc[cohort.dependent, 'person'].tolist()
            jobs = pd.DataFrame({'person': ids, 'RUCEMP': [str(i % 3 + 1).zfill(13) for i in range(len(ids))]})
            mapping = pd.DataFrame({'RUCEMP': [str(i + 1).zfill(13) for i in range(3)], 'CIIU': codes})
            sales = pd.DataFrame([dict(CIIU=code, Año=year, Mes=month, **{field: float((index+1)*10000 + (year-2023)*700 + month*100 + j*200) for j, field in enumerate(SALES)})
                                  for index, code in enumerate(codes) for year in range(2023, 2027) for month in range(1, 9 if year == 2026 else 13)])
            conflicts = 0
        else:
            with st.expander('Fuentes de empresas y ventas SRI'):
                data_dir = Path(__file__).resolve().parent / 'data'
                mapping_path = st.text_input('Archivo de empresas (TXT)', str(data_dir / 'validación.txt'))
                sales_path = st.text_input('Archivo de ventas SRI (Excel)', str(data_dir / 'consulta_sri_1.xlsx'))
                if st.button('Actualizar industrias y ventas'):
                    sources.clear()
                    employers.clear()
            with st.spinner('Cruzando empleadores con CIIU y ventas SRI…'):
                mapping, sales, conflicts = sources(mapping_path, sales_path, Path(mapping_path).stat().st_mtime_ns, Path(sales_path).stat().st_mtime_ns)
                jobs = employers(config, tuple(sorted(cohort.person.unique())))
        catalog, matched, total = match_employers(jobs, mapping)
        if catalog.empty:
            st.info('No se encontraron CIIU para los empleadores de los graduados seleccionados.')
            return
        a, b, c = st.columns(3)
        a.metric('Graduados con CIIU identificado', f'{matched:,}'.replace(',', '.'))
        b.metric('Graduados con empleador SIM', f'{total:,}'.replace(',', '.'))
        c.metric('CIIU identificados', len(catalog))
        with st.expander('Industrias donde trabajan los graduados', expanded=True):
            st.dataframe(catalog, hide_index=True, width='stretch')
        codes = st.multiselect('CIIU para analizar ventas', catalog.CIIU.tolist(), default=catalog.CIIU.tolist(),
                               format_func=lambda x: f"{x} · {catalog.set_index('CIIU').loc[x, 'Industria']}")
        if not codes:
            st.info('Selecciona al menos un CIIU.')
            return
        missing = sorted(set(codes) - set(sales.CIIU))
        if missing:
            st.caption('Sin ventas en la fuente SRI: ' + ', '.join(missing))
        monthly = monthly_sales(sales, codes)
        if monthly.empty:
            st.info('No hay ventas SRI para los CIIU seleccionados.')
            return
        blue, light, _ = PALETTES[palette]
        max_month = int(monthly.groupby('Año').Mes.max().min())
        month = st.slider('Acumulado comparable hasta el mes', 1, max_month, max_month) if max_month > 1 else 1
        annual = monthly[monthly.Mes.le(month)].groupby('Año')[['Personas naturales', 'Sociedades']].sum(min_count=1).reset_index()
        latest = int(annual.Año.max())
        growth = growth_summary(sales, codes, latest, month)
        st.markdown('**Distribución por macroindustria**')
        macro = macroindustry_summary(jobs, mapping, sales, codes, latest, month)
        from textwrap import wrap
        for measure, key in [('Ventas acumuladas', 'industry_macro_sales'), ('Graduados empleados', 'industry_macro_graduates')]:
            field = 'Ventas totales' if measure == 'Ventas acumuladas' else 'Graduados'
            ranked = macro.sort_values([field, 'Macroindustria'], ascending=[False, True], na_position='last')
            labels = ['<br>'.join(wrap(name, 43)) for name in ranked.Macroindustria]
            with st.container(border=True):
                st.markdown(f'**{measure} por macroindustria**')
                fig = go.Figure()
                if measure == 'Ventas acumuladas':
                    for label, color in [('Personas naturales', blue), ('Sociedades', light)]:
                        fig.add_trace(go.Bar(y=labels, x=ranked[label], name=label, orientation='h', marker_color=color,
                                            hovertemplate='%{y}<br>USD %{x:,.2f}<extra>%{fullData.name}</extra>'))
                else:
                    fig.add_trace(go.Bar(y=labels, x=ranked.Graduados, orientation='h', marker_color=blue,
                                        hovertemplate='%{y}<br>%{x:,.0f} graduados<extra></extra>'))
                fig.update_layout(height=680, barmode='stack', showlegend=measure == 'Ventas acumuladas',
                                  xaxis_title='USD · ventas 411 + 413' if measure == 'Ventas acumuladas' else 'Graduados únicos por macroindustria',
                                  yaxis=dict(tickmode='array', tickvals=labels, ticktext=labels, automargin=True,
                                             categoryorder='array', categoryarray=labels, autorange='reversed'),
                                  margin=dict(l=10, r=25, t=35, b=55), legend=dict(orientation='h'),
                                  paper_bgcolor='white', plot_bgcolor='white')
                st.plotly_chart(theme_figure(fig, palette), width='stretch', key=key)
        st.caption(f'Ventas acumuladas enero–mes {month:02d} de {latest}, solo de los CIIU seleccionados. Graduados empleados: corte SIM de enero de 2026; cada persona cuenta una vez dentro de cada macroindustria.')
        with st.expander('Ver cifras por macroindustria'):
            st.dataframe(macro, hide_index=True, width='stretch')
        overview, chart_col = st.columns([1, 2])
        with overview:
            with st.container(border=True):
                st.markdown('**Resumen del sector**')
                st.metric('Ventas totales · 411 + 413', compact_usd(growth['total']))
                st.markdown('**Macroindustria con mayor participación en ventas**')
                available = macro.dropna(subset=['Ventas totales'])
                if not available.empty and pd.notna(growth['total']) and growth['total'] > 0:
                    leader = available.sort_values(['Ventas totales', 'Macroindustria'], ascending=[False, True]).iloc[0]
                    share = 100 * leader['Ventas totales'] / growth['total']
                    st.metric('Participación en ventas', f'{share:.1f} %'.replace('.', ','))
                    st.write(leader['Macroindustria'])
                else:
                    st.write('Sin ventas suficientes para calcular la participación')
                st.markdown('**CIIU con mayor crecimiento**')
                top = growth['top']
                if top:
                    st.metric(top['CIIU'], f"{top['growth']:+.1f} %".replace('.', ','))
                    st.write(SECTIONS.get(top['CIIU'][0], 'Sin descripción'))
                else:
                    st.write('Sin base comparable')
                st.caption(f'Acumulado enero–mes {month:02d} de {latest}, frente al mismo periodo de {latest-1}.')
        with chart_col:
            fig = go.Figure()
            for label, color in [('Personas naturales', blue), ('Sociedades', light)]:
                fig.add_trace(go.Scatter(x=annual.Año.astype(str), y=annual[label], name=label, mode='lines+markers', line=dict(color=color, width=3), connectgaps=False))
            fig.update_layout(title='Evolución anual · ventas 411 + 413', xaxis_title='Año', yaxis_title='USD', legend=dict(orientation='h'), paper_bgcolor='white', plot_bgcolor='white')
            fig.update_xaxes(type='category', categoryorder='array', categoryarray=annual.Año.astype(str).tolist())
            st.plotly_chart(theme_figure(fig, palette), width='stretch', key='industry_annual')
        st.caption(f'Comparación enero–mes {month:02d} en cada año. Los meses y valores ausentes permanecen sin dato; no se sustituyen por cero.')
        fig = go.Figure()
        for label, color in [('Personas naturales', blue), ('Sociedades', light)]:
            timeline = monthly.set_index('Periodo')[label].reindex(pd.date_range(monthly.Periodo.min(), monthly.Periodo.max(), freq='MS'))
            fig.add_trace(go.Scatter(x=timeline.index, y=timeline, name=label, mode='lines', line=dict(color=color, width=2), connectgaps=False))
        fig.update_layout(title='Serie mensual · ventas 411 + 413', xaxis_title='Periodo', yaxis_title='USD', legend=dict(orientation='h'), paper_bgcolor='white', plot_bgcolor='white')
        st.plotly_chart(theme_figure(fig, palette), width='stretch', key='industry_monthly')
        st.markdown('**Detalle mensual por CIIU**')
        detail = sales[sales.CIIU.isin(codes)].sort_values(['CIIU', 'Año', 'Mes']).copy()
        detail.columns = pd.MultiIndex.from_tuples([('Actividad económica', 'CIIU'), ('Periodo', 'Año fiscal'), ('Periodo', 'Mes fiscal'),
            ('Ventas locales gravadas (411)', 'Personas naturales'), ('Ventas locales gravadas (411)', 'Sociedades'),
            ('Ventas locales 0% (413)', 'Personas naturales'), ('Ventas locales 0% (413)', 'Sociedades')])
        st.dataframe(detail, hide_index=True, width='stretch')
        st.caption('Cada CIIU se suma una sola vez. Una persona puede aparecer en varias industrias si tiene más de un empleador. Los valores vacíos del Excel se conservan sin dato.')
        if conflicts:
            st.caption(f'{conflicts} RUC con CIIU contradictorios en el catálogo se excluyen del cruce.')
    except Exception as exc:
        st.warning('No fue posible completar el cruce de industrias y ventas. Los demás indicadores siguen disponibles.')
        with st.expander('Detalle de la consulta de industrias'):
            st.code(str(exc))

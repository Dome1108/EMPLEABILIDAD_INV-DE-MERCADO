"""Flujo guiado de estacionariedad para las ventas mensuales."""
import importlib
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from palettes import PALETTES, theme_figure
import time_series as time_series_module
if getattr(time_series_module,'SERIES_API_VERSION',None)!=2:
    time_series_module=importlib.reload(time_series_module)
from time_series import (complete_monthly, comparable_panel, longest_monthly_block, transform, stationarity,
                         autocorrelation, differencing_flags)

STATUS = {'stationary':'Ambas pruebas compatibles con estacionariedad',
          'nonstationary':'Ambas pruebas apuntan a no estacionariedad',
          'inconclusive':'Pruebas discordantes: resultado inconcluso',
          'unavailable':'Sin diagnóstico válido'}


def line_chart(series, title, unit, palette, key, rolling=False):
    fig=go.Figure(go.Scatter(x=series.index,y=series.values,mode='lines+markers',name='Serie',
                             connectgaps=False,line=dict(color=PALETTES[palette][0],width=2),marker_size=4))
    if rolling:
        fig.add_trace(go.Scatter(x=series.index,y=series.rolling(12,min_periods=12).mean(),name='Media móvil · 12 meses',
                                line=dict(color=PALETTES[palette][1],width=2,dash='dash')))
    fig.update_layout(title=title,height=300,margin=dict(l=10,r=15,t=55,b=45),
                      xaxis_title='Mes',yaxis_title=unit,paper_bgcolor='white',plot_bgcolor='white',
                      legend=dict(orientation='h',y=-.25))
    st.plotly_chart(theme_figure(fig,palette),width='stretch',key=key)


def acf_chart(series, palette, key):
    table=autocorrelation(series)
    if table.empty:
        st.info('ACF no disponible: serie demasiado corta, constante o con huecos.')
        return
    table=table[table.lag.gt(0)]
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=table.lag,y=table.upper,mode='lines',line_width=0,showlegend=False,hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=table.lag,y=table.lower,mode='lines',line_width=0,fill='tonexty',
                             fillcolor='rgba(8,123,204,.10)',showlegend=False,hoverinfo='skip'))
    fig.add_trace(go.Bar(x=table.lag,y=table.acf,marker_color=PALETTES[palette][0],width=.25,
                         hovertemplate='Rezago %{x}<br>ACF %{y:.3f}<extra></extra>',showlegend=False))
    fig.add_hline(y=0,line_color='#aabaca',line_width=1)
    if table.lag.max()>=12:
        fig.add_vline(x=12,line_dash='dot',line_color='#aabaca')
    if table.lag.max()>=24:
        fig.add_vline(x=24,line_dash='dot',line_color='#aabaca')
    fig.update_layout(title='Autocorrelación · ACF',height=300,margin=dict(l=10,r=15,t=55,b=45),
                      xaxis_title='Rezagos mensuales',yaxis_title='Correlación',yaxis_range=[-1,1],
                      paper_bgcolor='white',plot_bgcolor='white')
    st.plotly_chart(theme_figure(fig,palette),width='stretch',key=key)
    st.caption('Bandas puntuales aproximadas del 95 % (Bartlett). Los picos en 12 o 24 meses son indicios, no una prueba de raíz unitaria estacional.')


def report_row(label, report):
    return {'Serie':label,'Meses':report['n'],'ADF · estadístico':report['adf_stat'],
            'ADF · p':report['adf_p'],'ADF · rezagos':report['adf_lags'],
            'KPSS · estadístico':report['kpss_stat'],'KPSS · p':report['kpss_p'],
            'KPSS · límite':report['kpss_bound'],'KPSS · rezagos':report['kpss_lags'],
            'Lectura conjunta':STATUS[report['status']]}


def show_tests(report):
    message=STATUS[report['status']]
    if report['status']=='stationary':
        st.success(message+(' alrededor de una tendencia determinística.' if report['regression']=='ct' else ' al nivel de 5 %.'))
    elif report['status'] in ('nonstationary','inconclusive'):
        st.warning(message+'.')
    else:
        st.info(message+'.')
    for message in report['warnings']:
        st.caption(message)
    if report['kpss_bound']!='=':
        st.caption(f"KPSS devuelve un límite tabulado: p {report['kpss_bound']} {report['kpss_p']:.2f}; no es un p-valor exacto.")


def render(monthly, sales, codes, palette):
    blue,light,_=PALETTES[palette]
    fig=go.Figure()
    for label,color in [('Personas naturales',blue),('Sociedades',light)]:
        timeline=monthly.set_index('Periodo')[label].reindex(pd.date_range(monthly.Periodo.min(),monthly.Periodo.max(),freq='MS'))
        fig.add_trace(go.Scatter(x=timeline.index,y=timeline,name=label,mode='lines',connectgaps=False,line=dict(color=color,width=2)))
    fig.update_layout(title='Serie mensual original · ventas 411 + 413',xaxis_title='Mes',yaxis_title='USD',
                      legend=dict(orientation='h'),paper_bgcolor='white',plot_bgcolor='white')
    st.plotly_chart(theme_figure(fig,palette),width='stretch',key='industry_monthly')
    with st.expander('Diagnóstico y transformación de la serie mensual',expanded=True):
        st.caption('Revisa tendencia, estacionalidad anual y amplitud de las oscilaciones antes de transformar. Este análisis usa todos los meses disponibles; no se recorta por el deslizador del acumulado anual.')
        measure=st.selectbox('Serie para analizar',['Ventas totales','Personas naturales','Sociedades'],key='ts_measure')
        mode=st.selectbox('Cobertura del diagnóstico',['Panel fijo comparable','Cobertura completa de todos los CIIU'],key='ts_coverage_mode')
        complete,coverage=complete_monthly(sales,codes)
        if complete.empty:
            st.info('No hay datos para el análisis mensual.')
            return
        panel_detail=None
        if mode=='Panel fijo comparable':
            source,panel_detail=comparable_panel(sales,codes,measure)
            count=int(panel_detail.Incluida.sum()) if len(panel_detail) else 0
            excluded=len(panel_detail)-count
            if excluded:
                st.info(f'Panel comparable: se conservan {count} de {len(panel_detail)} casillas CIIU/campo, las mismas durante todo el período. Se excluyen {excluded} casillas con información ausente en algún mes. Los vacíos no se convierten en cero. La suma representa este subconjunto informado, no el total completo de los sectores.')
            else:
                st.caption(f'Panel comparable completo: {count} casillas informadas durante todo el período.')
            with st.expander('Ver casillas incluidas y excluidas del panel'):
                st.dataframe(panel_detail,hide_index=True,width='stretch')
        else:
            source=complete[measure]
        block=longest_monthly_block(source)
        missing=int(source.isna().sum())
        if missing and mode!='Panel fijo comparable':
            st.warning(f'{missing} meses sin cobertura completa de las casillas de los CIIU seleccionados. No se imputan ceros ni se comprime el calendario. Las pruebas usan el tramo continuo más largo; ante empate, el más reciente.')
        if block.empty:
            st.info('No hay observaciones utilizables con esta cobertura. Prueba Sociedades, cambia el método de cobertura o revisa los CIIU seleccionados.')
            with st.expander('Cobertura por mes'):
                st.dataframe(coverage[[measure]].rename(columns={measure:'Proporción de casillas informadas'}),width='stretch')
            return
        st.caption(f"Tramo de análisis: {block.index[0]:%m/%Y} – {block.index[-1]:%m/%Y} · {len(block)} meses · {mode}. La serie analizada puede diferir del agregado original superior; su composición permanece fija.")
        if len(block)<60:
            st.caption('La historia es corta: las pruebas tienen poder limitado y hay pocos ciclos anuales para evaluar estacionalidad.')
        reg=st.selectbox('Componente determinístico en las pruebas de niveles',
                        ['Constante','Constante y tendencia'],key='ts_regression')
        regression='c' if reg=='Constante' else 'ct'
        st.markdown('**1–2. Serie en niveles, ACF y pruebas**')
        left,right=st.columns(2)
        with left:
            line_chart(block,'Niveles y media móvil', 'USD',palette,'ts_levels',rolling=True)
        with right:
            acf_chart(block,palette,'ts_acf_levels')
        levels=stationarity(block,regression)
        st.dataframe(pd.DataFrame([report_row('Niveles',levels)]),hide_index=True,width='stretch')
        show_tests(levels)
        st.caption('ADF: H₀ = raíz unitaria; p < 0,05 permite rechazarla. KPSS: H₀ = estacionariedad (en nivel o alrededor de tendencia, según selección); p > 0,05 no permite rechazarla. La coincidencia aporta evidencia, no una garantía.')
        with st.expander('Revisar amplitud de las oscilaciones'):
            line_chart(block.rolling(12,min_periods=12).std(),'Desviación estándar móvil · 12 meses','USD',palette,'ts_variance')
            st.caption('Compara esta amplitud con el nivel de la serie. Una amplitud creciente puede justificar log o Box-Cox; este gráfico por sí solo no lo demuestra.')
        st.markdown('**3–5. Elegir transformación y diferencias**')
        a,b,c=st.columns([2,1,1])
        with a:
            kind=st.selectbox('Transformación de varianza',['Niveles','Logaritmo','Box-Cox'],key='ts_kind')
        with b:
            d=int(st.number_input('Diferencias regulares · d',min_value=0,max_value=2,value=0,step=1,key='ts_d'))
        with c:
            D=int(st.number_input('Diferencias estacionales · D',min_value=0,max_value=1,value=0,step=1,key='ts_D'))
        s=12
        st.caption('Frecuencia mensual: s = 12. Prueba D = 1 con d = 0 antes de combinar ambas diferencias, cuando exista evidencia de estacionalidad.')
        detrend=st.checkbox('Eliminar tendencia lineal determinística en lugar de diferenciar',key='ts_detrend',disabled=bool(d or D)) and not (d or D)
        try:
            transformed,base,meta=transform(block,kind,d,D,s,detrend)
        except ValueError as exc:
            st.warning(str(exc))
            return
        if meta['boxcox_lambda'] is not None:
            st.caption(f"Box-Cox: λ estimado por máxima verosimilitud = {meta['boxcox_lambda']:.4f}. λ = 0 corresponde al logaritmo; no implica que la serie ya sea estacionaria.")
        if kind!='Niveles' or detrend:
            line_chart(base,'Serie base antes de diferenciar',kind if not detrend else 'Residuos sin tendencia',palette,'ts_base')
        if kind=='Logaritmo' and d==1 and D==0:
            st.caption('Δlog(y) es crecimiento mensual aproximado; multiplícalo por 100 para expresarlo en porcentaje. El crecimiento exacto es 100·(exp(Δlog(y))−1).')
        st.markdown('**6–7. Serie resultante y repetición de pruebas**')
        left,right=st.columns(2)
        with left:
            line_chart(transformed,'Serie transformada','USD' if kind=='Niveles' else kind,palette,'ts_transformed')
        with right:
            acf_chart(transformed,palette,'ts_acf_transformed')
        final=stationarity(transformed,'c') if (d or D or detrend) else stationarity(transformed,regression)
        st.dataframe(pd.DataFrame([report_row('Niveles',levels),report_row(f'{kind} · d={d}, D={D}, s=12',final)]),hide_index=True,width='stretch')
        show_tests(final)
        for flag in differencing_flags(block,transformed,kind,d,D,s):
            st.warning(flag)
        if d==2:
            first,_,_=transform(block,kind,1,D,s)
            if stationarity(first,'c')['status']=='stationary':
                st.warning('Las pruebas ya eran compatibles con estacionariedad con d = 1. Revisa si la segunda diferencia es necesaria.')
        with st.expander('Comparar alternativas antes de elegir el orden'):
            rows=[]
            for regular,seasonal in [(0,0),(1,0),(0,1),(1,1)]:
                alternative,_,_=transform(block,kind,regular,seasonal,s)
                test=stationarity(alternative,regression if regular==seasonal==0 else 'c')
                rows.append(dict(d=regular,D=seasonal,s=s,**report_row(kind,test)))
                if regular==1 and test['status'] in ('nonstationary','inconclusive'):
                    second,_,_=transform(block,kind,2,seasonal,s)
                    rows.append(dict(d=2,D=seasonal,s=s,**report_row(kind,stationarity(second,'c'))))
            st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
            st.caption('Las alternativas no cambian tu selección ni prueban cuál modelo pronosticará mejor. La segunda diferencia se muestra solo si la primera no aporta evidencia coincidente.')
        st.markdown('**8. Orden aplicado para una evaluación posterior de ARIMA/SARIMA**')
        st.code(f'Transformación: {kind}\nd = {d} · D = {D} · s = {s}\nTendencia lineal eliminada: {"sí" if detrend else "no"}')
        st.caption('Estos son los órdenes aplicados, no una identificación definitiva del orden de integración. ADF/KPSS no prueban raíces estacionales; p, q, P y Q quedan por estimar. No se ajusta ni se pronostica un modelo en este paso.')
        exported=pd.concat([source.rename('Original del diagnóstico'),base.rename('Base transformada'),
                            transformed.rename('Resultado')],axis=1)
        info=f'# Serie: {measure}\n# Cobertura: {mode}\n# CIIU: {", ".join(sorted(set(codes)))}\n# {kind}; d={d}; D={D}; s={s}; lambda={meta["boxcox_lambda"]}; detrend={detrend}\n'
        st.download_button('Descargar serie y transformación',
                           (info+exported.to_csv(sep=';',decimal=',',index_label='Mes')).encode('utf-8-sig'),
                           file_name='serie_mensual_transformacion.csv',mime='text/csv',key='ts_download')
        if panel_detail is not None:
            st.download_button('Descargar composición del panel',panel_detail.to_csv(index=False,sep=';').encode('utf-8-sig'),
                               file_name='composicion_panel_mensual.csv',mime='text/csv',key='ts_panel_download')

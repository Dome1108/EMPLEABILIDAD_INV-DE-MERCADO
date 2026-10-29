"""Perfil laboral descriptivo de la selección vinculada a una carrera."""
from html import escape
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from palettes import PALETTES, theme_figure


def estilo(fig,altura=320):
    fig.update_layout(height=altura,paper_bgcolor='white',plot_bgcolor='white',
        font=dict(color='#65748a'),margin=dict(l=25,r=30,t=35,b=50),
        legend=dict(orientation='h',y=-.15))
    fig.update_xaxes(automargin=True,gridcolor='#edf0f4')
    fig.update_yaxes(automargin=True,gridcolor='#edf0f4')
    return theme_figure(fig, st.session_state.get("color_palette", "Azul"))


def render_perfil(context,key):
    primary,light,muted=PALETTES[st.session_state.get("color_palette","Azul")]
    frame=pd.DataFrame(context.get('empleo',[])).sort_values('year')
    if frame.empty:
        st.info('No hay datos laborales para esta selección.')
        return
    st.markdown('### Empleabilidad nacional')
    previous=None
    for col,row in zip(st.columns(len(frame)),frame.to_dict('records')):
        rate=row.get('rate')
        delta=None if previous is None or pd.isna(rate) or pd.isna(previous) else f'{rate-previous:+.1f} pp'
        with col:
            st.metric(str(row['year']),f'{rate:.1f}%' if pd.notna(rate) else 'Sin dato',delta=delta)
            st.caption('Tasa de empleo visible · '+str(row.get('cutoff','')))
        previous=rate
    latest=frame.iloc[-1]
    left,right=st.columns([1,1.15])
    with left,st.container(border=True):
        st.markdown('**Composición del empleo**')
        counts=[latest.get(k) for k in ('dependent','independent','unknown')]
        if all(pd.notna(v) for v in counts) and sum(counts)>0:
            fig=go.Figure(go.Pie(labels=['Dependientes','Independientes','Sin información laboral'],values=counts,
                hole=.75,sort=False,marker=dict(colors=[primary,light,muted],line=dict(color='white',width=3)),
                textinfo='percent',hovertemplate='%{label}: %{value:,.0f} · %{percent}<extra></extra>'))
            fig.add_annotation(x=.5,y=.5,text=f"<b>{latest['rate']:.1f}%</b><br>empleo visible",showarrow=False,font=dict(size=22,color=primary))
            st.plotly_chart(estilo(fig,360),width='stretch',theme=None,key='perfil_composicion_'+key)
        else:st.info('Sin datos de composición del empleo.')
    with right:
        with st.container(border=True):
            st.markdown('**Banda salarial · rango intercuartílico**')
            low,high=latest.get('p25'),latest.get('p75')
            if pd.notna(low) and pd.notna(high):
                fig=go.Figure(go.Scatter(x=[low,high],y=[0,0],mode='lines+markers+text',
                    text=[f'P25 · USD {low:,.0f}',f'P75 · USD {high:,.0f}'],textposition=['top center','bottom center'],
                    line=dict(color=primary,width=7),marker=dict(size=18),hovertemplate='USD %{x:,.2f}<extra></extra>'))
                fig.update_yaxes(visible=False,range=[-1,1]);fig.update_xaxes(title='Ingreso mensual · USD',tickprefix='$')
                st.plotly_chart(estilo(fig,210),width='stretch',theme=None,key='perfil_salario_'+key)
                st.caption(f"Personas con salario: {latest.get('salary_n',0):,.0f} · corte {latest['cutoff']}")
            else:st.info('Sin salarios suficientes para calcular la banda.')
        territory=context.get('territorio')
        if territory:
            with st.container(border=True):
                st.markdown('**Empleabilidad · '+escape(territory['nombre'])+'**')
                t=territory['resumen'];n=t['graduates']
                st.metric('Empleo visible',f"{t['rate']:.1f}%" if n else 'Sin dato')
                if n:
                    st.caption(' · '.join(f'{label}: {100*t[field]/n:.1f}%' for label,field in [('Dependientes','dependent'),('Independientes','independent'),('Sin información','unknown')]))
                st.caption('Por domicilio · corte '+territory['corte'])
        else:st.caption('Consulta la distribución territorial en Empleabilidad y mercado para incorporar una zona.')
    sector=context.get('sector',{})
    macro=pd.DataFrame(sector.get('macroindustrias',[]))
    if not macro.empty:
        st.markdown('### Principales sectores')
        macro=macro.sort_values('Ventas totales',ascending=True,na_position='first')
        fig=go.Figure()
        for label,color in [('Personas naturales',primary),('Sociedades',light)]:
            fig.add_trace(go.Bar(x=macro[label],y=macro['Macroindustria'],name=label,orientation='h',marker_color=color,
                hovertemplate='%{y}<br>USD %{x:,.2f}<extra>%{fullData.name}</extra>'))
        fig.update_layout(barmode='stack');fig.update_xaxes(title='USD · ventas 411 + 413')
        st.plotly_chart(estilo(fig,530),width='stretch',theme=None,key='perfil_sectores_'+key)
        st.caption('Ventas de los CIIU seleccionados · '+sector['periodo_macro']+'. B = miles de millones; M = millones.')
    companies=pd.DataFrame(sector.get('empresas',[]))
    if not companies.empty:
        st.markdown('### Principales empresas')
        st.dataframe(companies,hide_index=True,width='stretch',column_config={
            'Participación (%)':st.column_config.NumberColumn(format='%.1f%%')})
        st.caption('Graduados únicos por empresa / graduados con empleador identificado. Una persona puede tener varios empleadores. Corte: '+sector['corte_laboral'])
    st.caption('Fuente: registros laborales SIM y SRI del observatorio; salarios de dependientes. No se atribuyen estos datos al INEC.')

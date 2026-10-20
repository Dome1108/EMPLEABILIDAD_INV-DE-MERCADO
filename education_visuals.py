"""Vista compacta de educación y exportación para diapositivas 16:9."""
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analytics import PRIVATE_ALIASES, institution_key

BLUE = '#087BCC'
LIGHT = '#76BDED'
VISUAL_LAYOUT_VERSION = 2
PUBLIC_LABELS = {
    'UNIVERSIDAD DE GUAYAQUIL': 'U. de Guayaquil',
    'UNIVERSIDAD CENTRAL DEL ECUADOR': 'U. Central del Ecuador',
    'ESCUELA SUPERIOR POLITECNICA DEL LITORAL': 'ESPOL',
    'ESCUELA POLITECNICA NACIONAL': 'EPN',
    'UNIVERSIDAD TECNICA DE MANABI': 'U. Técnica de Manabí',
    'UNIVERSIDAD TECNICA DE MACHALA': 'U. Técnica de Machala',
    'UNIVERSIDAD AGRARIA DEL ECUADOR': 'U. Agraria del Ecuador',
    'UNIVERSIDAD TECNICA ESTATAL DE QUEVEDO': 'U. Estatal de Quevedo',
    'UNIVERSIDAD LAICA ELOY ALFARO DE MANABI': 'ULEAM',
    'UNIVERSIDAD CATOLICA DE SANTIAGO DE GUAYAQUIL': 'UCSG',
    'UNIVERSIDAD LAICA VICENTE ROCAFUERTE DE GUAYAQUIL': 'ULVR',
    'UNIVERSIDAD DE CUENCA': 'U. de Cuenca',
    'UNIVERSIDAD TECNICA DE AMBATO': 'U. Técnica de Ambato',
}


def short_name(name):
    key = institution_key(name)
    label = PRIVATE_ALIASES.get(key) or PUBLIC_LABELS.get(key)
    if label:
        return label
    label = str(name).replace('UNIVERSIDAD', 'U.').replace('ESCUELA SUPERIOR POLITECNICA', 'E. Politécnica').title()
    return label if len(label) <= 30 else label[:29].rstrip()+'…'


def education_panels(national, private):
    national = national.rename(columns={'INSTITUCION_EDUCACION_SUPERIOR':'institution'}).copy()
    national['label'] = national['institution'].map(short_name)
    private = private.copy()
    private['label'] = private['code']
    return tuple(data.sort_values(['professionals','institution'], ascending=[False,True]).head(10).reset_index(drop=True)
                 for data in (national, private))


def education_figure(panels):
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=.23,
                        subplot_titles=['Nacional · top 10', 'Privadas Sierra · top 10'])
    for col, data in enumerate(panels, 1):
        data = data.iloc[::-1]
        y = np.arange(len(data))
        for pos, (_, item) in enumerate(data.iterrows()):
            fig.add_trace(go.Scatter(x=[item.recent,item.professionals], y=[pos,pos], mode='lines',
                line=dict(color='#cfdeec',width=3),showlegend=False,hoverinfo='skip'),row=1,col=col)
        for field, label, color in [('recent','Recién titulados',LIGHT),('professionals','Profesionales históricos',BLUE)]:
            fig.add_trace(go.Scatter(x=data[field].tolist(),y=y.tolist(),mode='markers',name=label,
                legendgroup=field,showlegend=col==1,marker=dict(color=color,size=10),customdata=data.institution.tolist(),
                hovertemplate='%{customdata}<br>'+label+': %{x:,.0f}<extra></extra>'),row=1,col=col)
        fig.update_yaxes(tickvals=y.tolist(),ticktext=data.label.tolist(),range=[-.65,max(len(data)-.35,.65)],
            showgrid=False,zeroline=False,tickfont=dict(size=12),row=1,col=col)
        maximum = max(float(data.professionals.max()), float(data.recent.max()), 1) if len(data) else 1
        fig.update_xaxes(side='bottom',range=[-maximum*.025,maximum*1.06],nticks=4,
            gridcolor='#eef3f8',zeroline=False,tickformat=',.0f',row=1,col=col)
    fig.update_layout(height=510,margin=dict(l=165,r=25,t=75,b=100),
        paper_bgcolor='white',plot_bgcolor='white',separators=',.',
        font=dict(family='Arial',color='#476783',size=12),
        legend=dict(orientation='h',x=.5,xanchor='center',y=-.23,yanchor='top'),
        hoverlabel=dict(bgcolor='white'))
    # Títulos arriba, escalas abajo: ocupan zonas separadas al redimensionar.
    for annotation, axis in zip(fig.layout.annotations, (fig.layout.xaxis, fig.layout.xaxis2)):
        annotation.update(x=axis.domain[0], xanchor='left', y=1, yanchor='bottom', yshift=25,
                          font=dict(size=16,color='#123F70'))
    return fig


def education_png(panels, year, careers, demo=False):
    """Una sola imagen 2560x1440 con los dos gráficos, sin dependencias de navegador."""
    fig = Figure(figsize=(16,9),dpi=160,facecolor='white')
    fig.subplots_adjust(left=.15,right=.96,top=.76,bottom=.17,wspace=.67)
    axes = fig.subplots(1,2)
    fig.text(.045,.925,'EDUCACIÓN',fontsize=26,weight='bold',color='#123F70')
    selected = ' · '.join(careers)
    if len(selected)>125:
        selected=selected[:122]+'…'
    fig.text(.045,.878,f'{year}  |  {selected}',fontsize=12,color='#6a8299')
    if demo:
        fig.text(.96,.93,'DEMOSTRACIÓN · DATOS SINTÉTICOS',ha='right',fontsize=10,color='#6a8299')
    for ax, data, title in zip(axes,panels,['Nacional · top 10','Privadas Sierra · top 10']):
        data=data.iloc[::-1]
        y=np.arange(len(data))
        ax.hlines(y,data.recent,data.professionals,color='#cfdeec',linewidth=2,zorder=1)
        recent=ax.scatter(data.recent,y,c=LIGHT,s=55,zorder=3,label='Recién titulados')
        historical=ax.scatter(data.professionals,y,c=BLUE,s=55,zorder=3,label='Profesionales históricos')
        ax.set_yticks(y, data.label,fontsize=11,color='#476783')
        ax.set_ylim(-.7,max(len(data)-.3,.7))
        maximum=max(float(data.professionals.max()),float(data.recent.max()),1) if len(data) else 1
        ax.set_xlim(-maximum*.025,maximum*1.08)
        ax.set_axisbelow(True)
        ax.grid(axis='x',color='#eef3f8')
        ax.xaxis.tick_bottom()
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(4,integer=True))
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda n,_:f'{n:,.0f}'.replace(',','.')))
        ax.tick_params(axis='both',length=0,labelcolor='#6a8299',pad=9)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_title(title,loc='left',fontsize=16,color='#123F70',weight='bold',pad=20)
    fig.legend(handles=[recent,historical],loc='lower center',bbox_to_anchor=(.5,.06),ncol=2,frameon=False,fontsize=12)
    output=BytesIO()
    fig.savefig(output,format='png',facecolor='white')
    return output.getvalue()

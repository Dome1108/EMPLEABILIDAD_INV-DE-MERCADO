"""Vista compacta de educación y exportación para diapositivas 16:9."""
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analytics import PRIVATE_ALIASES, institution_key
from palettes import PALETTES, theme_colors, theme_figure

BLUE = '#087BCC'
LIGHT = '#76BDED'
VISUAL_LAYOUT_VERSION = 2
# Cambia cuando cambian los gráficos de mercado; las sesiones abiertas recargan el módulo.
MARKET_VISUAL_VERSION = 3
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


def education_figure(panels, palette="Azul"):
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
    return theme_figure(fig, palette)


def education_png(panels, year, careers, demo=False, palette="Azul"):
    """Una sola imagen 2560x1440 con los dos gráficos, sin dependencias de navegador."""
    blue, light, _ = PALETTES[palette]
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
        recent=ax.scatter(data.recent,y,c=light,s=55,zorder=3,label='Recién titulados')
        historical=ax.scatter(data.professionals,y,c=blue,s=55,zorder=3,label='Profesionales históricos')
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
    if palette != "Azul":
        from matplotlib.colors import to_hex
        for artist in fig.findobj():
            if hasattr(artist, 'get_color') and hasattr(artist, 'set_color'):
                color = artist.get_color()
                if isinstance(color, str):
                    artist.set_color(theme_colors(to_hex(color), palette))
        for ax in axes:
            for collection in ax.collections:
                if hasattr(collection, 'get_colors') and len(collection.get_colors()):
                    collection.set_color([theme_colors(to_hex(c), palette) for c in collection.get_colors()])
    fig.savefig(output,format='png',facecolor='white')
    return output.getvalue()


# --- Mercado académico: matriculados, titulados y precios ---

NAVY = '#123F70'
UDLA_COLOR = '#E8590C'
SERIES_LABELS = {'PUBLICO': 'Público', 'PRIVADO': 'Privado', 'NO CLASIFICADO': 'No clasificado'}


def _market_layout(fig, height, palette):
    fig.update_layout(height=height, margin=dict(l=10, r=20, t=30, b=20), barmode='stack',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', separators=',.',
        font=dict(family='DM Sans, Arial', color='#617d99', size=12),
        legend=dict(orientation='h', x=0, y=-.14, yanchor='top'),
        hoverlabel=dict(bgcolor='white', font_size=13), bargap=.35)
    fig.update_xaxes(type='category', showgrid=False)
    fig.update_yaxes(gridcolor='#edf2f9', zeroline=False, tickformat=',.0f', rangemode='tozero')
    return theme_figure(fig, palette)


def trend_figure(table, measure, palette='Azul', projected=()):
    """Barras apiladas por financiamiento y línea del total, una escala. Años proyectados se marcan con '*'."""
    blue, light, muted = PALETTES['Azul']
    colors = {'PUBLICO': blue, 'PRIVADO': light, 'NO CLASIFICADO': muted}
    years = list(table.columns)
    labels = [f'{year}*' if year in projected else str(year) for year in years]
    fig = go.Figure()
    for row in [r for r in table.index if r != 'TOTAL']:
        values = table.loc[row].tolist()
        fig.add_trace(go.Bar(x=labels, y=values, name=SERIES_LABELS.get(row, row.title()),
            # Opacidad fija: 2025* con el mismo color que los demás años.
            marker=dict(color=colors.get(row, muted), opacity=1, line=dict(color='white', width=2)),
            hovertemplate='%{x} · ' + SERIES_LABELS.get(row, row) + '<br>%{y:,.0f} ' + measure + '<extra></extra>'))
    total = table.loc['TOTAL'].tolist()
    fig.add_trace(go.Scatter(x=labels, y=total, name='Total', mode='lines+markers+text',
        line=dict(color=NAVY, width=2), marker=dict(size=8, color=NAVY),
        text=[f'{v:,.0f}'.replace(',', '.') for v in total], textposition='top center',
        textfont=dict(color='#476783', size=11),
        hovertemplate='%{x} · Total<br>%{y:,.0f} ' + measure + '<extra></extra>'))
    fig.update_yaxes(title=measure.capitalize(), range=[0, max(max(total, default=0), 1) * 1.18])
    return _market_layout(fig, 380, palette)


def _own_reference(fig, data, own, info):
    """Arancel UDLA que no es un punto del mercado: estimado por facultad o real vía CARRERA_UDLA."""
    if not info or info.get('arancel') is None or data.SIGLA.eq(own).any():
        return
    price = info['arancel']
    if info['tipo'] == 'estimado':
        careers = info.get('carreras_referencia') or []
        listed = '<br>'.join(f'· {c.title()}' for c in careers[:8]) + ('<br>…' if len(careers) > 8 else '')
        hover = (f'<b>Arancel UDLA estimado: ${price:,.0f}</b><br>Facultad: {info["facultad"].title()}'
                 f'<br>Nivel: {info["nivel"].title()}<br>Periodo: {info["periodo"]}'
                 + (' (estimación histórica)' if info.get('historico') else '')
                 + f'<br>Carreras utilizadas: {info["numero_carreras"]}<br>{listed}<extra></extra>')
        label, symbol, dash = 'UDLA estimado', 'diamond-open', 'dash'
    else:
        origin = (f'Carrera UDLA: {info["carrera_udla"].title()}' if info.get('carrera_udla')
                  else info.get('fuente', 'Oferta UDLA'))
        hover = f'<b>Arancel UDLA: ${price:,.0f}</b><br>{origin}<br>Periodo: {info["periodo"]}<extra></extra>'
        label, symbol, dash = own, 'diamond', 'solid'
    # Línea a lo ancho de la caja: referencia, no un punto más de la distribución.
    fig.add_shape(type='line', x0=-.42, x1=.42, y0=price, y1=price,
                  line=dict(color=UDLA_COLOR, width=2, dash=dash))
    fig.add_trace(go.Scatter(x=[.5], y=[price], mode='markers+text', name=label, text=[label],
        textposition='middle right', textfont=dict(color=NAVY, size=12),
        marker=dict(symbol=symbol, size=14, color=UDLA_COLOR, line=dict(color=UDLA_COLOR, width=2)),
        hovertemplate=hover))


def price_boxplot(table, career='', palette='Azul', own='UDLA', own_info=None):
    """Boxplot vertical del arancel representativo por institución con un punto etiquetado por SIGLA.

    own_info (obtener_arancel_udla) agrega el arancel UDLA cuando no es una oferta del mercado:
    «UDLA estimado» con línea discontinua y marcador hueco, o «UDLA» si es real vía CARRERA_UDLA.
    """
    blue, light, _ = PALETTES['Azul']
    data = table.dropna(subset=['ARANCEL_PROMEDIO']).sort_values('ARANCEL_PROMEDIO').reset_index(drop=True)
    fig = go.Figure()
    if data.empty:
        fig.add_annotation(text='No hay aranceles válidos para los filtros seleccionados.', x=.5, y=.5,
            xref='paper', yref='paper', showarrow=False, font=dict(color='#68809b', size=14))
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        return _market_layout(fig, 420, palette)
    fig.add_trace(go.Box(y=data.ARANCEL_PROMEDIO, x=[0] * len(data), name='Mercado', boxpoints=False,
        width=.55, fillcolor='rgba(118,189,237,.25)', line=dict(color=blue, width=2), showlegend=False,
        hoverinfo='y', boxmean=False))
    # Desplazamiento alterno determinista: puntos a ambos lados del eje con su sigla hacia afuera.
    side = np.where(np.arange(len(data)) % 2 == 0, 1, -1)
    x = side * (.08 + .1 * ((np.arange(len(data)) // 2) % 3))
    customdata = data.assign(CARRERA=career, FINANCIAMIENTO=data.FINANCIAMIENTO.astype(object).fillna('—'),
        SEMESTRE_POS=data.SEMESTRE_POS.astype(str))[
        ['ARANCEL_MINIMO', 'ARANCEL_MAXIMO', 'SEMESTRE_POS', 'CARRERA', 'FINANCIAMIENTO']].to_numpy(dtype=object)
    for name, mask, color, size in [('Instituciones', data.SIGLA.ne(own).to_numpy(), blue, 10),
                                    (own, data.SIGLA.eq(own).to_numpy(), UDLA_COLOR, 14)]:
        if not mask.any():
            continue
        fig.add_trace(go.Scatter(x=x[mask], y=data.ARANCEL_PROMEDIO[mask], mode='markers+text', name=name,
            text=data.SIGLA[mask], textposition=['middle right' if s > 0 else 'middle left' for s in side[mask]],
            textfont=dict(color=NAVY if name == own else '#476783', size=12 if name == own else 11),
            marker=dict(color=color, size=size, line=dict(color='white', width=2)),
            customdata=customdata[mask],
            hovertemplate=('<b>%{text}</b><br>Arancel promedio: $%{y:,.2f}'
                           '<br>Rango: $%{customdata[0]:,.2f} – $%{customdata[1]:,.2f}'
                           '<br>Semestre: %{customdata[2]}<br>Carrera: %{customdata[3]}'
                           '<br>Financiamiento: %{customdata[4]}<extra></extra>')))
    _own_reference(fig, data, own, own_info)
    fig.update_layout(title=dict(text='Distribución de aranceles del mercado', x=0, font=dict(size=16, color=NAVY)))
    fig = _market_layout(fig, 520, palette)
    fig.update_layout(margin=dict(l=10, r=20, t=55, b=20), legend=dict(y=-.06))
    fig.update_xaxes(type='linear', range=[-.9, .9], visible=False)
    fig.update_yaxes(title='Arancel (USD)', tickprefix='$', rangemode='normal')
    return fig

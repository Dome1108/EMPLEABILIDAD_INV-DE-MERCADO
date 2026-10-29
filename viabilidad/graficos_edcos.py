"""Radar EdCo con los mismos ejes del modelo de carreras."""
import plotly.graph_objects as go

EJES_EDCO=['Demanda','Empleabilidad','Competencia','Precio','Sector económico']


def monedas_precio(ficha):
    return [currency for currency in ('USD','CRC') if any(o['tipo']=='Institucional' and o.get('precio_'+currency.lower()) is not None and o.get('precio_verificado',True) for o in ficha['ofertas'])]


def moneda_precio(ficha):
    return ficha.get('evidencia_visual',{}).get('precio',{}).get('moneda',next(iter(monedas_precio(ficha)),'USD'))


def ofertas_precio(ficha,moneda=None):
    field='precio_'+(moneda or moneda_precio(ficha)).lower()
    return [o for o in ficha['ofertas'] if o['tipo']=='Institucional' and o.get(field) is not None and o.get('precio_verificado',True)]


def grafico_dimension(ficha, dimension):
    """Evidencia descriptiva; no inventa series ni subpuntajes de la rúbrica."""
    fig=go.Figure()
    evidence=ficha.get('evidencia_visual',{}).get(dimension,{})
    if dimension=='demanda':
        rows=evidence.get('serie',[])
        for i,term in enumerate(dict.fromkeys(r['termino'] for r in rows)):
            values=sorted((r for r in rows if r['termino']==term),key=lambda r:r['fecha'])
            fig.add_trace(go.Scatter(x=[r['fecha'] for r in values],y=[r['indice'] for r in values],
                mode='lines+markers',name=term,line=dict(color=['#3975b9','#91bbdf'][i%2]),
                hovertemplate='%{x}<br>Interés: %{y:g}/100<extra>%{fullData.name}</extra>'))
        fig.update_xaxes(title='Mes',type='date')
        fig.update_yaxes(title='Interés relativo de Google Trends',range=[0,105])
        if not rows:
            observations=evidence.get('observaciones',[])
            if observations:
                fig.add_trace(go.Bar(x=[r['valor'] for r in observations],y=[r['etiqueta'] for r in observations],orientation='h',
                    marker_color='#3975b9',text=[f"{r['valor']:,.0f}" for r in observations],textposition='outside',
                    hovertemplate='%{y}<br>%{x:,.0f} inscripciones acumuladas<br>Ubicación no desglosada<extra></extra>'))
                fig.update_xaxes(title='Participación acumulada publicada · no son búsquedas',type='linear',rangemode='tozero')
                fig.update_yaxes(title='',range=None,autorange='reversed',type='category')
            else:
                fig.add_annotation(text='Google Trends: acceso limitado; sin serie verificable',x=.5,y=.5,xref='paper',yref='paper',showarrow=False)
    elif dimension=='empleabilidad':
        rows=evidence.get('habilidades',[])
        is_local=evidence.get('origen')=='linkedin'
        if is_local:
            rows=sorted(rows,key=lambda r:-r['menciones'])[:10]
        fig.add_trace(go.Bar(x=[r['porcentaje'] if is_local else r['importancia'] for r in rows],y=[r['habilidad'] for r in rows],orientation='h',
            marker_color=['#3975b9' if r['cobertura']=='Explícita' else '#a7c6e2' for r in rows],
            text=[f"{r['porcentaje']:.1f}%" if is_local else str(r['importancia']) for r in rows],textposition='outside',
            customdata=['Habilidad explícita' if r['cobertura']=='Explícita' else 'Habilidad homologada · asociación analítica por revisar' for r in rows],
            hovertemplate='%{y}<br>Participación: %{x:.1f}% de las publicaciones revisadas<br>Cobertura del brief: %{customdata}<extra></extra>' if is_local else '%{y}<br>Importancia O*NET: %{x}/100<br>Cobertura del brief: %{customdata}<extra></extra>'))
        fig.update_xaxes(title='Participación por habilidad (%)' if is_local else 'Importancia ocupacional O*NET · escala 0–100',range=[0,110],ticksuffix='%' if is_local else '')
        fig.update_yaxes(autorange='reversed')
        if is_local:fig.update_layout(height=430)
    elif dimension=='competencia':
        rows=evidence.get('matriz',[])
        cut_x=evidence.get('umbral_busquedas',75)
        cut_y=evidence.get('umbral_competidores',3)
        ymax=max([6,cut_y+3]+[r['competidores']+1 for r in rows])
        for x0,x1,y0,y1,color in [(0,cut_x,0,cut_y,'#fbf0f2'),(cut_x,100,0,cut_y,'#edf7f1'),(0,cut_x,cut_y,ymax,'#eef2f6'),(cut_x,100,cut_y,ymax,'#faf6eb')]:
            fig.add_shape(type='rect',x0=x0,x1=x1,y0=y0,y1=y1,fillcolor=color,line_width=0,layer='below')
        fig.add_vline(x=cut_x,line_dash='dash',line_color='#9babbb')
        fig.add_hline(y=cut_y,line_dash='dash',line_color='#9babbb')
        for text,x,y in [('BAJA TRACCIÓN',cut_x/2,.3),('MERCADO ATRACTIVO',(cut_x+100)/2,.3),('MERCADO DÉBIL',cut_x/2,ymax-.3),('MERCADO COMPETIDO',(cut_x+100)/2,ymax-.3)]:
            fig.add_annotation(x=x,y=y,text=text,showarrow=False,font=dict(size=10,color='#72869c'))
        if rows:
            fig.add_trace(go.Scatter(x=[r['busquedas'] for r in rows],y=[r['competidores'] for r in rows],text=[r['programa'] for r in rows],mode='markers',marker=dict(color='#3975b9',size=13),hovertemplate='%{text}<br>Búsquedas: %{x}/100<br>Competidores: %{y}<extra></extra>'))
        else:
            fig.add_annotation(text='Oferta revisada · búsquedas sin serie verificable<br>No se asigna posición horizontal',x=.5,y=.5,xref='paper',yref='paper',showarrow=False,bgcolor='white',borderpad=10)
        fig.update_xaxes(title='Interés de búsqueda · índice comparable 0–100',range=[0,100])
        fig.update_yaxes(title='Competidores comparables activos',range=[0,ymax],dtick=1)
    elif dimension=='precio':
        currency=moneda_precio(ficha)
        field='precio_'+currency.lower()
        offers=ofertas_precio(ficha)
        fig.add_trace(go.Box(y=[o[field] for o in offers],x=[0]*len(offers),name='Mercado',boxpoints=False,
            quartilemethod='linear',fillcolor='rgba(57,117,185,.20)',line=dict(color='#0076ba',width=2),width=.5,
            hovertemplate='Distribución de precios publicados<extra></extra>'))
        fig.add_trace(go.Scatter(x=[-.06+.12*i/max(1,len(offers)-1) for i in range(len(offers))],y=[o[field] for o in offers],
            mode='markers+text',marker=dict(color='#3975b9',size=15),
            text=[o.get('etiqueta_precio',o['institucion']) for o in offers],textposition=['bottom right' if i%2==0 else 'top right' for i in range(len(offers))] if ficha.get('institucion_id')=='ulatina_cr' else 'middle right',
            customdata=[o['estado'] for o in offers],hovertemplate='%{text}<br>'+currency+' %{y:,.0f}<br>%{customdata}<extra></extra>'))
        fig.update_xaxes(visible=False,range=[-.7,.9])
        fig.update_yaxes(title='Arancel total publicado · '+currency,rangemode='tozero',tickprefix='₡' if currency=='CRC' else '$')
    elif dimension=='sector':
        if evidence.get('origen')=='bccr':
            rows=evidence['serie_indice']
            fig.add_trace(go.Scatter(x=[r['fecha'] for r in rows],y=[r['valor'] for r in rows],mode='lines+markers',name=evidence['actividad'],line=dict(color='#3975b9',width=3),hovertemplate='%{x}<br>Índice: %{y:.1f}<extra></extra>'))
            fig.update_xaxes(type='date',title='Mes · serie original',dtick='M2',tickformat='%b %Y')
            fig.update_yaxes(title=dict(text=f"IMAE · base {evidence.get('base',2017)} = 100",standoff=24),rangemode='normal',automargin=True,ticklabelposition='outside',ticks='outside',ticklen=4)
            fig.update_layout(height=360,showlegend=False,paper_bgcolor='white',plot_bgcolor='white',margin=dict(l=90,r=35,t=30,b=65),font=dict(family='Arial',color='#60758b',size=12))
            fig.update_xaxes(gridcolor='#edf2f7');fig.update_yaxes(gridcolor='#edf2f7')
            return fig
        rows=evidence.get('ventas',[])
        for key,label,color in [('naturales','Personas naturales','#3975b9'),('sociedades','Sociedades','#91bbdf')]:
            fig.add_trace(go.Scatter(x=[str(r['anio']) if r.get('meses',12)==12 else f"{r['anio']} · ene–ago" if r.get('meses')==8 else f"{r['anio']} · {r['meses']} meses" for r in rows],y=[r[key] for r in rows],customdata=[r.get('meses',12) for r in rows],mode='lines+markers',name=label,line=dict(color=color,width=3),marker=dict(size=8,symbol=['circle' if r.get('meses',12)==12 else 'diamond-open' for r in rows]),connectgaps=False,hovertemplate='%{x}<br>USD %{y:,.0f}<br>Acumulado: %{customdata} meses<extra>%{fullData.name}</extra>'))
        periods={r.get('meses',12) for r in rows}
        period='enero–diciembre' if periods=={12} else 'enero–agosto' if periods=={8} else f"enero–mes {next(iter(periods))}" if len(periods)==1 else '2026 parcial · hasta agosto'
        fig.update_xaxes(type='category',title='Año · '+period)
        fig.update_yaxes(title='Ventas declaradas · USD',rangemode='tozero')
        if not rows:
            fig.add_annotation(text='Serie SRI por actividad y tipo de contribuyente<br>pendiente de verificación',x=.5,y=.5,xref='paper',yref='paper',showarrow=False)
    fig.update_layout(height=440 if dimension=='empleabilidad' else 360,showlegend=dimension=='sector' or (dimension=='demanda' and bool(evidence.get('serie'))),paper_bgcolor='white',plot_bgcolor='white',
        margin=dict(l=20,r=90,t=30,b=55),font=dict(family='Arial',color='#60758b',size=12),bargap=.55)
    fig.update_xaxes(gridcolor='#edf2f7',zeroline=False)
    fig.update_yaxes(gridcolor='#edf2f7',zeroline=False,automargin=True)
    return fig

def radar_edco(resultado):
    values=[r['puntaje'] for r in resultado['filas']]
    labels=EJES_EDCO+[EJES_EDCO[0]]
    complete=all(v is not None for v in values)
    fig=go.Figure()
    fig.add_trace(go.Scatterpolar(r=values+[values[0]],theta=labels,mode='lines+markers',connectgaps=False,fill='toself' if complete else None,fillcolor='rgba(0,141,193,.10)',line=dict(color='#008ec1',width=2.6),marker=dict(color='#008ec1',size=7),name='Programa evaluado',hovertemplate='%{theta}: %{r:.1f}/100<extra></extra>'))
    fig.add_trace(go.Scatterpolar(r=[100]*6,theta=labels,mode='lines',line=dict(color='#b4c2d0',width=1.7,dash='dash'),showlegend=False,name='Máximo del modelo',hovertemplate='%{theta}: máximo 100<extra></extra>'))
    fig.update_layout(height=380,margin=dict(l=85,r=85,t=40,b=45),showlegend=False,paper_bgcolor='white',font=dict(family='Arial',color='#60758b',size=11),polar=dict(bgcolor='white',radialaxis=dict(range=[0,105],tickvals=[25,50,75,100],ticksuffix='%',tickfont=dict(size=9,color='#90a1b1'),gridcolor='#e5edf4',linecolor='#e5edf4'),angularaxis=dict(rotation=90,direction='clockwise',gridcolor='#e5edf4',linecolor='#e5edf4')),meta={'dimensiones':[r['id'] for r in resultado['filas']],'pendientes':[r['id'] for r in resultado['filas'] if r['puntaje'] is None]})
    return fig

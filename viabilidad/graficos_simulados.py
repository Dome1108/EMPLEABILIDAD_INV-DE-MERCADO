"""Visuales ilustrativos; sus datos no intervienen en el modelo de viabilidad."""
import random
import plotly.graph_objects as go


def cruce_lineal(precios, curva_a, curva_b):
    """Intersección por segmentos, coherente con las líneas del gráfico."""
    for i in range(len(precios)-1):
        delta=curva_a[i]-curva_b[i]
        next_delta=curva_a[i+1]-curva_b[i+1]
        if delta==0:
            return precios[i],curva_a[i]
        if delta*next_delta<=0:
            t=delta/(delta-next_delta)
            return precios[i]+t*(precios[i+1]-precios[i]),curva_a[i]+t*(curva_a[i+1]-curva_a[i])
    raise ValueError('Las curvas simuladas deben cruzarse en el rango mostrado.')


def crear_grafico_precio(programa, nivel, precio_udla=None):
    # Semilla estable: una selección siempre muestra el mismo escenario ficticio.
    rng=random.Random(f'{programa}|{nivel}|simulacion-v1')
    price_scale=rng.uniform(.8,1.15)*(1 if nivel=='Pregrado' else 1.4)
    # Percepciones ficticias: no provienen de matrículas ni de una encuesta real.
    prices=[round(x*price_scale/10)*10 for x in range(1000,8001,1000)]
    too_cheap=[80,55,30,12,4,1,0,0]
    cheap=[95,85,70,55,35,15,5,0]
    expensive=[5,15,30,45,65,85,95,100]
    too_expensive=[0,2,8,22,40,65,85,100]
    lower,_=cruce_lineal(prices,too_cheap,[100-y for y in cheap])
    upper,_=cruce_lineal(prices,too_expensive,[100-y for y in expensive])
    distribution=go.Figure()
    distribution.add_vrect(x0=lower,x1=upper,fillcolor='rgba(0,114,188,.075)',line_width=0,layer='below')
    for x in [lower,upper]:
        distribution.add_shape(type='line',x0=x,x1=x,y0=0,y1=100,line=dict(color='#8396a8',width=1.3,dash='dash'),layer='below')
    for label,curve,color,dash,symbol in [('Demasiado barato',too_cheap,'#244a67','solid','circle'),('Barato',cheap,'#accbdf','dash','circle'),('Caro',expensive,'#4384ae','solid','circle'),('Demasiado caro',too_expensive,'#687f94','dash','circle')]:
        distribution.add_trace(go.Scatter(x=prices,y=curve,mode='lines+markers',name=label,line=dict(color=color,width=2.4,dash=dash),marker=dict(size=6,symbol=symbol,color='white',line=dict(color=color,width=1.4)),hovertemplate='Precio: $%{x:,.0f}<br>Percepción: %{y:.1f}%<extra>'+label+' · simulado</extra>'))
    # OPP: demasiado barato / demasiado caro. IPP: barato / caro.
    for label,(x,y),offset in [('OPP',cruce_lineal(prices,too_cheap,too_expensive),-35),('IPP',cruce_lineal(prices,cheap,expensive),-28)]:
        distribution.add_trace(go.Scatter(x=[x],y=[y],mode='markers',name=label,showlegend=False,marker=dict(symbol='x',size=11,color='#334f6a',line=dict(width=2)),hovertemplate=f'{label} · simulado<br>Precio: $%{{x:,.0f}}<br>Percepción: %{{y:.1f}}%<extra></extra>'))
        # Los cruces se consultan en hover; se evita llenar el reporte de etiquetas.
    if precio_udla is not None:
        label='UDLA' if nivel=='Pregrado' else 'UDLA · base pregrado'
        distribution.add_vline(x=precio_udla,line=dict(color='#c65f6b',width=1.8,dash='dot'))
        distribution.add_annotation(x=precio_udla,y=103,text=f'<b>{label} · ${precio_udla:,.0f}</b>',showarrow=False,xanchor='center',yanchor='bottom',font=dict(color='#c65f6b',size=12),bgcolor='rgba(255,255,255,.95)',borderpad=3)
        distribution.add_trace(go.Scatter(x=[precio_udla],y=[100],mode='markers',marker=dict(color='#c65f6b',symbol='line-ns',size=12),showlegend=False,hovertemplate=f'{label}<br>Precio del archivo: $%{{x:,.2f}}<extra>Precio de pregrado</extra>'))
    axis_prices=prices+([precio_udla] if precio_udla is not None else [])
    distribution.update_layout(meta=dict(limite_inferior=lower,limite_superior=upper),height=470,margin=dict(l=25,r=20,t=40,b=65),paper_bgcolor='white',plot_bgcolor='white',font=dict(family='Arial',size=12,color='#60758b'),legend=dict(orientation='h',y=-.19,x=.5,xanchor='center',font=dict(size=11)),xaxis=dict(title='Precio del programa (USD)',range=[min(axis_prices)*.85,max(axis_prices)*1.05],tickprefix='$',tickformat=',.0f',gridcolor='#eef1f4',zeroline=False),yaxis=dict(title='Percepción del precio',range=[0,112],tickvals=[0,20,40,60,80,100],ticksuffix='%',gridcolor='#e8ecf0',zeroline=False))
    return distribution

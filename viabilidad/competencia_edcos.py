"""Comparativos descriptivos de contenidos y posicionamiento de oferentes."""
from copy import deepcopy
import math
import plotly.graph_objects as go
from modelo_edcos import INSTITUCIONES_EDCO
from graficos_edcos import moneda_precio


def filas_contenidos(ficha,tipos=None,solo_inscripcion=False):
    data=ficha.get('comparativa_contenidos',{})
    records=[]
    for offer in ficha['ofertas']:
        if offer['tipo']=='Otro nivel':continue
        if tipos is not None and offer['tipo'] not in tipos:continue
        if solo_inscripcion and offer.get('disponibilidad')!='Inscripción declarada' and offer['tipo']!='Oferta propia':continue
        review=data.get('ofertas',{}).get(offer['fuente'],{})
        if not any(isinstance(value,bool) for value in review.get('contenidos',{}).values()):
            continue
        records.append(dict(offer,revision=deepcopy(review)))
    records.sort(key=lambda r:r['tipo']!='Oferta propia')
    return records


def resumen_contenidos(ficha,rows):
    topics=ficha['comparativa_contenidos']['temas']
    external=[r for r in rows if r['tipo'] not in ('Oferta propia','Otro nivel') and r['revision'].get('revisado')]
    counts={t['id']:sum(r['revision']['contenidos'].get(t['id']) is True for r in external) for t in topics}
    return dict(total=len(external),conteos=counts,sin_verificar=sum(not r['revision'].get('revisado',False) for r in rows if r['tipo']!='Oferta propia'))


def grafico_contenidos(ficha,rows):
    data=ficha['comparativa_contenidos'];topics=data['temas']
    institution=INSTITUCIONES_EDCO[ficha['institucion_id']]['nombre']
    proposed=dict(institucion=institution+' · Programa propuesto',programa=ficha['nombre'],tipo='Propuesta',fuente='brief',revision=data['propuesta'])
    visible=[proposed]+rows
    labels=[r['revision'].get('etiqueta',r['institucion']) for r in visible]
    z=[];texts=[];custom=[]
    for r in visible:
        values=[r['revision'].get('contenidos',{}).get(t['id']) for t in topics]
        z.append([1 if v is True else 0 if v is False else -1 for v in values])
        texts.append(['✓' if v is True else '·' if v is False else '' for v in values])
        custom.append([[r['programa'],'Declarado' if v is True else 'No identificado en la descripción' if v is False else 'Sin verificar',r['revision'].get('detalle','No hay descripción verificable.'),r.get('estado','Brief del proponente')] for v in values])
    fig=go.Figure(go.Heatmap(z=z,x=[t['etiqueta'] for t in topics],y=labels,zmin=-1,zmax=1,
        colorscale=[[0,'#e1e7ed'],[.2499,'#e1e7ed'],[.25,'#f7f9fc'],[.7499,'#f7f9fc'],[.75,'#b7d6ec'],[1,'#b7d6ec']],
        showscale=False,xgap=5,ygap=5,text=texts,texttemplate='%{text}',textfont=dict(size=17,color='#23506e'),customdata=custom,
        hovertemplate='<b>%{y}</b><br>%{customdata[0]}<br>%{x}: %{customdata[1]}<br>%{customdata[2]}<br>%{customdata[3]}<extra></extra>'))
    fig.update_layout(height=max(330,37*len(visible)+135),paper_bgcolor='white',plot_bgcolor='white',
        margin=dict(l=240,r=10,t=80,b=20),font=dict(family='Arial',color='#60758b',size=11))
    fig.update_xaxes(side='top',tickangle=0,fixedrange=True)
    fig.update_yaxes(autorange='reversed',fixedrange=True)
    fig.add_shape(type='rect',xref='paper',yref='y',x0=0,x1=1,y0=-.5,y1=.5,line=dict(color='#348c9b',width=2))
    return fig


def posicionamiento(ficha,rows):
    currency=moneda_precio(ficha)
    price_field='precio_'+currency.lower()
    def positive(value):
        return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>0
    def valid_price(row):
        value=row.get(price_field)
        return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>=0 and row.get('precio_verificado',True)
    valid=[r for r in rows if positive(r.get('horas')) and valid_price(r)]
    missing=[dict(institucion=r['institucion'],programa=r['programa'],motivo=' y '.join((["horas no publicadas"] if not positive(r.get('horas')) else [])+([f'precio {currency} no verificado'] if not valid_price(r) else []))) for r in rows if r not in valid]
    fig=go.Figure()
    for typ,label,color,symbol in [('Institucional','Universidades e institutos','#3975b9','circle'),('Plataforma','Plataformas','#bd8a40','diamond'),('Oferta propia','Oferta institucional propia','#71869b','square')]:
        group=[r for r in valid if r['tipo']==typ]
        if not group:continue
        fig.add_trace(go.Scatter(x=[r['horas'] for r in group],y=[r[price_field] for r in group],
            mode='markers+text',name=label,marker=dict(color=color,symbol=symbol,size=13,line=dict(width=2,color='white')),
            text=[r['institucion'] if typ=='Plataforma' else r['revision'].get('etiqueta',r['institucion']) for r in group],textposition='top right' if typ=='Plataforma' else ['top center' if i%2==0 else 'bottom center' for i in range(len(group))],cliponaxis=False,
            customdata=[[r['programa'],r.get('tipo_horas','No especificado'),r['estado']] for r in group],
            hovertemplate='<b>%{text}</b><br>%{customdata[0]}<br>%{x:g} horas · %{customdata[1]}<br>'+currency+' %{y:,.2f}<br>%{customdata[2]}<extra></extra>'))
    fig.update_layout(height=390,paper_bgcolor='white',plot_bgcolor='white',font=dict(family='Arial',color='#60758b',size=11),
        margin=dict(l=65,r=70,t=40,b=75),legend=dict(orientation='h',y=-.25,x=0))
    fig.update_xaxes(title='Duración publicada · horas',rangemode='tozero',gridcolor='#edf2f7')
    fig.update_yaxes(title='Precio total publicado · '+currency,rangemode='tozero',gridcolor='#edf2f7',tickprefix='₡' if currency=='CRC' else '$')
    return fig,missing

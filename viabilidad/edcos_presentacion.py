"""Presentación ejecutiva del brief; mantiene el detalle original consultable."""
from html import escape


def participacion_html(ficha):
    evidence=ficha['evidencia_visual']['demanda']
    sources={s['id']:s for s in ficha['fuentes']}
    cards=[]
    for row in evidence.get('observaciones',[]):
        platform,_,course=row['etiqueta'].partition(' · ')
        count=f"{row['valor']:,.0f}".replace(',','.')
        source=sources.get(row.get('fuente'),{})
        link=f'<a href="{escape(source["url"],quote=True)}" target="_blank" rel="noopener noreferrer">Ver curso ↗</a>' if source.get('url') else ''
        cards.append(f'<article class="edco-demand-card"><div class="edco-demand-platform">{escape(platform)}</div><div class="edco-demand-count">{count}</div><div class="edco-demand-unit">inscripciones acumuladas</div><div class="edco-demand-course">{escape(course)}</div>{link}</article>')
    country=escape(ficha['brief']['pais'])
    reading=evidence.get('lectura','Estos cursos registran participación en el tema. Las cifras corresponden a cada curso, con distinta antigüedad, alcance y condiciones.')
    return '<div class="edco-demand-cards">'+''.join(cards)+'</div><div class="edco-demand-reading"><strong>Qué nos dice</strong><p>'+escape(reading)+'</p><span>No se suman como personas únicas ni permiten estimar cuántos participantes tendría el programa en '+country+'.</span></div>'


def propuesta_html(ficha):
    pillars=[
        ('Biometría aplicada','Experimentación','Eye tracking, respuesta electrodérmica y pruebas del consumidor en laboratorio.',
         '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>','#2879b4'),
        ('Neuro-UX','Experiencia digital','Auditoría de sitios, comercio electrónico y puntos de contacto digitales.',
         '<rect x="3" y="4" width="18" height="14" rx="2"/><path d="M3 8h18M8 21h8m-4-3v3M8 12h3m-3 3h7"/>','#368b9b'),
        ('IA y visión computacional','Inteligencia aplicada','Herramientas de análisis del consumidor con una evaluación crítica de su precisión.',
         '<rect x="6" y="6" width="12" height="12" rx="3"/><path d="M9 2v4m6-4v4M9 18v4m6-4v4M2 9h4m-4 6h4M18 9h4m-4 6h4"/><path d="m9 13 2-3 2 4 2-3"/>','#667fad'),
    ]
    # Estos titulares sintetizan los tres diferenciadores de la ficha inicial.
    # Otras propuestas conservan su texto propio en tarjetas genéricas.
    initial=ficha.get('id')=='neuromarketing_digital'
    cards=[]
    for i,text in enumerate(ficha['brief']['diferenciadores']):
        title,tag,summary,icon,accent=pillars[i] if initial and i<len(pillars) else (f'Diferenciador {i+1}','Propuesta académica',text,'<path d="m5 12 4 4L19 6"/>','#2879b4')
        if not initial and i<len(ficha['brief'].get('pilares',[])):
            title=ficha['brief']['pilares'][i]
        cards.append(f'<article class="edco-pillar" style="--accent:{accent}"><div class="edco-pillar-top"><div class="edco-icon"><svg viewBox="0 0 24 24" aria-hidden="true">{icon}</svg></div><span class="edco-tag">{escape(tag)}</span></div><h3>{escape(title)}</h3><p>{escape(summary)}</p></article>')
    segments=''.join(f'<div class="edco-segment"><span>{i:02}</span><strong>{escape(s)}</strong></div>' for i,s in enumerate(ficha['audiencia_propuesta']['segmentos'],1))
    return '<div class="edco-section"><div><div class="edco-kicker">La propuesta académica</div><h2>Qué hace diferente al programa</h2></div><p>Tres ejes que definen su enfoque y aplicación profesional.</p></div><div class="edco-pillars">'+''.join(cards)+'</div><div class="edco-audience"><div><h3>A quién se dirige</h3><small>Segmentos sugeridos a partir del brief.</small></div><div class="edco-segments">'+segments+'</div></div>'

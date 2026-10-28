"""Frecuencia de habilidades sobre publicaciones documentadas, sin contar vacantes."""
import unicodedata


def resumir_habilidades(evidencia,areas=None,estados=None):
    def normalizar(value):
        return ''.join(c for c in unicodedata.normalize('NFKD',value.casefold()) if not unicodedata.combining(c)).strip()
    rows=[]
    ids=set();posts=set()
    for row in evidencia.get('publicaciones',[]):
        identity=row.get('identificador_linkedin',row['id'])
        post=tuple(normalizar(row[k]) for k in ['empresa','cargo','ciudad'])
        if identity in ids or post in posts:continue
        ids.add(identity);posts.add(post)
        if areas is not None and row.get('area') not in areas:continue
        if estados is not None and row.get('estado_clasificacion') not in estados:continue
        rows.append(row)
    total=len(rows)
    skills=[]
    for skill in evidencia.get('catalogo_habilidades',evidencia.get('habilidades',[])):
        ids_fuentes=[r['fuente'] for r in rows if skill['id'] in set(r['habilidades'])]
        skills.append(dict(skill,menciones=len(ids_fuentes),muestra=total,porcentaje=100*len(ids_fuentes)/total if total else None,fuentes=ids_fuentes))
    skills.sort(key=lambda r:-(r['menciones']))
    return dict(publicaciones=rows,habilidades=skills,total=total,empresas=len({normalizar(r['empresa']) for r in rows}))

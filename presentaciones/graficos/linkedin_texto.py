"""[Copia de Tendencias · scrapers/linkedin/jobs.py] Resúmenes de anuncios de LinkedIn.

Solo las funciones que usa la presentación (sin Selenium ni descargas).
"""
import re
import unicodedata
from collections import Counter


def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', texto.casefold())
                   if not unicodedata.combining(c)).strip()


def resumir_cargos(vacantes, limite=5):
    """Cuenta títulos de anuncios únicos, ignorando mayúsculas y acentos."""
    conteos, nombres, vistos = Counter(), {}, set()
    for vacante in vacantes:
        url = vacante.get('url')
        if url and url in vistos:
            continue
        if url:
            vistos.add(url)
        titulo = ' '.join(str(vacante.get('titulo') or '').split())
        clave = normalizar(titulo)
        if not clave:
            continue
        nombres.setdefault(clave, titulo)
        conteos[clave] += 1
    return [(nombres[clave], cantidad) for clave, cantidad in conteos.most_common(limite)]


def extraer_requisitos(texto):
    inicio = re.compile(r'^(?:requisitos|requerimientos|requirements|qualifications|'
                        r'perfil requerido|perfil que buscamos|que buscamos|que necesitas|'
                        r'perfil del candidato|perfil profesional|habilidades requeridas|'
                        r'conocimientos requeridos|experiencia requerida|educacion requerida|'
                        r'competencias requeridas|formacion requerida|requerido|requerida|'
                        r'habilidades tecnicas|habilidades blandas|competencias tecnicas|'
                        r'skills|technical skills|soft skills|required skills|'
                        r'que esperamos de ti|what you bring|what we are looking for)\b|'
                        r'^(?:experiencia|conocimientos|habilidades|competencias|'
                        r'formacion academica|educacion|estudios)(?:\s*:|\s*$)')
    fin = re.compile(r'^(responsabilidades|funciones|beneficios|ofrecemos|'
                     r'we offer|about us|acerca de nosotros|como postular|'
                     r'tus tareas|actividades|objetivo del puesto|what you will do|'
                     r'unete a nuestro equipo|postula ahora)\b')
    solicitud = re.compile(r'\b(se requiere|requerid[oa]s?|requerimos|debe(?:s)? contar|'
                           r'debe(?:s)? tener|indispensable|imprescindible|deseable|'
                           r'necesari[oa]|required|must have|proficiency|'
                           r'experiencia (?:en|de|con|como|minima)|\d+\s+anos? de experiencia|'
                           r'conocimientos? (?:en|de)|dominio de|manejo de|'
                           r'capacidad (?:de|para)|habilidad(?:es)? (?:de|para)|'
                           r'titulo (?:en|de)|graduad[oa] en|profesional en|'
                           r'licenciatura en|nivel de ingles)\b')
    requisitos, activo = [], False
    excluido = False
    for linea in texto.splitlines():
        linea = linea.strip(' \t•-*·')
        if not linea:
            continue
        normalizada = normalizar(linea).lstrip('¡!¿? ')
        if re.fullmatch(r'[.\s…]*(?:(?:ver|mostrar|show|see)\s+)?(?:mas|menos|more|less)[.\s…]*', normalizada):
            continue
        if fin.search(normalizada):
            activo, excluido = False, True
            continue
        if inicio.search(normalizada) and len(linea) < 160:
            activo = True
            excluido = False
            contenido = linea.split(':', 1)[1].strip() if ':' in linea else ''
            if contenido:
                requisitos.append(contenido)
            elif solicitud.search(normalizada) and len(linea.split()) > 3:
                requisitos.append(linea)
        elif activo:
            requisitos.append(linea)
        elif not excluido:
            # Algunas vacantes describen lo exigido en frases, sin encabezados.
            for frase in re.split(r'(?<=[.;])\s+', linea):
                if solicitud.search(normalizar(frase)):
                    requisitos.append(frase)
    return requisitos


def resumir_requisitos(vacantes, limite=8, solo_habilidades=False):
    """Cada requisito cuenta como máximo una vez por anuncio, incluso si se repite."""
    conteos, nombres, urls = Counter(), {}, set()
    for vacante in vacantes:
        url = vacante.get('url')
        if url and url in urls:
            continue
        if url:
            urls.add(url)
        vistos = set()
        requisitos = vacante.get('requisitos') or extraer_requisitos(vacante.get('descripcion', ''))
        for requisito in requisitos:
            texto = normalizar(requisito)
            if re.search(r'\b(no se requiere|no requiere|not required)\b', texto):
                continue
            categorias = []
            for nombre, patron in (
                ('Excel', r'\bexcel\b'), ('Inglés', r'\bingles\b|\benglish\b'),
                ('Microsoft Office', r'\boffice\b|ofimatica'),
                ('Experiencia laboral', r'\bexperiencia\b|\bexperience\b'),
                ('Formación universitaria', r'universitari|licenciatura|bachelor|titulo profesional|'
                 r'titulo de tercer nivel|\blic\.? en'),
                ('Registro en Senescyt', r'\bsenescyt\b'),
                ('Salud ocupacional', r'salud ocupacional|enfermer[oa] ocupacional'),
                ('Primeros auxilios', r'primeros auxilios'),
                ('Bioseguridad', r'\bbioseguridad\b'),
                ('Disponibilidad inmediata', r'disponibilidad inmediata'),
                ('Comunicación', r'comunicacion|communication'),
                ('Trabajo en equipo', r'trabajo en equipo|teamwork'),
                ('Liderazgo', r'liderazgo|leadership'), ('SQL', r'\bsql\b'),
                ('Python', r'\bpython\b'), ('Power BI', r'\bpower\s*bi\b'),
                ('Análisis de datos', r'analisis de datos|data analysis'),
                ('AutoCAD', r'\bautocad\b'), ('Revit', r'\brevit\b'),
                ('BIM', r'\bbim\b'), ('SAP', r'\bsap\b'),
                ('Gestión de proyectos', r'gestion de proyectos|project management'),
                ('Resolución de problemas', r'resolucion de problemas|problem.solving'),
                ('Pensamiento crítico', r'pensamiento critico|critical thinking'),
                ('Atención al cliente', r'atencion al cliente|customer service'),
                ('Negociación', r'negociacion|negotiation'),
                ('Organización', r'organizacion|organizational skills'),
            ):
                if re.search(patron, texto):
                    categorias.append(nombre)
            if solo_habilidades:
                categorias = [n for n in categorias if n not in (
                    'Experiencia laboral', 'Formación universitaria',
                    'Registro en Senescyt', 'Disponibilidad inmediata')]
                # Conservar conocimientos propios de cualquier carrera, aunque
                # no estén en el vocabulario anterior, sin incluir condiciones laborales.
                if not categorias:
                    habilidad = re.search(
                        r'\b(?:conocimientos? (?:en|de)|dominio de|manejo de|'
                        r'capacidad (?:de|para)|habilidades? (?:de|para|en))\s+(.+)',
                        requisito, flags=re.IGNORECASE)
                    if habilidad:
                        nombre = habilidad.group(1).strip(' .;:')
                        if nombre and not re.search(
                            r'\b(disponibilidad|residir|residencia|horarios|titulo|licencia de conducir)\b',
                            normalizar(nombre)):
                            categorias.append(nombre)
            for nombre in categorias or ([] if solo_habilidades else [requisito]):
                clave = re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', normalizar(nombre))).strip()
                if clave:
                    vistos.add(clave)
                    nombres.setdefault(clave, nombre)
        conteos.update(vistos)
    return [(nombres[clave], cantidad) for clave, cantidad in
            sorted(conteos.items(), key=lambda item: (-item[1], item[0]))
            if cantidad >= 2][:limite]



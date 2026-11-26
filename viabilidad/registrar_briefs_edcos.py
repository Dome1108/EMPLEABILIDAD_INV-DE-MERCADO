"""Registra briefs nuevos como fichas EdCo en estado «En evaluación».

Cada brief se transcribe una vez en BRIEFS. El script genera una ficha JSON por
programa en edcos_data/ y, si se indica la carpeta de los PDF, copia el brief
original en edcos_fuentes/. No asigna puntajes ni completa evidencia de mercado:
las cinco dimensiones quedan sin calificar hasta que exista investigación.

Uso:
    python registrar_briefs_edcos.py "C:/ruta/a/los/briefs"
    python registrar_briefs_edcos.py "C:/ruta/a/los/briefs" figma_ia diseno_estrategico   (solo esos)

Se omiten identificadores personales del formulario (nombre del solicitante,
correo, cédula e IP); el PDF original se conserva para consulta.
"""
import json
import shutil
import sys
from pathlib import Path

from modelo_edcos import INSTITUCIONES_EDCO, validar_ficha

BASE = Path(__file__).parent
FECHA_REGISTRO = '2026-11-06'
VERSION = FECHA_REGISTRO + '-brief-registrado'

SUBCATEGORIAS = {
    'demanda': ['Interés en la habilidad', 'Intención de capacitación', 'Necesidad de aplicación'],
    'empleabilidad': ['Aplicación profesional de las competencias', 'Relevancia para los perfiles destinatarios',
                      'Valor del resultado práctico'],
    'competencia': ['Oferta institucional comparable', 'Plataformas y sustitutos', 'Diferenciación práctica'],
    'precio': ['Rangos publicados del mercado', 'Intensidad y acompañamiento de las alternativas', 'Posicionamiento de valor'],
    'sector': ['Actividad del sector', 'Evolución del entorno económico', 'Aplicación de las competencias del programa'],
}
NO_INFORMADO = 'No informado en el brief'


def oferta(institucion, programa, tipo='Institucional', modalidad='Por verificar', horas=None, usd=None, crc=None, nota=''):
    """Alternativa mencionada por el proponente: se muestra, pero nunca como precio verificado."""
    return dict(institucion=institucion, programa=programa, tipo=tipo, modalidad=modalidad, horas=horas,
                precio_usd=usd, precio_crc=crc, estado='Declarado por el proponente; sin verificación externa',
                disponibilidad='Por confirmar', competidor_directo=False, fuente='brief',
                nota=('Referencia del brief, no verificada. ' + nota).strip(), precio_verificado=False)


BRIEFS = [
    dict(
        id='analisis_noticias_cr', archivo_json='ulatina_analisis_noticias_cr.json', institucion_id='ulatina_cr',
        pdf='Brief CR Análisis de Noticias y Política Internacional.pdf', paginas='1–6', fecha_propuesta='2026-10-26',
        nombre='Técnico en Análisis de Noticias y Política Internacional', tipo='Técnico · Apertura de nuevo programa',
        area='Comunicación colectiva', facultad='Facultad de Arte, Diseño y Comunicación Colectiva', unidad='Técnicos',
        duracion='3 cuatrimestres', horas_totales=288,
        modalidad='Flex (educación presencial o en línea de acuerdo con las necesidades del estudiante)',
        objetivo='Al concluir los seis módulos bimestrales, correspondientes a las 288 horas de formación, la persona graduada estará en capacidad de identificar, verificar, contextualizar, analizar y comunicar acontecimientos de la actualidad y la política internacional, mediante la aplicación de conocimientos interdisciplinarios, herramientas digitales y metodologías básicas de análisis informativo y geopolítico.',
        diferenciadores=[
            'Enfoque interdisciplinario y aplicado: integra relaciones internacionales, geopolítica, ciencia política y comunicación para analizar acontecimientos internacionales desde múltiples perspectivas.',
            'Formación práctica en verificación de noticias y desinformación: talleres de fact-checking, análisis de fuentes, identificación de noticias falsas y uso de herramientas digitales e inteligencia artificial.',
            'Laboratorio de análisis de coyuntura internacional: seguimiento noticioso, boletines, informes ejecutivos, análisis geopolíticos y construcción de escenarios.',
            'Desarrollo de competencias digitales y analíticas: fuentes abiertas (OSINT), bases de datos internacionales y plataformas de monitoreo informativo.',
            'Vinculación con el entorno profesional: conversatorios, talleres con especialistas y visitas a medios, instituciones públicas y organismos internacionales (componentes propuestos).',
            'Formación orientada a productos profesionales: portafolio con análisis de noticias, informes de coyuntura, boletines y ejercicios de comunicación estratégica.',
        ],
        habilidades=['Pensamiento crítico y analítico', 'Investigación y verificación de información', 'Análisis geopolítico y prospectivo',
                     'Competencias digitales e inteligencia informativa', 'Comunicación estratégica y síntesis ejecutiva'],
        nombres_alternativos=['Técnico en Análisis Geopolítico y Actualidad Internacional', 'Técnico en Inteligencia Informativa y Análisis Internacional'],
        palabras_clave=['Geopolítica', 'Política Internacional', 'Inteligencia Informativa', 'Actualidad Internacional', 'Análisis Estratégico',
                        'Verificación de Noticias', 'Desinformación', 'Inteligencia Artificial', 'Fuentes Abiertas (OSINT)', 'Prospectiva Internacional'],
        sector_declarado='Información y comunicación · Actividades profesionales, científicas y técnicas · Administración pública y defensa · Otras actividades de servicio',
        interes_investigacion='Demanda potencial e intención de matrícula, perfil del estudiantado, pertinencia laboral, disposición de pago, preferencias académicas, competencia, canales de captación y viabilidad comercial.',
        segmentos=[],
        ofertas=[
            oferta('ULACIT', 'Técnico en Relaciones Internacionales', nota='El proponente lo señala como competidor más cercano; tarifa no verificada.'),
            oferta('ULACIT', 'Bachillerato Bilingüe en Relaciones Internacionales', tipo='Otro nivel', crc=8087396, nota='Monto según tarifario 2026, incluidos costos fijos, citado en el brief.'),
            oferta('Universidad San Judas Tadeo', 'Bachillerato en Periodismo', tipo='Otro nivel', crc=6847850, nota='Monto según proforma citada en el brief.'),
            oferta('Universidad Nacional (UNA)', 'Bachillerato y Licenciatura en Relaciones Internacionales', tipo='Otro nivel', nota='Monto por carrera no verificado.'),
            oferta('Universidad de Costa Rica (UCR)', 'Ciencias de la Comunicación Colectiva, énfasis en Periodismo', tipo='Otro nivel', nota='Monto por carrera no verificado.'),
            oferta('Universidad Internacional de las Américas (UIA)', 'Periodismo y Relaciones Internacionales', tipo='Otro nivel', nota='Precio por confirmar.'),
        ],
    ),
    dict(
        id='eventos_corporativos_cr', archivo_json='ulatina_eventos_corporativos_cr.json', institucion_id='ulatina_cr',
        pdf='Brief CR Dirección y Gestión de Eventos Corporativos.pdf', paginas='1–4', fecha_propuesta='2026-10-19',
        nombre='Dirección y Gestión de Eventos Corporativos', tipo='Técnico · Apertura de nuevo programa',
        area='Comunicación colectiva', facultad='Facultad de Arte, Diseño y Comunicación Colectiva', unidad='Otro · Academia',
        duracion='2 cuatrimestres', horas_totales=None, modalidad='Presencial (100% presencial)',
        objetivo='Quien se certifique desarrollará habilidades de liderazgo y dirección, así como la capacidad de planificar y ejecutar eventos especiales creando relaciones saludables con las organizaciones, proveedores y productoras. También desarrollará habilidades analíticas y podrá ofrecer al mundo laboral el perfil de un productor de eventos integral.',
        diferenciadores=['Habilidades gerenciales.', 'Bases en finanzas y presupuestos para eventos.', 'Contacto directo con productoras activas en el mercado actual.',
                         'Relación con la industria creativa.', 'Taller de liderazgo participativo.'],
        habilidades=['Capacidad de investigación', 'Detección de cambios', 'Toma de decisiones', 'Creatividad e innovación', 'Resolución de problemas'],
        nombres_alternativos=['Dirección y Gestión de Eventos Corporativos', 'Ejecutivo de Eventos Especiales'],
        palabras_clave=['Evento', 'Presupuesto', 'Protocolo', 'Innovación', 'Planificación', 'Liderazgo', 'Gastronomía', 'Marketing', 'Creatividad', 'Dirección'],
        sector_declarado='Información y comunicación · Actividades financieras y de seguros · Actividades profesionales, científicas y técnicas · Actividades de servicios administrativos y de apoyo · Enseñanza · Actividades artísticas, de entretenimiento y recreativas · Otras actividades de servicio',
        interes_investigacion='Las aspiraciones del prospecto; demografía y estado socioeconómico del público objetivo.',
        segmentos=[],
        ofertas=[
            oferta('Universidad del Turismo', 'Taller Profesional de Organización de Bodas', modalidad='Presencial'),
            oferta('Universidad Creativa', 'Planificación y Producción de Eventos', modalidad='Virtual'),
            oferta('ISEIE', 'Organización de eventos · curso libre', usd=344),
        ],
    ),
    dict(
        id='interiores_comerciales_cr', archivo_json='ulatina_interiores_comerciales_cr.json', institucion_id='ulatina_cr',
        pdf='Brief CR Diseño de Interiores Comerciales.pdf', paginas='1–4', fecha_propuesta='2026-10-20',
        nombre='Diseño de Interiores Comerciales', tipo='Técnico · Apertura de nuevo programa',
        area='Diseño', facultad='Facultad de Arte, Diseño y Comunicación Colectiva', unidad='Otro · Facultad Campus Creativo',
        duracion='3 cuatrimestres', horas_totales=None, modalidad='Presencial (100% presencial)',
        objetivo='El estudiante comprende los fundamentos del diseño y la decoración de interiores (composición espacial, teoría del color, iluminación, materiales y acabados, mobiliario, ergonomía, tendencias, sostenibilidad y herramientas digitales de representación); analiza espacios y necesidades de los usuarios, desarrolla y comunica propuestas de diseño considerando funcionalidad, estética, bienestar y presupuesto, con creatividad, sensibilidad estética, pensamiento crítico y comportamiento ético.',
        diferenciadores=[
            'Aprendizaje práctico basado en proyectos: talleres de diseño interior para espacios residenciales, comerciales y otros ambientes, desde la conceptualización hasta la presentación.',
            'Integración de tendencias, materiales y tecnología: color, iluminación, mobiliario, acabados y materialidad, con visualización tridimensional e inteligencia artificial aplicada al diseño.',
            'Experiencias de aprendizaje fuera del aula: visitas a salas de exhibición, tiendas especializadas, proveedores de mobiliario, iluminación y acabados, y espacios interiores de referencia.',
        ],
        habilidades=['Creatividad e innovación', 'Observación y análisis de tendencias', 'Pensamiento crítico y criterio estético',
                     'Competencia digital y visualización', 'Adaptabilidad y aprendizaje continuo'],
        nombres_alternativos=['Diseño de Interiores Comerciales', 'Principios Diseño de Interiores'],
        palabras_clave=['Diseño de interiores', 'Decoración y ambientación', 'Diseño espacial', 'Ergonomía y bienestar', 'Teoría del color',
                        'Iluminación interior', 'Materiales y acabados', 'Mobiliario y equipamiento', 'Diseño sostenible', 'Visualización digital e inteligencia artificial'],
        sector_declarado='Actividades profesionales, científicas y técnicas · Actividades artísticas, de entretenimiento y recreativas',
        interes_investigacion='Perfil de las personas interesadas en el diseño, la decoración y la transformación de espacios interiores.',
        segmentos=['Jóvenes que buscan desarrollar competencias creativas', 'Adultos que desean actualizar conocimientos o adquirir herramientas profesionales',
                   'Estudiantes de secundaria', 'Personas vinculadas al diseño, la arquitectura, la construcción, el mobiliario y el sector inmobiliario',
                   'Emprendedores de servicios de interiorismo'],
        ofertas=[],
        competencia_texto='El proponente indica que hay tres universidades que dan la carrera, pero no el técnico; no las identifica.',
    ),
    dict(
        id='escritura_creativa_cr', archivo_json='ulatina_escritura_creativa_cr.json', institucion_id='ulatina_cr',
        pdf='Brief CR Escritura Creativa.pdf', paginas='1–4', fecha_propuesta='2026-10-17',
        nombre='Técnico en Escritura Creativa', tipo='Técnico · Apertura de nuevo programa',
        area='Artes visuales', facultad='Facultad de Arte, Diseño y Comunicación Colectiva', unidad='Técnicos',
        duracion='3 cuatrimestres (12 meses, 6 módulos bimestrales, según los diferenciadores)', horas_totales=None,
        modalidad='Presencial (100% presencial)',
        objetivo='El estudiante desarrollará conocimientos en escritura creativa, estructuras narrativas, creación de personajes y construcción de mundos ficticios; habilidades para conceptualizar, redactar, analizar y perfeccionar obras literarias; así como actitudes de creatividad, pensamiento crítico y disciplina.',
        diferenciadores=['Duración de 12 meses, en 6 módulos bimestrales.', 'Accesibilidad al no requerir conocimientos previos en escritura literaria.',
                         'Desarrollo de proyectos literarios desde cero, con conocimiento sobre cómo publicarlos.', 'Formación progresiva en módulos especializados sobre temas específicos.',
                         'Enfoque especializado en escritura de ficción literaria: cuentos, relatos y novelas.'],
        habilidades=['Escritura creativa y narrativa', 'Creación de personajes y mundos', 'Pensamiento creativo y crítico', 'Edición y revisión literaria',
                     'Adaptación a nuevas tendencias literarias'],
        nombres_alternativos=['Técnico en Escritura Creativa', 'Técnico en Creación Literaria'],
        palabras_clave=['Escritura creativa', 'Narrativa', 'Literatura', 'Ficción', 'Creación literaria', 'Personajes', 'Construcción de mundos', 'Tramas', 'Cuentos', 'Novelas'],
        sector_declarado='Actividades artísticas, de entretenimiento y recreativas',
        interes_investigacion='Qué aspectos de la escritura creativa generan mayor interés en el público.',
        segmentos=[],
        ofertas=[
            oferta('Universidad Creativa', 'Escritura Creativa', nota='6 semanas; costo desconocido.'),
            oferta('Universidad Continental de las Ciencias y las Artes (UCCART)', 'Escritura Creativa', crc=120000, nota='12 semanas.'),
            oferta('Tecnológico de Costa Rica (TEC)', 'Taller de Guion para Audiovisuales', crc=75000, nota='8 sesiones.'),
            oferta('Universidad de Costa Rica (UCR)', 'Introducción a la Escritura Creativa', horas=12, crc=0, nota='Declarado gratuito.'),
        ],
    ),
    dict(
        id='fotografia_digital_cr', archivo_json='ulatina_fotografia_digital_cr.json', institucion_id='ulatina_cr',
        pdf='Brief CR Fotografía Digital.pdf', paginas='1–4', fecha_propuesta='2026-10-22',
        nombre='Fotografía Digital', tipo='Técnico · Apertura de nuevo programa',
        area='Artes visuales', facultad='Facultad de Arte, Diseño y Comunicación Colectiva', unidad='Otro · Campus Creativo',
        duracion='3 cuatrimestres', horas_totales=None, modalidad='Presencial (100% presencial)',
        objetivo='Identificar las características de los equipos fotográficos digitales, controlar la exposición, aplicar composición e iluminación, realizar fotografía de retrato, producto y otras aplicaciones, editar y retocar imágenes, preparar archivos para medios digitales o impresos, incorporar herramientas de inteligencia artificial en la edición y desarrollar un portafolio fotográfico.',
        diferenciadores=['Enfoque integral y práctico: desde los fundamentos técnicos de la captura hasta la edición, el tratamiento digital y la preparación de imágenes para distintos contextos.',
                         'Combina el dominio de los parámetros técnicos de la cámara con la sensibilidad visual, la composición, el manejo de la iluminación y la comunicación de ideas mediante imágenes.'],
        habilidades=['Dominio técnico de la fotografía digital', 'Creatividad y narrativa visual', 'Edición y posproducción fotográfica',
                     'Producción fotográfica comercial y turística', 'Gestión de proyectos y emprendimiento'],
        nombres_alternativos=['Fotografía Digital', 'Producción Fotográfica'],
        palabras_clave=['Fotografía', 'Digital', 'Producción', 'Iluminación', 'Composición', 'Publicidad', 'Producto', 'Retrato', 'Cámaras', 'Edición'],
        sector_declarado='Información y comunicación · Actividades inmobiliarias · Actividades artísticas, de entretenimiento y recreativas · Otras actividades de servicio',
        interes_investigacion='Monto dispuesto a pagar y horarios preferidos. El programa está pensado para Santa Cruz.',
        segmentos=[],
        ofertas=[
            oferta('Tecnológico de Costa Rica (TEC)', 'Técnico en Fotografía', crc=1083240, nota='₡90.270 por curso; aproximadamente ₡1.083.240 por los 12 cursos, según el brief.'),
            oferta('Universidad LCI Veritas', 'Técnico en Fotografía', nota='₡423.900 por cuatrimestre según el brief; no se conoce el total.'),
            oferta('Universidad Creativa', 'Técnico en Fotografía', nota='Sin precio informado.'),
        ],
    ),
    dict(
        id='cooperacion_internacional_cr', archivo_json='ulatina_cooperacion_internacional_cr.json', institucion_id='ulatina_cr',
        pdf='Brief CR Gestión de la Cooperación Internacional y Proyectos de Desarrollo.pdf', paginas='1–5', fecha_propuesta='2026-10-26',
        nombre='Técnico en Gestión de la Cooperación Internacional y Proyectos de Desarrollo', tipo='Técnico · Apertura de nuevo programa',
        area='Comunicación colectiva', facultad='Facultad de Arte, Diseño y Comunicación Colectiva', unidad='Técnicos',
        duracion='3 cuatrimestres', horas_totales=None,
        modalidad='Flex (educación presencial o en línea de acuerdo con las necesidades del estudiante)',
        objetivo='Comprender el sistema de cooperación internacional para el desarrollo, la Agenda 2030 y las fuentes de financiamiento; formular, presupuestar, monitorear y evaluar proyectos (marco lógico, teoría del cambio, gestión por resultados), identificar cooperantes, movilizar recursos y negociar alianzas, con ética, transparencia y respeto intercultural.',
        diferenciadores=[
            'Formación práctica orientada a proyectos: los seis módulos articulan una propuesta de cooperación internacional desde el diagnóstico hasta su presentación final.',
            'Talleres de formulación y gestión de proyectos: marco lógico, teoría del cambio, gestión por resultados y presupuestos.',
            'Simulaciones de negociación y búsqueda de financiamiento: identificación de cooperantes, convocatorias, presentación de propuestas y alianzas.',
            'Enfoque territorial y regional: Costa Rica y Centroamérica, con énfasis en gobiernos locales, organizaciones sociales e instituciones públicas.',
            'Vinculación con actores de la cooperación: conversatorios, visitas y talleres con agencias, organismos internacionales, ONG y especialistas.',
            'Proyecto integrador y portafolio profesional: diagnóstico, cooperantes, propuesta, presupuesto, indicadores y estrategia de seguimiento.',
        ],
        habilidades=['Formulación y gestión de proyectos', 'Identificación de oportunidades de financiamiento', 'Negociación y gestión de alianzas',
                     'Planificación estratégica y gestión por resultados', 'Comunicación técnica y gestión intercultural'],
        nombres_alternativos=['Técnico en Formulación y Gestión de Proyectos de Cooperación Internacional', 'Técnico en Cooperación Internacional y Movilización de Recursos para el Desarrollo'],
        palabras_clave=['Cooperación Internacional', 'Gestión de Proyectos', 'Desarrollo Sostenible', 'Formulación de Proyectos', 'Movilización de Recursos',
                        'Financiamiento Internacional', 'Gestión por Resultados', 'Marco Lógico', 'Alianzas Estratégicas', 'Monitoreo y Evaluación'],
        sector_declarado='Información y comunicación · Actividades profesionales, científicas y técnicas · Actividades de servicios administrativos y de apoyo · Administración pública y defensa · Otras actividades de servicio',
        interes_investigacion='Demanda e intención de matrícula, necesidades de capacitación, pertinencia laboral, aceptación de la tarifa preliminar (₡150.000 por módulo y ₡900.000 por el programa), preferencias académicas, competencia, empleabilidad y viabilidad con un mínimo de 10 estudiantes.',
        tarifa_preliminar='₡150.000 por módulo · ₡900.000 programa completo (tarifa preliminar mencionada por el proponente, por validar)',
        segmentos=['Profesionales', 'Funcionarios públicos', 'Estudiantes', 'Colaboradores de organizaciones sociales'],
        ofertas=[
            oferta('Universidad Nacional (UNA)', 'Relaciones Internacionales y formación en cooperación internacional', tipo='Otro nivel', nota='Lista preliminar del proponente; costo por verificar.'),
            oferta('Universidad de Costa Rica (UCR)', 'Administración Pública y formación en gestión de proyectos', tipo='Otro nivel', nota='Lista preliminar del proponente; costo por verificar.'),
            oferta('Universidad Estatal a Distancia (UNED)', 'Gestión de proyectos y desarrollo local', nota='Lista preliminar del proponente; costo por verificar.'),
            oferta('ULACIT', 'Relaciones Internacionales y programas afines', tipo='Otro nivel', nota='Lista preliminar del proponente; costo por verificar.'),
            oferta('Instituto Centroamericano de Administración Pública (ICAP)', 'Gestión de proyectos, administración pública y desarrollo', nota='Lista preliminar del proponente; costo por verificar.'),
            oferta('INCAE Business School', 'Dirección y gestión de proyectos', nota='Lista preliminar del proponente; costo por verificar.'),
        ],
    ),
    dict(
        id='ataque_defensa_nube_cr', archivo_json='ulatina_ataque_defensa_nube_cr.json', institucion_id='ulatina_cr',
        pdf='Brief CR Introducción al Ataque y Defensa de Aplicaciones en la Nube.pdf', paginas='1–4', fecha_propuesta='2026-10-26',
        nombre='Técnico en Introducción al Ataque y Defensa de Aplicaciones en la Nube', tipo='Técnico · Apertura de nuevo programa',
        area='Ingeniería', facultad='Facultad de Ingenierías y TICs', unidad='Rectoría',
        duracion='2 cuatrimestres', horas_totales=None, modalidad='Presencial (100% presencial)',
        objetivo='Desarrollar conocimientos fundamentales en ciberseguridad aplicada a la computación en la nube (seguridad de aplicaciones, protección de datos, identidades y accesos, amenazas y vulnerabilidades, DevSecOps y Ethical Hacking) y habilidades prácticas para evaluar riesgos, aplicar controles, realizar pruebas de seguridad autorizadas e integrar buenas prácticas en el ciclo de desarrollo de software.',
        diferenciadores=[
            'Integración de tres áreas estratégicas de ciberseguridad: Cloud Security, DevSecOps y Ethical Hacking.',
            'Formación alineada con certificaciones internacionales de EC-Council: Cloud Security Essentials (CSE), DevSecOps Essentials (DSE) y Ethical Hacking Essentials (EHE).',
            'Enfoque práctico mediante laboratorios especializados: vulnerabilidades, pruebas de penetración y protección de aplicaciones cloud en escenarios simulados.',
            'Seguridad integrada al desarrollo de software: DevSecOps, automatización de controles, análisis de vulnerabilidades y protección de procesos CI/CD.',
            'Proyecto integrador con escenarios reales: seguridad ofensiva, defensiva, análisis de riesgos y protección de aplicaciones cloud-native.',
        ],
        habilidades=['Seguridad en Cloud', 'Hacking Ético', 'Análisis de Vulnerabilidades', 'Gestión de Riesgos', 'Automatización DevSecOps'],
        nombres_alternativos=['Introducción al Ataque y Defensa de Aplicaciones en la Nube'],
        palabras_clave=['Ciberseguridad', 'Cloud Security', 'Ethical Hacking', 'DevSecOps', 'Seguridad Ofensiva', 'Seguridad Defensiva',
                        'Computación en la Nube', 'Análisis de Vulnerabilidades', 'Seguridad de Aplicaciones', 'Pruebas de Penetración'],
        sector_declarado='Actividades profesionales, científicas y técnicas',
        interes_investigacion='Interés y demanda potencial en Costa Rica, necesidades de formación y competencias valoradas, perfil de estudiantes, disposición de pago, modalidades y horarios, factores de decisión, oferta competidora y rangos de precios.',
        nota_registro='El formulario se registró desde Ecuador con un correo UDLA, pero el brief indica ULatina ([Q35]) y el mercado de Costa Rica; se registra en ULatina · Costa Rica.',
        segmentos=[],
        ofertas=[],
        competencia_texto='El proponente menciona competencia nacional en formación técnica de ciberseguridad sin identificar instituciones ni precios.',
    ),
    dict(
        id='marca_personal_cr', archivo_json='ulatina_marca_personal_cr.json', institucion_id='ulatina_cr',
        pdf='Brief CR Marca Personal.pdf', paginas='1–4', fecha_propuesta='2026-10-20',
        nombre='Marca Personal', tipo='Técnico · Apertura de nuevo programa',
        area='Comunicación colectiva', facultad='Facultad de Arte, Diseño y Comunicación Colectiva', unidad='Otro · Campus Creativo',
        duracion='2 cuatrimestres', horas_totales=None, modalidad='Presencial (100% presencial)',
        objetivo='Definir la marca personal y la propuesta de valor; aplicar dicción, manejo de la voz, expresión oral, lenguaje corporal y presencia frente a cámaras; planificar, producir y editar contenidos digitales con storytelling; desarrollar una estrategia básica de posicionamiento digital apoyada en herramientas de inteligencia artificial.',
        diferenciadores=['Integra la comunicación personal, la expresión corporal y oral, y la producción de contenido digital en una sola experiencia formativa.',
                         'A diferencia de propuestas centradas en marketing digital o redes sociales, trabaja cómo se presenta y comunica la persona y cómo proyecta su identidad en medios digitales.'],
        habilidades=['Marca personal para diferenciación profesional y emprendimiento', 'Creación de contenido audiovisual para redes y plataformas',
                     'Comunicación frente a cámaras', 'Manejo del lenguaje corporal', 'Storytelling y comunicación auténtica'],
        nombres_alternativos=['Posicionamiento Profesional y Marca Personal', 'Gestión de Marca Personal'],
        palabras_clave=['Marca', 'Personal', 'Imagen', 'Profesional', 'Digital', 'Posicionamiento', 'Networking', 'Contenido', 'Storytelling', 'Comunicación'],
        sector_declarado='Información y comunicación · Actividades financieras y de seguros · Actividades inmobiliarias · Enseñanza · Actividades artísticas, de entretenimiento y recreativas',
        interes_investigacion='Preferencia por modalidad presencial o híbrida, horario y frecuencia (uno o dos días por semana).',
        segmentos=[],
        ofertas=[
            oferta('FUNDEPOS', 'Marca Personal Innovadora', horas=40, usd=400),
            oferta('Universidad de Costa Rica (UCR)', 'Curso de Marca Personal', usd=100, nota='4 sesiones.'),
            oferta('TECH Global University', 'Marca Personal', horas=150, nota='6 semanas; precio no especificado.'),
        ],
    ),
    dict(
        id='multiplataformas_deportivas_cr', archivo_json='ulatina_multiplataformas_deportivas_cr.json', institucion_id='ulatina_cr',
        pdf='Brief CR Multiplataformas deportivas.pdf', paginas='1–4', fecha_propuesta='2026-10-19',
        nombre='Multiplataformas deportivas', tipo='Técnico · Apertura de nuevo programa',
        area='Comunicación colectiva', facultad='Facultad de Arte, Diseño y Comunicación Colectiva', unidad='Técnicos',
        duracion='1 cuatrimestre (estructura de diez semanas, según los diferenciadores)', horas_totales=None, modalidad='Presencial (100% presencial)',
        objetivo='Conocer los ecosistemas mediáticos deportivos, las audiencias digitales y los formatos audiovisuales; investigar, planificar y ejecutar coberturas deportivas, construir narrativas, entrevistar, desenvolverse frente a cámara y producir contenidos móviles para redes sociales, pódcast, videopódcast y transmisiones en vivo.',
        diferenciadores=['Enfoque integral, intensivo y orientado a la producción de contenidos deportivos multiplataforma, más allá de la narración, el comentario o la cobertura tradicional.',
                         'Estructura de diez semanas que combina periodismo, creatividad y tecnología con experiencias teórico-prácticas en situaciones reales o simuladas.'],
        habilidades=['Comunicación digital', 'Producción audiovisual', 'Narrativa transmedia', 'Estrategia de contenidos', 'Análisis de tendencias'],
        nombres_alternativos=['SportsMedia Lab', 'Producción de contenidos deportivos'],
        palabras_clave=['Comunicación deportiva', 'Periodismo deportivo', 'Producción audiovisual', 'Narrativas digitales', 'Contenido multiplataforma',
                        'Marketing deportivo', 'Redes sociales', 'Transmisiones deportivas', 'Storytelling', 'Estrategia digital'],
        sector_declarado='Información y comunicación · Enseñanza',
        interes_investigacion='Tendencias: periodismo móvil (MOJO), videos cortos, streaming, pódcast y videopódcast, storytelling deportivo, IA, datos y estadísticas, e integración del periodismo con la creación de contenido digital.',
        segmentos=[],
        ofertas=[
            oferta('Universidad de Costa Rica (UCR)', 'Curso de Producción y Realización Audiovisual en Vivo', crc=219300, nota='Matrícula ₡35.700 + 4 mensualidades de ₡45.900.'),
            oferta('Tecnológico de Costa Rica (TEC)', 'Curso básico de Producción de Videos para Emprendedores', modalidad='Virtual', horas=16, crc=22000),
        ],
    ),
    dict(
        id='storymakers_cr', archivo_json='ulatina_storymakers_cr.json', institucion_id='ulatina_cr',
        pdf='Brief CR StoryMakers.pdf', paginas='1–4', fecha_propuesta='2026-10-19',
        nombre='StoryMakers', tipo='Técnico · Apertura de nuevo programa',
        area='Comunicación colectiva', facultad='Facultad de Arte, Diseño y Comunicación Colectiva', unidad='Técnicos',
        duracion='2 cuatrimestres', horas_totales=None, modalidad='Presencial (100% presencial)',
        objetivo='La persona graduada podrá participar en procesos de investigación de audiencias, conceptualización creativa, escritura narrativa, producción de contenido, integración responsable de inteligencia artificial y evaluación del desempeño digital, con un portafolio de proyectos que evidencie sus competencias.',
        diferenciadores=['Formación aplicada que combina creatividad, estrategia, tecnología y medición de resultados.',
                         'Cada participante aprenderá a transformar ideas en soluciones de comunicación concretas, fundamentadas y adaptadas a las audiencias y al mercado profesional.'],
        habilidades=['Storytelling creativo', 'Creación de contenidos', 'Narrativa digital', 'Pensamiento creativo', 'Producción audiovisual'],
        nombres_alternativos=['El arte de contar historias', 'StoryLab'],
        palabras_clave=['Storytelling', 'Creatividad', 'Narrativa', 'Contenidos', 'Guionismo', 'Audiovisual', 'Innovación', 'Comunicación', 'Digital', 'Publicidad'],
        sector_declarado='Información y comunicación · Enseñanza',
        interes_investigacion='Tendencias de la industria creativa: IA generativa, storytelling y narrativas de marca, producción multiplataforma, análisis de audiencias, personalización y automatización, analítica digital, distribución y posicionamiento en buscadores.',
        segmentos=[],
        ofertas=[
            oferta('Universidad de Costa Rica (UCR)', 'Storytelling y Marketing Digital', horas=12, crc=61200, nota='El brief también menciona ₡56.000 para el mismo curso.'),
            oferta('Universidad de Costa Rica (UCR)', 'Especialización Profesional en Diseño y Creación de Contenido', crc=1137300, nota='Matrícula ₡35.700 + 18 mensualidades de ₡61.200.'),
            oferta('Universidad CENFOTEC', 'Data Storytelling', usd=224.40, nota='US$220 + 2% de IVA.'),
            oferta('Universidad Nacional (UNA)', 'Guion para Producción Audiovisual', crc=122400, nota='Programa Investigación, Arte y Transmedia; IVA incluido.'),
        ],
    ),
    dict(
        id='diseno_generativo_ia', archivo_json='udla_diseno_generativo_ia.json', institucion_id='udla_ec',
        pdf='Brief EDCO Diseño Generativo y Automatización con IA.pdf', paginas='1–5', fecha_propuesta='2026-10-11',
        nombre='Diplomado en Diseño Generativo y Automatización con IA', tipo='Diplomado · Educación continua (EDCO)',
        area='Ingeniería, industria y construcción › Arquitectura y construcción › Arquitectura', facultad='Facultad de Arquitectura y Diseño',
        unidad='Facultad de Arquitectura y Diseño', duracion='3 semestres', horas_totales=None, modalidad='En línea (100% en línea)',
        experto='Propuesto en el brief (dato personal omitido en la vista)',
        objetivo='Desarrollar competencias para integrar la inteligencia artificial como asistente en los procesos de diseño, mediante la exploración y representación de propuestas, el análisis de información para fundamentar decisiones y la optimización de tareas de documentación técnica en CAD, manteniendo el criterio, la autoría y la responsabilidad del diseñador.',
        ejes=['Ideación, representación y posproducción de imágenes con IA', 'Análisis de datos para el diseño con IA', 'Documentación técnica y procesos CAD'],
        diferenciadores=[
            'Tres módulos independientes, sin prerrequisitos entre ellos: exploración gráfica, análisis de datos o documentación técnica.',
            'IA aplicada a arquitectura, diseño industrial, diseño de interiores y diseño gráfico, con ejercicios adaptados a espacios, productos y comunicación visual.',
            'Exploración visual, decisiones fundamentadas y desarrollo técnico en una misma oferta: alternativas gráficas, criterios de diseño y planos o despieces editables en CAD.',
            'Talleres con acompañamiento docente experto: cada módulo combina 12 horas sincrónicas con ejercicios asincrónicos y un proyecto breve.',
            'Control del resultado y conservación del criterio del diseñador: dirigir, comparar y corregir los resultados de la IA.',
        ],
        habilidades=['IA para diseño', 'Flujos de trabajo con IA', 'Pensamiento crítico', 'Comunicación gráfica efectiva', 'Automatización de procesos'],
        nombres_alternativos=['Diplomado en estrategias de diseño con IA', 'Diplomado en IA para procesos de diseño'],
        palabras_clave=['IA para diseño', 'Inteligencia artificial generativa', 'IA en arquitectura', 'Diseño industrial IA', 'Diseño gráfico IA',
                        'Posproducción con IA', 'Análisis de datos', 'Automatización CAD', 'Planos con IA', 'IA aplicada'],
        ciiu='M7410.09', sector_declarado=None,
        interes_investigacion='Qué problemas motivarían la inscripción, diferencias entre perfiles (arquitectos, diseñadores industriales, de interiores y gráficos; estudiantes y profesionales), herramientas que usan y qué nombre comunica mejor el programa (p. ej., «Diseño Aumentado con IA»).',
        segmentos=['Arquitectos', 'Diseñadores industriales', 'Diseñadores de interiores', 'Diseñadores gráficos', 'Estudiantes y profesionales desde niveles intermedios de formación'],
        ofertas=[
            oferta('UDLA', 'Diplomado en Principios y Estrategias en Inteligencia Artificial', tipo='Oferta propia', nota='Cuatro meses, tres materias; posible solapamiento interno según el brief.'),
            oferta('UDLA', 'Diplomado en Inteligencia Artificial para la Estrategia de Marketing y Ventas', tipo='Oferta propia', modalidad='Híbrida', horas=70, nota='Finalidad comercial distinta, según el brief.'),
            oferta('UDLA', 'Maestrías en Inteligencia Artificial Aplicada y en Diseño Arquitectónico Avanzado', tipo='Otro nivel', nota='Requieren título de grado.'),
            oferta('USFQ', 'Diseño Gráfico potenciado por Inteligencia Artificial', nota='Coincide con el primer módulo, según el brief.'),
            oferta('Universidad Hemisferios', 'Certificación en Diseño Gráfico y Creación de Contenido con Inteligencia Artificial', nota='Coincide con el primer módulo, según el brief.'),
            oferta('Universidad del Azuay', 'Prompt Engineering: IA en Arquitectura', nota='Dirigido a docentes de su Facultad de Arquitectura.'),
            oferta('UNAM', 'Diplomado-Taller de Arquitectura 4.0 e Inteligencia Artificial Aplicada', nota='Referencia regional; módulos secuenciales.'),
            oferta('Universidad Continental', 'Programa sin nombre indicado en el brief', nota='Referencia regional: arquitectura, ingeniería y construcción con IA, BIM y automatización.'),
            oferta('Pontificia Universidad Católica de Chile', 'Diplomado sin nombre indicado en el brief', nota='Referencia regional; exige título profesional, licenciatura o equivalente.'),
        ],
    ),
    dict(
        id='figma_ia', archivo_json='udla_figma_ia.json', institucion_id='udla_ec', fecha_registro='2026-11-16',
        pdf='Brief EDCO Figma e Inteligencia Artificial.pdf', paginas='1–5', fecha_propuesta='2026-11-13',
        nombre='Diplomado en Figma e Inteligencia Artificial', tipo='Diplomado · Educación continua (EDCO)',
        area='Artes y humanidades › Artes › Diseño', facultad='Facultad de Comunicación y Artes Audiovisuales',
        unidad='Facultad de Comunicación y Artes Audiovisuales', duracion='1 semestre', horas_totales=None,
        modalidad='En línea (100% en línea)', experto='Propuesto en el brief (dato personal omitido en la vista)',
        objetivo='Formar profesionales capaces de diseñar interfaces digitales funcionales y atractivas para web y móvil, utilizando Figma y herramientas de inteligencia artificial, con un portafolio profesional que les permita insertarse o crecer en el mercado laboral del diseño digital.',
        ejes=['Diseño de interfaces y sistemas visuales', 'Herramientas digitales e inteligencia artificial aplicada al diseño',
              'Lenguajes del diseño web y del prototipo al código', 'Portafolio y práctica profesional'],
        diferenciadores=[
            'Primer escalón de una ruta apilable (diplomado, certificación y maestría): las materias se homologan directamente al subir de nivel.',
            'La inteligencia artificial se aplica en cada materia como herramienta de trabajo, no como un módulo teórico aparte.',
            'El estudiante egresa con un portafolio real publicado, listo para postular a empleos.',
            'Incluye una materia homologable desde el pregrado UDLA, lo que facilita el acceso a exalumnos.',
            'Docentes activos en la industria del diseño de productos digitales.',
        ],
        habilidades=['Diseño de interfaces', 'Prototipado en Figma', 'IA aplicada al diseño', 'Pensamiento visual', 'Portafolio profesional'],
        nombres_alternativos=['Diseño de Interfaces con Figma e Inteligencia Artificial', 'Figma e Inteligencia Artificial para el Diseño de Interfaces'],
        palabras_clave=['Figma', 'Inteligencia artificial', 'Interfaces', 'UI', 'Prototipado', 'Diseño web', 'Apps', 'Portafolio',
                        'Componentes', 'Experiencia de usuario'],
        ciiu='J6201.01', sector_declarado=None,
        interes_investigacion='Tamaño del público potencial en Quito, Guayaquil y Cuenca por perfil (diseñadores gráficos, comunicadores, desarrolladores, egresados UDLA); disposición de pago y modalidad preferida; demanda de empresas (banca, fintech, consultoras de software) para cohortes corporativas; nombre más atractivo para el público; intención de continuar hacia la certificación y la maestría.',
        segmentos=['Diseñadores gráficos', 'Comunicadores', 'Desarrolladores', 'Egresados UDLA',
                   'Empresas de banca, fintech y consultoras de software (cohortes corporativas)'],
        ofertas=[
            oferta('USFQ', 'UX con IA para diseño y prototipado de apps', usd=330, nota='Curso de 4 semanas; precio para público general.'),
            oferta('Coderhouse', 'Diseño UX/UI', tipo='Plataforma', modalidad='En línea', nota='13 semanas; precio no publicado.'),
            oferta('IEBS', 'Diplomado en UX Product Design', tipo='Plataforma', modalidad='En línea', nota='6 meses; precio no publicado.'),
            oferta('Google · Coursera', 'Certificado Profesional en Diseño UX', tipo='Plataforma', modalidad='En línea', nota='Pago por suscripción.'),
            oferta('Universidad Casa Grande', 'Maestría en Experiencia de Usuario y Diseño de Interfaces UX/UI', tipo='Otro nivel', modalidad='En línea', nota='Precio no publicado.'),
            oferta('Universidad UTE', 'Maestría en Diseño, mención Diseño Digital', tipo='Otro nivel', usd=3990, nota='Monto aproximado según el brief.'),
        ],
    ),
    dict(
        id='diseno_estrategico', archivo_json='udla_diseno_estrategico.json', institucion_id='udla_ec', fecha_registro='2026-11-16',
        pdf='Brief EDCO DISEÑO ESTRATÉGICO DEL MÉTODO AL SISTEMA.pdf', paginas='1–4', fecha_propuesta='2026-11-13',
        nombre='Diplomado en Diseño Estratégico: del Método al Sistema', tipo='Diplomado · Educación continua (EDCO)',
        area='Artes y humanidades › Artes › Artes', facultad='Facultad de Comunicación y Artes Audiovisuales',
        unidad='Otro · Producto', duracion='1 semestre', horas_totales=None,
        modalidad='Presencial (100% presencial)', experto='Propuesto en el brief (dato personal omitido en la vista)',
        objetivo='Desarrollar competencias en investigación, pensamiento sistémico y gestión estratégica del diseño, mediante la aplicación de metodologías de análisis, evaluación de sistemas materiales y criterios de sostenibilidad, que permitan formular soluciones innovadoras y gestionar proyectos interdisciplinarios orientados a la generación de valor en organizaciones y comunidades.',
        ejes=['Metodologías de investigación y pensamiento sistémico', 'Innovación, sistemas materiales y economía circular',
              'Gestión estratégica y desarrollo de proyectos de diseño'],
        diferenciadores=['Conexión con industrias textiles.', 'Estampería Quiteña.', 'Creación de colección.'],
        habilidades=['Pensamiento sistémico y crítico', 'Investigación y análisis contextual', 'Innovación en sistemas materiales',
                     'Planificación y gestión estratégica del diseño', 'Liderazgo y colaboración interdisciplinaria'],
        nombres_alternativos=['Diplomado en Diseño Estratégico e Innovación de Sistemas Materiales', 'Diplomado en Metodologías y Gestión Estratégica del Diseño'],
        palabras_clave=['Diseño estratégico', 'Metodologías del diseño', 'Pensamiento sistémico', 'Investigación aplicada', 'Innovación',
                        'Sistemas materiales', 'Economía circular', 'Sostenibilidad', 'Gestión de proyectos', 'Diseño interdisciplinario'],
        ciiu='M7410.09', sector_declarado=None,
        nota_registro='El brief declara M7410.00, que es la clase de cuatro dígitos (actividades especializadas de diseño) y no existe como código de seis dígitos en el SRI; se usa la subclase M7410.09 «otras actividades especializadas de diseño», la más cercana al diseño estratégico y de sistemas.',
        interes_investigacion='Demanda de formación especializada en diseño estratégico, sectores productivos y organizacionales con mayor interés, competencias profesionales requeridas por el mercado y disposición de pago del público objetivo; tendencias y oportunidades del diseño estratégico, la innovación en sistemas materiales y la sostenibilidad en Ecuador.',
        segmentos=[],
        ofertas=[
            oferta('Universidad Hemisferios', 'Diplomado en Design Thinking', nota='Precio no informado.'),
            oferta('Universidad del Azuay', 'Maestría en Diseño, Desarrollo y Gestión de Productos', tipo='Otro nivel', nota='Precio no informado.'),
            oferta('Pontificia Universidad Católica de Chile', 'Diplomado en Proyectos de Diseño e Innovación', nota='Referencia regional; precio no informado.'),
            oferta('Universidad Adolfo Ibáñez', 'Diplomado en Innovación Estratégica y Design Thinking', nota='Referencia regional (Chile); precio no informado.'),
            oferta('Universidad del Desarrollo', 'Diplomado en Diseño de Estrategias Sostenibles y Upcycling', nota='Referencia regional (Chile); precio no informado.'),
        ],
    ),
    dict(
        id='forma_textil_superficies', archivo_json='udla_forma_textil_superficies.json', institucion_id='udla_ec', fecha_registro='2026-11-16',
        pdf='Brief EDCO FORMA, TEXTIL Y SUPERFICIES.pdf', paginas='1–4', fecha_propuesta='2026-11-13',
        nombre='Diplomado en Forma, Textil y Superficies', tipo='Diplomado · Educación continua (EDCO)',
        area='Artes y humanidades › Artes › Artes', facultad='Facultad de Comunicación y Artes Audiovisuales',
        unidad='Otro · Producto', duracion='1 semestre', horas_totales=None,
        modalidad='Presencial (100% presencial)', experto='Propuesto en el brief (dato personal omitido en la vista)',
        objetivo='Desarrollar competencias en dirección de arte, diseño de superficies y tecnologías digitales, mediante la integración de conceptos estéticos, exploración de materiales y procesos de diseño y prototipado, para generar soluciones visuales, funcionales e innovadoras con criterios de calidad, viabilidad y sostenibilidad.',
        ejes=['Dirección de arte, expresión visual y materialidad', 'Diseño de superficies y procesos productivos',
              'Diseño digital, tecnologías y prototipado'],
        diferenciadores=['Conexión con industrias textiles.', 'Estampería Quiteña.', 'Creación de colección.'],
        habilidades=['Conceptualización y dirección de arte', 'Diseño y desarrollo de superficies', 'Exploración y selección de materiales',
                     'Modelado y representación digital', 'Prototipado y fabricación digital'],
        nombres_alternativos=['Diplomado en Diseño de Superficies, Materialidad e Innovación Digital', 'Diplomado en Dirección de Arte y Diseño Digital de Superficies'],
        palabras_clave=['Dirección de arte', 'Materialidad', 'Superficies', 'Diseño textil', 'Cultura visual', 'Diseño paramétrico',
                        'Inteligencia artificial', 'Modelado tridimensional', 'Prototipado', 'Fabricación digital'],
        ciiu='M7410.01', sector_declarado=None,
        nota_registro='El brief declara M7410.00, que es la clase de cuatro dígitos (actividades especializadas de diseño) y no existe como código de seis dígitos en el SRI; se usa la subclase M7410.01, diseño de telas, prendas de vestir y artículos de moda, la más cercana al diseño textil y de superficies.',
        interes_investigacion='Demanda de formación especializada en diseño de superficies, dirección de arte y tecnologías digitales; sectores creativos y productivos con mayor potencial de aplicación; herramientas y competencias técnicas requeridas por el mercado; oferta académica competidora y disposición de pago del público objetivo.',
        segmentos=[],
        ofertas=[
            oferta('Universidad Hemisferios', 'Diplomado en Diseño Gráfico', nota='Precio no informado.'),
            oferta('Universidad del Azuay', 'Maestría en Diseño Textil y de Indumentaria, mención Gestión y Producción', tipo='Otro nivel', nota='Precio no informado.'),
            oferta('Pontificia Universidad Católica de Chile', 'Diplomado en Creación Textil y Diseño de Superficies', nota='Referencia regional; precio no informado.'),
            oferta('Pontificia Universidad Católica de Chile', 'Diplomado en Fabricación Digital: Diseño y Producción de Prototipos', nota='Referencia regional; precio no informado.'),
            oferta('Universidad Finis Terrae', 'Diplomado en Diseño y Producción Experimental Textil', nota='Referencia regional (Chile); precio no informado.'),
        ],
    ),
    dict(
        id='manufactura_avanzada_cr', archivo_json='ulatina_manufactura_avanzada_cr.json', institucion_id='ulatina_cr',
        pdf='Brief CR Manufactura Avanzada.pdf', paginas='1–4', fecha_propuesta='2026-11-16', fecha_registro='2026-11-24',
        nombre='Técnico en Manufactura Avanzada', tipo='Técnico · Apertura de nuevo programa',
        area='Ingeniería', facultad='Facultad de Ingenierías y TICs', unidad='Técnicos',
        duracion='3 cuatrimestres', horas_totales=None, modalidad='Presencial (100% presencial)',
        objetivo='Comprender los principios de los procesos de manufactura, calidad, productividad, mejora continua, seguridad ocupacional, mantenimiento, automatización y tecnologías aplicadas a la manufactura moderna; ejecutar procedimientos de producción, utilizar herramientas y equipos básicos, registrar información de procesos, identificar oportunidades de mejora y aplicar controles básicos de calidad y seguridad.',
        diferenciadores=[
            'Enfoque práctico en manufactura moderna: materias orientadas a producción, calidad, mejora continua, seguridad, mantenimiento y automatización.',
            'Aprendizaje aplicado en laboratorio: uso de equipos, herramientas y tecnologías asociadas con Industria 4.0 y procesos de manufactura.',
            'Giras y visitas técnicas a plantas y empresas para conocer procesos productivos reales y buenas prácticas industriales.',
            'Resolución de problemas reales: talleres enfocados en productividad, reducción de desperdicios y mejora de procesos.',
        ],
        habilidades=['Mejora continua y optimización de procesos', 'Control de calidad y estandarización', 'Automatización y uso de tecnologías de manufactura',
                     'Resolución de problemas y análisis de datos', 'Seguridad, mantenimiento y trabajo en equipo'],
        nombres_alternativos=['Técnico en Procesos de Manufactura e Industria 4.0'],
        palabras_clave=['Manufactura avanzada', 'Industria 4.0', 'Automatización', 'Producción', 'Calidad', 'Mejora continua',
                        'Mantenimiento', 'Productividad', 'Procesos industriales', 'Seguridad ocupacional'],
        sector_declarado='Industrias manufactureras',
        interes_investigacion='Interés y disposición de matrícula, perfil del estudiante potencial (edad, experiencia, nivel educativo, sector), áreas de mayor interés, modalidad y horarios, rango de precio, razones de elección, empresas y sectores que demandarían el perfil y percepción de la duración de un año.',
        nota_registro='El brief también menciona el nombre «Técnico en Manufactura Moderna» al describir la investigación solicitada.',
        segmentos=[],
        ofertas=[
            oferta('Universidad CENFOTEC', 'Técnico en Calidad y Operaciones 4.0', usd=2193, nota='Programa completo, según el brief.'),
            oferta('Tecnológico de Costa Rica (TEC)', 'Técnico en Supervisión de Producción', crc=1155732, nota='Programa completo aproximado, según el brief.'),
            oferta('Tecnológico de Costa Rica (TEC)', 'Técnico en Calidad', crc=1215000, nota='Programa completo aproximado, según el brief.'),
            oferta('Universidad CENFOTEC', 'Técnico en Ingeniería Robótica', crc=3774720, nota='Programa completo, según el brief.'),
        ],
    ),
    dict(
        id='ia_databricks_cr', archivo_json='ulatina_ia_databricks_cr.json', institucion_id='ulatina_cr',
        pdf='Brief CR Inteligencia Artificial Aplicada con Databricks.pdf', paginas='1–4', fecha_propuesta='2026-11-08', fecha_registro='2026-11-24',
        nombre='Técnico en Inteligencia Artificial Aplicada con Databricks', tipo='Técnico · Apertura de nuevo programa',
        area='Ingeniería', facultad='Facultad de Ingenierías y TICs', unidad='Otro · Facultad de Ingenierías y TICs',
        duracion='4 cuatrimestres', horas_totales=None, modalidad='En línea (100% en línea)',
        objetivo='Desarrollar conocimientos sobre fundamentos de inteligencia artificial, Machine Learning e IA generativa, modelos de lenguaje (LLM), arquitecturas RAG y agentes inteligentes, y habilidades prácticas para diseñar, desarrollar, implementar y evaluar soluciones de IA con Databricks, integrando datos empresariales, automatizando procesos y aplicando herramientas de despliegue, monitoreo, seguridad y gobernanza.',
        diferenciadores=[
            'Especialización en IA aplicada con Databricks, orientada a egresados del Técnico en Ingeniería de Datos y profesionales con experiencia en Databricks, sin repetir fundamentos de ingeniería de datos.',
            'Formación práctica con laboratorios y proyectos en Databricks, LLM, arquitecturas RAG, agentes de IA y MLflow.',
            'Contenidos alineados con la certificación Databricks Certified Generative AI Engineer Associate.',
            'Proyectos empresariales integradores para automatizar procesos, aprovechar datos empresariales y mejorar la toma de decisiones.',
            'Enfoque transversal en seguridad, ética, privacidad y gobernanza de la IA.',
        ],
        habilidades=['Soluciones de IA generativa con LLM y Databricks', 'Aplicaciones RAG con datos empresariales', 'Agentes de IA para automatizar procesos',
                     'Despliegue, evaluación y monitoreo con MLflow y Databricks', 'Seguridad, gobernanza y uso responsable de la IA'],
        nombres_alternativos=['Técnico en Inteligencia Artificial Generativa y Agentes Inteligentes con Databricks',
                              'Técnico en Desarrollo de Soluciones de Inteligencia Artificial con Databricks'],
        palabras_clave=['Inteligencia Artificial Aplicada', 'Inteligencia Artificial Generativa', 'Databricks', 'Modelos de Lenguaje (LLM)',
                        'Generación Aumentada por Recuperación (RAG)', 'Agentes Inteligentes', 'Machine Learning', 'MLflow y LLMOps',
                        'Despliegue y Monitoreo de Modelos', 'Seguridad y Gobernanza de IA'],
        sector_declarado='Actividades profesionales, científicas y técnicas',
        interes_investigacion='Atractivo del programa para profesionales que ya utilizan Databricks, principales barreras para matricularse y factores de decisión frente a otras opciones de formación en inteligencia artificial.',
        segmentos=[],
        ofertas=[],
        competencia_texto='El proponente indica que ninguna institución posee programas específicos en Databricks.',
    ),
]


def construir_ficha(d):
    institucion = INSTITUCIONES_EDCO[d['institucion_id']]
    fecha = d.get('fecha_registro', FECHA_REGISTRO)
    copia = f"edcos_fuentes/brief_{d['id']}.pdf"
    evaluacion = {key: dict(puntaje=None, estado='Sin calificar', subcategorias=subcats,
                            justificacion='Pendiente de investigación de mercado. El brief registra la propuesta; no constituye evidencia de demanda, empleabilidad, competencia, precio ni sector.',
                            fuentes=[], nivel_evidencia='Sin investigación de mercado')
                  for key, subcats in SUBCATEGORIAS.items()}
    origen = ('Segmentos mencionados por el proponente en el brief; pendientes de contraste con el mercado.' if d['segmentos']
              else 'El brief no describe segmentos de audiencia; se definirán en la investigación de mercado.')
    brief = dict(
        archivo=d['pdf'], copia_local=copia, fecha_propuesta=d['fecha_propuesta'], tipo=d['tipo'], pais=institucion['pais'],
        area_estudio=d['area'], facultad=d['facultad'], unidad=d['unidad'], duracion=d['duracion'], horas_totales=d['horas_totales'],
        modalidad=d['modalidad'], experto=d.get('experto', 'No definido en el brief'), objetivo=d['objetivo'],
        diferenciadores=d['diferenciadores'], ejes=d.get('ejes', [NO_INFORMADO]), habilidades=d['habilidades'],
        nombres_alternativos=d['nombres_alternativos'], palabras_clave=d['palabras_clave'], ciiu=d.get('ciiu'),
        sector_declarado=d['sector_declarado'] or 'Ver código CIIU', interes_investigacion=d['interes_investigacion'],
        competencia_declarada=d.get('competencia_texto', f"{len(d['ofertas'])} alternativa(s) mencionada(s) por el proponente; ver Oferta y plataformas."),
    )
    for key in ('tarifa_preliminar', 'nota_registro'):
        if d.get(key):
            brief[key] = d[key]
    ficha = dict(
        id=d['id'], nombre=d['nombre'], institucion_id=d['institucion_id'], fecha_revision=fecha,
        version_investigacion=fecha + '-brief-registrado',
        brief=brief, audiencia_propuesta=dict(origen=origen, segmentos=d['segmentos'], tamano=None, pagador='No definido'),
        fuentes=[dict(id='brief', titulo='Brief del proponente · ' + d['nombre'], archivo=d['pdf'], paginas=d['paginas'], fecha=fecha)],
        ofertas=d['ofertas'], evaluacion=evaluacion, recomendaciones=[],
    )
    validar_ficha(ficha)
    return ficha


def registrar(carpeta_pdf=None, ids=None):
    """``ids``: registra solo esos briefs (sin reescribir las demás fichas)."""
    for d in BRIEFS:
        if ids and d['id'] not in ids:
            continue
        ficha = construir_ficha(d)
        (BASE / 'edcos_data' / d['archivo_json']).write_text(json.dumps(ficha, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        if carpeta_pdf:
            origen = Path(carpeta_pdf) / d['pdf']
            if origen.is_file():
                shutil.copyfile(origen, BASE / ficha['brief']['copia_local'])
            else:
                print('PDF no encontrado:', origen)
        print('Registrado:', d['archivo_json'])
    # Las fichas con investigación (edcos_investigacion/<id>.json) se completan de nuevo,
    # para que volver a registrar no borre la evidencia de mercado.
    from completar_investigacion_edcos import completar_todos
    completar_todos()


if __name__ == '__main__':
    registrar(sys.argv[1] if len(sys.argv) > 1 else None, sys.argv[2:] or None)

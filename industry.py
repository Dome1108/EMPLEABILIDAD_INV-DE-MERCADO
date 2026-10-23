"""Cruce de empleadores con CIIU y ventas sectoriales SRI."""
import re
import pandas as pd

SALES = ['411 · Personas naturales', '411 · Sociedades', '413 · Personas naturales', '413 · Sociedades']
SECTIONS = dict(zip('ABCDEFGHIJKLMNOPQRSTU', [
    'Agricultura, ganadería, silvicultura y pesca', 'Minas y canteras', 'Manufactura',
    'Electricidad y gas', 'Agua y saneamiento', 'Construcción', 'Comercio',
    'Transporte y almacenamiento', 'Alojamiento y comidas', 'Información y comunicación',
    'Finanzas y seguros', 'Actividades inmobiliarias', 'Actividades profesionales, científicas y técnicas',
    'Servicios administrativos y de apoyo', 'Administración pública', 'Enseñanza',
    'Salud y asistencia social', 'Arte y recreación', 'Otros servicios',
    'Actividades de los hogares', 'Organizaciones extraterritoriales']))

MACROINDUSTRIES = [
    ('A', 'Agricultura, ganadería, silvicultura y pesca'),
    ('B', 'Petróleo, minería y extracción'),
    ('C', 'Industria manufacturera'),
    ('DE', 'Energía, agua y saneamiento'),
    ('F', 'Construcción e infraestructura'),
    ('G', 'Comercio y distribución'),
    ('H', 'Transporte y logística'),
    ('I', 'Turismo, alojamiento y gastronomía'),
    ('J', 'Tecnología, información y comunicaciones'),
    ('KL', 'Servicios financieros, seguros e inmobiliarios'),
    ('MN', 'Servicios profesionales, empresariales y administrativos'),
    ('OPQRSTU', 'Servicios públicos, educación, salud, cultura y otros servicios'),
]
MACRO_BY_SECTION = {letter: name for letters, name in MACROINDUSTRIES for letter in letters}


def macroindustry_summary(jobs, mapping, sales, codes, year, month):
    selected_mapping = mapping[mapping.CIIU.isin(set(codes))].copy()
    selected_mapping['Macroindustria'] = selected_mapping.CIIU.str[0].map(MACRO_BY_SECTION)
    people = jobs.copy()
    people['RUCEMP'] = people.RUCEMP.map(ruc)
    matched = people.dropna(subset=['RUCEMP']).merge(selected_mapping[['RUCEMP', 'Macroindustria']], on='RUCEMP', validate='many_to_one')
    graduates = matched.groupby('Macroindustria').person.nunique()
    values = sales[sales.CIIU.isin(set(codes)) & sales['Año'].eq(year) & sales.Mes.le(month)].copy()
    values['Macroindustria'] = values.CIIU.str[0].map(MACRO_BY_SECTION)
    grouped = values.groupby('Macroindustria')[SALES].sum(min_count=1)
    result = pd.DataFrame({'Macroindustria': [name for _, name in MACROINDUSTRIES]}).set_index('Macroindustria')
    result['Graduados'] = graduates.reindex(result.index).fillna(0).astype(int)
    result['Personas naturales'] = grouped[[SALES[0], SALES[2]]].sum(axis=1, min_count=2).reindex(result.index)
    result['Sociedades'] = grouped[[SALES[1], SALES[3]]].sum(axis=1, min_count=2).reindex(result.index)
    result['Ventas totales'] = grouped[SALES].sum(axis=1, min_count=1).reindex(result.index)
    return result.reset_index()


def ciiu(value):
    text = re.sub(r'[^A-Z0-9]', '', str(value).strip().upper())
    return text if re.fullmatch(r'[A-Z][0-9]{6}', text) else None


def ruc(value):
    text = str(value).strip()
    return text.zfill(13) if re.fullmatch(r'[0-9]{1,13}', text) else None


def read_sources(mapping_source, sales_source):
    mapping = pd.read_csv(mapping_source, sep='\t', dtype=str, encoding='utf-8-sig',
                          usecols=['RUCEMP', 'NOMEMP', 'CIUU'])
    mapping['RUCEMP'] = mapping.RUCEMP.map(ruc)
    mapping['CIIU'] = mapping.CIUU.map(ciiu)
    mapping = mapping.dropna(subset=['RUCEMP', 'CIIU'])
    # Un RUC con códigos contradictorios requiere validación antes del cruce.
    counts = mapping.groupby('RUCEMP').CIIU.nunique()
    conflicts = int(counts.gt(1).sum())
    mapping = mapping[mapping.RUCEMP.isin(counts[counts.eq(1)].index)].drop_duplicates('RUCEMP')
    sales = pd.read_excel(sales_source, engine='openpyxl')
    if len(sales.columns) != 7:
        raise ValueError('El Excel debe tener actividad, año, mes y las cuatro columnas de ventas 411/413.')
    sales.columns = ['CIIU', 'Año', 'Mes', *SALES]
    sales['CIIU'] = sales.CIIU.map(ciiu)
    for column in ['Año', 'Mes', *SALES]:
        sales[column] = pd.to_numeric(sales[column], errors='coerce')
    sales = sales.dropna(subset=['CIIU', 'Año', 'Mes'])
    sales = sales[sales.Mes.between(1, 12)]
    sales[['Año', 'Mes']] = sales[['Año', 'Mes']].astype(int)
    if sales.duplicated(['CIIU', 'Año', 'Mes']).any():
        raise ValueError('Hay filas repetidas por CIIU, año y mes en el Excel SRI; revisa la fuente para evitar doble conteo.')
    return mapping, sales, conflicts


def match_employers(jobs, mapping):
    jobs = jobs.copy()
    jobs['RUCEMP'] = jobs.RUCEMP.map(ruc)
    jobs = jobs.dropna(subset=['RUCEMP']).drop_duplicates(['person', 'RUCEMP'])
    matched = jobs.merge(mapping[['RUCEMP', 'CIIU']], on='RUCEMP', how='inner', validate='many_to_one')
    result = matched.groupby('CIIU').agg(Graduados=('person', 'nunique'), Empresas=('RUCEMP', 'nunique')).reset_index()
    result['Industria'] = result.CIIU.str[0].map(SECTIONS).fillna('Sin descripción')
    return result.sort_values('Graduados', ascending=False), matched.person.nunique(), jobs.person.nunique()


def monthly_sales(sales, codes):
    # Cada CIIU entra una sola vez, independientemente de graduados o empleadores.
    selected = sales[sales.CIIU.isin(set(codes))]
    result = selected.groupby(['Año', 'Mes'])[SALES].sum(min_count=1).reset_index()
    result['Personas naturales'] = result[[SALES[0], SALES[2]]].sum(axis=1, min_count=2)
    result['Sociedades'] = result[[SALES[1], SALES[3]]].sum(axis=1, min_count=2)
    result['Periodo'] = pd.to_datetime(dict(year=result.Año, month=result.Mes, day=1))
    return result


def growth_summary(sales, codes, year, month):
    data = sales[sales.CIIU.isin(set(codes)) & sales.Mes.le(month)]
    current = data[data['Año'].eq(year)]
    total = current[SALES].sum(min_count=1).sum(min_count=1)
    comparisons = []
    for code in set(codes):
        now = current[current.CIIU.eq(code)].set_index('Mes')[SALES].sort_index()
        before = data[data.CIIU.eq(code) & data['Año'].eq(year-1)].set_index('Mes')[SALES].sort_index()
        expected = list(range(1, month+1))
        if now.index.tolist() != expected or before.index.tolist() != expected:
            continue
        # Comparar las mismas casillas informadas; vacío no equivale a cero.
        if not now.notna().equals(before.notna()) or not now.notna().any().any():
            continue
        now_total = now.sum(min_count=1).sum(min_count=1)
        before_total = before.sum(min_count=1).sum(min_count=1)
        if before_total > 0:
            comparisons.append(dict(CIIU=code, current=now_total, previous=before_total,
                                    growth=100*(now_total/before_total-1)))
    top = max(comparisons, key=lambda row: (row['growth'], row['CIIU'])) if comparisons else None
    growth = float('nan')
    if len(comparisons) == len(set(codes)) and comparisons:
        growth = 100*(sum(row['current'] for row in comparisons)/sum(row['previous'] for row in comparisons)-1)
    return dict(total=total, growth=growth, top=top)


def compact_usd(value):
    if pd.isna(value):
        return 'Sin datos'
    for scale, suffix in [(1e9, 'mil millones'), (1e6, 'millones'), (1e3, 'mil')]:
        if abs(value) >= scale:
            return f"USD {value/scale:.1f}".replace('.', ',') + ' ' + suffix
    return f'USD {value:.2f}'.replace('.', ',')

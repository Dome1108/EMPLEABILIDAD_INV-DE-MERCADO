"""Empresas del ranking y empleados reportados, con cruce sectorial por CIIU."""
import re
import unicodedata
import numpy as np
import pandas as pd

from industry import ciiu, ruc, MACRO_BY_SECTION, SECTIONS

MATCH_VERSION = 3


def graduate_distribution(jobs, mapping, matches=None):
    """Personas únicas por empleador/sector; participación sobre la población SIM completa."""
    data=jobs.copy()
    data['RUCEMP']=data.RUCEMP.map(ruc)
    data=data.dropna(subset=['RUCEMP','person']).drop_duplicates(['person','RUCEMP'])
    total=int(data.person.nunique())
    if data.empty:
        columns=['SIM_RUC','SIM_company','CIIU','macroindustry','sim_graduates','share']
        return pd.DataFrame(columns=columns),pd.DataFrame(),pd.DataFrame(),0
    def name(values):
        names=sorted(set(values.dropna().astype(str).str.strip())-{''})
        return names[0] if names else 'Empresa sin nombre'
    companies=data.groupby('RUCEMP').agg(SIM_company=('NOMEMP',name),sim_graduates=('person','nunique')).reset_index().rename(columns={'RUCEMP':'SIM_RUC'})
    catalog=mapping[['RUCEMP','CIIU']].copy()
    catalog['RUCEMP']=catalog.RUCEMP.map(ruc)
    catalog=catalog.dropna(subset=['RUCEMP','CIIU']).drop_duplicates()
    ambiguous=catalog.groupby('RUCEMP').CIIU.nunique().gt(1)
    catalog=catalog[~catalog.RUCEMP.isin(ambiguous[ambiguous].index)]
    companies=companies.merge(catalog.rename(columns={'RUCEMP':'SIM_RUC'}),on='SIM_RUC',how='left',validate='one_to_one')
    if matches is not None and len(matches):
        fallback=matches.set_index('SIM_RUC').CIIU
        companies['CIIU']=companies.CIIU.fillna(companies.SIM_RUC.map(fallback))
    companies['CIIU']=companies.CIIU.fillna('Sin CIIU')
    companies['macroindustry']=companies.CIIU.where(companies.CIIU.ne('Sin CIIU')).str[0].map(MACRO_BY_SECTION).fillna('Sin actividad identificada')
    companies['share']=100*companies.sim_graduates/total
    linked=data[['person','RUCEMP']].merge(companies[['SIM_RUC','CIIU','macroindustry']],left_on='RUCEMP',right_on='SIM_RUC',validate='many_to_one')
    def summarize(column):
        result=linked.groupby(column).agg(sim_graduates=('person','nunique'),companies=('SIM_RUC','nunique')).reset_index()
        result['share']=100*result.sim_graduates/total
        return result
    by_code=summarize('CIIU')
    by_code['label']=by_code.CIIU.map(lambda code: code+' · '+SECTIONS.get(code[0],'Sin actividad identificada') if code!='Sin CIIU' else 'Sin actividad identificada')
    by_macro=summarize('macroindustry').rename(columns={'macroindustry':'label'})
    return companies,by_code,by_macro,total


def company_name_key(value):
    if pd.isna(value):
        return ''
    name=unicodedata.normalize('NFKD',str(value).upper())
    name=''.join(ch for ch in name if not unicodedata.combining(ch))
    name=name.replace('.','')
    name=re.sub(r'[^A-Z0-9]+',' ',name).strip()
    for pattern,replacement in [
        (r'\bSOCIEDAD POR ACCIONES SIMPLIFICADA$','SAS'),
        (r'\bSOCIEDAD ANONIMA$','SA'),
        (r'\bCOMPANIA ANONIMA$','CA'),
        (r'\b(?:COMPANIA|CIA) (?:LIMITADA|LTDA)$','CIA LTDA'),
        (r'\bS A S$','SAS'),(r'\bS A$','SA'),(r'\bC A$','CA'),
    ]:
        name=re.sub(pattern,replacement,name)
    return name


def match_sim_companies(jobs, ranking, year=2025):
    """Coincidencias exactas tras normalización; ambiguas y colisiones no asignan empleados."""
    if 'NOMEMP' not in jobs:
        raise ValueError('La consulta SIM debe incluir NOMEMP. Actualiza la consulta de empleadores.')
    ranking=ranking[ranking.year.eq(year)].copy()
    ranking['name_key']=ranking.company.map(company_name_key)
    lookup=ranking[ranking.name_key.ne('')].groupby('name_key').company_id.agg(lambda s:set(s))
    jobs=jobs.copy()
    jobs['RUCEMP']=jobs.RUCEMP.map(ruc)
    jobs['name_key']=jobs.NOMEMP.map(company_name_key)
    invalid=int(jobs.RUCEMP.isna().sum())
    jobs=jobs.dropna(subset=['RUCEMP'])
    rows=[]
    for employer,group in jobs.groupby('RUCEMP'):
        keys=sorted(set(group.name_key)-{''})
        candidates=set().union(*(lookup.get(key,set()) for key in keys))
        names=sorted(set(group.NOMEMP.dropna().astype(str).str.strip())-{''})
        status=('Coincidencia exacta normalizada' if len(candidates)==1 else
                'Ambigua: varios expedientes' if len(candidates)>1 else
                'Sin nombre SIM' if not keys else 'Sin coincidencia por nombre')
        rows.append(dict(SIM_RUC=employer,SIM_company=' | '.join(names),
                         sim_graduates=group.person.nunique(),company_id=next(iter(candidates)) if len(candidates)==1 else None,
                         match_status=status))
    result=pd.DataFrame(rows,columns=['SIM_RUC','SIM_company','sim_graduates','company_id','match_status'])
    # Un mismo nombre del ranking no identifica automáticamente dos RUC distintos.
    collision=result.company_id.notna() & result.company_id.duplicated(keep=False)
    result.loc[collision,'match_status']='Ambigua: varios RUC SIM para un expediente'
    result.loc[collision,'company_id']=None
    result=result.merge(ranking.drop(columns='name_key'),on='company_id',how='left',validate='many_to_one')
    quality={'sim_companies':len(result),'matched':int(result.company_id.notna().sum()),
             'ambiguous':int(result.match_status.str.startswith('Ambigua').sum()),'invalid_ruc_rows':invalid}
    return result,quality


def prepare_ranking(raw):
    required=['Año','Expediente','Nombre','Actividad económica','Cant. Empleados']
    missing=set(required)-set(raw.columns)
    if missing:
        raise ValueError('Faltan columnas en ranking: '+', '.join(sorted(missing)))
    data=raw[required].copy()
    data=data.rename(columns={'Año':'year','Expediente':'company_id','Nombre':'company',
                             'Actividad económica':'activity','Cant. Empleados':'employees'})
    def identity(value):
        if pd.isna(value):
            return None
        text=str(value).strip()
        # Excel puede representar expedientes enteros como números decimales.
        if re.fullmatch(r'\d+\.0+',text):
            text=text.split('.')[0]
        return str(int(text)) if re.fullmatch(r'\d+',text) else None
    data['company_id']=data.company_id.map(identity)
    data['year']=pd.to_numeric(data.year,errors='coerce')
    valid_year=data.year.between(1900,2100)&data.year.mod(1).eq(0)
    data['CIIU']=data.activity.astype('string').str.upper().str.strip().str.extract(r'^([A-U]\d{4}\.?\d{2})\b',expand=False).map(ciiu)
    values=pd.to_numeric(data.employees,errors='coerce')
    valid_employees=np.isfinite(values)&values.ge(0)&values.mod(1).eq(0)
    quality={'source_rows':len(data),'invalid_identity':int(data.company_id.isna().sum()),
             'invalid_ciiu':int(data.CIIU.isna().sum()),'invalid_year':int((~valid_year).sum()),
             'missing_employees':int((~valid_employees).sum())}
    data['employees']=values.where(valid_employees)
    data=data[data.company_id.notna()&data.CIIU.notna()&valid_year].copy()
    data['year']=data.year.astype(int)
    # Un expediente/año es una empresa. No elegir arbitrariamente entre valores distintos.
    counts=data.groupby(['year','company_id']).agg(codes=('CIIU','nunique'),
        headcounts=('employees',lambda s:s.nunique(dropna=False)))
    bad=counts.index[counts.codes.gt(1)|counts.headcounts.gt(1)]
    quality['conflicting_companies']=len(bad)
    data=data[~pd.MultiIndex.from_frame(data[['year','company_id']]).isin(bad)]
    before=len(data)
    data=data.drop_duplicates(['year','company_id'])
    quality['duplicate_rows_removed']=before-len(data)
    data['company']=data.company.fillna('Sin nombre').astype(str).str.strip()
    data['macroindustry']=data.CIIU.str[0].map(MACRO_BY_SECTION)
    return data.reset_index(drop=True),quality


def read_ranking(path):
    # La primera fila contiene la fecha de corte; la segunda, los encabezados.
    columns=['Año','Expediente','Nombre','Actividad económica','Cant. Empleados']
    raw=pd.read_excel(path,sheet_name='Ranking2025',header=1,usecols=columns,
                      dtype={'Expediente':str},engine='openpyxl')
    return prepare_ranking(raw)


def ranking_summary(ranking, codes, year=2025):
    selected=ranking[ranking.CIIU.isin(set(codes))&ranking.year.eq(year)].copy()
    def aggregate(column):
        return selected.groupby(column).agg(companies=('company_id','nunique'),
            companies_with_employees=('employees','count'),
            employees=('employees',lambda s:s.sum(min_count=1))).reset_index()
    by_code=aggregate('CIIU')
    by_code['activity']=by_code.CIIU.map(selected.groupby('CIIU').activity.first())
    return selected,by_code,aggregate('macroindustry')

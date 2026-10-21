"""Indicadores territoriales por domicilio Atlas, sin modificar el nacional."""
import pandas as pd
from analytics import normalize_id, institution_key


def locations(atlas):
    data = atlas.copy()
    data['person'] = data.cedula.map(normalize_id)
    for column in ('provincia', 'canton', 'parroquia'):
        data[column] = data[column].map(lambda x: institution_key(x) if pd.notna(x) else '')
    data = data.dropna(subset=['person']).drop_duplicates(['person', 'provincia', 'canton', 'parroquia'])
    conflicting = data.loc[data.person.duplicated(keep=False), 'person'].nunique()
    data = data[~data.person.duplicated(keep=False)]
    return data[['person', 'provincia', 'canton', 'parroquia']], conflicting


def territorial_summary(people, province, canton='', parish=''):
    subset = people[people.provincia.eq(province)]
    if canton:
        subset = subset[subset.canton.eq(canton)]
    if parish:
        subset = subset[subset.parroquia.eq(parish)]
    salaries = subset.loc[subset.dependent, 'salary'].dropna()
    n = len(subset)
    employed = int(subset.visible.sum())
    dependent = int(subset.dependent.sum())
    return dict(graduates=n, employed=employed, rate=100 * employed / n if n else float('nan'),
                dependent=dependent, independent=employed-dependent, unknown=n-employed,
                p25=salaries.quantile(.25), p75=salaries.quantile(.75), salary_n=len(salaries))

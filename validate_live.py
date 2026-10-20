"""Verifica fuentes y cálculos reales sin imprimir identificaciones personales."""
import json
import tomllib
from pathlib import Path

from analytics import calculate
from data_access import careers, load


if __name__ == '__main__':
    config = tomllib.loads(Path('.streamlit/secrets.toml').read_text(encoding='utf-8'))['sql']
    options = careers(config)
    print('Carreras disponibles:', len(options), flush=True)
    selected = [c for c in options if c.upper() in ('ECONOMÍA', 'ECONOMIA')]
    if not selected:
        raise RuntimeError('No se encontró Economía en CARRERA_HOMOLOGADA.')
    result = calculate(*load(config, selected, progress=lambda message: print(message,flush=True)))
    summary, _, _, quality = result
    assert (summary.dependent + summary.independent + summary.unknown == summary.graduates).all()
    assert (summary.employed <= summary.graduates).all()
    assert (summary.p25.dropna() <= summary.p75.dropna()).all()
    assert (summary.salary_n > 0).all()
    print(summary.to_json(orient='records', date_format='iso', indent=2), flush=True)
    print('Calidad y tarjeta academica:', json.dumps({k:v for k,v in quality.items() if k != 'private_institutions'}), flush=True)
    private = [row for row in quality['private_institutions'] if row['year']==2026]
    print('IES Privadas Sierra:', len(private), '; con graduados:', sum(row['professionals']>0 for row in private), flush=True)

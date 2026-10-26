"""Diagnóstico mensual: cobertura, transformaciones, ADF, KPSS y ACF."""
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import acf, adfuller, kpss

from industry import SALES

MIN_OBSERVATIONS = 20
SERIES_API_VERSION = 2
MEASURES = {
    'Ventas totales': SALES,
    'Personas naturales': [SALES[0], SALES[2]],
    'Sociedades': [SALES[1], SALES[3]],
}


def complete_monthly(sales, codes):
    """Suma solo meses con todas las casillas de TODOS los CIIU seleccionados."""
    codes = sorted(set(codes))
    selected = sales[sales.CIIU.isin(codes)].copy()
    if selected.empty:
        return pd.DataFrame(columns=list(MEASURES)), pd.DataFrame()
    if selected.duplicated(['CIIU', 'Año', 'Mes']).any():
        raise ValueError('Hay registros duplicados por CIIU y mes.')
    selected['Periodo'] = pd.to_datetime(dict(year=selected['Año'], month=selected.Mes, day=1))
    dates = pd.date_range(selected.Periodo.min(), selected.Periodo.max(), freq='MS')
    grid = pd.MultiIndex.from_product([dates, codes], names=['Periodo', 'CIIU'])
    values = selected.set_index(['Periodo', 'CIIU'])[SALES].reindex(grid).astype(float)
    values = values.where(np.isfinite(values))
    result, coverage = pd.DataFrame(index=dates), pd.DataFrame(index=dates)
    result.index.name = coverage.index.name = 'Periodo'
    for measure, columns in MEASURES.items():
        required = len(codes)*len(columns)
        count = values[columns].notna().sum(axis=1).groupby(level='Periodo').sum()
        total = values[columns].sum(axis=1, min_count=len(columns)).groupby(level='Periodo').sum(min_count=1)
        result[measure] = total.where(count.eq(required))
        coverage[measure] = count/required
    return result, coverage


def comparable_panel(sales, codes, measure):
    """Panel fijo de casillas CIIU/campo informadas en todos los meses; no imputa vacíos."""
    codes=sorted(set(codes))
    selected=sales[sales.CIIU.isin(codes)].copy()
    if selected.empty:
        return pd.Series(dtype=float), pd.DataFrame()
    if selected.duplicated(['CIIU','Año','Mes']).any():
        raise ValueError('Hay registros duplicados por CIIU y mes.')
    selected['Periodo']=pd.to_datetime(dict(year=selected['Año'],month=selected.Mes,day=1))
    dates=pd.date_range(selected.Periodo.min(),selected.Periodo.max(),freq='MS')
    grid=pd.MultiIndex.from_product([dates,codes],names=['Periodo','CIIU'])
    values=selected.set_index(['Periodo','CIIU'])[MEASURES[measure]].reindex(grid).astype(float)
    values=values.where(np.isfinite(values))
    wide=values.unstack('CIIU')
    keep=wide.notna().all(axis=0)
    columns=wide.loc[:,keep]
    result=columns.sum(axis=1,min_count=len(columns.columns)) if len(columns.columns) else pd.Series(np.nan,index=dates)
    result.name='Ventas informadas · panel fijo'
    result.index.name='Periodo'
    detail=pd.DataFrame([dict(CIIU=code,Campo=field,**{'Meses informados':int(wide[(field,code)].notna().sum()),
        'Meses del período':len(dates),'Incluida':bool(keep[(field,code)])}) for field,code in wide.columns])
    return result,detail


def longest_monthly_block(series):
    """Tramo continuo más largo; ante empate conserva el más reciente."""
    series = series.sort_index().astype(float)
    if series.index.has_duplicates:
        raise ValueError('El índice mensual contiene duplicados.')
    if series.empty:
        return series
    series = series.reindex(pd.date_range(series.index.min(), series.index.max(), freq='MS'))
    series = series.where(np.isfinite(series))
    valid = series.notna()
    groups = valid.ne(valid.shift()).cumsum()
    blocks = [block for _, block in series.groupby(groups) if block.notna().all()]
    return max(blocks, key=lambda block: (len(block), block.index[-1])).copy() if blocks else series.iloc[:0]


def _values(series):
    values = np.asarray(series, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError('Se necesita un tramo sin meses faltantes ni valores infinitos.')
    if isinstance(series.index, pd.DatetimeIndex) and len(series):
        expected = pd.date_range(series.index[0], series.index[-1], freq='MS')
        if not series.index.equals(expected):
            raise ValueError('Se necesita un índice mensual continuo; no se comprimen meses faltantes.')
    return values


def transform(series, kind='Niveles', d=0, D=0, s=12, detrend=False):
    if d not in (0, 1, 2) or D not in (0, 1) or s < 2:
        raise ValueError('Usa d entre 0 y 2, D entre 0 y 1 y s >= 2.')
    if detrend and (d or D):
        raise ValueError('La eliminación de tendencia determinística es una alternativa a diferenciar.')
    values = _values(series)
    if not len(values):
        raise ValueError('No hay observaciones para transformar.')
    lam = None
    if kind in ('Logaritmo', 'Box-Cox'):
        if (values <= 0).any():
            raise ValueError('Logaritmo y Box-Cox requieren todos los valores estrictamente positivos; no se agrega una constante.')
        if kind == 'Logaritmo':
            values = np.log(values)
        else:
            if np.ptp(values) == 0:
                raise ValueError('Box-Cox no puede estimar lambda con una serie constante.')
            values, lam = stats.boxcox(values)
            lam = float(lam)
    elif kind != 'Niveles':
        raise ValueError('Transformación desconocida.')
    if not np.isfinite(values).all():
        raise ValueError('La transformación produjo valores no finitos.')
    base = pd.Series(values, index=series.index, name=kind)
    trend_slope = None
    if detrend:
        if len(base) < 3:
            raise ValueError('Se necesitan al menos tres observaciones para eliminar una tendencia.')
        trend_slope, intercept = np.polyfit(np.arange(len(base)), base.to_numpy(), 1)
        base = base - (intercept + trend_slope*np.arange(len(base)))
    result = base.copy()
    for _ in range(D):
        result = result.diff(s)
    for _ in range(d):
        result = result.diff()
    # Quitar solo las pérdidas iniciales conocidas, nunca comprimir huecos interiores.
    result = result.iloc[D*s+d:]
    return result, base, dict(kind=kind, d=d, D=D, s=s, boxcox_lambda=lam,
                             detrend=detrend, trend_slope=trend_slope)


def stationarity(series, regression='c'):
    report = dict(n=len(series), regression=regression, adf_p=np.nan, kpss_p=np.nan,
                  adf_stat=np.nan, kpss_stat=np.nan, adf_lags=None, kpss_lags=None,
                  kpss_bound='=', status='unavailable', warnings=[])
    try:
        values = _values(series)
    except ValueError as exc:
        report['warnings'].append(str(exc))
        return report
    if len(values) < MIN_OBSERVATIONS:
        report['warnings'].append(f'Se requieren al menos {MIN_OBSERVATIONS} meses para este diagnóstico; quedan {len(values)}.')
        return report
    spread = float(np.std(values))
    if spread <= max(1, float(np.max(np.abs(values))))*1e-12:
        report['warnings'].append('Serie constante o casi constante: ADF y KPSS no son interpretables.')
        return report
    # Estas pruebas son invariantes a escala; normalizar mejora estabilidad numérica.
    values = (values-values.mean())/spread
    for name in ('adf', 'kpss'):
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                if name == 'adf':
                    maxlag = max(0, min(12, len(values)//5, len(values)//2-(2 if regression == 'ct' else 1)-1))
                    stat, p, lags, *_ = adfuller(values, regression=regression, maxlag=maxlag, autolag='AIC')
                else:
                    stat, p, lags, _ = kpss(values, regression=regression, nlags='auto')
            report[f'{name}_stat'], report[f'{name}_p'], report[f'{name}_lags'] = float(stat), float(p), int(lags)
            for warning in caught:
                message = str(warning.message)
                if name == 'kpss' and 'greater than' in message:
                    report['kpss_bound'] = '>'
                elif name == 'kpss' and 'smaller than' in message:
                    report['kpss_bound'] = '<'
                else:
                    report['warnings'].append(f'{name.upper()}: {message}')
        except (ValueError, OverflowError, np.linalg.LinAlgError, ZeroDivisionError) as exc:
            report['warnings'].append(f'{name.upper()} no disponible: {exc}')
    if np.isfinite(report['adf_p']) and np.isfinite(report['kpss_p']):
        adf_ok, kpss_ok = report['adf_p'] < .05, report['kpss_p'] > .05
        report['status'] = ('stationary' if adf_ok and kpss_ok else
                            'nonstationary' if not adf_ok and not kpss_ok else 'inconclusive')
    return report


def autocorrelation(series, max_lags=24):
    try:
        values = _values(series)
    except ValueError:
        return pd.DataFrame()
    if len(values) < 3 or np.std(values) <= max(1,float(np.max(np.abs(values))))*1e-12:
        return pd.DataFrame()
    correlations, ci = acf(values, nlags=min(max_lags,len(values)-1), alpha=.05, fft=False, missing='raise')
    return pd.DataFrame(dict(lag=np.arange(len(correlations)), acf=correlations,
                             lower=ci[:,0]-correlations, upper=ci[:,1]-correlations))


def differencing_flags(original, transformed, kind, d, D, s=12):
    flags = []
    if not (d or D):
        return flags
    correlation = autocorrelation(transformed)
    if len(correlation)>1 and correlation.iloc[1]['acf'] <= -.45:
        flags.append('ACF(1) muy negativa: posible sobrediferenciación; también puede reflejar una estructura MA.')
    previous, _, _ = transform(original, kind, d=max(d-1,0), D=D if d else max(D-1,0), s=s)
    aligned = pd.concat([previous.rename('before'),transformed.rename('after')],axis=1).dropna()
    if len(aligned)>2 and aligned.before.var()>0 and aligned.after.var()>1.25*aligned.before.var():
        flags.append('La varianza aumentó más de 25 % al añadir la última diferencia, en fechas comunes y la misma escala. Revisa si es necesaria.')
    return flags

"""Formatos de número en español (copiados de analytics/empleabilidad.py del proyecto Tendencias)."""
import numpy as np
import pandas as pd

MESES = ("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
         "Octubre", "Noviembre", "Diciembre")


def entero(value):
    if value is None or pd.isna(value):
        return "N/D"
    return f"{int(round(float(value))):,}".replace(",", ".")


def decimal(value, digits=1):
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def dinero(value):
    return "N/D" if value is None or pd.isna(value) else "$" + entero(value)


def porcentaje(value, digits=1, signo=False):
    if value is None or pd.isna(value):
        return "N/D"
    texto = decimal(value, digits) + " %"
    return ("+" if signo and value >= 0 else "") + texto


def variacion(inicio, fin):
    """Cambio porcentual sin inventar un porcentaje con base cero."""
    try:
        inicio, fin = float(inicio), float(fin)
    except (TypeError, ValueError):
        return None
    if not inicio or not np.isfinite(inicio) or not np.isfinite(fin):
        return None
    return (fin - inicio) / abs(inicio) * 100


def variaciones(summary):
    """Texto de variación de cada corte frente al anterior, en puntos porcentuales."""
    textos = []
    for i, rate in enumerate(summary["rate"]):
        previo = summary["rate"].iloc[i - 1] if i else np.nan
        delta = rate - previo
        if not i:
            textos.append("Primer corte")
        elif pd.isna(delta):
            textos.append("N/D")
        else:
            textos.append(f"{'+' if delta >= 0 else ''}{decimal(delta)} pp")
    return textos


def lista(nombres):
    nombres = [n for n in nombres if n]
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


_CONECTORES = {"de", "del", "la", "las", "el", "los", "y", "e", "en", "para", "por", "a", "con", "o", "u"}


def titulo(texto):
    """'INGENIERIA EN SOFTWARE' → 'Ingenieria en Software' (conectores en minúscula)."""
    palabras = str(texto).strip().lower().split()
    return " ".join(p if i and p in _CONECTORES else p.capitalize() for i, p in enumerate(palabras))


def mayuscula_inicial(texto):
    """Primera letra en mayúscula sin cambiar el resto (str.capitalize baja «Google Trends»)."""
    return texto[:1].upper() + texto[1:]


def mes_anio(fecha):
    return f"{MESES[fecha.month - 1]} {fecha.year}"


def normalizar_carrera(valor):
    """Igual que _norm de viabilidad (mayúsculas, sin tildes ni espacios dobles)."""
    import unicodedata

    texto = "".join(c for c in unicodedata.normalize("NFKD", str(valor)) if not unicodedata.combining(c))
    return " ".join(texto.strip().upper().split())

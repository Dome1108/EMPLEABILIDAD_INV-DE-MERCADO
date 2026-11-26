"""Modelo exploratorio de referencia competitiva de precios.

Integración en una app Streamlit existente:
    from modelo_referencia_precios import render_modelo_precios
    render_modelo_precios(df_precios)  # DataFrame histórico ya cargado

Requiere: streamlit, pandas, numpy, plotly.
Advertencia: las curvas NO son el Van Westendorp tradicional y sus
intersecciones NO representan disposición a pagar ni precio óptimo.
"""
from __future__ import annotations

import unicodedata
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _norm(value: object) -> str:
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(value.strip().upper().split())


def _price_column(level: str) -> str:
    normalized = _norm(level)
    if "3ER" in normalized or "TERCER" in normalized:
        return "ARANCEL"
    if "4TO" in normalized or "CUARTO" in normalized or "TECNO" in normalized:
        return "TOTAL"
    raise ValueError(f"Nivel académico sin regla de precio: {level}")


def _crossover(x: np.ndarray, y1: np.ndarray, y2: np.ndarray):
    """Primer cruce de dos curvas interpoladas; solo dato descriptivo."""
    d = y1 - y2
    for i in range(len(x) - 1):
        a, b = d[i], d[i + 1]
        if a == 0 and b == 0:
            continue
        if a == 0:
            return float(x[i]), float(y1[i])
        if a * b <= 0:
            t = a / (a - b) if a != b else 0.0
            return float(x[i] + t * (x[i+1] - x[i])), float(y1[i] + t * (y1[i+1] - y1[i]))
    return None


def calcular_modelo(df: pd.DataFrame, nivel: str, carrera: str, periodo):
    """Retorna datos descriptivos y las 4 curvas, sin modificar el DataFrame original."""
    required = {"NIVEL ACADEMICO", "CARRERA UDLA", "Semestre Pos", "SIGLA", "ARANCEL", "TOTAL"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Columnas faltantes: {', '.join(sorted(missing))}")

    data = df.loc[
        df["NIVEL ACADEMICO"].map(_norm).eq(_norm(nivel))
        & df["CARRERA UDLA"].map(_norm).eq(_norm(carrera))
        & df["Semestre Pos"].astype(str).str.strip().eq(str(periodo).strip())
    ].copy()
    col = _price_column(nivel)
    data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.loc[data[col].notna() & (data[col] > 0)].copy()
    data["_institucion"] = data["SIGLA"].map(_norm)
    data = data.loc[data["_institucion"].ne("") & data["_institucion"].ne("NAN")]

    # Una institución = un peso. Si hay múltiples ofertas comparables por
    # universidad en el mismo período, usamos su mediana (regla revisable).
    resumen = data.groupby("_institucion", as_index=False)[col].median()
    precio_udla = resumen.loc[resumen["_institucion"].eq("UDLA"), col]
    precio_udla = float(precio_udla.iloc[0]) if len(precio_udla) else None
    competencia = resumen.loc[resumen["_institucion"].ne("UDLA")].copy()
    vals = competencia[col].to_numpy(dtype=float)
    n = len(vals)
    result = {"n": n, "competidores": competencia, "precio_udla": precio_udla,
              "columna": col, "periodo": periodo, "nivel": nivel, "carrera": carrera,
              "curvas": None, "referencias": None, "cruces": {}}
    if n == 0:
        return result

    q0, q25, q50, q75, q100 = np.percentile(vals, [0,25,50,75,100])
    result["referencias"] = {"min":float(q0), "p25":float(q25),
                              "p50":float(q50), "p75":float(q75),"max":float(q100)}
    if n < 5 or len(np.unique(vals)) < 3:
        return result

    # Distancias estimadas desde los precios observados, no encuestas.
    d_inf_ext = q50 - q0
    d_inf_int = q50 - q25
    d_sup_int = q75 - q50
    d_sup_ext = q100 - q50
    umbrales = {
        "Muy barato": np.maximum(0, vals - d_inf_ext),
        "Barato": np.maximum(0, vals - d_inf_int),
        "Caro": vals + d_sup_int,
        "Muy caro": vals + d_sup_ext,
    }
    high = max(float(max(a.max() for a in umbrales.values()) * 1.05), 1)
    x = np.linspace(0, high, 700)
    curves = {
        "Muy barato": np.mean(umbrales["Muy barato"][None, :] >= x[:, None], axis=1) * 100,
        "Barato": np.mean(umbrales["Barato"][None, :] >= x[:, None], axis=1) * 100,
        "Caro": np.mean(umbrales["Caro"][None, :] <= x[:, None], axis=1) * 100,
        "Muy caro": np.mean(umbrales["Muy caro"][None, :] <= x[:, None], axis=1) * 100,
    }
    result["curvas"] = {"x": x, "series": curves}
    # Intermedios para mostrar el cálculo paso a paso (no cambian el modelo).
    result["distancias"] = {"Muy barato": float(d_inf_ext), "Barato": float(d_inf_int),
                            "Caro": float(d_sup_int), "Muy caro": float(d_sup_ext)}
    result["umbrales"] = umbrales
    parejas = {
        "Cruce inferior": ("Muy barato", "Caro"),
        "Cruce superior": ("Barato", "Muy caro"),
        "Cruce externo": ("Muy barato", "Muy caro"),
        "Cruce interno": ("Barato", "Caro"),
    }
    result["cruces"] = {nombre: _crossover(x, curves[a], curves[b])
                         for nombre,(a,b) in parejas.items()}
    return result


def render_modelo_precios(df: pd.DataFrame):
    """Widget para incrustar dentro de una pantalla existente de Streamlit."""
    st.subheader("Referencia competitiva de precios académicos")
    st.caption("Gráfico exploratorio inspirado en Van Westendorp. No mide disposición a pagar.")
    niveles = sorted(v for v in df["NIVEL ACADEMICO"].dropna().unique()
                    if any(t in _norm(v) for t in ("3ER", "TERCER", "4TO", "CUARTO", "TECNO")))
    if not niveles:
        st.warning("No se encontraron niveles académicos reconocidos.")
        return
    nivel = st.selectbox("Nivel académico", niveles, key="comp_nivel")
    subset = df.loc[df["NIVEL ACADEMICO"].map(_norm).eq(_norm(nivel))]
    carreras = sorted(str(v) for v in subset["CARRERA UDLA"].dropna().unique()
                     if _norm(v) not in ("SIN REGISTRO", ""))
    if not carreras:
        st.warning("No hay carreras homologadas para este nivel.")
        return
    carrera = st.selectbox("Carrera", carreras, key="comp_carrera")
    subset = subset.loc[subset["CARRERA UDLA"].map(_norm).eq(_norm(carrera))]
    periodos = sorted(subset["Semestre Pos"].dropna().unique().tolist(),
                      key=lambda a: (pd.to_numeric(a, errors="coerce") if pd.notna(pd.to_numeric(a, errors="coerce")) else -1),
                      reverse=True)
    if not periodos:
        st.warning("No hay períodos registrados para esta carrera.")
        return
    periodo = st.selectbox("Período", periodos, index=0, key="comp_periodo")
    r = calcular_modelo(df, nivel, carrera, periodo)
    st.caption(f"Variable comparada: {r['columna']} · Competidores: {r['n']} · Período: {periodo}")
    if r["n"] == 0:
        st.warning("No hay competidores con precios válidos en este período.")
        return
    ref = r["referencias"]
    if r["n"] < 5 or r["curvas"] is None:
        st.info("Muestra pequeña o sin variación suficiente. Se muestran precios observados, sin curvas ni rango recomendado.")
        st.dataframe(r["competidores"].rename(columns={"_institucion": "Universidad", r["columna"]: "Precio"}),hide_index=True)
        return

    fig = crear_figura(r)
    st.plotly_chart(fig,width="stretch")
    a,b=st.columns(2)
    a.metric("Rango inferior (P50)",f"${ref['p50']:,.2f}")
    b.metric("Rango superior (P75)",f"${ref['p75']:,.2f}")
    if r["precio_udla"] is not None:
        p=r["precio_udla"]
        st.info(f"Precio UDLA: ${p:,.2f}, {posicion_udla(r)} del rango competitivo de referencia.")
    if r["n"] < 10:
        st.warning(f"Resultado exploratorio: solo {r['n']} instituciones competidoras.")
    st.caption("Rango P50–P75: referencia medio-alta del mercado. Las intersecciones son simuladas y no determinan un precio óptimo.")


def posicion_udla(r):
    """'dentro', 'debajo' o 'encima' del rango P50–P75; None sin precio UDLA o sin referencias."""
    p, ref = r["precio_udla"], r["referencias"]
    if p is None or ref is None:
        return None
    return "dentro" if ref["p50"] <= p <= ref["p75"] else ("debajo" if p < ref["p50"] else "encima")


def _vertices(x, y):
    """Extremos de la curva y cada punto donde cambia el escalón (una universidad).

    Los tramos planos inicial y final se conservan: antes de la primera universidad
    y después de la última, la curva no inventa porcentajes intermedios.
    """
    cambios = np.flatnonzero(np.diff(y)) + 1
    if not len(cambios):
        return x[[0, -1]], y[[0, -1]]
    idx = np.unique(np.concatenate(([0, cambios[0] - 1], cambios, [len(x) - 1])))
    return x[idx], y[idx]


# Cruces de Van Westendorp: (nombre en el gráfico, curvas que se cruzan).
CRUCES_VW = {
    "PMC": ("PMC · precio marginalmente barato (límite inferior)", ("Muy barato", "Caro")),
    "OPP": ("OPP · cruce Demasiado barato × Demasiado caro", ("Muy barato", "Muy caro")),
    "IPP": ("IPP · cruce Barato × Caro", ("Barato", "Caro")),
    "PME": ("PME · precio marginalmente caro (límite superior)", ("Barato", "Muy caro")),
}


def _vertices_exactos(u, decreciente, xmax):
    """Puntos de la curva en el umbral exacto de cada universidad.

    En cada umbral t se dibuja el valor que queda después de contar esa universidad:
    bajan → % con umbral > t; suben → % con umbral ≤ t. Antes del primer umbral y
    después del último la curva queda plana (100/0 o 0/100).
    """
    ts = np.unique(u)
    if decreciente:
        inicio, fin = 100.0, 0.0
        valores = [float(np.mean(u > t) * 100) for t in ts]
    else:
        inicio, fin = 0.0, 100.0
        valores = [float(np.mean(u <= t) * 100) for t in ts]
    puntos = [(0.0, inicio), (float(ts[0]), inicio)] + list(zip(ts.astype(float), valores)) + [(float(xmax), fin)]
    limpios = [puntos[0]]
    for p in puntos[1:]:
        if p != limpios[-1]:
            limpios.append(p)
    xs, ys = zip(*limpios)
    return np.array(xs), np.array(ys)


def _curvas_dibujadas(r):
    """Curvas tal como se dibujan: vértices exactos por universidad unidos con diagonales.

    Los cruces se buscan sobre estas mismas líneas con una resolución de ~$1.
    """
    xmax = float(r["curvas"]["x"][-1])
    x = np.linspace(0, xmax, max(2000, int(xmax) + 1))
    vertices, suaves = {}, {}
    for name, u in r["umbrales"].items():
        xs, ys = _vertices_exactos(u, name in ("Muy barato", "Barato"), xmax)
        vertices[name] = (xs, ys)
        suaves[name] = np.interp(x, xs, ys)
    return x, vertices, suaves


def cruces_van_westendorp(r):
    """PMC, OPP, IPP y PME sobre las líneas dibujadas; {clave: (precio, %)} o None si no se cruzan."""
    if r.get("curvas") is None:
        return {}
    x, _, suaves = _curvas_dibujadas(r)
    return {key: _crossover(x, suaves[a], suaves[b]) for key, (_, (a, b)) in CRUCES_VW.items()}


def tablas_calculo(r):
    """Tablas del cálculo paso a paso, con los mismos valores que usa el gráfico."""
    ref, col = r["referencias"], r["columna"]
    percentiles = pd.DataFrame({
        "Variable": ["Mínimo", "P25", "P50 (mediana)", "P75", "Máximo"],
        "Valor": [ref["min"], ref["p25"], ref["p50"], ref["p75"], ref["max"]]})
    d = r["distancias"]
    distancias = pd.DataFrame({
        "Distancia": ["Demasiado barato", "Barato", "Caro", "Demasiado caro"],
        "Fórmula": ["P50 − Mínimo", "P50 − P25", "P75 − P50", "Máximo − P50"],
        "Valor": [d["Muy barato"], d["Barato"], d["Caro"], d["Muy caro"]]})
    u = r["umbrales"]
    umbrales = pd.DataFrame({
        "Universidad": r["competidores"]["_institucion"].to_numpy(),
        "Precio": r["competidores"][col].to_numpy(dtype=float),
        "Demasiado barato (precio − D)": u["Muy barato"],
        "Barato (precio − D)": u["Barato"],
        "Caro (precio + D)": u["Caro"],
        "Demasiado caro (precio + D)": u["Muy caro"]}).sort_values("Precio")
    cruces = cruces_van_westendorp(r)
    visibles = {"Muy barato": "Demasiado barato", "Barato": "Barato", "Caro": "Caro", "Muy caro": "Demasiado caro"}
    tabla_cruces = pd.DataFrame([{"Cruce": key, "Curvas": " × ".join(visibles[c] for c in CRUCES_VW[key][1]),
                                  "Precio": p[0] if p else None, "Porcentaje": p[1] if p else None}
                                 for key, p in cruces.items()])
    return percentiles, distancias, umbrales, tabla_cruces


def rango_van_westendorp(r):
    """Rango aceptable PMC–PME; None si falta un cruce o quedan invertidos."""
    cruces = cruces_van_westendorp(r)
    pmc, pme = cruces.get("PMC"), cruces.get("PME")
    if pmc is None or pme is None or pmc[0] > pme[0]:
        return None
    return pmc[0], pme[0]


def posicion_en_rango(precio, rango):
    """'dentro', 'debajo' o 'encima'; None sin precio o sin rango."""
    if precio is None or rango is None:
        return None
    low, high = rango
    return "dentro" if low <= precio <= high else ("debajo" if precio < low else "encima")


def crear_figura(r):
    """Van Westendorp: 4 curvas, rango PMC–PME, cruces y precio UDLA; requiere r['curvas']."""
    fig = go.Figure()
    # Estilo del tablero: (nombre visible, color, trazo). Los cálculos usan los nombres del modelo.
    estilos = {"Muy barato": ("Demasiado barato", "#244a67", "solid"),
               "Barato": ("Barato", "#accbdf", "dash"),
               "Caro": ("Caro", "#4384ae", "solid"),
               "Muy caro": ("Demasiado caro", "#687f94", "dash")}
    x, vertices, suaves = _curvas_dibujadas(r)
    # Rango aceptable: de la X del PMC a la X del PME, con bordes punteados que pasan por ellas.
    rango = rango_van_westendorp(r)
    if rango is not None:
        fig.add_vrect(x0=rango[0],x1=rango[1],fillcolor="rgba(0,114,188,.075)",line_width=0,layer="below")
        for limite in rango:
            fig.add_shape(type="line",x0=limite,x1=limite,y0=0,y1=100,layer="below",
                          line={"color":"#8396a8","width":1.3,"dash":"dash"})
    # Presentación: se unen con diagonales los puntos donde cambia cada escalón (una universidad).
    for name, (xs, ys) in vertices.items():
        label, color, dash = estilos[name]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", name=label,
                                 line={"color":color,"width":2.4,"dash":dash},
                                 marker={"size":6,"symbol":"circle","color":"white","line":{"color":color,"width":1.4}},
                                 hovertemplate="Precio: $%{x:,.0f}<br>Acumulado: %{y:.1f}%<extra>"+label+"</extra>"))
    # Cruces sobre las líneas dibujadas: X sin entrada en la leyenda, nombre en el hover.
    puntos = [(CRUCES_VW[key][0], p) for key, (_, (a, b)) in CRUCES_VW.items()
              if (p := _crossover(x, suaves[a], suaves[b])) is not None]
    if puntos:
        fig.add_trace(go.Scatter(x=[p[0] for _, p in puntos],y=[p[1] for _, p in puntos],mode="markers",
                                 marker={"symbol":"x","size":11,"color":"#334f6a","line":{"width":2}},
                                 name="Cruces",showlegend=False,customdata=[name for name, _ in puntos],
                                 hovertemplate="%{customdata}<br>Precio: $%{x:,.0f}<br>Acumulado: %{y:.1f}%<extra></extra>"))
    if r["precio_udla"] is not None:
        fig.add_shape(type="line",x0=r["precio_udla"],x1=r["precio_udla"],y0=0,y1=105,
                      line={"color":"#c65f6b","width":1.8,"dash":"dot"})
        fig.add_annotation(x=r["precio_udla"],y=103,text=f"<b>UDLA · ${r['precio_udla']:,.0f}</b>",showarrow=False,
                           xanchor="center",yanchor="bottom",font={"color":"#c65f6b","size":12},
                           bgcolor="rgba(255,255,255,.95)",borderpad=3)
    fig.update_layout(height=470,margin={"l":25,"r":20,"t":40,"b":65},paper_bgcolor="white",plot_bgcolor="white",
                      font={"family":"Arial","size":12,"color":"#60758b"},hovermode="closest",
                      legend={"orientation":"h","y":-0.19,"x":0.5,"xanchor":"center","font":{"size":11}},
                      xaxis={"title":f"Precio del programa · {r['columna']} (USD)","tickprefix":"$","tickformat":",.0f",
                             "gridcolor":"#eef1f4","zeroline":False},
                      yaxis={"title":"Porcentaje acumulado","range":[0,112],"tickvals":[0,20,40,60,80,100],
                             "gridcolor":"#e8ecf0","zeroline":False})
    return fig

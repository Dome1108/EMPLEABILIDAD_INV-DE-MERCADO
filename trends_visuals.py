"""Gráficos de Google Trends para «Demanda e interés académico» (Plotly)."""
from datetime import date
from textwrap import wrap

import plotly.graph_objects as go

from palettes import PALETTES, theme_figure
from trends_analysis import TOP_KEYWORDS

REGION_COLORS = {"Ecuador": "#76BDED", "LATAM": "#087BCC", "Todo el mundo": "#9AA6B2"}
FONT = dict(family="Arial", size=12, color="#60758b")


def _layout(fig, height, palette, **extra):
    extra.setdefault("margin", dict(l=10, r=20, t=30, b=40))
    fig.update_layout(height=height, paper_bgcolor="white", plot_bgcolor="white", font=FONT, **extra)
    return theme_figure(fig, palette)


def keywords_figure(keywords, base_mean, palette="Azul"):
    """Promedio de Google Trends por palabra; las 6 que entran al indicador en color principal."""
    blue, light, _ = PALETTES[palette]
    data = keywords.dropna(subset=["promedio"]).sort_values("promedio", ascending=False).reset_index(drop=True)
    labels = ["<br>".join(wrap(str(word), 28)) for word in data["palabra"]]
    colors = [blue if i < TOP_KEYWORDS else light for i in range(len(data))]
    fig = go.Figure(go.Bar(
        x=data["promedio"], y=labels, orientation="h", marker_color=colors,
        text=[f"{v:.1f}".replace(".", ",") for v in data["promedio"]], textposition="outside", cliponaxis=False,
        customdata=data[["palabra"]].fillna("").to_numpy(),
        hovertemplate="%{customdata[0]}<br>Promedio Google Trends: %{x:.2f}<extra></extra>"))
    if base_mean is not None:
        fig.add_vline(x=base_mean, line=dict(color="#c65f6b", width=1.6, dash="dot"))
        fig.add_annotation(x=base_mean, y=1.02, yref="paper", showarrow=False, yanchor="bottom",
                           text=f"Base carrera de referencia · {base_mean:.1f}".replace(".", ","),
                           font=dict(color="#c65f6b", size=11))
    top = max([*data["promedio"].tolist(), base_mean or 0, 1])
    return _layout(fig, max(300, 34 * len(data) + 80), palette,
                   xaxis=dict(title="Promedio del índice de Google Trends (0–100)", range=[0, top * 1.18],
                              gridcolor="#eef1f4", zeroline=False),
                   yaxis=dict(autorange="reversed", automargin=True), showlegend=False)


def _transparent(color, alpha):
    """``#RRGGBB`` -> ``rgba(...)`` para el relleno de las áreas."""
    red, green, blue = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({red},{green},{blue},{alpha})"


def regional_figure(series, trends, palette="Azul"):
    """Evolución anual del interés: Ecuador, LATAM y todo el mundo, con recta del primer al último punto.

    Igual que la diapositiva de Tendencias: cada región lleva su área sombreada
    (superpuestas, semitransparentes) bajo la línea.
    """
    years = list(series.index)
    partial = years[-1] if years and years[-1] >= date.today().year else None
    labels = [f"{y}*" if y == partial else str(y) for y in years]
    fig = go.Figure()
    for name in series.columns:
        values = series[name]
        if values.notna().sum() == 0:
            continue
        color = REGION_COLORS.get(name, "#087BCC")
        fig.add_trace(go.Scatter(x=labels, y=values, mode="lines+markers", name=name, connectgaps=False,
                                 line=dict(color=color, width=2.6), marker=dict(size=7),
                                 fill="tozeroy", fillcolor=_transparent(color, .2),
                                 hovertemplate=f"{name}<br>%{{x}}: %{{y:.1f}}<extra></extra>"))
        trend = trends.get(name, {})
        if trend.get("slope") is not None:
            slope = trend["slope"]
            fig.add_trace(go.Scatter(x=labels, y=trend["line"], mode="lines", name=f"Tendencia {name}",
                                     line=dict(color=color, width=1.5, dash="dash"), hoverinfo="skip",
                                     showlegend=False))
            # La etiqueta va junto al último punto con dato (final de la recta).
            last = max(i for i, v in enumerate(trend["line"]) if v == v)
            fig.add_annotation(x=labels[last], y=trend["line"][last], xanchor="left", xshift=8, showarrow=False,
                               text=f"<b>{'+' if slope >= 0 else '−'}{abs(slope):.2f} pts/año</b>".replace(".", ","),
                               font=dict(color=color, size=11))
    return _layout(fig, 400, palette, margin=dict(l=10, r=110, t=30, b=40),
                   legend=dict(orientation="h", y=1.08, x=0),
                   xaxis=dict(type="category", gridcolor="#f3f5f7"),
                   yaxis=dict(title="Índice relativo (0–100)", gridcolor="#eef1f4", rangemode="tozero"))


def country_map(countries, palette="Azul"):
    """Mapa del interés promedio en español por país (índice de Google Trends)."""
    blue, light, _ = PALETTES[palette]
    data = countries.dropna(subset=["ISO3", "Promedio español"])
    fig = go.Figure(go.Choropleth(
        locations=data["ISO3"], z=data["Promedio español"], text=data["País"],
        colorscale=[[0, "#eef5fb"], [.5, light], [1, blue]], marker_line_color="white", marker_line_width=.4,
        colorbar=dict(title="Índice", thickness=12, len=.7),
        hovertemplate="%{text}<br>Promedio en español: %{z:.1f}<extra></extra>"))
    _world_view(fig)
    return _layout(fig, MAP_HEIGHT, palette, margin=dict(l=0, r=0, t=10, b=0))


def comparison_map(table, words, palette="Azul"):
    """Desglose comparativo por región, como en Google Trends.

    Cada país se pinta con el color sólido de la palabra que más se busca allí
    (celeste: español, azul: inglés, igual que la diapositiva de Tendencias); la
    leyenda indica el color de cada palabra y el cursor muestra los porcentajes.
    """
    blue, light, _ = PALETTES[palette]
    spanish, english = words
    data = table.dropna(subset=["ISO3"])
    groups = (("Español", f"{spanish} (español)", light, "% español"),
              ("Inglés", f"{english} (inglés)", blue, "% inglés"),
              ("Empate", "Empate (50 % · 50 %)", "#C3CCD5", "% español"))
    fig = go.Figure()
    for winner, label, color, share in groups:
        rows = data[data["Predomina"].eq(winner)]
        if rows.empty:
            continue
        fig.add_trace(go.Choropleth(
            locations=rows["ISO3"], z=[1] * len(rows), zmin=0, zmax=1,
            colorscale=[[0, color], [1, color]], showscale=False, name=label,
            marker_line_color="white", marker_line_width=.4,
            customdata=rows[["País", "% español", "% inglés"]].to_numpy(),
            hovertemplate=("<b>%{customdata[0]}</b><br>" + spanish + ": %{customdata[1]:.0f} %<br>"
                           + english + ": %{customdata[2]:.0f} %<extra></extra>")))
        # Elemento de leyenda: un cuadrado con el color de la palabra.
        fig.add_trace(go.Scattergeo(lon=[None], lat=[None], mode="markers", name=label, showlegend=True,
                                    marker=dict(symbol="square", size=14, color=color), hoverinfo="skip"))
    _world_view(fig)
    return _layout(fig, MAP_HEIGHT, palette, margin=dict(l=0, r=0, t=36, b=0),
                   legend=dict(orientation="h", y=1, yanchor="bottom", x=0, font=dict(size=13)))


# Alto del mapa: con la Antártida recortada, el mundo ocupa todo el ancho de la tarjeta.
MAP_HEIGHT = 560


def _world_view(fig):
    """Mundo completo centrado en el meridiano 0, sin Antártida, ocupando todo el espacio del gráfico."""
    fig.update_geos(projection_type="natural earth", projection_rotation=dict(lon=0, lat=0, roll=0),
                    center=dict(lon=0, lat=14), lonaxis_range=[-180, 180], lataxis_range=[-56, 84],
                    fitbounds=False, domain=dict(x=[0, 1], y=[0, 1]), showframe=False, showcoastlines=False,
                    # showland: dibuja todos los países (los que no tienen dato quedan en gris).
                    showland=True, showcountries=True, countrycolor="#ffffff", landcolor="#dfe3e8",
                    bgcolor="white",
                    showocean=False, showlakes=False)
    # Mapa fijo: no se arrastra ni se acerca; la leyenda no oculta países al hacer clic.
    fig.update_layout(dragmode=False, legend=dict(itemclick=False, itemdoubleclick=False))


# Configuración de st.plotly_chart para los mapas: sin barra, sin zoom con la rueda ni doble clic.
MAP_CONFIG = {"displayModeBar": False, "scrollZoom": False, "doubleClick": False}

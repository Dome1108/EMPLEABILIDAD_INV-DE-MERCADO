"""Convierte las figuras Plotly del tablero en PNG sin navegador.

El reporte PDF dibuja exactamente los trazos, formas y anotaciones de la figura
que muestra Streamlit; solo cambia el motor de dibujo (matplotlib) para no
depender de Chrome ni de kaleido.
"""
from io import BytesIO
import math
import os
from pathlib import Path
import re

import matplotlib
matplotlib.use('Agg')
from matplotlib import dates as mdates, font_manager, transforms
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter

DPI = 220


def fuente_reporte():
    """Century Gothic si está instalada; si no, DejaVu Sans incluida en matplotlib.

    Devuelve (familia, archivo regular, archivo negrita) para el PDF y los gráficos.
    """
    folders = [Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts',
               Path.home() / 'AppData' / 'Local' / 'Microsoft' / 'Windows' / 'Fonts',
               Path('/usr/share/fonts/truetype/msttcorefonts'), Path('/Library/Fonts')]
    for folder in folders:
        for regular, bold in (('GOTHIC.TTF', 'GOTHICB.TTF'), ('gothic.ttf', 'gothicb.ttf')):
            if (folder / regular).is_file() and (folder / bold).is_file():
                return 'Century Gothic', folder / regular, folder / bold
    bundled = Path(matplotlib.get_data_path()) / 'fonts' / 'ttf'
    return 'DejaVu Sans', bundled / 'DejaVuSans.ttf', bundled / 'DejaVuSans-Bold.ttf'


FAMILY, *_FILES = fuente_reporte()
for _file in _FILES:
    font_manager.fontManager.addfont(str(_file))
DASHES = {None: '-', 'solid': '-', 'dash': '--', 'dot': ':', 'dashdot': '-.', 'longdash': '--'}
MARKERS = {None: 'o', 'circle': 'o', 'diamond': 'D', 'x': 'X', 'line-ns': '|', 'square': 's'}
PX = .75  # 1 px de Plotly a puntos tipográficos


def color(value, default='#60758b'):
    if value is None:
        return default
    text = str(value).strip()
    match = re.fullmatch(r'rgba?\(([^)]*)\)', text.replace(' ', ''))
    if match:
        parts = [float(p) for p in match[1].split(',')]
        rgb = [p / 255 for p in parts[:3]]
        return (*rgb, parts[3] if len(parts) > 3 else 1.0)
    return text


def plain(text):
    return re.sub(r'<br\s*/?>', '\n', re.sub(r'<(?!br)[^>]+>', '', str(text or '')))


def _transform(ax, xref, yref):
    x = ax.transAxes if xref and ('domain' in xref or xref == 'paper') else ax.transData
    y = ax.transAxes if yref and ('domain' in yref or yref == 'paper') else ax.transData
    return transforms.blended_transform_factory(x, y)


def _formatter(axis):
    prefix, suffix = axis.tickprefix or '', axis.ticksuffix or ''
    thousands = (axis.tickformat or '').startswith(',')

    def fmt(value, _):
        number = f'{value:,.0f}' if thousands or abs(value) >= 10000 else f'{value:g}'
        return f'{prefix}{number}{suffix}'
    return FuncFormatter(fmt)


def _axis(ax, layout_axis, which, default_grid=True, categorical=False):
    set_label, set_lim, set_ticks = ((ax.set_xlabel, ax.set_xlim, ax.set_xticks) if which == 'x'
                                     else (ax.set_ylabel, ax.set_ylim, ax.set_yticks))
    if layout_axis.title and layout_axis.title.text:
        set_label(plain(layout_axis.title.text), color='#60758b', fontsize=9)
    if layout_axis.range:
        set_lim(*layout_axis.range)
    elif layout_axis.rangemode == 'tozero' and not categorical:
        low, high = (ax.get_xlim() if which == 'x' else ax.get_ylim())
        set_lim(min(0, low), max(0, high) * 1.04 if high > 0 else high)
    if layout_axis.autorange == 'reversed':
        (ax.invert_xaxis if which == 'x' else ax.invert_yaxis)()
    if layout_axis.visible is False:
        (ax.get_xaxis() if which == 'x' else ax.get_yaxis()).set_visible(False)
        return
    if layout_axis.type == 'date':
        low, high = (ax.get_xlim() if which == 'x' else ax.get_ylim())
        locator = mdates.MonthLocator(interval=max(1, math.ceil((high - low) / 30.4 / 8)))
        (ax.xaxis if which == 'x' else ax.yaxis).set_major_locator(locator)
        (ax.xaxis if which == 'x' else ax.yaxis).set_major_formatter(mdates.DateFormatter('%b %Y'))
        ax.grid(True, axis=which, color=color(layout_axis.gridcolor, '#e8ecf0'), linewidth=.7)
        ax.tick_params(axis=which, colors='#60758b', labelsize=8, length=0)
        return
    if categorical:  # Etiquetas de categorías ya colocadas por el trazo (barras).
        ax.tick_params(axis=which, colors='#60758b', labelsize=8, length=0)
        return
    if layout_axis.tickvals:
        set_ticks(list(layout_axis.tickvals))
    elif layout_axis.dtick and layout_axis.range:
        low, high = layout_axis.range
        step = float(layout_axis.dtick)
        set_ticks([v * step for v in range(math.ceil(low / step), math.floor(high / step) + 1)])
    (ax.xaxis if which == 'x' else ax.yaxis).set_major_formatter(_formatter(layout_axis))
    grid = default_grid if layout_axis.showgrid is None else layout_axis.showgrid
    if grid:
        ax.grid(True, axis=which, color=color(layout_axis.gridcolor, '#e8ecf0'), linewidth=.7)
    ax.tick_params(axis=which, colors='#60758b', labelsize=8, length=0)


def _shapes_and_annotations(fig, ax):
    for shape in fig.layout.shapes or []:
        below = shape.layer == 'below'
        transform = _transform(ax, shape.xref or 'x', shape.yref or 'y')
        if shape.type == 'rect':
            width = shape.line.width if shape.line and shape.line.width is not None else 0
            ax.add_patch(Rectangle((shape.x0, shape.y0), shape.x1 - shape.x0, shape.y1 - shape.y0,
                                   transform=transform, facecolor=color(shape.fillcolor, 'none'),
                                   edgecolor=color(shape.line.color) if width else 'none',
                                   linewidth=width * PX, zorder=0 if below else 3))
        elif shape.type == 'line':
            line = shape.line
            ax.plot([shape.x0, shape.x1], [shape.y0, shape.y1], transform=transform,
                    color=color(line.color), linewidth=(line.width or 1) * PX,
                    linestyle=DASHES.get(line.dash, '--'), zorder=.5 if below else 3)
    for note in fig.layout.annotations or []:
        font = note.font
        box = dict(facecolor=color(note.bgcolor), edgecolor='none', pad=2) if note.bgcolor else None
        ax.text(note.x, note.y, plain(note.text), transform=_transform(ax, note.xref or 'x', note.yref or 'y'),
                ha={'left': 'left', 'right': 'right'}.get(note.xanchor, 'center'),
                va={'bottom': 'bottom', 'top': 'top'}.get(note.yanchor, 'center'),
                color=color(font.color if font else None), fontsize=((font.size if font and font.size else 11) * PX),
                fontweight='bold' if '<b>' in str(note.text) else 'normal', bbox=box, clip_on=False, zorder=5)


# Desplazamiento (puntos) y alineación de etiquetas según textposition de Plotly.
def _text_offset(position, size=6):
    position = str(position or 'top center')
    gap = size / 2 + 5
    dx = gap if 'right' in position else -gap if 'left' in position else 0
    dy = gap if 'top' in position else -gap if 'bottom' in position else 0
    ha = 'left' if 'right' in position else 'right' if 'left' in position else 'center'
    va = 'bottom' if 'top' in position else 'top' if 'bottom' in position else 'center'
    return (dx, dy), ha, va


def _dates(values):
    import pandas as pd
    return list(pd.to_datetime(list(values)))


def _scatter(ax, trace, date_x=False):
    mode = trace.mode or 'lines+markers'
    marker = trace.marker
    line = trace.line
    stroke = color(line.color if line else None)
    face = color(marker.color if marker else None, stroke)
    edge = color(marker.line.color if marker and marker.line else None, face)
    edge_width = (marker.line.width if marker and marker.line and marker.line.width is not None else 0) * PX
    size = (marker.size if marker and marker.size else 6) * PX
    alpha = marker.opacity if marker and marker.opacity is not None else 1
    x, y = list(trace.x), list(trace.y)
    if date_x:
        x = _dates(x)
    name = None if trace.showlegend is False else trace.name
    if 'lines' in mode:
        ax.plot(x, y, color=stroke, linewidth=(line.width or 2) * PX, linestyle=DASHES.get(line.dash, '-'),
                label=name, zorder=2)
    if 'markers' in mode:
        symbol = MARKERS.get(marker.symbol if marker else None, 'o')
        ax.plot(x, y, linestyle='none', marker=symbol, markersize=size, markerfacecolor=face,
                markeredgecolor=edge if edge_width else face, markeredgewidth=edge_width or (1.6 if symbol in 'X|' else 0),
                alpha=alpha, label=None if 'lines' in mode else name, zorder=4)
    if 'text' in mode and trace.text is not None:
        positions = trace.textposition
        positions = list(positions) if isinstance(positions, (list, tuple)) else [positions] * len(x)
        for xi, yi, label, position in zip(x, y, trace.text, positions):
            offset, ha, va = _text_offset(position, size)
            ax.annotate(str(label), (xi, yi), textcoords='offset points', xytext=offset, ha=ha, va=va, fontsize=7,
                        color='#476783', annotation_clip=False)


def _box(ax, trace):
    """Caja con cuartiles lineales y bigotes al mínimo y máximo (boxpoints=False)."""
    import numpy as np
    values = sorted(v for v in trace.y if v is not None)
    if not values:
        return
    q1, med, q3 = np.percentile(values, [25, 50, 75], method='linear')
    position = list(trace.x)[0] if trace.x is not None and len(trace.x) else 0
    line = color(trace.line.color if trace.line else None, '#0076ba')
    ax.bxp([dict(med=med, q1=q1, q3=q3, whislo=values[0], whishi=values[-1], fliers=[])], positions=[position],
           widths=[(trace.width or .5) * .9], showfliers=False, patch_artist=True,
           boxprops=dict(facecolor=color(trace.fillcolor, 'none'), edgecolor=line, linewidth=1.5),
           medianprops=dict(color=line, linewidth=1.5), whiskerprops=dict(color=line, linewidth=1.2),
           capprops=dict(color=line, linewidth=1.2), manage_ticks=False, zorder=1)


def _bar(ax, trace):
    labels, values = list(trace.y), list(trace.x)
    colors = trace.marker.color
    colors = [color(c) for c in colors] if isinstance(colors, (list, tuple)) else color(colors)
    positions = range(len(labels))
    ax.barh(positions, values, color=colors, height=.72, zorder=2)
    ax.set_yticks(list(positions), labels)
    if trace.text is not None:
        span = max(values) if values else 1
        for position, value, text in zip(positions, values, trace.text):
            ax.text(value + span * .008, position, str(text), va='center', fontsize=7, color='#60758b')


def _polar(fig, figure):
    ax = figure.add_subplot(projection='polar')
    polar = fig.layout.polar
    ax.set_theta_offset(math.radians(polar.angularaxis.rotation if polar.angularaxis.rotation is not None else 90))
    ax.set_theta_direction(-1 if polar.angularaxis.direction == 'clockwise' else 1)
    labels = []
    for trace in fig.data:
        for label in trace.theta:
            if label not in labels:
                labels.append(label)
    angle = {label: 2 * math.pi * i / len(labels) for i, label in enumerate(labels)}
    for trace in fig.data:
        theta = [angle[t] for t in trace.theta]
        r = list(trace.r)
        line = trace.line
        ax.plot(theta, r, color=color(line.color), linewidth=(line.width or 2) * PX,
                linestyle=DASHES.get(line.dash, '-'), zorder=3)
        if trace.fill == 'toself':
            ax.fill(theta, r, color=color(trace.fillcolor), zorder=2)
        if 'markers' in (trace.mode or ''):
            ax.plot(theta, r, linestyle='none', marker='o', markersize=(trace.marker.size or 6) * PX,
                    color=color(trace.marker.color), zorder=4)
    radial = polar.radialaxis
    if radial.range:
        ax.set_ylim(*radial.range)
    if radial.tickvals:
        ax.set_yticks(list(radial.tickvals))
        ax.set_yticklabels([f'{v:g}{radial.ticksuffix or ""}' for v in radial.tickvals], fontsize=7, color='#90a1b1')
    ax.set_xticks(list(angle.values()), labels, fontsize=8.5, color='#60758b')
    # Escala radial entre el 2.º y 3.er eje, lejos de la cima del polígono.
    ax.set_rlabel_position(math.degrees(2 * math.pi * 1.5 / len(labels)))
    ax.tick_params(axis='x', pad=8)
    ax.grid(color='#e5edf4')
    ax.spines['polar'].set_color('#e5edf4')


def figura_png(fig, width_cm, height_cm):
    """PNG de alta resolución de una figura Plotly del tablero."""
    # Contexto local: no cambia la fuente de otras exportaciones matplotlib del tablero.
    # DejaVu Sans como respaldo por glifo (p. ej. ₡, ausente en Century Gothic).
    with matplotlib.rc_context({'font.family': [FAMILY, 'DejaVu Sans']}):
        return _figura_png(fig, width_cm, height_cm)


def _figura_png(fig, width_cm, height_cm):
    figure = Figure(figsize=(width_cm / 2.54, height_cm / 2.54), dpi=DPI, facecolor='white', layout='constrained')
    if any(trace.type == 'scatterpolar' for trace in fig.data):
        _polar(fig, figure)
    else:
        ax = figure.add_subplot()
        ax.set_facecolor(color(fig.layout.plot_bgcolor, 'white') if fig.layout.plot_bgcolor else 'white')
        for spine in ax.spines.values():
            spine.set_visible(False)
        has_bars = False
        date_x = fig.layout.xaxis.type == 'date'
        for trace in fig.data:
            if trace.type == 'bar':
                has_bars = True
                _bar(ax, trace)
            elif trace.type == 'scatter':
                _scatter(ax, trace, date_x)
            elif trace.type == 'box':
                _box(ax, trace)
        _axis(ax, fig.layout.xaxis, 'x', default_grid=True, categorical=fig.layout.xaxis.type == 'category')
        _axis(ax, fig.layout.yaxis, 'y', default_grid=not has_bars, categorical=has_bars)
        _shapes_and_annotations(fig, ax)
        named = [t for t in fig.data if t.showlegend is not False and t.name]
        if fig.layout.showlegend is not False and len(named) > 1:
            handles, labels = ax.get_legend_handles_labels()
            ax.legend(handles, labels, loc='upper center', bbox_to_anchor=(.5, -.14), ncol=len(labels),
                      frameon=False, fontsize=8, labelcolor='#60758b')
    output = BytesIO()
    figure.savefig(output, format='png', dpi=DPI, facecolor='white')
    return output.getvalue()

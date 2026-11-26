# [Copia de Tendencias · presentation/charts/linkedin_template_graphs.py; solo cambian las rutas de import]
"""Dibuja los gráficos de la plantilla siguiendo Graficos_Inv.ipynb."""
from io import BytesIO
from textwrap import fill
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch
from matplotlib.ticker import FuncFormatter, MaxNLocator

AZUL = '#006EBF'
CLARO = '#A6CAEC'


def insertar_figura(slide, shape, figura, descripcion):
    buffer = BytesIO()
    figura.savefig(buffer, format='png', dpi=180, bbox_inches='tight', facecolor='white')
    plt.close(figura)
    buffer.seek(0)
    nuevo = slide.shapes.add_picture(buffer, shape.left, shape.top, shape.width, shape.height)
    nuevo._element.nvPicPr.cNvPr.set('descr', descripcion)
    parent = shape._element.getparent()
    index = parent.index(shape._element)
    parent.remove(nuevo._element)
    parent.remove(shape._element)
    parent.insert(index, nuevo._element)
    return nuevo


def grafico_aptitudes(categorias, series, titulo, porcentaje=True):
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.subplots_adjust(left=.25, right=.97, top=.86, bottom=.18)
    for j, (region, valores) in enumerate(series):
        desplazamiento = (j - (len(series) - 1) / 2) * .36
        for i, valor in enumerate(valores):
            y = i + desplazamiento
            if valor is None:
                ax.text(.2, y, 'N/D', va='center', color='#777777', fontsize=10)
                continue
            ax.add_patch(FancyBboxPatch((0, y - .14), valor, .28,
                boxstyle='round,pad=0,rounding_size=0.08', linewidth=0,
                facecolor=(AZUL, CLARO)[j % 2]))
    maximo = max((v for _, vs in series for v in vs if v is not None), default=0)
    ax.set_xlim(0, max(maximo * 1.08, 1))
    ax.set_ylim(max(len(categorias), 1) - .5, -.5)
    ax.set_yticks(range(len(categorias)), [fill(str(c), 27) for c in categorias], fontsize=12)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:g}%' if porcentaje else f'{x:g}'))
    ax.grid(axis='x', linestyle=(0, (3, 3)), linewidth=1, color='#D9D9D9', alpha=.65)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis='both', length=0, labelsize=11)
    ax.set_title(titulo, fontsize=16, fontweight='bold', pad=22)
    if not categorias:
        ax.text(.5, .5, 'N/D', transform=ax.transAxes, ha='center', color='#777777')
    ax.legend(handles=[Patch(facecolor=(AZUL, CLARO)[i % 2], edgecolor='none',
                             label=('LATAM' if n == 'América Latina' else n))
                       for i, (n, _) in enumerate(series)], frameon=False,
              loc='upper center', bbox_to_anchor=(.5, -.1), ncol=2, fontsize=12)
    return fig


def grafico_empresas_sectores(empresas, sectores):
    fig, ax = plt.subplots(figsize=(10, 9))
    ax.axis('off')
    ax.set_xlim(0, 10.4)
    ax.set_ylim(-.7, 10.6)
    for titulo, filas, alto, posiciones in (
        ('Principales sectores de empleo', sectores[:5], 10.1, [9.2, 8.3, 7.4, 6.5, 5.6]),
        ('Principales empleadores', empresas[:5], 4.05, [3.55, 2.65, 1.75, .85, -.05])):
        ax.text(.3, alto, titulo, fontsize=20, va='center')
        ax.plot([4.6, 4.6], [posiciones[-1] - .35, posiciones[0] + .5],
                color='#D9D9D9', linewidth=1.5, linestyle=(0, (2, 2)))
        maximo = max((f['profesionales'] for f in filas if f['profesionales'] is not None), default=0)
        if not filas:
            ax.text(.7, posiciones[0], 'N/D', color='#555555', fontsize=14)
        for fila, y in zip(filas, posiciones):
            valor = fila['profesionales']
            ax.text(.7, y, fill(fila['nombre'], 31), fontsize=12, color='#555555', va='center')
            if valor is not None:
                ax.barh(y, valor / maximo * 4.2 if maximo else 0, left=4.6,
                        height=.52, color='#E2E2E2', edgecolor='none')
            texto = f'({valor:,.0f})'.replace(',', '.') if valor is not None else 'N/D'
            ax.text(9.15, y, texto, fontsize=13, color=AZUL, fontweight='bold', va='center')
    ax.plot([.4, 10.1], [4.75, 4.75], color='#D9D9D9', linewidth=1.2)
    fig.subplots_adjust(left=.01, right=.99, top=.99, bottom=.01)
    return fig


def grafico_cargos(cargos):
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.axis('off')
    ax.set_xlim(-45, 106)
    ax.set_ylim(5, -.7)
    ax.text(-45, -.45, 'Principales cargos', fontsize=20, fontweight='bold')
    ax.plot([0, 0], [-.15, 4.8], color='#00618C', linewidth=1.7)
    total = sum(v for _, v in cargos if v is not None)
    if not cargos:
        ax.text(-30, .3, 'N/D', fontsize=16, color='#666666')
    for i, (nombre, valor) in enumerate(cargos[:5]):
        ax.text(-4, i + .15, fill(nombre, 25), ha='right', va='center', fontsize=13)
        ax.text(-4, i + .42, f'{valor:,.0f} profesionales'.replace(',', '.') if valor is not None else 'N/D',
                ha='right', va='center', fontsize=10, color='#666666')
        ax.add_patch(FancyBboxPatch((0, i), 100, .5, boxstyle='round,pad=0,rounding_size=.08',
                                   linewidth=0, facecolor='#DCEAF7'))
        if valor is not None and total:
            pct = valor / total * 100
            ax.add_patch(FancyBboxPatch((0, i), pct, .5, boxstyle='round,pad=0,rounding_size=.08',
                                       linewidth=0, facecolor=CLARO))
            ax.text(min(pct + 2, 94), i + .25, f'{pct:.0f}%', va='center', color='#555555',
                    fontsize=11, fontweight='bold')
    fig.subplots_adjust(left=.01, right=.99, top=.99, bottom=.01)
    return fig

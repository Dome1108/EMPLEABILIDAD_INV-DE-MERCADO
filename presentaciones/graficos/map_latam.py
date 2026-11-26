# [Copia de Tendencias · presentation/charts/map_latam.py; solo cambian las rutas de import]
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.io.shapereader as shapereader
from presentaciones.graficos.linkedin import cantidad_ubicacion, clave_aptitud

# Mapeo de ubicaciones a países
def mapear_a_pais(ubicacion):
    ubicacion = clave_aptitud(ubicacion)
    if any(nombre in ubicacion for nombre in ("brasil", "brazil", "são paulo", "sao paulo",
                                             "río de janeiro", "rio de janeiro", "belo horizonte")):
        return "Brazil"
    if "argentina" in ubicacion or "buenos aires" in ubicacion:
        return "Argentina"
    if "mexico" in ubicacion or "ciudad de mexico" in ubicacion:
        return "Mexico"
    if "chile" in ubicacion or "santiago" in ubicacion:
        return "Chile"
    if "colombia" in ubicacion or "bogota" in ubicacion:
        return "Colombia"
    if "ecuador" in ubicacion or "quito" in ubicacion or "guayaquil" in ubicacion:
        return "Ecuador"
    if "peru" in ubicacion or "lima" in ubicacion:
        return "Peru"
    if "uruguay" in ubicacion or "montevideo" in ubicacion:
        return "Uruguay"
    if "venezuela" in ubicacion or "caracas" in ubicacion:
        return "Venezuela"
    if "paraguay" in ubicacion or "asuncion" in ubicacion:
        return "Paraguay"
    if "bolivia" in ubicacion or "la paz" in ubicacion:
        return "Bolivia"
    for nombre, ingles in (('costa rica', 'Costa Rica'), ('panama', 'Panama'),
                          ('guatemala', 'Guatemala'), ('honduras', 'Honduras'),
                          ('el salvador', 'El Salvador'), ('nicaragua', 'Nicaragua'),
                          ('cuba', 'Cuba'), ('republica dominicana', 'Dominican Republic'),
                          ('puerto rico', 'Puerto Rico'), ('haiti', 'Haiti')):
        if nombre in ubicacion:
            return ingles
    # Otros países de Latam pueden agregarse aquí
    return None

def generar_mapa_latam(rows=(), ruta_salida="mapa_latam.png"):
    print("=== Datos originales de linkedin_ubicaciones ===")
    for ubicacion, cantidad in rows:
        print(f"Ubicacion: {ubicacion} | Cantidad: {cantidad}")
    # Agrupar por país
    paises = {}
    for ubicacion, cantidad in rows:
        pais = mapear_a_pais(str(ubicacion))
        if pais:
            paises[pais] = paises.get(pais, 0) + (cantidad_ubicacion(cantidad) or 0)
    print("\n=== Agrupación por país ===")
    for pais, total in paises.items():
        print(f"{pais}: {total}")
    # Top 5 países
    top_paises = sorted(paises.items(), key=lambda x: x[1], reverse=True)[:5]
    print("\n=== Top 5 países ===")
    for i, (pais, total) in enumerate(top_paises, 1):
        print(f"{i}. {pais}: {total}")
    top_pais_nombres = [p[0] for p in top_paises]
    # Escala azul de la plantilla.
    color_principal = "#006DBF"
    escala_azules = ["#398BCB", "#6BA8D7", "#9CC5E3", "#CCE2F2"]
    color_gris_claro = "#eeeeee"
    # Mapeo de colores por país
    pais_color = {}
    if top_pais_nombres:
        pais_color[top_pais_nombres[0]] = color_principal
        for idx, p in enumerate(top_pais_nombres[1:]):
            pais_color[p] = escala_azules[idx] if idx < len(escala_azules) else color_gris_claro
    # El resto en gris claro
    # Lista de países de Latam
    latam_countries = [
        "Brazil", "Argentina", "Mexico", "Chile", "Colombia", "Ecuador", "Peru",
        "Uruguay", "Venezuela", "Paraguay", "Bolivia", "Guyana", "Suriname", "French Guiana",
        "Costa Rica", "Panama", "Guatemala", "Honduras", "El Salvador", "Nicaragua",
        "Cuba", "Dominican Republic", "Puerto Rico", "Haiti"
    ]
    mostrar_mexico = paises.get('Mexico', 0) > 0
    if not mostrar_mexico:
        latam_countries.remove('Mexico')
    print(f'[MAPA LATAM] México: {"incluido con datos" if mostrar_mexico else "omitido por falta de datos"}')
    fig = plt.figure(figsize=(7, 9))
    ax = plt.axes(projection=ccrs.PlateCarree())
    # Límites pegados al contorno de los países: sin océano vacío alrededor.
    ax.set_extent([-118, -33, -56.5, 33] if mostrar_mexico else [-93, -33, -56.5, 24],
                  crs=ccrs.PlateCarree())
    # No agregar LAND ni OCEAN para fondo transparente
    # Los bordes se dibujan con cada país para no mostrar siluetas excluidas.
    # Quitar el marco (spines) del gráfico
    for spine in ax.spines.values():
        spine.set_visible(False)
    # Dibujar países de Latam usando shapereader
    shpfilename = shapereader.natural_earth(resolution='110m', category='cultural', name='admin_0_countries')
    reader = shapereader.Reader(shpfilename)
    for record in reader.records():
        name = record.attributes.get('NAME_LONG') or record.attributes.get('NAME')
        if name in latam_countries:
            color = pais_color.get(name, color_gris_claro)
            ax.add_geometries([record.geometry], ccrs.PlateCarree(),
                              facecolor=color, edgecolor='white', linewidth=0.8)
    plt.tight_layout()
    
    # Crear directorio de salida si no existe
    os.makedirs(os.path.dirname(ruta_salida) or '.', exist_ok=True)
    
    plt.savefig(ruta_salida, bbox_inches='tight', pad_inches=0.02, dpi=300, transparent=True)
    plt.close(fig)
    print(f"Mapa generado y guardado en {ruta_salida}")
    return top_paises

if __name__ == "__main__":
    generar_mapa_latam()

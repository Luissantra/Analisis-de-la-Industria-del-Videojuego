import folium
import pandas as pd
from folium.plugins import MarkerCluster
import urllib.parse
import base64
from pathlib import Path
import config

def get_base64_logo(parent_name):
    """Lee el logo local y lo convierte a base64 para inyectarlo en el popup del mapa."""
    if pd.isna(parent_name) or parent_name == "Independent & Other Publishers":
        return None
    
    safe_name = "".join([c if c.isalnum() or c in " &()_-" else "_" for c in parent_name])
    logos_dir = getattr(config, 'LOGOS_DIR', Path(__file__).resolve().parent / "assets" / "logos")
    img_path = logos_dir / f"{safe_name}.png"
    
    if img_path.exists():
        with open(img_path, "rb") as img_file:
            encoded = base64.b64encode(img_file.read()).decode()
            return f"data:image/png;base64,{encoded}"
    return None

def create_interactive_map(df, center=[20, 0], zoom=2):
    """
    Crea un mapa interactivo utilizando Folium para visualizar 
    la ubicación de los estudios de videojuegos de forma intereactiva.
    """
    # 1. Inicializamos el mapa. Al no especificar tiles aquí, usaremos la primera TileLayer añadida como default.
    m = folium.Map(location=center, zoom_start=zoom, tiles=None)

    # 2. Añadimos nuestras propias capas base
    # Añadimos primero el Tema Oscuro para que sea el predeterminado
    folium.TileLayer('cartodbdark_matter', name='Tema Oscuro', overlay=False, control=True).add_to(m)
    
    # Añadimos el resto de capas
    # Establecemos show=False para que no se superpongan y el Tema Oscuro sea el real predeterminado
    folium.TileLayer('cartodbpositron', name='Tema Claro', overlay=False, control=True, show=False).add_to(m)
    
    # Vista Satélite (usando la API pública de Esri)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satélite',
        overlay=False,
        control=True,
        show=False
    ).add_to(m)


    # Estilos personalizados para las regiones
    region_styles = {
        'North America': {'pin': 'purple', 'hex': '#800080'},
        'South America': {'pin': 'green', 'hex': '#28a745'},
        'Europe': {'pin': 'blue', 'hex': '#007bff'},
        'Asia': {'pin': 'red', 'hex': '#dc3545'},
        'Africa': {'pin': 'orange', 'hex': '#fd7e14'},
        'Oceania': {'pin': 'cadetblue', 'hex': '#5f9ea0'},
        'Other': {'pin': 'gray', 'hex': '#6c757d'}
    }
    # Capturamos las regiones únicas para crear un clúster de marcadores por región
    unique_regions = df['Region'].unique()
    for region in unique_regions:
        style = region_styles.get(region, region_styles['Other'])
        hex_color = style['hex']
        pin_color = style['pin']

        # Creamos capa de regiones
        region_layer = folium.FeatureGroup(name=region)

        # Modificamos los colores de las regiones de forma dinámica
        custom_js = f"""
        function(cluster) {{
            var childCount = cluster.getChildCount();
            var size = Math.min(30 + (childCount * 2), 80); 
            
            var html = '<div style="' +
                'background-color: {hex_color}40; ' +  // 40 adds transparency to the hex code
                'border: 2px solid {hex_color}; ' +
                'border-radius: 50%; ' +
                'color: {hex_color}; ' +
                'font-weight: bold; ' +
                'font-size: 14px; ' +
                'display: flex; ' +
                'align-items: center; ' +
                'justify-content: center; ' +
                'width: ' + size + 'px; ' +
                'height: ' + size + 'px;' +
                'box-shadow: 0 0 10px {hex_color};' + 
                '">' + childCount + '</div>';
                
            return new L.DivIcon({{ html: html, className: 'custom-cluster', iconSize: new L.Point(size, size) }});
        }}
        """

        # Inicializamos el cluster
        region_cluster = MarkerCluster(icon_create_function=custom_js).add_to(region_layer)

        # Filtramos el DataFrame por región
        region_df = df[df['Region'] == region]
        valid_locations = region_df.dropna(subset=['Lat', 'Lon'])

        # Añadimos las estudios de la región al cluster
        for idx, row in valid_locations.iterrows():
            if pd.notna(row['Lat']) and pd.notna(row['Lon']):
                
                # Limpiamos y preparamos el texto para la URL
                search_query = f"{row['Studio Name']} {row['City']} {row['Country']}"
                safe_query = urllib.parse.quote_plus(search_query)
                maps_url = f"https://www.google.com/maps/search/?api=1&query={safe_query}"

                # Extracción de metadatos adicionales de la base de datos (si están presentes en el df)
                parent = row.get('Parent', 'Independiente')
                top_game = row.get('Top_Game', 'Información no disponible')
                score = row.get('Metacritic', 'N/A')
                logo_url = row.get('Logo_URL')
                
                # Determinamos el color del badge de Metacritic
                score_val = pd.to_numeric(score, errors='coerce')
                score_color = "#28a745" if score_val >= 75 else "#ffc107" if score_val >= 50 else "#dc3545" if score_val < 50 else "#6c757d"

                # Construimos el HTML del popup con un enlace a Google Maps
                popup_html = f"""
                <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; min-width: 220px; color: #333;">
                    <div style="text-align: center; margin-bottom: 8px;">
                        {f'<img src="{logo_url}" style="max-height: 40px; margin-bottom: 5px; border-radius: 4px;">' if pd.notna(logo_url) and logo_url != 'No registrado' else f'<h5 style="margin:0; color:{hex_color};">{parent}</h5>'}
                        <h4 style="margin: 2px 0; color: #111; border-bottom: 1px solid #ddd; padding-bottom: 5px;">{row['Studio Name']}</h4>
                    </div>
                    
                    <div style="font-size: 13px;">
                        <p style="margin: 3px 0;"><b>🌍 Región:</b> {region}</p>
                        <p style="margin: 3px 0;"><b>📍 Ciudad:</b> {row['City']}, {row['Country']}</p>
                        <div style="background: #f8f9fa; border-radius: 5px; padding: 8px; margin-top: 8px; border: 1px solid #eee;">
                            <p style="margin: 0 0 4px 0;"><b>🎮 Juego:</b> {top_game}</p>
                            <p style="margin: 0;"><b>🏆 Metacritic:</b> 
                                <span style="background-color: {score_color}; color: white; padding: 1px 6px; border-radius: 3px; font-weight: bold;">
                                    {score}
                                </span>
                            </p>
                        </div>
                    </div>
                    
                    <div style="margin-top: 15px; text-align: center;">
                        <a href="{maps_url}" target="_blank" 
                           style="background-color: {pin_color}; color: white; padding: 6px 12px; 
                                  text-decoration: none; border-radius: 4px; font-size: 13px; 
                                  display: inline-block; width: 80%; font-weight: bold;">
                           📍 Abrir en Google Maps
                        </a>
                    </div>
                </div>
                """
                
                folium.Marker(
                    location=[row['Lat'], row['Lon']],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=row['Studio Name'],
                    icon=folium.Icon(color=pin_color, icon='gamepad', prefix='fa')
                ).add_to(region_cluster)

        # Capa completa regional
        region_layer.add_to(m)
    # Añadimos control de capas para poder activar/desactivar regiones
    folium.LayerControl(collapsed=False).add_to(m)

    # Auto-Zoom dinámico
    # Verificamos que el dataframe no esté vacío
    if not df.empty:
        # Obtenemos los límites de latitud y longitud para ajustar el zoom
        sw = [df['Lat'].min(), df['Lon'].min()]  # Suroeste
        ne = [df['Lat'].max(), df['Lon'].max()] # Noreste

        # comprobamos que no sean valores nulos
        if pd.notna(sw[0]) and pd.notna(sw[1]):
            # caso especial para un solo punto, ajustamos el zoom manualmente
            if sw == ne:
                m.location = sw
                m.zoom_start = 10
            else:
                m.fit_bounds([sw, ne], padding=(35, 35))  # Ajustamos el zoom para mostrar todos los puntos

    return m

import folium
import pandas as pd
from folium.plugins import MarkerCluster
import urllib.parse

def create_interactive_map(df, center=[20, 0], zoom=2):
    """
    Crea un mapa interactivo utilizando Folium para visualizar 
    la ubicación de los estudios de videojuegos de forma intereactiva.
    """
    # 1. Inicializamos el mapa con la capa base por defecto
    m = folium.Map(location=center, zoom_start=zoom, tiles='cartodbdark_matter')

    # 2. Añadimos alternativas de capas base
    # Tema Claro
    folium.TileLayer('cartodbpositron', name='Tema Claro').add_to(m)
    
    # Vista Satélite
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satélite'
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

                # Lógica para mostrar datos de IGDB solo si existen (es un estudio notable)
                has_igdb = pd.notna(row.get("Parent"))
                
                logo_img = f'<img src="{row["Logo_URL"]}" alt="Logo" style="max-height: 40px; margin-bottom: 5px; display: block; margin-left: auto; margin-right: auto;">' if has_igdb and pd.notna(row.get("Logo_URL")) else ""
                
                acquisition = row.get("Acquisition_Year")
                acq_str = f"<b>Fundación / Adquisición:</b> {acquisition}<br>" if pd.notna(acquisition) and acquisition != 'No registrado' else ""
                
                igdb_section = ""
                if has_igdb:
                    top_game = row.get("Top_Game", "No registrado")
                    metacritic = row.get("Metacritic", "N/A")
                    
                    if pd.notna(metacritic) and metacritic != 'N/A':
                        try:
                            meta_val = float(metacritic)
                            meta_color = "green" if meta_val >= 75 else ("orange" if meta_val >= 50 else "red")
                            metacritic_html = f'<span style="background-color: {meta_color}; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold;">{meta_val:g}</span>'
                        except ValueError:
                            metacritic_html = f'<span style="background-color: gray; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold;">{metacritic}</span>'
                    else:
                        metacritic_html = '<span style="color: #888;">N/A</span>'
                        
                    igdb_section = f"""
                    <hr style="margin: 8px 0; border: 0; border-top: 1px solid #eee;">
                    <p style="margin: 4px 0; font-size: 13px; color: #333;"><b>🎮 Top Game:</b> {top_game}</p>
                    <p style="margin: 4px 0; font-size: 13px; color: #333;"><b>⭐ Metacritic:</b> {metacritic_html}</p>
                    """

                # Construimos el HTML del popup
                popup_html = f"""
                <div style="font-family: Arial; min-width: 220px; text-align: center;">
                    {logo_img}
                    <h4 style="margin: 0px 0 5px 0; color: #333; border-bottom: 1px solid #ccc; padding-bottom: 5px;">
                        {row['Studio Name']}
                    </h4>
                    <p style="margin: 4px 0; font-size: 13px; color: #555;">{acq_str}<b>📍</b> {row['City']}, {row['Country']}</p>
                    {igdb_section}
                    
                    <div style="margin-top: 12px;">
                        <a href="{maps_url}" target="_blank" 
                           style="background-color: {pin_color}; color: white; padding: 6px 12px; 
                                  text-decoration: none; border-radius: 4px; font-size: 12px; 
                                  display: inline-block; width: 100%; box-sizing: border-box; font-weight: bold;">
                           📍 Ver en Google Maps
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




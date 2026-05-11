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
    # Validaciones defensivas y conversión numérica
    if df.empty or 'Lat' not in df.columns or 'Lon' not in df.columns:
        return folium.Map(location=[20, 0], zoom_start=2, tiles="cartodbdark_matter")

    df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
    df['Lon'] = pd.to_numeric(df['Lon'], errors='coerce')
    df_valid = df.dropna(subset=['Lat', 'Lon'])

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

                # Extracción segura de metadatos (evitando "None")
                parent = row['Parent'] if pd.notna(row.get('Parent')) else 'Independiente'
                top_game = row['Top_Game'] if pd.notna(row.get('Top_Game')) else 'Información no disponible'
                score = row['Metacritic'] if pd.notna(row.get('Metacritic')) else 'N/A'
                logo_url = row['Logo_URL'] if pd.notna(row.get('Logo_URL')) else None
                city = row['City'] if pd.notna(row.get('City')) else 'Desconocida'
                country = row['Country'] if pd.notna(row.get('Country')) else 'Desconocido'
                category = row['Category'] if pd.notna(row.get('Category')) else 'Estudio Independiente / Otro'
                
                # Determinamos el color del badge de Metacritic
                try:
                    score_val = float(score)
                    score_color = "#28a745" if score_val >= 75 else "#ffc107" if score_val >= 50 else "#dc3545"
                except (ValueError, TypeError):
                    score_color = "#6c757d"
                    score = "N/A"

                # Construimos el HTML del popup con un enlace a Google Maps
                popup_html = f"""
                <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; min-width: 220px; color: #333;">
                    <div style="text-align: center; margin-bottom: 8px;">
                        {f'<img src="{logo_url}" style="max-height: 40px; margin-bottom: 5px; border-radius: 4px;">' if logo_url and str(logo_url) != 'No registrado' else ''}
                        <h4 style="margin: 2px 0; color: #111; border-bottom: 1px solid #ddd; padding-bottom: 5px;">{row['Studio Name']}</h4>
                    </div>
                    
                    <div style="font-size: 13px;">
                        <p style="margin: 3px 0;"><b>🌍 Región:</b> {region}</p>
                        <p style="margin: 3px 0;"><b>📍 Ciudad:</b> {city}, {country}</p>
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

    # Añadir Leyenda HTML
    legend_html = '''
    <div style="position: fixed; 
        bottom: 50px; left: 50px; width: 150px; height: auto; 
        border:2px solid grey; z-index:9999; font-size:14px;
        background-color:rgba(14, 17, 23, 0.85); color: white;
        padding: 10px; border-radius: 8px; backdrop-filter: blur(4px);">
        <b style="margin-bottom: 5px; display: block;">Regiones</b>
    '''
    for r, style in region_styles.items():
        legend_html += f'<div style="margin-bottom:3px;"><i class="fa fa-circle" style="color:{style["hex"]}; margin-right: 5px;"></i> {r}</div>'
    legend_html += '</div>'
    
    m.get_root().html.add_child(folium.Element(legend_html))

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

def create_category_distribution_chart(df):
    """
    Crea un gráfico de dona mostrando la distribución de estudios por categoría.
    """
    if 'Category' not in df.columns:
        return None
        
    counts = df['Category'].value_counts().reset_index()
    counts.columns = ['Categoría', 'Cantidad']
    
    import plotly.express as px
    
    fig = px.pie(
        counts, 
        names='Categoría', 
        values='Cantidad', 
        hole=0.6,
        template="plotly_dark",
        color='Categoría',
        color_discrete_map={
            'Estudio AAA (Conglomerado Mayor)': '#3498db',
            'Estudio AA / Destacado': '#9b59b6',
            'Estudio Independiente / Otro': '#95a5a6'
        }
    )
    
    fig.update_traces(
        textposition='inside', 
        textinfo='percent+label',
        marker=dict(line=dict(color='#0E1117', width=2))
    )
    
    fig.update_layout(
        margin=dict(t=20, l=20, r=20, b=20),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    
    return fig

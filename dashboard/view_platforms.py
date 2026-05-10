import streamlit as st
import pandas as pd
import sqlite3
import base64
from pathlib import Path
import config
from charts_platforms import create_roadmap_timeline, PLATFORM_COLORS

@st.cache_data(show_spinner="Cargando plataformas...")
def load_platforms_data():
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        df = pd.read_sql_query("SELECT * FROM platforms", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def render_platforms_module():
    st.title("🕹️ Evolución y Roadmap de Consolas")
    st.markdown("Explora la histórica 'Guerra de Consolas'. Cada carril representa a un fabricante. El tamaño de los puntos indica el éxito comercial (ventas globales).")
    
    df_platforms = load_platforms_data()
    if df_platforms.empty:
        st.warning("⚠️ No se encontraron datos. Ejecuta primero 'python scripts/etl_platforms.py'")
        return

    st.markdown("### Línea de Tiempo Histórica")
    fig = create_roadmap_timeline(df_platforms)
    
    # Capturamos clics en el gráfico
    evento = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
    
    st.divider()
    
    # Si el usuario hace clic en una consola
    if evento and "selection" in evento and evento["selection"].get("points"):
        punto = evento["selection"]["points"][0]
        nombre_consola = punto["customdata"][0]
        
        # Filtramos los datos de esa consola específica
        consola_data = df_platforms[df_platforms['name'] == nombre_consola].iloc[0]
        color_marca = PLATFORM_COLORS.get(consola_data['manufacturer'], "white")
        
        c1, c2 = st.columns([1, 1.5])
        
        with c1:
            # Validamos que tengamos nombre de imagen y no sea nulo (NaN)
            img_name = consola_data['local_image']
            if pd.notna(img_name) and bool(img_name):
                # Usar config.CONSOLES_DIR si existe, si no, construir la ruta localmente para evitar problemas de caché de Streamlit
                consoles_dir = getattr(config, 'CONSOLES_DIR', Path(__file__).resolve().parent / "assets" / "consoles")
                img_path = consoles_dir / str(img_name)
                if img_path.exists():
                    # Mostramos la imagen con el logo o render 3D de la consola
                    with open(img_path, "rb") as img_file:
                        encoded = base64.b64encode(img_file.read()).decode()
                    st.markdown(f'<div style="text-align:center; padding: 20px; background-color: rgba(255,255,255,0.05); border-radius: 15px;"><img src="data:image/png;base64,{encoded}" style="max-width: 100%; max-height: 250px; drop-shadow: 0 10px 15px rgba(0,0,0,0.5);"></div>', unsafe_allow_html=True)
                else:
                    st.info("Imagen no disponible.")
            else:
                st.info("Imagen no disponible.")
                
        with c2:
            st.markdown(f"<h2 style='color:{color_marca};'>{consola_data['name']}</h2>", unsafe_allow_html=True)
            st.markdown(f"**Fabricante:** {consola_data['manufacturer']}")
            st.markdown(f"**Lanzamiento:** {consola_data['release_year']}")
            st.markdown(f"**Generación:** {consola_data['generation']}")
            st.metric("Ventas Totales", f"{consola_data['units_sold_millions']} Millones")
    else:
        st.info("👆 Haz clic en cualquier consola en la línea de tiempo superior para ver sus detalles.")
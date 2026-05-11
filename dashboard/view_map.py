import streamlit as st
from streamlit_folium import st_folium
from charts import create_interactive_map

def render_map_module(filtered_df):
    """
    Renderiza el módulo del mapa interactivo con los datos filtrados.
    """
    st.subheader("Mapa de Ubicación de Estudios de Videojuegos")

    # --- Panel de Métricas Dinámicas ---
    # Es crucial comprobar que el DataFrame no esté vacío 
    if not filtered_df.empty:
        total_estudios = len(filtered_df)
        total_paises = filtered_df['Country'].nunique()
        
        # Calculamos la región dominante de forma segura
        region_top = filtered_df['Region'].mode()
        region_principal = region_top[0] if not region_top.empty else "N/A"

        # Mostramos las métricas en 3 columnas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Estudios", total_estudios)
        with col2:
            st.metric("Países Diferentes", total_paises)
        with col3:
            st.metric("Región Principal", region_principal)
        
        st.divider() # Un pequeño separador visual antes del mapa
    else:
        st.info("No se encontraron estudios con los filtros actuales.")
    # ------------------------------------------

    # Creamos y renderizamos el mapa (con nuestro parche de rendimiento)
    folium_map = create_interactive_map(filtered_df)
    st_folium(
        folium_map, 
        use_container_width=True, 
        height=650,               
        returned_objects=[]       
    )
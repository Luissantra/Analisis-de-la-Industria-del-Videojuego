import streamlit as st
import plotly.express as px
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

        # Métricas de Tiers
        aaa_count = len(filtered_df[filtered_df['studio_tier'] == 'AAA'])
        aa_count = len(filtered_df[filtered_df['studio_tier'] == 'AA'])
        indie_count = len(filtered_df[filtered_df['studio_tier'] == 'Indie'])

        # Mostramos las métricas en 6 columnas
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric("Total Estudios", total_estudios)
        with col2:
            st.metric("Países", total_paises)
        with col3:
            st.metric("Región Principal", region_principal)
        with col4:
            st.metric("🏢 AAA", aaa_count)
        with col5:
            st.metric("🎯 AA", aa_count)
        with col6:
            st.metric("🎮 Indie", indie_count)
        
        st.divider() # Un pequeño separador visual antes del mapa
        
        # Creamos y renderizamos el mapa (con nuestro parche de rendimiento)
        folium_map = create_interactive_map(filtered_df)
        st_folium(
            folium_map, 
            use_container_width=True, 
            height=650,               
            returned_objects=[]       
        )
        
        st.divider() # Separador visual después del mapa
        
        # Donut Chart for Tiers
        col_blank, col_chart, col_blank2 = st.columns([1, 2, 1])
        with col_chart:
            tier_data = filtered_df['studio_tier'].value_counts().reset_index()
            tier_data.columns = ['Tier', 'Count']
            
            color_map = {
                'AAA': '#dc3545', 
                'AA': '#ffc107', 
                'Indie': '#28a745'
            }
            
            fig = px.pie(
                tier_data, 
                values='Count', 
                names='Tier', 
                hole=0.6,
                color='Tier',
                color_discrete_map=color_map,
                title="Distribución de Tiers"
            )
            fig.update_traces(textinfo='percent', textfont_size=14)
            fig.update_layout(
                showlegend=True, 
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                margin=dict(t=30, b=0, l=0, r=0),
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)
            
    else:
        st.info("No se encontraron estudios con los filtros actuales.")
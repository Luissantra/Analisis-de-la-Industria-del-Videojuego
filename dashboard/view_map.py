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
        
        # Calculamos la región dominante de forma segura, excluyendo 'Other' y 'N/A'
        valid_regions = filtered_df[~filtered_df['Region'].isin(['Other', 'N/A'])]
        region_top = valid_regions['Region'].mode()
        region_principal = region_top[0] if not region_top.empty else "N/A"

        # Métricas de Tiers
        aaa_count = len(filtered_df[filtered_df['studio_tier'] == 'AAA'])
        aa_count = len(filtered_df[filtered_df['studio_tier'] == 'AA'])
        indie_count = len(filtered_df[filtered_df['studio_tier'] == 'Indie'])

        st.markdown("""
        <style>
        .metric-card {
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            border-left: 4px solid #1f77b4;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .metric-card.aaa { border-left-color: #dc3545; }
        .metric-card.aa { border-left-color: #ffc107; }
        .metric-card.indie { border-left-color: #28a745; }
        .metric-value { font-size: 24px; font-weight: bold; margin: 0; }
        .metric-label { font-size: 13px; color: #aaa; margin: 0; text-transform: uppercase; letter-spacing: 1px; }
        </style>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.markdown(f'<div class="metric-card"><p class="metric-value">{total_estudios}</p><p class="metric-label">🗺️ Total</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><p class="metric-value">{total_paises}</p><p class="metric-label">🌍 Países</p></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card"><p class="metric-value" style="font-size:18px; padding-top:4px;">{region_principal}</p><p class="metric-label">📍 Top Región</p></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="metric-card aaa"><p class="metric-value" style="color:#dc3545;">{aaa_count}</p><p class="metric-label">🏢 AAA</p></div>', unsafe_allow_html=True)
        with col5:
            st.markdown(f'<div class="metric-card aa"><p class="metric-value" style="color:#ffc107;">{aa_count}</p><p class="metric-label">🎯 AA</p></div>', unsafe_allow_html=True)
        with col6:
            st.markdown(f'<div class="metric-card indie"><p class="metric-value" style="color:#28a745;">{indie_count}</p><p class="metric-label">🎮 Indie</p></div>', unsafe_allow_html=True)
        
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
        
        # --- Panel de Visualizaciones Analíticas ---
        col_left, col_right = st.columns(2)
        
        with col_left:
            tier_data = filtered_df['studio_tier'].value_counts().reset_index()
            tier_data.columns = ['Tier', 'Count']
            
            color_map = {
                'AAA': '#dc3545', 
                'AA': '#ffc107', 
                'Indie': '#28a745',
                'No Clasificado': '#6c757d'
            }
            
            fig = px.treemap(
                tier_data, 
                path=['Tier'], 
                values='Count',
                color='Tier',
                color_discrete_map=color_map,
                title="Distribución de Tiers de Estudios"
            )
            fig.update_traces(textinfo="label+value+percent entry")
            fig.update_layout(
                margin=dict(t=40, b=10, l=10, r=10),
                height=350,
                template="plotly_dark"
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with col_right:
            region_data = filtered_df['Region'].value_counts().reset_index()
            region_data.columns = ['Region', 'Count']
            
            region_color_map = {
                'North America': '#800080',
                'South America': '#28a745',
                'Europe': '#007bff',
                'Asia': '#dc3545',
                'Africa': '#fd7e14',
                'Oceania': '#5f9ea0',
                'Other': '#6c757d',
                'N/A': '#444444'
            }
            
            fig_region = px.pie(
                region_data,
                names='Region',
                values='Count',
                hole=0.6,
                color='Region',
                color_discrete_map=region_color_map,
                title="Estudios por Región Geográfica"
            )
            
            fig_region.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate="<b>%{label}</b><br>Estudios: %{value}<br>Porcentaje: %{percent}<extra></extra>",
                marker=dict(line=dict(color='#0E1117', width=2))
            )
            
            # Anotación central con el total de estudios
            total_region_estudios = region_data['Count'].sum()
            fig_region.add_annotation(
                text=f"<span style='font-family: system-ui, Arial, sans-serif; font-size:26px; font-weight:bold; color:white;'>{total_region_estudios}</span><br><span style='font-family: system-ui, Arial, sans-serif; font-size:11px; color:#aaa; font-weight:500; letter-spacing: 0.5px;'>ESTUDIOS</span>",
                x=0.5, y=0.5,
                showarrow=False,
                align="center"
            )
            
            fig_region.update_layout(
                margin=dict(t=40, b=10, l=10, r=10),
                height=350,
                template="plotly_dark",
                showlegend=False
            )
            st.plotly_chart(fig_region, use_container_width=True)
            
    else:
        st.info("No se encontraron estudios con los filtros actuales.")
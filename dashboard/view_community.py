import streamlit as st
import pandas as pd
from model_corporate import get_all_corporate_data
from charts_community import plot_critic_vs_user, plot_top_controversies

def render_community_module():
    st.title("🗣️ Comunidad y Recepción (Review Bombing)")
    st.markdown("Analiza el fenómeno del **Review Bombing**, identificando aquellos títulos donde la recepción de los usuarios discrepa severamente de la nota otorgada por la crítica profesional.")
    
    # Cargamos la capa semántica usando la función existente del módulo corporativo
    df = get_all_corporate_data()
    
    # Validación de seguridad defensiva
    if 'Review_Bombing_Index' not in df.columns:
        st.warning("⚠️ Faltan métricas de la comunidad. Asegúrate de haber ejecutado `python scripts/etl_games.py` y luego `python scripts/build_db.py`.")
        return
    
    # --- Zona de Filtros ---
    st.markdown("#### Filtros de Análisis")
    col1, col2 = st.columns(2)
    
    with col1:
        # Extraer conglomerados únicos descartando nulos
        publishers = ["Todos"] + sorted(df['Parent'].dropna().unique().tolist())
        selected_publisher = st.selectbox("Filtrar por Conglomerado (Publisher):", publishers)
        
    with col2:
        # Permitir al usuario ajustar el umbral mínimo de reviews para ver datos más o menos de nicho
        min_reviews = st.number_input("Mínimo de reseñas de usuarios (Ratings Count):", min_value=0, max_value=5000, value=10, step=10)

    # --- Aplicación de Filtros ---
    df_filtered = df.copy()
    if selected_publisher != "Todos":
        df_filtered = df_filtered[df_filtered['Parent'] == selected_publisher]
        
    df_filtered['Ratings_Count'] = pd.to_numeric(df_filtered['Ratings_Count'], errors='coerce').fillna(0)
    df_filtered = df_filtered[df_filtered['Ratings_Count'] >= min_reviews]
    
    st.divider()
    
    # --- Renderizado de Gráficos ---
    st.markdown("### 📊 Crítica Profesional vs. Usuarios")
    fig_scatter = plot_critic_vs_user(df_filtered)
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    st.divider()
    
    st.markdown("### 🧨 Top Controversias (Review Bombing)")
    fig_bar = plot_top_controversies(df_filtered)
    st.plotly_chart(fig_bar, use_container_width=True)
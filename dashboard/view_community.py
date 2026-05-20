import streamlit as st
import pandas as pd
from model_corporate import get_all_games_data
from charts_community import plot_critic_vs_user, plot_top_controversies, plot_top_acclaimed, plot_social_traction, create_playtime_scatter_chart
import streamlit.components.v1 as components

def render_community_module():
    st.title("🗣️ Comunidad y Recepción")
    st.markdown("Analiza la recepción de la audiencia, el perfil demográfico y el fenómeno del **Review Bombing**, identificando qué títulos conectan realmente con el público general.")
    
    # Cargamos la capa de juegos individuales
    df = get_all_games_data()
    
    # Validación de seguridad defensiva
    if 'rawg_rating' not in df.columns:
        st.warning("⚠️ Faltan métricas de la comunidad. Asegúrate de haber ejecutado el pipeline de extracción de juegos de RAWG.")
        return
    
    # --- Zona de Filtros ---
    st.markdown("#### Filtros de Análisis")
    col1, col2 = st.columns(2)
    
    with col1:
        # Extraer conglomerados únicos descartando nulos
        publishers = ["Todos"] + sorted(df['conglomerate'].dropna().unique().tolist())
        selected_publisher = st.selectbox("Filtrar por Conglomerado (Publisher):", publishers)
        
    with col2:
        # Permitir al usuario ajustar el umbral mínimo de reviews para ver datos más o menos de nicho
        min_reviews = st.number_input("Mínimo de reseñas de usuarios (Ratings Count):", min_value=0, max_value=5000, value=10, step=10)

    # --- Aplicación de Filtros ---
    df_filtered = df.copy()
    if selected_publisher != "Todos":
        df_filtered = df_filtered[df_filtered['conglomerate'] == selected_publisher]
        
    df_filtered['rawg_ratings_count'] = pd.to_numeric(df_filtered['rawg_ratings_count'], errors='coerce').fillna(0)
    df_filtered = df_filtered[df_filtered['rawg_ratings_count'] >= min_reviews]
    
    st.divider()
    
    # --- Renderizado de Gráficos ---
    st.markdown("### 👥 Capítulo 1: Compromiso y Engagement de los Jugadores")
    st.markdown("""
    ¿Cuánto tiempo invierten los jugadores en sus títulos favoritos? El tiempo de juego medio (Playtime) 
    cruza la duración con la calidad media, evaluando el valor real de diversión percibido.
    """)
    fig_play = create_playtime_scatter_chart(df_filtered)
    if fig_play: st.plotly_chart(fig_play, use_container_width=True)

    st.divider()
    
    st.markdown("### 🎭 Capítulo 2: El Espectro de la Crítica")
    st.markdown("""
    ¿Coincide la prensa con los jugadores? En este gráfico buscamos la correlación. Los títulos en la diagonal superior 
    son éxitos unánimes, mientras que los alejados de la línea revelan discrepancias de criterio.
    """)
    fig_scatter = plot_critic_vs_user(df_filtered)
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    st.divider()
    
    st.markdown("### 🧨 Capítulo 3: Review Bombing y Controversias")
    st.markdown("""
    Aquí visualizamos las mayores brechas negativas. Títulos donde la nota de los usuarios es significativamente 
    inferior a la de la crítica, a menudo señal de controversias técnicas, políticas o de monetización.
    """)
    fig_bar = plot_top_controversies(df_filtered)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    st.markdown("### 🌟 Capítulo 4: Aclamación Popular")
    st.markdown("""
    El "Vox Populi". Juegos que, independientemente de su presupuesto o nota de prensa, han logrado conectar 
    profundamente con la comunidad.
    """)
    fig_acclaim = plot_top_acclaimed(df_filtered)
    st.plotly_chart(fig_acclaim, use_container_width=True)

    st.divider()

    st.markdown("### 🚀 Capítulo 5: Hype y Tracción Social")
    st.markdown("""
    ¿Cuánto se habla de estos juegos verdaderamente? Comparamos el volumen de interacción real 
    de los usuarios frente a la nota de calidad, identificando fenómenos virales.
    """)
    
    fig_social = plot_social_traction(df_filtered)
    if fig_social:
        st.plotly_chart(fig_social, use_container_width=True)
        
    st.write("---")
    st.info("💡 **Análisis de Tendencias Externas (Google Trends)**")
    st.markdown("Configura los parámetros para evaluar la fuerza de la marca a nivel de interés de búsqueda global.")
    
    # Controles Interactivos para Google Trends
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        default_kw = "videojuegos" if selected_publisher == "Todos" else selected_publisher
        search_term = st.text_input("Palabra clave a analizar (Google Trends):", value=default_kw)
    with col_t2:
        timeframe_option = st.selectbox(
            "Periodo temporal de análisis:",
            ["Últimos 12 meses", "Últimos 5 años", "Últimos 15 años", "Histórico (Desde 2004)"],
            index=2
        )
        
    # Mapeo de opciones de tiempo de Google Trends
    timeframe_map = {
        "Últimos 12 meses": "today 12-m",
        "Últimos 5 años": "today 5-y",
        "Últimos 15 años": "today 15-y",
        "Histórico (Desde 2004)": "all"
    }
    timeframe_value = timeframe_map[timeframe_option]
    
    html_code = f"""
    <script type="text/javascript" src="https://ssl.gstatic.com/trends_nrtr/3720_RC01/embed_loader.js"></script>
    <script type="text/javascript">
      trends.embed.renderExploreWidget("TIMESERIES", {{"comparisonItem":[{{"keyword":"{search_term}","geo":"","time":"{timeframe_value}"}}],"category":0,"property":""}}, {{"exploreQuery":"q={search_term}&date={timeframe_value}","guestPath":"https://trends.google.es:443/trends/embed/"}});
    </script>
    """
    components.html(html_code, height=450)
import streamlit as st
import pandas as pd
import sqlite3
import os
import config
from model_corporate import get_all_games_data
from charts_community import plot_critic_vs_user, plot_top_controversies, plot_top_acclaimed, plot_social_traction, create_playtime_scatter_chart
import streamlit.components.v1 as components

def render_community_module():
    st.title("🗣️ Comunidad y Recepción")
    st.markdown("Analiza la recepción de la audiencia, el perfil demográfico y el fenómeno del **Review Bombing**, identificando qué títulos conectar realmente con el público general.")
    
    tab_analytics, tab_timeline = st.tabs(["📊 Análisis Estadístico", "📅 Cronología de Hitos (Timeline)"])
    
    with tab_analytics:
        # Cargamos la capa de juegos individuales
        df = get_all_games_data()
        
        # Validación de seguridad defensiva
        if 'rawg_rating' not in df.columns:
            st.warning("⚠️ Faltan métricas de la comunidad. Asegúrate de haber ejecutado el pipeline de extracción de juegos de RAWG.")
        else:
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
            
    with tab_timeline:
        st.subheader("📅 Cronología de los Grandes Hitos del Siglo XXI")
        st.markdown("""
        Explora los títulos más influyentes y mejor valorados de la industria año por año. 
        Este timeline interactivo recupera las carátulas y valoraciones de los juegos más relevantes de cada época.
        """)
        
        # Filtros de rango de año para el timeline
        year_range = st.slider("Selecciona el rango de años a mostrar:", 2000, 2026, (2012, 2026), key="timeline_years_slider")
        
        # Consultar la DB
        try:
            conn = sqlite3.connect(config.DATABASE_PATH)
            query = """
                SELECT 
                    g.rawg_id,
                    g.title,
                    g.release_year,
                    g.metacritic,
                    g.rawg_rating,
                    g.rawg_ratings_count,
                    dr.rawg_name as studio,
                    c.name as conglomerate
                FROM games g
                JOIN developers_rawg dr ON g.developer_rawg_id = dr.rawg_developer_id
                JOIN notable_studios s ON dr.studio_id = s.id
                JOIN conglomerates c ON s.parent_id = c.id
                WHERE g.release_year >= ? AND g.release_year <= ? AND g.metacritic IS NOT NULL
                ORDER BY g.release_year DESC, g.metacritic DESC, g.rawg_ratings_count DESC
            """
            df_timeline = pd.read_sql_query(query, conn, params=(year_range[0], year_range[1]))
            conn.close()
        except Exception as e:
            st.error(f"Error consultando el catálogo de la línea de tiempo: {e}")
            df_timeline = pd.DataFrame()
            
        if not df_timeline.empty:
            # Obtener los top 2 juegos por año
            df_timeline_top = df_timeline.groupby('release_year').head(2)
            
            # Ordenar por año descendente, metacritic descendente
            df_timeline_top = df_timeline_top.sort_values(by=['release_year', 'metacritic'], ascending=[False, False])
            
            # CSS y HTML para renderizar el Timeline
            timeline_html = """
            <style>
            .timeline-container {
                padding: 20px;
                position: relative;
                max-width: 900px;
                margin: 0 auto;
                font-family: 'Inter', 'Helvetica Neue', sans-serif;
            }
            .timeline-container::after {
                content: '';
                position: absolute;
                width: 4px;
                background-color: rgba(255, 255, 255, 0.1);
                top: 0;
                bottom: 0;
                left: 50%;
                margin-left: -2px;
                border-radius: 2px;
            }
            .timeline-item {
                padding: 10px 40px;
                position: relative;
                background-color: inherit;
                width: 50%;
                box-sizing: border-box;
            }
            .timeline-item::after {
                content: '';
                position: absolute;
                width: 16px;
                height: 16px;
                right: -8px;
                background-color: #0e1117;
                border: 3px solid #e60012;
                top: 25px;
                border-radius: 50%;
                z-index: 1;
                transition: all 0.3s ease;
            }
            .left {
                left: 0;
            }
            .right {
                left: 50%;
            }
            .right::after {
                left: -8px;
            }
            .timeline-content {
                padding: 15px;
                background: rgba(255, 255, 255, 0.02);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.05);
                position: relative;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
                display: flex;
                gap: 15px;
                transition: all 0.3s ease;
            }
            .timeline-content:hover {
                transform: translateY(-4px);
                box-shadow: 0 8px 25px rgba(230, 0, 18, 0.25);
                border-color: rgba(230, 0, 18, 0.4);
                background: rgba(255, 255, 255, 0.04);
            }
            .timeline-item:hover::after {
                background-color: #e60012;
                box-shadow: 0 0 10px #e60012;
                transform: scale(1.2);
            }
            .timeline-year {
                font-size: 26px;
                font-weight: 900;
                color: #e60012;
                margin: 0 0 8px 0;
                font-family: 'Outfit', 'Inter', sans-serif;
                text-shadow: 0 0 10px rgba(230, 0, 18, 0.2);
            }
            .timeline-img {
                width: 90px;
                height: 120px;
                object-fit: cover;
                border-radius: 8px;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            .timeline-details {
                flex-grow: 1;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            }
            .timeline-title {
                margin: 0 0 4px 0;
                font-size: 16px;
                color: #fff;
                font-weight: 700;
            }
            .timeline-studio {
                font-size: 12px;
                color: #b3b3b3;
                margin-bottom: 6px;
            }
            .timeline-badges {
                display: flex;
                gap: 8px;
                align-items: center;
            }
            .meta-badge {
                background-color: rgba(0, 0, 0, 0.6);
                border: 1px solid #4caf50;
                color: #4caf50;
                padding: 2px 6px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            .rating-badge {
                background-color: rgba(0, 0, 0, 0.6);
                border: 1px solid #2196f3;
                color: #2196f3;
                padding: 2px 6px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            @media screen and (max-width: 768px) {
                .timeline-container::after {
                    left: 31px;
                }
                .timeline-item {
                    width: 100%;
                    padding-left: 70px;
                    padding-right: 25px;
                }
                .timeline-item::after {
                    left: 22px;
                }
                .right {
                    left: 0%;
                }
            }
            </style>
            <div class="timeline-container">
            """
            
            # Importar la función de caché de carátulas de view_hall_of_fame
            from view_hall_of_fame import get_game_cover_url
            
            # Construir items
            left_side = True
            for idx, row in df_timeline_top.iterrows():
                side_class = "left" if left_side else "right"
                left_side = not left_side
                
                title = row['title']
                year = row['release_year']
                rawg_id = row['rawg_id']
                studio = row['studio']
                metacritic = row['metacritic']
                rating = row['rawg_rating'] or "N/A"
                
                cover_url = get_game_cover_url(rawg_id, title)
                
                # HTML para cada item de la cronología
                timeline_html += f"""
                <div class="timeline-item {side_class}">
                    <div class="timeline-content">
                        <img class="timeline-img" src="{cover_url}" alt="{title}">
                        <div class="timeline-details">
                            <div>
                                <div class="timeline-year">{year}</div>
                                <div class="timeline-title">{title}</div>
                                <div class="timeline-studio">🏢 {studio}</div>
                            </div>
                            <div class="timeline-badges">
                                <span class="meta-badge">⭐ {metacritic}</span>
                                <span class="rating-badge">👍 {rating}</span>
                            </div>
                        </div>
                    </div>
                </div>
                """
                
            timeline_html += "</div>"
            # Limpiar indentación de cada línea para evitar que el analizador de Markdown de Streamlit
            # interprete el texto con espacios iniciales como un bloque de código.
            clean_timeline_html = "\n".join([line.strip() for line in timeline_html.split("\n")])
            st.markdown(clean_timeline_html, unsafe_allow_html=True)
        else:
            st.info("ℹ️ No hay datos de lanzamientos para el período seleccionado.")
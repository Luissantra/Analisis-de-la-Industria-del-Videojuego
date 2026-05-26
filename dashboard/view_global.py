import streamlit as st
import pandas as pd
import sqlite3
import json
import config
from pathlib import Path
from model_corporate import get_all_games_data
from charts_corporate import create_genre_and_score_chart
from charts_global import create_intersectoral_chart, create_genre_race_chart

def get_industry_comparison_data() -> pd.DataFrame:
    """
    Carga los datos estáticos de comparación de industrias desde el JSON configurado.
    """
    json_path = config.BASE_DIR / "config_data" / "industry_comparison.json"
    if not json_path.exists():
        return pd.DataFrame()
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return pd.DataFrame(data)
    except Exception as e:
        config.get_logger("view_global").error(f"Error al cargar datos intersectoriales: {e}")
        return pd.DataFrame()

def get_genre_evolution_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Procesa el catálogo de juegos para obtener la evolución anual por género.
    Explota los géneros separados por coma y los cuenta por año.
    """
    if 'genres' not in df.columns or 'release_year' not in df.columns:
        return pd.DataFrame()
        
    df_clean = df.copy()
    # Limpiamos nulos de año y géneros
    df_clean = df_clean.dropna(subset=['release_year', 'genres'])
    df_clean = df_clean[df_clean['genres'] != '']
    df_clean = df_clean[df_clean['genres'] != 'Desconocido']
    
    # Explotamos la columna de géneros
    df_clean['Genre_List'] = df_clean['genres'].astype(str).str.split(', ')
    df_exploded = df_clean.explode('Genre_List')
    
    # Agrupamos por año y género
    df_grouped = df_exploded.groupby(['release_year', 'Genre_List']).size().reset_index(name='Game_Count')
    df_grouped.rename(columns={'release_year': 'Año', 'Genre_List': 'Género', 'Game_Count': 'Cantidad de Juegos'}, inplace=True)
    
    # Filtramos años razonables (desde 1980 hasta 2026) para evitar datos erróneos
    df_grouped = df_grouped[(df_grouped['Año'] >= 1980) & (df_grouped['Año'] <= 2026)]
    
    return df_grouped

def get_genre_color_map(df: pd.DataFrame) -> dict:
    """
    Genera un diccionario que asocia cada género único a un color específico
    para garantizar la coherencia cromática en todas las gráficas de la vista global.
    """
    if 'genres' not in df.columns:
        return {}
    
    # Extraer géneros únicos ignorando nulos y 'Desconocido'
    df_clean = df.dropna(subset=['genres'])
    df_clean = df_clean[df_clean['genres'] != '']
    df_clean = df_clean[df_clean['genres'] != 'Desconocido']
    
    genres_series = df_clean['genres'].astype(str).str.split(', ').explode()
    unique_genres = sorted(genres_series.unique().tolist())
    
    import plotly.express as px
    import itertools
    # Usar exclusivamente la paleta Vivid (cíclica) para garantizar saturación 
    # y permitir que el texto blanco sea legible.
    colors = px.colors.qualitative.Vivid
    
    return dict(zip(unique_genres, itertools.cycle(colors)))

def get_sales_race_data() -> pd.DataFrame:
    """
    Procesa el acumulado de ventas históricas año a año por género a partir de la tabla game_sales.
    Rellena huecos con 0 e interpola (pasos de 0.2 años) para una animación fluida en el Bar Chart Race de Plotly.
    """
    import sqlite3
    import numpy as np
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        query = """
            SELECT release_year AS Año, genre AS Género, SUM(total_sales) AS Ventas
            FROM game_sales
            WHERE total_sales > 0 AND genre IS NOT NULL AND genre != '' AND release_year BETWEEN 1990 AND 2020
            GROUP BY release_year, genre
        """
        df_sales = pd.read_sql_query(query, conn)
        conn.close()
    except Exception as e:
        config.get_logger("view_global").error(f"Error al cargar ventas para race chart: {e}")
        return pd.DataFrame()
        
    if df_sales.empty:
        return pd.DataFrame()
        
    # Rango de años válidos para el gráfico animado de ventas reales de VGChartz
    min_year = 1990
    max_year = 2020
    
    # 1. Crear un producto cartesiano de Años x Géneros para no tener saltos de frames
    all_years = range(min_year, max_year + 1)
    all_genres = df_sales['Género'].unique()
    idx = pd.MultiIndex.from_product([all_years, all_genres], names=['Año', 'Género'])
    
    df_filled = df_sales.set_index(['Año', 'Género']).reindex(idx, fill_value=0).reset_index()
    
    # Calcular la suma acumulada por género
    df_filled = df_filled.sort_values(by=['Género', 'Año'])
    df_filled['Ventas_Acumuladas'] = df_filled.groupby('Género')['Ventas'].cumsum()
    
    # 2. Interpolación lineal para conseguir una animación mucho más suave
    # Generamos pasos de 0.2 años (1990.0, 1990.2, 1990.4...)
    interp_years = np.arange(min_year, max_year + 0.2, 0.2)
    interp_years = np.round(interp_years, 1)  # Redondeamos a un decimal
    idx_interp = pd.MultiIndex.from_product([interp_years, all_genres], names=['Año', 'Género'])
    
    # Preparamos el dataframe vacío con los años interpolados
    df_interp = pd.DataFrame(index=idx_interp).reset_index()
    
    # Mezclamos los datos acumulados reales
    df_merged = pd.merge(df_interp, df_filled[['Año', 'Género', 'Ventas_Acumuladas']], on=['Año', 'Género'], how='left')
    
    # Para cada género, interpolamos los valores faltantes en los frames decimales
    df_merged['Ventas_Acumuladas'] = df_merged.groupby('Género')['Ventas_Acumuladas'].transform(
        lambda x: x.interpolate(method='linear')
    )
    
    # Aseguramos el orden de tiempo y aplicamos ffill/bfill por si los extremos quedan en NaN
    df_merged = df_merged.sort_values(by=['Año', 'Género'])
    df_merged['Ventas_Acumuladas'] = df_merged.groupby('Género')['Ventas_Acumuladas'].ffill().bfill()
    
    return df_merged

def create_genre_evolution_chart(df_grouped: pd.DataFrame, color_map: dict = None):
    if df_grouped.empty:
        return None
        
    df_grouped = df_grouped.sort_values(by='Año')
    
    # Calcular el total de juegos por género para ordenar la pila de abajo hacia arriba (mayor a menor volumen)
    genre_order = df_grouped.groupby('Género')['Cantidad de Juegos'].sum().sort_values(ascending=False).index.tolist()
    
    import plotly.express as px
    fig = px.area(
        df_grouped,
        x='Año',
        y='Cantidad de Juegos',
        color='Género',
        line_group='Género',
        category_orders={'Género': genre_order},
        color_discrete_map=color_map if color_map else {},
        color_discrete_sequence=px.colors.qualitative.Vivid if not color_map else None,
        template="plotly_dark"
    )
    
    fig.update_layout(
        margin=dict(t=20, l=10, r=10, b=20),
        xaxis_title="Año de Lanzamiento",
        yaxis_title="Cantidad de Títulos Lanzados",
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5
        )
    )
    
    fig.update_traces(
        hovertemplate="<b>%{y}</b> juegos<extra></extra>"
    )
    
    return fig

def render_global_vision_module():
    st.title("🌍 Visión Global de la Industria")
    st.markdown("""
    Esta dimensión ofrece una perspectiva histórica, estratégica y macroeconómica del mercado de los videojuegos. 
    Analizamos desde su posición comparativa frente a otros sectores del entretenimiento hasta la evolución de sus géneros principales.
    """)
    
    df_games_all = get_all_games_data()
    
    if df_games_all.empty:
        st.warning("⚠️ No se encontraron juegos en la base de datos. Por favor, ejecuta el pipeline primero.")
        return
        
    # Extraemos el mapa de colores unificado para que todas las gráficas de género sean coherentes
    color_map = get_genre_color_map(df_games_all)
        
    # --- Capítulo 1: Comparativa Intersectorial (Macro Industria) ---
    st.subheader("Capítulo 1: El Gigante del Entretenimiento")
    st.markdown("""
    Esta visualización pone en perspectiva el tamaño de la industria global del videojuego en comparación con otros 
    grandes pilares del entretenimiento: la taquilla de cine (Box Office), la música grabada y el streaming de vídeo (OTT). 
    Los ingresos están expresados en miles de millones de dólares (USD Bn).
    """)
    
    df_industry = get_industry_comparison_data()
    if not df_industry.empty:
        fig_intersectoral = create_intersectoral_chart(df_industry)
        st.plotly_chart(fig_intersectoral, width="stretch")
    else:
        st.info("ℹ️ No se pudieron cargar los datos de comparación intersectorial.")
        
    st.markdown("<br><hr style='border: 1px solid rgba(255,255,255,0.1);'><br>", unsafe_allow_html=True)
    
    # --- Capítulo 2: La Evolución Histórica de los Géneros ---
    st.subheader("Capítulo 2: La Evolución Histórica de los Géneros")
    st.markdown("""
    El gráfico de áreas acumuladas (Stacked Area Chart) ilustra cómo han cambiado las tendencias de desarrollo 
    y la oferta de lanzamientos por género desde 1980 hasta la actualidad.
    *Tip: Haz doble clic en un género en la leyenda para aislarlo, o un solo clic para desactivarlo.*
    """)
    
    df_evolution = get_genre_evolution_data(df_games_all)
    fig_area = create_genre_evolution_chart(df_evolution, color_map=color_map)
    
    if fig_area:
        st.plotly_chart(fig_area, width="stretch")
    else:
        st.info("ℹ️ No hay suficientes datos para generar el gráfico de evolución de géneros.")
        
    st.markdown("<br><hr style='border: 1px solid rgba(255,255,255,0.1);'><br>", unsafe_allow_html=True)
        
    # --- Capítulo 3: Matriz de Portfolio Global ---
    st.subheader("Capítulo 3: Matriz de Portfolio Global")
    st.markdown("""
    Analizamos la relación entre el **volumen de producción** (cantidad de títulos) y la **calidad crítica media por género** (Metacritic). 
    El tamaño de las burbujas es proporcional al volumen total de títulos.
    Las zonas superiores representan géneros con alta aclamación crítica, mientras que el eje horizontal muestra el volumen de oferta comercial.
    """)
    
    fig_portfolio = create_genre_and_score_chart(df_games_all, color_map=color_map)
    
    if fig_portfolio:
        st.plotly_chart(fig_portfolio, width="stretch")
    else:
        st.info("ℹ️ Ejecuta `etl_games_rawg.py` para habilitar gráficos de géneros y valoraciones.")
        
    st.markdown("<br><hr style='border: 1px solid rgba(255,255,255,0.1);'><br>", unsafe_allow_html=True)

    # --- Capítulo 4: Carrera de los Géneros (Bar Chart Race) ---
    st.subheader("Capítulo 4: La Carrera Comercial por el Dominio (Bar Chart Race)")
    st.markdown("""
    Esta simulación animada muestra cómo los diferentes géneros han competido por el **volumen total acumulado de ventas (en millones de copias)** 
    desde 1990 hasta 2020 (datos reales de VGChartz). Observa cómo la industria se expande comercialmente y cómo ciertos géneros 
    alcanzan picos comerciales de masas en momentos clave de la historia de los videojuegos.
    """)
    
    df_race = get_sales_race_data()
    if not df_race.empty:
        fig_race = create_genre_race_chart(df_race, color_map=color_map)
        st.plotly_chart(fig_race, width="stretch")
    else:
        st.info("ℹ️ No hay datos de ventas de VGChartz suficientes para animar la carrera de géneros.")

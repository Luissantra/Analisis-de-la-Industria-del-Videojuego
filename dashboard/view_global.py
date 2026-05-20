import streamlit as st
import pandas as pd
import sqlite3
import config
from pathlib import Path
from model_corporate import get_all_games_data
from charts_corporate import create_genre_and_score_chart
import plotly.express as px

def get_genre_evolution_data(df):
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

def create_genre_evolution_chart(df_grouped):
    if df_grouped.empty:
        return None
        
    df_grouped = df_grouped.sort_values(by='Año')
    
    fig = px.area(
        df_grouped,
        x='Año',
        y='Cantidad de Juegos',
        color='Género',
        line_group='Género',
        color_discrete_sequence=px.colors.qualitative.Vivid,
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
    Esta dimensión ofrece una perspectiva histórica y estratégica del mercado de los videojuegos. 
    Analizamos la evolución de los géneros a lo largo de las décadas y la especialización productiva general.
    """)
    
    df_games_all = get_all_games_data()
    
    if df_games_all.empty:
        st.warning("⚠️ No se encontraron juegos en la base de datos. Por favor, ejecuta el pipeline primero.")
        return
        
    # --- Pestañas o Secciones ---
    tab1, tab2 = st.tabs(["📈 Tendencias y Géneros (Línea de Tiempo)", "🎯 Matriz de Portfolio y Especialización"])
    
    with tab1:
        st.subheader("Capítulo 1: La Evolución de los Géneros")
        st.markdown("""
        El gráfico de áreas acumuladas (Stacked Area Chart) ilustra cómo han cambiado las preferencias de desarrollo 
        y los lanzamientos por género desde 1980 hasta la actualidad. 
        *Tip: Haz doble clic en un género en la leyenda para aislarlo, o un solo clic para desactivarlo.*
        """)
        
        df_evolution = get_genre_evolution_data(df_games_all)
        fig_area = create_genre_evolution_chart(df_evolution)
        
        if fig_area:
            st.plotly_chart(fig_area, use_container_width=True)
        else:
            st.info("ℹ️ No hay suficientes datos para generar el gráfico de evolución de géneros.")
            
    with tab2:
        st.subheader("Capítulo 2: Matriz de Portfolio Global")
        st.markdown("""
        Analizamos la relación entre el **volumen de producción** (cantidad de títulos) y la **calidad media por género** (Metacritic). 
        El tamaño de las burbujas es proporcional al volumen total de títulos.
        Las zonas superiores representan géneros de alta calidad (aclamación crítica), mientras que el eje horizontal muestra la popularidad comercial o volumen.
        """)
        
        fig_portfolio = create_genre_and_score_chart(df_games_all)
        
        if fig_portfolio:
            st.plotly_chart(fig_portfolio, use_container_width=True)
        else:
            st.info("ℹ️ Ejecuta `etl_games_rawg.py` para habilitar gráficos de géneros y valoraciones.")

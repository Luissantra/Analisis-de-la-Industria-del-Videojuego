import streamlit as st
import pandas as pd
import sqlite3
import sys
import os
from pathlib import Path

# Agregamos el directorio raíz al path para que Python encuentre el módulo 'config'
root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

# Importamos nuestros módulos de visualización
from view_map import render_map_module
from view_market import render_market_module
from view_corporate import render_corporate_module
from view_platforms import render_platforms_module
from view_community import render_community_module


# Page Configuration
st.set_page_config(
    page_title="Análisis de la Industria del Videojuego",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Data loading and caching

def load_data(query):
    if not os.path.exists(config.DATABASE_PATH):
        st.error(f"Error crítico: No se encontró la base de datos en {config.DATABASE_PATH}")
        st.info("Por favor, ejecuta el pipeline primero: python main.py")
        st.stop()
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error cargando datos de la base de datos: {e}")
        st.stop()

# Dimensión geográfica (mapa)
@st.cache_data(show_spinner="Cargando datos del mapa... Esto puede tardar unos segundos.")
def load_geo_data():
  """
  Carga el dataset preparado para el análisis.
  """

  query = """
    SELECT 
        sl."Studio Name",
        sl.City,
        sl.Country,
        sl.Lat,
        sl.Lon,
        sl.Region,
        sl.studio_tier,
        sl.is_notable,
        d.Parent,
        d.Acquisition_Year,
        d.Top_Game,
        d.Metacritic,
        d.Logo_URL,
        d.Genres
    FROM studio_locations sl
    LEFT JOIN dim_studios_corporate d ON LOWER(sl."Studio Name") = LOWER(d."Studio Name")
  """
  return load_data(query)

# Dimensión de mercado (bolsa)
@st.cache_data(show_spinner="Cargando lista de activos...")
def get_market_assets():
    """
    Consulta a la BBDD y separa dinámicamente empresas de índices (benchmarks)
    basándose en la columna 'Category'.
    """
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        # Traemos nombres y categorías
        query = 'SELECT DISTINCT "Company Name", "Category" FROM stock_prices'
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Filtramos dinámicamente: Si la categoría contiene la palabra "Índice", es un benchmark
        indices = df[df['Category'].str.contains('Índice', case=False, na=False)]['Company Name'].tolist()
        empresas = df[~df['Category'].str.contains('Índice', case=False, na=False)]['Company Name'].tolist()
        
        # Las ordenamos alfabéticamente
        return sorted(empresas), sorted(indices)
    except Exception as e:
        return [], []

@st.cache_data(show_spinner="Consultando datos financieros...")
def load_dynamic_market_data(selected_companies):
    """
    Carga el histórico de mercado SOLO para las empresas que el usuario ha seleccionado.
    """
    if not selected_companies:
        return pd.DataFrame() # Si no hay selección, devolvemos un dataframe vacío rápido
        
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        
        # Construimos la consulta SQL con placeholders para evitar inyecciones y problemas de formato
        placeholders = ','.join(['?'] * len(selected_companies))
        query = f'SELECT * FROM stock_prices WHERE "Company Name" IN ({placeholders})'
        
        # Pasamos la lista de empresas como parámetros
        df = pd.read_sql_query(query, conn, params=selected_companies)
        df['Date'] = pd.to_datetime(df['Date']) 
        conn.close()
        
        return df
    except Exception as e:
        return pd.DataFrame()
    
  

# Cargamos los datos
df_studios = load_geo_data()




# --- Navegación Principal ---
st.title("🎮 Análisis de la Industria del Videojuego")
menu = st.sidebar.radio(
    "Selecciona una dimensión:",
    ["Mapa de estudios", "Evolución de plataformas", "Análisis de mercado", "Estructura corporativa", "Comunidad y Recepción"]
)

st.sidebar.divider()

# --- Módulo 1: Dimensión Geográfica (Mapa de Estudios) ---
if menu == "Mapa de estudios":
    st.sidebar.header("Filtros de Ubicación")

    country_list = ["Todos"] + sorted(df_studios['Country'].dropna().unique().tolist())
    selected_country = st.sidebar.selectbox("Selecciona un país:", country_list)
    search_query = st.sidebar.text_input("Buscar por nombre de estudio:")

    st.sidebar.header("Filtros de Clasificación")
    only_notables = st.sidebar.toggle("Solo estudios notables", value=False)
    
    tier_options = ["AAA", "AA", "Indie"]
    selected_tiers = st.sidebar.multiselect("Nivel del estudio (Tier):", options=tier_options, default=tier_options)

    # Aplicamos filtros
    filtered_df = df_studios.copy()
    if selected_country != "Todos":
        filtered_df = filtered_df[filtered_df['Country'] == selected_country]
    if search_query:
        filtered_df = filtered_df[filtered_df['Studio Name'].str.contains(search_query, case=False, na=False)]
    if only_notables:
        filtered_df = filtered_df[filtered_df['is_notable'] == 1]
        if selected_tiers:
            filtered_df = filtered_df[filtered_df['studio_tier'].isin(selected_tiers)]
    else:
        if selected_tiers:
            filtered_df = filtered_df[
                (filtered_df['studio_tier'].isin(selected_tiers)) |
                (filtered_df['is_notable'] != 1) |
                (filtered_df['studio_tier'] == 'No Clasificado')
            ]

    # Renderizamos el mapa
    render_map_module(filtered_df)
    
    # Colocamos la tabla justo debajo del mapa 
    st.divider()
    with st.expander("📊 Ver directorio completo en formato tabla"):
        # Adaptative columns
        if only_notables:
            display_cols = ["Studio Name", "City", "Country", "studio_tier", "Parent", "Top_Game", "Metacritic", "Genres"]
        else:
            display_cols = ["Studio Name", "City", "Country", "Region", "studio_tier"]
            
        st.dataframe(filtered_df[display_cols], use_container_width=True, hide_index=True)

# --- Módulo Nuevo: Evolución de Plataformas ---
elif menu == "Evolución de plataformas":
    render_platforms_module()

# --- Módulo 2: Dimensión de Mercado (Análisis Financiero) ---
elif menu == "Análisis de mercado":
    st.title("Análisis Financiero de Gigantes del Sector")
    
    solo_empresa, indices = get_market_assets()
    
    if not solo_empresa:
        st.warning("No se encontraron datos financieros. Ejecuta el pipeline de datos primero.")
    else:
        default_companies = [c for c in ["Nintendo Co., Ltd.", "Electronic Arts", "Microsoft Corporation"] if c in solo_empresa]
        
        # OJO: Estos controles ahora están en la pantalla principal de este módulo, 
        # pero también podrías pasarlos al sidebar si quisieras. Por ahora los dejamos aquí.
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_companies = st.multiselect("Empresas a comparar:", options=solo_empresa, default=default_companies)
        with col2:
            selected_benchmark = st.selectbox("Benchmark (opcional):", options=["Ninguno"] + indices)

        query_companies = selected_companies.copy()
        if selected_benchmark != "Ninguno":
            query_companies.append(selected_benchmark)
        
        df_market = load_dynamic_market_data(query_companies)
        render_market_module(df_market, selected_companies, benchmark=selected_benchmark)

# --- Módulo 3: Dimensión Corporativa ---
elif menu == "Estructura corporativa":
    render_corporate_module()

# --- Módulo 4: Comunidad y Recepción ---
elif menu == "Comunidad y Recepción":
    render_community_module()
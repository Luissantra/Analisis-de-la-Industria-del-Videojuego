import sqlite3
import pandas as pd
import streamlit as st
import sys
import os
from pathlib import Path
from contextlib import closing

root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

def run_query(query: str, params: tuple | list = (), use_pyarrow: bool = True) -> pd.DataFrame:
    """Helper genérico para ejecutar consultas de lectura de forma segura y optimizada."""
    dtype_backend = "pyarrow" if use_pyarrow else "numpy_nullable"
    
    if not os.path.exists(config.DATABASE_PATH):
        st.error(f"Error crítico: No se encontró la base de datos en {config.DATABASE_PATH}")
        st.info("Por favor, ejecuta el pipeline primero: python main.py")
        st.stop()
        
    try:
        with closing(sqlite3.connect(config.DATABASE_PATH)) as conn:
            return pd.read_sql_query(query, conn, params=params, dtype_backend=dtype_backend)
    except Exception as e:
        st.error(f"Error cargando datos de la base de datos: {e}")
        return pd.DataFrame()

# --- Dimensión Geográfica (Mapa) ---
@st.cache_data(show_spinner="Cargando datos del mapa... Esto puede tardar unos segundos.")
def load_geo_data() -> pd.DataFrame:
    """Carga el dataset preparado para el análisis."""
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
    return run_query(query)

# --- Dimensión de Mercado Financiero ---
@st.cache_data(show_spinner="Cargando lista de activos...")
def get_market_assets() -> tuple[list[str], list[str]]:
    """Consulta a la BBDD y separa dinámicamente empresas de índices (benchmarks)."""
    query = 'SELECT DISTINCT "Company Name", "Category" FROM stock_prices'
    df = run_query(query)
    
    if df.empty:
        return [], []
        
    indices = df[df['Category'].str.contains('Índice', case=False, na=False)]['Company Name'].tolist()
    empresas = df[~df['Category'].str.contains('Índice', case=False, na=False)]['Company Name'].tolist()
    
    return sorted(empresas), sorted(indices)

@st.cache_data(show_spinner="Consultando datos financieros...")
def load_dynamic_market_data(selected_companies: list[str]) -> pd.DataFrame:
    """Carga el histórico de mercado SOLO para las empresas que el usuario ha seleccionado."""
    if not selected_companies:
        return pd.DataFrame()
        
    placeholders = ','.join(['?'] * len(selected_companies))
    query = f'SELECT * FROM stock_prices WHERE "Company Name" IN ({placeholders})'
    
    df = run_query(query, params=selected_companies)
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        
    return df

# --- Dimensión Evolución de Plataformas ---
@st.cache_data(show_spinner="Cargando plataformas...")
def load_platforms_data() -> pd.DataFrame:
    return run_query("SELECT * FROM platforms")

# --- Dimensión Corporativa ---
def _get_base_query(where_clause: str = "") -> str:
    return f"""
        SELECT *
        FROM dim_studios_corporate
        {where_clause}
    """

@st.cache_data(show_spinner="Cargando estructura corporativa global...")
def get_all_corporate_data() -> pd.DataFrame:
    """Carga toda la matriz de estudios y juegos (Vista Macro)."""
    return run_query(_get_base_query(""))

@st.cache_data(show_spinner="Consultando datos del conglomerado...")
def get_conglomerate_data(parent_name: str) -> pd.DataFrame:
    """Consulta optimizada a la DB filtrando solo el conglomerado seleccionado."""
    return run_query(_get_base_query("WHERE Parent = ?"), params=(parent_name,))

@st.cache_data(show_spinner="Cargando catálogo completo de juegos...")
def get_all_games_data() -> pd.DataFrame:
    """Carga todos los juegos individuales de la base de datos."""
    return run_query("SELECT * FROM v_games_detail")

@st.cache_data(show_spinner="Calculando eventos de mercado...")
def get_dynamic_market_events() -> list[dict]:
    """Genera hitos dinámicos (adquisiciones y juegos top) para la gráfica financiera."""
    COMPANY_MAP = {
        "Microsoft Gaming (Xbox, ZeniMax, Activision Blizzard)": "Microsoft Corporation",
        "Sony Interactive Entertainment (PlayStation Studios)": "Sony Group Corporation",
        "Tencent": "Tencent Holdings",
        "Nintendo": "Nintendo Co., Ltd.",
        "Electronic Arts (EA)": "Electronic Arts",
        "Take-Two Interactive": "Take-Two Interactive",
        "Ubisoft": "Ubisoft Entertainment",
        "Sega Sammy": "Sega Sammy"
    }

    with closing(sqlite3.connect(config.DATABASE_PATH)) as conn:
        query_acq = "SELECT c.name as parent, s.acquisition_year, s.name as studio FROM notable_studios s JOIN conglomerates c ON s.parent_id = c.id WHERE s.acquisition_year IS NOT NULL AND s.acquisition_year != '' AND s.acquisition_year != 'Por definir'"
        df_acq = pd.read_sql_query(query_acq, conn)
        
        events = []
        for _, row in df_acq.iterrows():
            if row['parent'] in COMPANY_MAP:
                year_str = str(row['acquisition_year'])
                date_str = f"{year_str}-01-01" if len(year_str) == 4 else year_str
                events.append({"date": date_str, "company": COMPANY_MAP[row['parent']], "event": f"Adquisición: {row['studio']}"})

        query_games = "SELECT c.name as parent, g.release_date, g.title, g.metacritic FROM games g JOIN developers_rawg dr ON g.developer_rawg_id = dr.rawg_developer_id JOIN notable_studios s ON dr.studio_id = s.id JOIN conglomerates c ON s.parent_id = c.id WHERE g.metacritic >= 92 AND g.release_date IS NOT NULL AND g.release_date != ''"
        df_games = pd.read_sql_query(query_games, conn)
        
        for _, row in df_games.iterrows():
            if row['parent'] in COMPANY_MAP:
                events.append({"date": str(row['release_date']), "company": COMPANY_MAP[row['parent']], "event": f"Hit Lanzado: {row['title']} (Meta: {row['metacritic']})"})
                
    return events
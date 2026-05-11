import sqlite3
import pandas as pd
import streamlit as st
import sys
from pathlib import Path

root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

def _get_base_query(where_clause=""):
    return f"""
        SELECT *
        FROM dim_studios_corporate
        {where_clause}
    """

@st.cache_data(show_spinner="Cargando estructura corporativa global...")
def get_all_corporate_data():
    """Carga toda la matriz de estudios y juegos (Vista Macro)."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    # Usar dtype_backend='pyarrow' optimiza drásticamente el uso de memoria en Streamlit
    df = pd.read_sql_query(
        _get_base_query(""), 
        conn, 
        dtype_backend="pyarrow"
    )
    conn.close()
    return df

@st.cache_data(show_spinner="Consultando datos del conglomerado...")
def get_conglomerate_data(parent_name):
    """Consulta optimizada a la DB filtrando solo el conglomerado seleccionado."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    df = pd.read_sql_query(
        _get_base_query("WHERE Parent = ?"), 
        conn, 
        params=(parent_name,),
        dtype_backend="pyarrow"
    )
    conn.close()
    return df

@st.cache_data(show_spinner="Cargando catálogo completo de juegos...")
def get_all_games_data():
    """Carga todos los juegos individuales de la base de datos."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM v_games_detail", 
        conn, 
        dtype_backend="pyarrow"
    )
    conn.close()
    return df

@st.cache_data(show_spinner="Calculando eventos de mercado...")
def get_dynamic_market_events():
    """Genera hitos dinámicos (adquisiciones y juegos top) para la gráfica financiera."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    
    # Mapeo de nombres largos de la DB a los tickers de stock_prices
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

    # 1. Adquisiciones
    query_acq = """
    SELECT c.name as parent, s.acquisition_year, s.name as studio
    FROM notable_studios s 
    JOIN conglomerates c ON s.parent_id = c.id 
    WHERE s.acquisition_year IS NOT NULL 
    AND s.acquisition_year != '' 
    AND s.acquisition_year != 'Por definir'
    """
    df_acq = pd.read_sql_query(query_acq, conn)
    
    events = []
    for _, row in df_acq.iterrows():
        parent_name = row['parent']
        if parent_name in COMPANY_MAP:
            # Si solo es el año, asumimos 1 de Enero
            year_str = str(row['acquisition_year'])
            if len(year_str) == 4:
                date_str = f"{year_str}-01-01"
            else:
                date_str = year_str
                
            events.append({
                "date": date_str,
                "company": COMPANY_MAP[parent_name],
                "event": f"Adquisición: {row['studio']}"
            })

    # 2. Top Games (Metacritic >= 92 para evitar demasiados eventos)
    query_games = """
    SELECT c.name as parent, g.release_date, g.title, g.metacritic
    FROM games g
    JOIN developers_rawg dr ON g.developer_rawg_id = dr.rawg_developer_id
    JOIN notable_studios s ON dr.studio_id = s.id
    JOIN conglomerates c ON s.parent_id = c.id
    WHERE g.metacritic >= 92 AND g.release_date IS NOT NULL AND g.release_date != ''
    """
    df_games = pd.read_sql_query(query_games, conn)
    
    for _, row in df_games.iterrows():
        parent_name = row['parent']
        if parent_name in COMPANY_MAP:
            events.append({
                "date": str(row['release_date']),
                "company": COMPANY_MAP[parent_name],
                "event": f"Hit Lanzado: {row['title']} (Meta: {row['metacritic']})"
            })
            
    conn.close()
    return events
import sqlite3
import pandas as pd
import streamlit as st
import sys
from pathlib import Path

root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

def _clean_corporate_df(df):
    """Centraliza la limpieza de datos nulos para mantener consistencia visual."""
    df['City'] = df['City'].fillna('N/A')
    df['Country'] = df['Country'].fillna('N/A')
    df['Top_Game'] = df['Top_Game'].fillna('No registrado')
    df['Acquisition_Year'] = df['Acquisition_Year'].fillna('No registrado')
    df['Genres'] = df['Genres'].fillna('Desconocido')
    return df

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
    df = pd.read_sql_query(_get_base_query(""), conn)
    conn.close()
    return _clean_corporate_df(df)

@st.cache_data(show_spinner="Consultando datos del conglomerado...")
def get_conglomerate_data(parent_name):
    """Consulta optimizada a la DB filtrando solo el conglomerado seleccionado."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    df = pd.read_sql_query(_get_base_query("WHERE Parent = ?"), conn, params=(parent_name,))
    conn.close()
    return _clean_corporate_df(df)
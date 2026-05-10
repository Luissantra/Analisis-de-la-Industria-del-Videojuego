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
        SELECT 
            c.name as Parent,
            s.name as "Studio Name",
            CASE 
                WHEN sl.City IS NOT NULL AND sl.City != 'Unknown City' THEN sl.City
                WHEN s.city IS NOT NULL AND s.city != '' AND s.city != 'N/A' THEN s.city
                ELSE 'N/A'
            END as City,
            CASE 
                WHEN sl.Country IS NOT NULL AND sl.Country != 'Unknown Country' THEN sl.Country
                WHEN s.country IS NOT NULL AND s.country != '' AND s.country != 'N/A' THEN s.country
                ELSE 'N/A'
            END as Country,
            s.acquisition_year as Acquisition_Year,
            COALESCE(g.name, 'No registrado') as Top_Game,
            COALESCE(g.genres, 'Desconocido') as Genres,
            g.metacritic as Metacritic
        FROM conglomerates c
        JOIN notable_studios s ON c.id = s.parent_id
        -- Cruce inteligente (Fuzzy Match) para ignorar sufijos como "(Nintendo)" o sucursales
        LEFT JOIN studio_locations sl 
            ON s.name = sl."Studio Name" 
            OR s.name LIKE sl."Studio Name" || ' %'
            OR sl."Studio Name" LIKE s.name || ' %'
        LEFT JOIN games_metadata g ON s.id = g.studio_id
        {where_clause}
        GROUP BY c.name, s.name
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
    df = pd.read_sql_query(_get_base_query("WHERE c.name = ?"), conn, params=(parent_name,))
    conn.close()
    return _clean_corporate_df(df)
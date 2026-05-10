import sqlite3
import pandas as pd
import sys
from pathlib import Path

# Agregamos el directorio raíz
root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

def run_audit():
    print("🔍 Iniciando Auditoría de la Base de Datos...\n")
    
    if not config.DATABASE_PATH.exists():
        print("❌ Error: No se encontró la base de datos SQLite.")
        return
        
    conn = sqlite3.connect(config.DATABASE_PATH)
    
    # --- 1. AUDITORÍA CORPORATIVA (Años de Adquisición) ---
    print("🏢 --- DIMENSIÓN CORPORATIVA ---")
    df_studios = pd.read_sql_query("SELECT name, parent_id, acquisition_year FROM notable_studios", conn)
    total_studios = len(df_studios)
    
    # Consideramos nulos, vacíos o textos por defecto como "faltantes"
    faltan_anio = df_studios[
        df_studios['acquisition_year'].isna() | 
        df_studios['acquisition_year'].isin(['No registrado', 'N/A', 'Desconocido', ''])
    ]
    
    print(f"Total Estudios Notables: {total_studios}")
    print(f"Estudios sin Año de Adquisición: {len(faltan_anio)} ({(len(faltan_anio)/total_studios)*100:.1f}%)")
    if not faltan_anio.empty:
        print("Ejemplos sin año:", ", ".join(faltan_anio['name'].head(5).tolist()), "...\n")

    # --- 2. AUDITORÍA DE VIDEOJUEGOS (API RAWG) ---
    print("🎮 --- DIMENSIÓN VIDEOJUEGOS (METADATOS) ---")
    df_games = pd.read_sql_query("SELECT name, name_api, metacritic, genres FROM games_metadata", conn)
    total_games = len(df_games)
    
    faltan_api = df_games[df_games['name_api'] == 'No encontrado']
    faltan_meta = df_games[df_games['metacritic'].isna()]
    faltan_genero = df_games[df_games['genres'].isin(['Desconocido', None, ''])]
    
    print(f"Total Juegos Registrados: {total_games}")
    print(f"Juegos no encontrados en RAWG: {len(faltan_api)} ({(len(faltan_api)/total_games)*100:.1f}%)")
    print(f"Juegos sin nota Metacritic: {len(faltan_meta)} ({(len(faltan_meta)/total_games)*100:.1f}%)")
    print(f"Juegos sin Género: {len(faltan_genero)} ({(len(faltan_genero)/total_games)*100:.1f}%)")
    
    if not faltan_meta.empty:
        print("Ejemplos sin Metacritic:", ", ".join(faltan_meta['name'].head(5).tolist()), "...\n")

    # --- 3. AUDITORÍA GEOGRÁFICA ---
    print("🌍 --- DIMENSIÓN GEOGRÁFICA ---")
    try:
        df_geo = pd.read_sql_query("SELECT * FROM studio_locations", conn)
        total_geo = len(df_geo)
        geo_unknown = df_geo[df_geo['Country'].str.contains('UNKNOWN', case=False, na=False)]
        
        print(f"Total Estudios en Mapa: {total_geo}")
        print(f"Estudios con País Desconocido: {len(geo_unknown)} ({(len(geo_unknown)/total_geo)*100:.1f}%)")
    except Exception as e:
        print(f"No se pudo analizar el mapa: {e}")

    print("\n-------------------------------------------------")
    print("💡 PRÓXIMOS PASOS SUGERIDOS:")
    if len(faltan_meta) > 0:
        print("1. Limpiar manualmente los nombres de los juegos en 'apply_games_data.py' (ej. quitar 'Franquicia') para que RAWG los encuentre.")
    if len(faltan_anio) > 0:
        print("2. Crear un scraper automatizado a Wikipedia (o ChatGPT prompt) para rellenar los años de adquisición faltantes.")
    
    conn.close()

if __name__ == "__main__":
    run_audit()
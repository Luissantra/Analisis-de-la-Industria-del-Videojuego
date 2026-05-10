import pandas as pd
from sqlalchemy import create_engine, text
import os
import sys
from pathlib import Path

# Agregamos el directorio raíz al path para que Python encuentre el módulo 'config'
root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

def build_database():
    """
    Construye la base de datos a partir de los dataset CSVs procesados.
    """
    print("Construyendo la base de datos...")

    # Crear una conexión a la base de datos SQLite usando SQLAlchemy
    engine = create_engine(f'sqlite:///{config.DATABASE_PATH}')
    print("Conexión con la base de datos establecida.")

    # --- Tabla GameDevMap (Estudios) ---
    if os.path.exists(config.GAMEDEVMAP_CSV):
        print(f" - Cargando datos desde {config.GAMEDEVMAP_CSV}...")
        df_geo = pd.read_csv(config.GAMEDEVMAP_CSV)
        
        # Escribimos el DataFrame a la base de datos
        df_geo.to_sql('studio_locations', con=engine, if_exists='replace', index=False)
        print(" [OK] Tabla 'studio_locations' creada y datos insertados.")
    else:
        print(f" [Advertencia] No se encontró {config.GAMEDEVMAP_CSV}. Ejecuta el pipeline de ETL primero.")
        
    # --- Tabla Master Data Management (Estudios IGDB) ---
    MDM_CSV = config.PROCESSED_DATA_DIR / "mdm" / "master_studios.csv"
    if os.path.exists(MDM_CSV):
        print(f" - Cargando Master Data desde {MDM_CSV}...")
        df_mdm = pd.read_csv(MDM_CSV)
        df_mdm.to_sql('master_studios', con=engine, if_exists='replace', index=False)
        print(" [OK] Tabla 'master_studios' creada y datos insertados.")
    else:
        print(f" [Advertencia] No se encontró {MDM_CSV}. Ejecuta scripts/etl_igdb.py primero.")

    # --- Tabla Stock_Prices (Bolsa) ---
    if os.path.exists(config.MARKETDATA_CSV):
        print(f" - Cargando datos desde {config.MARKETDATA_CSV}...")
        df_market = pd.read_csv(config.MARKETDATA_CSV)
        
        df_market.to_sql('stock_prices', con=engine, if_exists='replace', index=False)
        print(" [OK] Tabla 'stock_prices' creada y datos insertados.")
    else:
        print(f" [Advertencia] No se encontró {config.MARKETDATA_CSV}. Ejecuta la extracción de mercado primero.")

    # --- Consolidación para el Dashboard (Capa Semántica) ---
    print(" - Creando tabla consolidada 'dim_studios_corporate' para el Dashboard...")
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS dim_studios_corporate;"))
        connection.execute(text("""
            CREATE TABLE dim_studios_corporate AS
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
                sl.Lat as Lat,
                sl.Lon as Lon,
                sl.Region as Region,
                COALESCE(SUBSTR(m.igdb_start_date, 1, 4), s.acquisition_year) as Acquisition_Year,
                COALESCE(m.igdb_top_game, g.name, 'No registrado') as Top_Game,
                COALESCE(g.genres, 'Desconocido') as Genres,
                COALESCE(m.igdb_top_game_rating, g.metacritic) as Metacritic,
                m.igdb_logo_url as Logo_URL,
                m.igdb_description as Description
            FROM conglomerates c
            JOIN notable_studios s ON c.id = s.parent_id
            LEFT JOIN master_studios m ON s.id = m.internal_id
            LEFT JOIN studio_locations sl ON s.name = sl."Studio Name"
            LEFT JOIN games_metadata g ON s.id = g.studio_id
            GROUP BY c.name, s.name;
        """))
    print(" [OK] Capa semántica consolidada.")

if __name__ == "__main__":
    build_database()
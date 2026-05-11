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
    # NOTA: Ahora `studio_locations` se carga directamente a SQLite desde `etl_gameDevMap.py`.
    print(" [OK] Tabla 'studio_locations' es gestionada directamente por el ETL.")

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
                sl.Region,
                COALESCE(
                    strftime('%Y', datetime(m.igdb_start_date, 'unixepoch')), 
                    s.acquisition_year, 
                    'No registrado') AS Acquisition_Year,
                COALESCE(m.igdb_top_game, 'No registrado') AS Top_Game,
                COALESCE(SUBSTR(gm.released, 1, 4), 'N/A') AS Game_Year,
                COALESCE(gm.genres, 'Desconocido') AS Genres,
                COALESCE(gm.metacritic, m.igdb_top_game_rating, 'N/A') AS Metacritic,
                COALESCE(gm.user_rating, 0) AS User_Rating,
                COALESCE(gm.ratings_count, 0) AS Ratings_Count,
                (COALESCE(gm.user_rating, 0) * 20) AS User_Score_100,
                CASE WHEN COALESCE(gm.metacritic, m.igdb_top_game_rating) IS NOT NULL AND gm.user_rating IS NOT NULL 
                     THEN COALESCE(gm.metacritic, m.igdb_top_game_rating) - (gm.user_rating * 20) 
                     ELSE NULL END as Review_Bombing_Index,
                COALESCE(m.igdb_logo_url, '') as Logo_URL,
                COALESCE(m.igdb_description, 'Sin descripción') as Description
            FROM conglomerates c
            JOIN notable_studios s ON c.id = s.parent_id
            LEFT JOIN master_studios m ON s.id = m.internal_id
            LEFT JOIN studio_locations sl ON s.name = sl."Studio Name"
            LEFT JOIN games_metadata gm ON s.id = gm.id
            GROUP BY c.name, s.name;
        """))
        
        # Creación de índices para optimizar las consultas en Streamlit
        connection.execute(text('CREATE INDEX idx_dim_parent ON dim_studios_corporate(Parent);'))
        connection.execute(text('CREATE INDEX idx_dim_country ON dim_studios_corporate(Country);'))
        connection.execute(text('CREATE INDEX idx_stock_company ON stock_prices("Company Name");'))
        connection.execute(text('CREATE INDEX idx_stock_date ON stock_prices(Date);'))
    print(" [OK] Capa semántica consolidada.")

if __name__ == "__main__":
    build_database()
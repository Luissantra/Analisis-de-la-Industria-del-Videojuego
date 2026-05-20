import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config
from scripts.etl_vgchartz import run_vgchartz_etl

log = config.get_logger("build_db")

def build_database():
    """
    Construye la base de datos a partir de los dataset CSVs procesados.
    Crea la capa semántica consolidada para el dashboard.
    """
    log.info("Construyendo la base de datos...")

    engine = create_engine(f"sqlite:///{config.DATABASE_PATH}")
    log.info("Conexión con la base de datos establecida.")

    # ─── Tabla Master Data Management (Estudios IGDB) ───────────────
    MDM_CSV = config.PROCESSED_DATA_DIR / "mdm" / "master_studios.csv"
    if os.path.exists(MDM_CSV):
        log.info("Cargando Master Data desde %s...", MDM_CSV)
        df_mdm = pd.read_csv(MDM_CSV)
        df_mdm.to_sql("master_studios", con=engine, if_exists="replace", index=False)
        log.info("Tabla 'master_studios' creada y datos insertados.")
    else:
        log.warning("No se encontró %s. Ejecuta scripts/etl_igdb.py primero.", MDM_CSV)

    # ─── Tabla Stock_Prices (Bolsa) ─────────────────────────────────
    if os.path.exists(config.MARKETDATA_CSV):
        log.info("Cargando datos de mercado desde %s...", config.MARKETDATA_CSV)
        df_market = pd.read_csv(config.MARKETDATA_CSV)
        df_market.to_sql("stock_prices", con=engine, if_exists="replace", index=False)
        log.info("Tabla 'stock_prices' creada y datos insertados.")
    else:
        log.warning("No se encontró %s. Ejecuta la extracción de mercado primero.", config.MARKETDATA_CSV)

    # ─── Consolidación para el Dashboard (Capa Semántica) ──────────
    log.info("Creando tabla consolidada 'dim_studios_corporate' para el Dashboard...")
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS dim_studios_corporate;"))
        connection.execute(text("DROP VIEW IF EXISTS v_games_detail;"))
        
        # Elimina la antigua tabla de metadata si aún existe
        connection.execute(text("DROP TABLE IF EXISTS games_metadata;"))

        # Construcción de la capa corporativa (1 fila por notable_studio)
        connection.execute(text("""
            CREATE TABLE dim_studios_corporate AS
            SELECT 
                c.name AS Parent,
                s.name AS "Studio Name",
                COALESCE(s.city, 'N/A') AS City,
                COALESCE(s.country, 'N/A') AS Country,
                sl.Lat, 
                sl.Lon, 
                sl.Region,
                CASE
                    WHEN m.igdb_company_size >= 6 THEN 'AAA'
                    WHEN m.igdb_company_size >= 4 THEN 'AA'
                    WHEN m.igdb_company_size IS NOT NULL AND m.igdb_company_size < 4 THEN 'Indie'
                    WHEN c.name IN ('Sony Interactive Entertainment (PlayStation Studios)', 
                                     'Microsoft Gaming (Xbox, ZeniMax, Activision Blizzard)', 
                                     'Nintendo', 'Electronic Arts (EA)', 'Take-Two Interactive',
                                     'Ubisoft', 'Tencent', 'Sega Sammy', 'Epic Games', 
                                     'Warner Bros. Games', 'Krafton') THEN 'AAA'
                    WHEN c.name = 'Independent & Other Publishers' THEN 'Indie'
                    ELSE 'AA'
                END AS studio_tier,
                COALESCE(
                    CASE 
                        WHEN m.igdb_start_date > 0 AND m.igdb_start_date < 2147483647 
                        THEN strftime('%Y', datetime(m.igdb_start_date, 'unixepoch'))
                        ELSE NULL 
                    END,
                    s.acquisition_year,
                    'No registrado'
                ) AS Acquisition_Year,
                m.igdb_logo_url AS Logo_URL,
                COALESCE(m.igdb_description, 'Sin descripción') AS Description,
                dr.rawg_developer_id,
                COALESCE(dr.games_count, 0) AS Total_Games,
                
                -- Campos agregados desde la nueva tabla games
                COALESCE(agg.avg_metacritic, 'N/A') AS avg_metacritic,
                COALESCE(agg.avg_user_rating, 'N/A') AS avg_user_rating,
                COALESCE(agg.total_ratings_count, 0) AS total_ratings_count,
                COALESCE(agg.top_game_title, m.igdb_top_game, 'No registrado') AS Top_Game,
                COALESCE(agg.top_game_metacritic, m.igdb_top_game_rating, 'N/A') AS top_game_metacritic,
                COALESCE(agg.primary_genres, 'Desconocido') AS Genres,
                
                -- Retrocompatibilidad (mantener nombres de columnas viejas si el dashboard las usa directamente)
                COALESCE(agg.top_game_title, m.igdb_top_game, 'No registrado') AS Top_Game_Legacy,
                COALESCE(agg.avg_metacritic, m.igdb_top_game_rating, 'N/A') AS Metacritic,
                COALESCE(agg.avg_user_rating, 0) AS User_Rating,
                COALESCE(agg.total_ratings_count, 0) AS Ratings_Count,
                
                -- Métricas calculadas para Review Bombing
                (COALESCE(agg.avg_user_rating, 0) * 20) AS User_Score_100,
                CASE 
                    WHEN agg.avg_metacritic IS NOT NULL AND agg.avg_user_rating IS NOT NULL 
                    THEN agg.avg_metacritic - (agg.avg_user_rating * 20) 
                    ELSE NULL 
                END AS Review_Bombing_Index
                
            FROM conglomerates c
            JOIN notable_studios s ON c.id = s.parent_id
            LEFT JOIN master_studios m ON s.id = m.internal_id
            LEFT JOIN studio_locations sl ON s.name = sl."Studio Name" COLLATE NOCASE
            LEFT JOIN developers_rawg dr ON s.id = dr.studio_id
            LEFT JOIN (
                SELECT 
                    g.developer_rawg_id,
                    ROUND(AVG(g.metacritic), 1) AS avg_metacritic,
                    ROUND(AVG(g.rawg_rating), 2) AS avg_user_rating,
                    SUM(g.rawg_ratings_count) AS total_ratings_count,
                    
                    -- Obtener el título del juego con mayor metacritic
                    (SELECT g2.title FROM games g2 
                     WHERE g2.developer_rawg_id = g.developer_rawg_id 
                     AND g2.metacritic IS NOT NULL
                     ORDER BY g2.metacritic DESC LIMIT 1) AS top_game_title,
                     
                    (SELECT MAX(g3.metacritic) FROM games g3 
                     WHERE g3.developer_rawg_id = g.developer_rawg_id) AS top_game_metacritic,
                     
                    -- Obtener el género primario (el más común para este dev)
                    (SELECT g4.genres FROM games g4 
                     WHERE g4.developer_rawg_id = g.developer_rawg_id AND g4.genres != ''
                     GROUP BY g4.genres ORDER BY COUNT(*) DESC LIMIT 1) AS primary_genres
                     
                FROM games g
                -- Solo contar juegos que tengan al menos algún rating
                WHERE (g.metacritic > 0 OR g.rawg_rating > 0)
                GROUP BY g.developer_rawg_id
            ) agg ON dr.rawg_developer_id = agg.developer_rawg_id;
        """))

        # Propagate studio_tier and is_notable to studio_locations
        try:
            # Check if columns exist
            res = connection.execute(text("PRAGMA table_info(studio_locations)"))
            cols = [row[1] for row in res]
            if 'studio_tier' not in cols:
                connection.execute(text("ALTER TABLE studio_locations ADD COLUMN studio_tier TEXT DEFAULT 'No Clasificado'"))
            if 'is_notable' not in cols:
                connection.execute(text("ALTER TABLE studio_locations ADD COLUMN is_notable INTEGER DEFAULT 0"))
            
            # Update values
            connection.execute(text("""
                UPDATE studio_locations
                SET studio_tier = (
                    SELECT dc.studio_tier FROM dim_studios_corporate dc
                    WHERE LOWER(dc."Studio Name") = LOWER(studio_locations."Studio Name")
                ),
                is_notable = 1
                WHERE EXISTS (
                    SELECT 1 FROM dim_studios_corporate dc
                    WHERE LOWER(dc."Studio Name") = LOWER(studio_locations."Studio Name")
                )
            """))
            log.info("Columnas studio_tier e is_notable propagadas a studio_locations.")
        except Exception as e:
            log.warning(f"No se pudo propagar studio_tier a studio_locations (¿tabla no existe aún?): {e}")


        # Crear vista detallada de juegos para análisis profundo si se necesita en el futuro
        connection.execute(text("""
            CREATE VIEW v_games_detail AS
            SELECT 
                c.name AS conglomerate,
                s.name AS studio,
                g.title, g.release_date, g.release_year,
                g.metacritic, g.rawg_rating, g.rawg_ratings_count,
                g.genres, g.platforms, g.esrb_rating, g.playtime_hours
            FROM games g
            JOIN developers_rawg dr ON g.developer_rawg_id = dr.rawg_developer_id
            JOIN notable_studios s ON dr.studio_id = s.id
            JOIN conglomerates c ON s.parent_id = c.id;
        """))

        # Índices para optimizar las consultas en Streamlit
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_dim_parent ON dim_studios_corporate(Parent);"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_dim_country ON dim_studios_corporate(Country);"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_stock_company ON stock_prices('Company Name');"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_stock_date ON stock_prices(Date);"))
        
        # Índices para la tabla games (útiles si el dashboard consulta games directamente)
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_games_dev ON games(developer_rawg_id);"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_games_year ON games(release_year);"))

    log.info("Capa semántica consolidada exitosamente.")

    # Ejecutar el ETL de VGChartz de manera automática para incorporar los datos de ventas
    try:
        run_vgchartz_etl()
    except Exception as e:
        log.error(f"Error al ejecutar el ETL de VGChartz durante la construcción de la base de datos: {e}")

if __name__ == "__main__":
    build_database()
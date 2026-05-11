import sqlite3
import pandas as pd
import sys
from pathlib import Path

# Agregamos el directorio raíz
root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

log = config.get_logger("audit_data")

def run_audit():
    log.info("🔍 Iniciando Auditoría de la Base de Datos (Data Quality Tests)...")
    
    if not config.DATABASE_PATH.exists():
        log.error("❌ Error: No se encontró la base de datos SQLite.")
        sys.exit(1)
        
    conn = sqlite3.connect(config.DATABASE_PATH)
    
    # Auditamos directamente la capa semántica consolidada
    log.info("🏢 --- AUDITORÍA DE CAPA SEMÁNTICA (dim_studios_corporate) ---")
    try:
        df_dim = pd.read_sql_query("SELECT * FROM dim_studios_corporate", conn)
        df_games = pd.read_sql_query("SELECT * FROM games", conn)
        df_devs = pd.read_sql_query("SELECT * FROM developers_rawg", conn)
    except Exception as e:
        log.error(f"❌ Error al consultar la base de datos: {e}")
        sys.exit(1)

    total_studios = len(df_dim)
    if total_studios == 0:
        log.error("❌ Error: La tabla dim_studios_corporate está vacía.")
        sys.exit(1)

    # 1. Años de adquisición
    faltan_anio = df_dim[
        df_dim['Acquisition_Year'].isna() | 
        df_dim['Acquisition_Year'].isin(['No registrado', 'N/A', 'Desconocido', ''])
    ]
    pct_faltan_anio = (len(faltan_anio) / total_studios) * 100

    # 2. Match de Developers RAWG
    matched_devs = len(df_devs)
    pct_matched_devs = (matched_devs / total_studios) * 100

    # 3. Geografía
    faltan_geo = df_dim[
        df_dim['Country'].isin(['Unknown Country', 'N/A', 'Desconocido', '']) | 
        df_dim['City'].isin(['Unknown City', 'N/A', 'Desconocida', ''])
    ]
    pct_faltan_geo = (len(faltan_geo) / total_studios) * 100

    log.info(f"Total Estudios Consolidados: {total_studios}")
    log.info(f" - Sin Año Adq/Fund: {len(faltan_anio)} ({pct_faltan_anio:.1f}%)")
    log.info(f" - Mapeo RAWG: {matched_devs}/{total_studios} ({pct_matched_devs:.1f}%)")
    log.info(f" - Sin Ubicación Precisa: {len(faltan_geo)} ({pct_faltan_geo:.1f}%)")
    
    log.info("🎮 --- AUDITORÍA DE JUEGOS (games table) ---")
    total_games = len(df_games)
    con_metacritic = len(df_games.dropna(subset=['metacritic']))
    con_userscore = len(df_games.dropna(subset=['rawg_rating']))
    
    log.info(f"Total Juegos Individuales: {total_games}")
    log.info(f" - Con Metacritic: {con_metacritic}")
    log.info(f" - Con User Rating: {con_userscore}")

    # Evaluamos las aserciones (Data Quality Gates)
    errores = []
    
    if pct_faltan_anio > 15.0:
        errores.append("Faltan años de adquisición en > 15% de estudios.")
    
    if pct_matched_devs < 80.0:
        errores.append("Mapeo de desarrolladores en RAWG inferior al 80%.")

    if pct_faltan_geo > 5.0:
        errores.append("Falta ubicación (Ciudad/País) en > 5% de estudios.")
        
    if total_games < 1000:
        errores.append(f"Muy pocos juegos individuales en base de datos ({total_games}). Esperados: >1000.")

    if errores:
        log.error("❌ DATA QUALITY PIPELINE FAILED:")
        for e in errores:
            log.error(f"   - {e}")
        conn.close()
        sys.exit(1)

    log.info("✅ DATA QUALITY PASSED. La base de datos está lista para producción.")
    conn.close()

if __name__ == "__main__":
    run_audit()
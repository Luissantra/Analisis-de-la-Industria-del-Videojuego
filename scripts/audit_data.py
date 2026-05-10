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
    print("🔍 Iniciando Auditoría de la Base de Datos (Data Quality Tests)...\n")
    
    if not config.DATABASE_PATH.exists():
        print("❌ Error: No se encontró la base de datos SQLite.")
        sys.exit(1)
        
    conn = sqlite3.connect(config.DATABASE_PATH)
    
    # Auditamos directamente la capa semántica consolidada
    print("🏢 --- AUDITORÍA DE CAPA SEMÁNTICA (dim_studios_corporate) ---")
    try:
        df_dim = pd.read_sql_query("SELECT * FROM dim_studios_corporate", conn)
    except Exception as e:
        print(f"❌ Error al consultar la capa semántica: {e}")
        sys.exit(1)

    total_studios = len(df_dim)
    if total_studios == 0:
        print("❌ Error: La tabla dim_studios_corporate está vacía.")
        sys.exit(1)

    # 1. Años de adquisición
    faltan_anio = df_dim[
        df_dim['Acquisition_Year'].isna() | 
        df_dim['Acquisition_Year'].isin(['No registrado', 'N/A', 'Desconocido', ''])
    ]
    pct_faltan_anio = (len(faltan_anio) / total_studios) * 100

    # 2. Metacritic / Juegos
    faltan_meta = df_dim[
        df_dim['Metacritic'].isna() | 
        (df_dim['Top_Game'] == 'No registrado')
    ]
    pct_faltan_meta = (len(faltan_meta) / total_studios) * 100

    # 3. Geografía
    faltan_geo = df_dim[
        df_dim['Country'].isin(['Unknown Country', 'N/A', '']) | 
        df_dim['City'].isin(['Unknown City', 'N/A', ''])
    ]
    pct_faltan_geo = (len(faltan_geo) / total_studios) * 100

    print(f"Total Estudios Consolidados: {total_studios}")
    print(f" - Sin Año de Adquisición/Fundación: {len(faltan_anio)} ({pct_faltan_anio:.1f}%)")
    print(f" - Sin Top Game o Metacritic: {len(faltan_meta)} ({pct_faltan_meta:.1f}%)")
    print(f" - Sin Ubicación Precisa: {len(faltan_geo)} ({pct_faltan_geo:.1f}%)")

    # Evaluamos las aserciones (Data Quality Gates)
    errores = []
    
    # Permitimos un pequeño margen de error (ej. 15% para metadatos que a veces no existen en IGDB/RAWG)
    MAX_TOLERANCE_PCT = 15.0

    if pct_faltan_anio > MAX_TOLERANCE_PCT:
        errores.append(f"Faltan años de adquisición en > {MAX_TOLERANCE_PCT}% de estudios.")
    
    if pct_faltan_meta > MAX_TOLERANCE_PCT:
        errores.append(f"Falta Metacritic o Top Game en > {MAX_TOLERANCE_PCT}% de estudios.")

    if pct_faltan_geo > MAX_TOLERANCE_PCT:
        errores.append(f"Falta ubicación (Ciudad/País) en > {MAX_TOLERANCE_PCT}% de estudios.")

    if errores:
        print("\n❌ DATA QUALITY PIPELINE FAILED:")
        for e in errores:
            print(f"   - {e}")
        conn.close()
        sys.exit(1)

    print("\n✅ DATA QUALITY PASSED. La base de datos está lista para producción.")
    conn.close()

if __name__ == "__main__":
    run_audit()
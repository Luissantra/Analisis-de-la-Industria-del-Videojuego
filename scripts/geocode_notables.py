"""
geocode_notables.py — Geocodifica estudios notables que no tienen coordenadas.

Lee la tabla notable_studios, busca los que no tienen match en studio_locations,
los geocodifica usando Nominatim y los inserta en studio_locations con
is_notable = 1.
"""

import os
import ssl
import sys
import sqlite3
from pathlib import Path

import certifi
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

log = config.get_logger("geocode_notables")

# Force CA bundle for macOS
os.environ.setdefault('SSL_CERT_FILE', certifi.where())


def run_geocode_notables():
    log.info("Iniciando geocodificación de estudios notables faltantes...")
    conn = sqlite3.connect(config.DATABASE_PATH)

    # 1. Encontrar notables sin match en studio_locations
    query = """
        SELECT ns.id, ns.name as Company_Name, ns.city, ns.country
        FROM notable_studios ns
        LEFT JOIN studio_locations sl ON LOWER(ns.name) = LOWER(sl."Studio Name")
        WHERE sl."Studio Name" IS NULL
          AND ns.city IS NOT NULL AND ns.city != '' AND ns.city != 'N/A' AND ns.city != 'Desconocida'
          AND ns.country IS NOT NULL AND ns.country != '' AND ns.country != 'N/A' AND ns.country != 'Desconocido'
    """
    df_missing = pd.read_sql_query(query, conn)
    
    if df_missing.empty:
        log.info("No hay estudios notables faltantes con ciudad/país válidos.")
        conn.close()
        return

    log.info(f"Se encontraron {len(df_missing)} estudios notables sin coordenadas.")

    # 2. Cargar caché de geocodificación
    cache = {}
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS geocode_cache (
                        query_address TEXT PRIMARY KEY,
                        latitude REAL,
                        longitude REAL
                      )''')
    conn.commit()

    try:
        cursor.execute("SELECT query_address, latitude, longitude FROM geocode_cache")
        for r in cursor.fetchall():
            if pd.notna(r[0]) and pd.notna(r[1]) and pd.notna(r[2]):
                cache[r[0]] = (r[1], r[2])
    except Exception:
        pass

    # 3. Inicializar geocodificador
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    geolocator = Nominatim(user_agent="gamedev_analysis_tool_notables", ssl_context=ssl_ctx, timeout=15)
    geocode = RateLimiter(
        geolocator.geocode,
        min_delay_seconds=1.5,
        return_value_on_exception=None,
        max_retries=5,
        error_wait_seconds=10.0
    )

    def safe_geocode(q):
        try:
            return geocode(q)
        except Exception as e:
            log.warning(f"Error geocodificando {q}: {e}")
            return None

    # Helper from etl_gameDevMap to get region
    try:
        from scripts.etl_gameDevMap import obtain_region
    except ImportError:
        def obtain_region(country_name):
            return "Other"

    # Ensure columns exist in studio_locations
    cursor.execute("PRAGMA table_info(studio_locations)")
    cols = [r[1] for r in cursor.fetchall()]
    if "studio_tier" not in cols:
        cursor.execute("ALTER TABLE studio_locations ADD COLUMN studio_tier TEXT DEFAULT 'Indie'")
    if "is_notable" not in cols:
        cursor.execute("ALTER TABLE studio_locations ADD COLUMN is_notable INTEGER DEFAULT 0")

    # 4. Geocodificar e insertar
    inserted = 0
    for _, row in df_missing.iterrows():
        company = row['Company_Name']
        city = row['city']
        country = row['country']
        
        q_addr = f"{city}, {country}"
        lat, lon = None, None

        if q_addr in cache:
            lat, lon = cache[q_addr]
        else:
            log.info(f"Geocodificando: {q_addr} ({company})")
            loc = safe_geocode(q_addr)
            if loc:
                lat, lon = loc.latitude, loc.longitude
                cache[q_addr] = (lat, lon)
                cursor.execute("INSERT OR REPLACE INTO geocode_cache (query_address, latitude, longitude) VALUES (?, ?, ?)", (q_addr, lat, lon))
                conn.commit()

        if lat is not None and lon is not None:
            region = obtain_region(country)
            
            # Insert into studio_locations
            # Use 'Indie' as default tier, build_db.py will update it later with cross-update
            cursor.execute("""
                INSERT INTO studio_locations ("Studio Name", City, Country, Lat, Lon, Region, studio_tier, is_notable)
                VALUES (?, ?, ?, ?, ?, ?, 'Indie', 1)
            """, (company, city.title(), country.upper(), lat, lon, region))
            inserted += 1

    conn.commit()
    conn.close()
    
    log.info(f"Geocodificación completada. {inserted} estudios notables añadidos a studio_locations.")


if __name__ == "__main__":
    run_geocode_notables()

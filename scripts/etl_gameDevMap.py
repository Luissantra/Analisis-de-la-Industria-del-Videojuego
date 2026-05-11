"""
etl_gameDevMap.py — ETL para el mapa geográfico de estudios de videojuegos.

Lee los datos crudos de GameDevMap (CSV), transforma las columnas,
asigna regiones geográficas y carga directamente en SQLite.
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pycountry_convert as pc

root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

log = config.get_logger("etl_gameDevMap")

# ─── Correcciones de nombres de país ───────────────────────────────
# pycountry_convert no reconoce muchos nombres comunes.
# Las claves deben estar en MAYÚSCULAS (el df se pasa a .upper()).
COUNTRY_CORRECTIONS = {
    "USA": "United States",
    "UNITED STATES": "United States",
    "UNITED KINGDOM": "United Kingdom",
    "ENGLAND": "United Kingdom",
    "SCOTLAND": "United Kingdom",
    "WALES": "United Kingdom",
    "NORTHERN IRELAND": "United Kingdom",
    "UK": "United Kingdom",
    "SOUTH KOREA": "South Korea",
    "KOREA": "South Korea",
    "KOREA, REPUBLIC OF": "South Korea",
    "RUSSIAN FEDERATION": "Russian Federation",
    "RUSSIA": "Russian Federation",
    "CZECHIA": "Czech Republic",
    "CZECH REPUBLIC": "Czech Republic",
    "TAIWAN, PROVINCE OF CHINA": "Taiwan",
    "TAIWAN": "Taiwan",
    "BOSNIA & HERZEGOVINA": "Bosnia and Herzegovina",
    "BOSNIA AND HERZEGOVINA": "Bosnia and Herzegovina",
    "RHONE-ALPES": "France",
    "CÔTE D'IVOIRE": "Ivory Coast",
}


def obtain_region(country_name: str) -> str:
    """Mapea un país a su región geográfica (continente)."""
    if pd.isna(country_name) or country_name.strip().upper() in ("REMOTE", ""):
        return "Other"

    nombre_limpio = COUNTRY_CORRECTIONS.get(
        country_name.strip().upper(), country_name.strip().title()
    )

    try:
        country_code = pc.country_name_to_country_alpha2(nombre_limpio)
        continent_code = pc.country_alpha2_to_continent_code(country_code)
        return pc.convert_continent_code_to_continent_name(continent_code)
    except Exception:
        return "Other"


def run_geo_etl():
    """Ejecuta el ETL completo: extract → transform → load en SQLite."""
    log.info("Iniciando ETL para el mapa geográfico de desarrolladoras...")

    # ── 1. Extract ─────────────────────────────────────────────────
    geocoded_path = str(config.RAW_GAMEDEVMAP_CSV).replace(".csv", "_geocoded.csv")
    if Path(geocoded_path).exists():
        df_raw = pd.read_csv(geocoded_path)
        log.info("Cargado CSV geocodificado: %s", geocoded_path)
    else:
        df_raw = pd.read_csv(config.RAW_GAMEDEVMAP_CSV)
        log.info("Cargado CSV crudo: %s", config.RAW_GAMEDEVMAP_CSV)

    for col in ("Latitude", "Longitude"):
        if col not in df_raw.columns:
            df_raw[col] = None

    # ── 2. Transform ───────────────────────────────────────────────
    log.info("Transformando datos...")

    columns_to_keep = ["Company_Name", "City", "Country", "Latitude", "Longitude"]
    df_geo = df_raw[columns_to_keep].copy()

    df_geo.rename(
        columns={"Company_Name": "Studio Name", "Latitude": "Lat", "Longitude": "Lon"},
        inplace=True,
    )

    df_geo["City"] = df_geo["City"].fillna("Unknown City").str.title()
    df_geo["Country"] = df_geo["Country"].fillna("Unknown Country").str.upper()
    df_geo["Region"] = df_geo["Country"].apply(obtain_region)
    df_geo["studio_tier"] = "Indie"
    df_geo["is_notable"] = 0

    df_geo = df_geo.reset_index(drop=True)
    df_geo.index.name = "Geo_ID"

    log.info("Transformación completa. Total de estudios: %d", len(df_geo))

    # ── 3. Load ────────────────────────────────────────────────────
    log.info("Cargando datos en SQLite (tabla 'studio_locations')...")

    conn = sqlite3.connect(config.DATABASE_PATH)
    df_geo.to_sql("studio_locations", conn, if_exists="replace", index=False)
    conn.close()

    log.info("ETL completado. %d registros cargados.", len(df_geo))


if __name__ == "__main__":
    run_geo_etl()
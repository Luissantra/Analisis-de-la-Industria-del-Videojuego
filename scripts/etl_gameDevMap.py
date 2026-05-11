import pandas as pd
import pycountry_convert as pc
import sys
import sqlite3
from pathlib import Path

# Agregamos el directorio raíz al path para que Python encuentre el módulo 'config'
root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

def obtain_region(country_name):
    """
    Función auxiliar para mapear un país a su región geográfica.
    """
    if pd.isna(country_name) or country_name.upper() == "REMOTE":
        return "Other"
    
    # Casos especiales que a la librería le cuesta entender
    correcciones = {
        'UNITED KINGDOM': 'United Kingdom',
        'ENGLAND': 'United Kingdom',
        'SCOTLAND': 'United Kingdom',
        'WALES': 'United Kingdom',
        'NORTHERN IRELAND': 'United Kingdom',
        'SOUTH KOREA': 'South Korea',
        'KOREA, REPUBLIC OF': 'South Korea',
        'RUSSIAN FEDERATION': 'Russian Federation',
        'RUSSIA': 'Russian Federation',
        'CZECHIA': 'Czech Republic',
        'TAIWAN, PROVINCE OF CHINA': 'Taiwan'
    }
    
    nombre_limpio = correcciones.get(country_name.upper(), country_name.title())

    try:
        # 1. País -> Código de 2 letras (Ej: Spain -> ES)
        country_code = pc.country_name_to_country_alpha2(nombre_limpio)
        # 2. Código País -> Código Continente (Ej: ES -> EU)
        continent_code = pc.country_alpha2_to_continent_code(country_code)
        # 3. Código Continente -> Nombre (Ej: EU -> Europe)
        return pc.convert_continent_code_to_continent_name(continent_code)
    except Exception:
        # Si la librería falla con un país rarísimo, lo manda a Other
        return 'Other'


def run_geo_etl():
    print("Iniciando proceso ETL para el mapa geográfico de desarrolladoras...")
    
    # 1. Extract
    geocoded_path = str(config.RAW_GAMEDEVMAP_CSV).replace('.csv', '_geocoded.csv')
    if Path(geocoded_path).exists():
        df_raw = pd.read_csv(geocoded_path)
    else:
        df_raw = pd.read_csv(config.RAW_GAMEDEVMAP_CSV)

    # Prevenir KeyError si las coordenadas no existen (ej. si se omitió la geocodificación)
    for col in ['Latitude', 'Longitude']:
        if col not in df_raw.columns:
            df_raw[col] = None

    # 2. Transform
    print("Transformando datos...")

    # Nos quedamos solo con las columnas importantes
    columns_to_keep = ['Company_Name', 'City', 'Country', 'Latitude', 'Longitude']
    df_geo = df_raw[columns_to_keep].copy()

    # Renombramos columnas para mayor claridad
    df_geo.rename(columns={
        'Company_Name': 'Studio Name',
        'Latitude': 'Lat',
        'Longitude': 'Lon'
    }, inplace=True)

    # Estandarizamos nombres de países
    df_geo["City"] = df_geo["City"].fillna("Unknown City").str.title()
    df_geo["Country"] = df_geo["Country"].fillna("Unknown Country").str.upper()
    
    # Mapeamos cada país a su región usando la función auxiliar
    df_geo['Region'] = df_geo['Country'].apply(obtain_region)

    # Conservamos los estudios sin coordenadas para que no se pierdan del directorio
    # El mapa de Folium ya está preparado para ignorar de forma segura los valores nulos

    # Reseteamos índice
    df_geo = df_geo.reset_index(drop=True)
    df_geo.index.name = 'Geo_ID'

    print(f"Transformación completa. Total de estudios geocodificados: {len(df_geo)}")

    # 3. Load
    print("Guardando datos transformados directamente en SQLite...")

    # Eliminamos el CSV intermedio e inyectamos directamente en la base de datos
    conn = sqlite3.connect(config.DATABASE_PATH)
    df_geo.to_sql('studio_locations', conn, if_exists='replace', index=False)
    conn.close()

    print("¡ETL completado! Los datos han sido cargados en la tabla 'studio_locations'.")


if __name__ == "__main__":
    run_geo_etl()
    
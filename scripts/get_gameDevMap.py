import os
import ssl
import time
import urllib.parse
import csv
import certifi
import pandas as pd
import requests
import sys
from pathlib import Path

# Agregamos el directorio raíz al path para que Python encuentre el módulo 'config'
root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import config
import sqlite3

# Force requests/geopy to use certifi CA bundle (fixes SSL verification issues on macOS)
os.environ.setdefault('SSL_CERT_FILE', certifi.where())


def cargar_estudios_notables():
    """Carga la lista de estudios notables desde la base de datos."""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        df = pd.read_sql_query('SELECT name as Company_Name, city as City, country as Country FROM notable_studios', conn)
        conn.close()
        return df.to_dict('records')
    except Exception as e:
        print(f"[Advertencia] Error al cargar notables desde DB: {e}")
        return []

def get_available_locations(base_url):
    """Obtiene todos los valores de `location=` disponibles en la página principal.

    GameDevMap expone un mapa con áreas clicables (<area href="...location=..."></area>).
    Esta función extrae esos valores para poder iterar sobre cada ubicación.
    """

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    print(f"--- Extrayendo lista de ubicaciones desde {base_url} ---")

    try:
        response = requests.get(base_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        locations = []
        for tag in soup.find_all(href=True):
            href = tag.get("href")
            if not href or not isinstance(href, str):
                continue

            parsed = urllib.parse.urlparse(href)
            params = urllib.parse.parse_qs(parsed.query)
            locs = params.get('location')
            if not locs:
                continue

            for loc in locs:
                loc = loc.strip()
                if loc and loc not in locations:
                    locations.append(loc)

        print(f"Encontradas {len(locations)} ubicaciones únicas.")
        return locations

    except Exception as e:
        print(f"No se pudo extraer la lista de ubicaciones: {e}")
        return []


def extract_gamedev_data(url, location=None):
    """Extrae datos básicos de estudios desde una URL.

    Nota: La estructura de selectores (find_all) puede variar según la página exacta.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    print(f"--- Extrayendo datos de {url} ---")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        studios = []
        # Localizamos la tabla o los contenedores de los estudios
        # Este es un selector genérico, ajustalo según el HTML real
        rows = soup.find_all('tr')

        for row in rows:
            cols = row.find_all('td')
            # La tabla de studios usa las columnas: Company | Type | City | State/Province | Country/Region
            if len(cols) >= 5:
                name = cols[0].get_text(strip=True)
                city = cols[2].get_text(strip=True)
                country = cols[4].get_text(strip=True)
            elif len(cols) >= 3:
                # Fallback genérico si la tabla tiene menos columnas
                name = cols[0].get_text(strip=True)
                city = cols[1].get_text(strip=True)
                country = cols[2].get_text(strip=True)
            else:
                continue

            # Evitar encabezados de tabla comunes y contenido basura
            name_lower = name.lower()
            if (
                not name
                or len(name) > 80
                or any(skip in name_lower for skip in ['company', 'browse', 'gamedevmap', 'search', 'type', 'country'])
                or not city
                or not country
            ):
                continue

            # Si se pasa explícitamente el nombre de la ubicación, úsalo.
            # Si no, lo intentamos extraer de la querystring de la URL.
            loc_value = location
            if loc_value is None:
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
                loc_values = params.get('location', [])
                loc_value = loc_values[0] if loc_values else None

            studios.append({
                'Company_Name': name,
                'City': city,
                'Country': country,
                'Location': loc_value,
            })

        return pd.DataFrame(studios)

    except Exception as e:
        print(f"Error durante el scraping: {e}")
        return pd.DataFrame()

def geocode_studios(input_csv, output_csv):
    """Lee un CSV con City/Country y crea otro CSV con Latitude/Longitude.

    Se usa un cache en SQLite para no repetir consultas a Nominatim entre ejecuciones.
    El archivo de salida se va escribiendo en modo append para permitir reanudar.
    """
    print("--- Paso 2: Geocodificando ciudades (esto tomará tiempo) ---")

    # Leer datos de entrada y construir la dirección de consulta
    df = pd.read_csv(input_csv, dtype=str)
    df['City'] = df['City'].fillna('')
    df['Country'] = df['Country'].fillna('')
    # USAR SOLO CIUDAD Y PAÍS: OpenStreetMap no tiene mapeadas la mayoría de las empresas.
    # Buscar por nombre de empresa hace que la API falle y devuelva nulo para miles de registros.
    df['query_address'] = df['City'] + ", " + df['Country']

    # Cargar cache desde SQLite
    cache = {}
    conn = sqlite3.connect(config.DATABASE_PATH)
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

    # Determinar qué ya fue procesado (para poder reanudar en caso de interrupción)
    already_done = set()
    output_exists = os.path.exists(output_csv)

    # Si el archivo existe pero está vacío, lo eliminamos para poder escribir el header
    if output_exists and os.path.getsize(output_csv) == 0:
        try:
            os.remove(output_csv)
            output_exists = False
        except Exception:
            pass

    if output_exists:
        try:
            done_df = pd.read_csv(output_csv, dtype=str)
            if 'Company_Name' in done_df.columns:
                already_done = set(done_df['Company_Name'].dropna().tolist())
        except Exception:
            already_done = set()

    # Usar CA bundle de certifi para evitar errores de verificación SSL en macOS.
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())

    # Inicializar el geocodificador con un User Agent único
    geolocator = Nominatim(user_agent="gamedev_analysis_tool_luis_v2", ssl_context=ssl_ctx, timeout=15)

    # Configuramos el limitador para cumplir con la política de Nominatim (1 req/seg max)
    geocode = RateLimiter(
        geolocator.geocode,
        min_delay_seconds=1.5, 
        return_value_on_exception=None,
        max_retries=5, 
        error_wait_seconds=10.0
    )

    def safe_geocode(query):
        try:
            return geocode(query)
        except Exception as e:
            print(f"[geocode error] {query!r}: {e}")
            return None

    # Asegurarnos de que las columnas existan en el DataFrame base
    if 'Latitude' not in df.columns: df['Latitude'] = None
    if 'Longitude' not in df.columns: df['Longitude'] = None

    fieldnames = list(df.columns)

    with open(output_csv, mode='a', newline='', encoding='utf-8') as out_f:
        writer = csv.DictWriter(out_f, fieldnames=fieldnames)
        if not output_exists:
            writer.writeheader()

        # Iteramos sobre todas las filas del DataFrame
        for idx, row in df.iterrows():
            company = row.get('Company_Name')
            query = row.get('query_address')
            
            # 1. Si esta dirección ya se procesó y guardó en el CSV en una ejecución anterior, la saltamos.
            if company in already_done:
                continue
                
            lat = row.get('Latitude')
            lon = row.get('Longitude')
            
            # 2. LA MAGIA: Si no trae coordenadas previas (ej. inyectadas desde el JSON notable)...
            if pd.isna(lat) or pd.isna(lon) or str(lat).strip() == '':
                # ... miramos en la caché ...
                if query in cache:
                    lat, lon = cache[query]
                # ... y si no está en la caché, llamamos a Nominatim.
                else:
                    print(f"Geocodificando nueva ubicación: {query}")
                    loc = safe_geocode(query)
                    lat = loc.latitude if loc else None
                    lon = loc.longitude if loc else None
                    cache[query] = (lat, lon)
                    
                    # Guardamos incrementalmente en la base de datos
                    cursor.execute("INSERT OR REPLACE INTO geocode_cache (query_address, latitude, longitude) VALUES (?, ?, ?)", (query, lat, lon))
                    conn.commit()

            # 3. Guardamos la fila final (ya sea con las coordenadas del JSON o las de Nominatim)
            row_dict = row.to_dict()
            row_dict['Latitude'] = lat
            row_dict['Longitude'] = lon
            writer.writerow(row_dict)
            
            already_done.add(company) # Lo marcamos como hecho para esta sesión

    conn.close()

    # Retornar el DataFrame completo con lat/lon (cargando el archivo de salida para reflejar el progreso)
    result_df = pd.read_csv(output_csv, dtype=str)
    print(f"Geocodificación completada: {len(result_df)} filas guardadas en {output_csv}")
    return result_df

# --- EJECUCIÓN PRINCIPAL ---
def obtener_datos_gamedevmap(
    location="Tucson", 
    all_locations=False, 
    max_locations=None, 
    output=None, 
    skip_geocode=False, 
    delay=.4, 
    force_scrape=False
):
    if output is None:
        output = config.RAW_GAMEDEVMAP_CSV
        
    base_url = "https://www.gamedevmap.com/index.php"
    
    # Nos aseguramos de que el directorio exista
    salida_path = str(output)
    os.makedirs(os.path.dirname(salida_path) if os.path.dirname(salida_path) else '.', exist_ok=True)

    # --- 1. DEFINIMOS LA LISTA DE NOTABLES ---
    notable_studios_data = cargar_estudios_notables()
    df_notable = pd.DataFrame(notable_studios_data)
    if 'Studio Name' in df_notable.columns:
        df_notable.rename(columns={'Studio Name': 'Company_Name'}, inplace=True)
        
    df_notable['Location'] = 'Custom Notable List'

    # --- 2. LÓGICA DE DATOS (Cargar o Scrapear) ---
    if os.path.exists(output) and not force_scrape:
        print(f"\n[INFO] El archivo '{output}' ya existe.")
        print("[INFO] Cargando datos existentes para inyectar la lista de notables...")
        raw_data = pd.read_csv(output, dtype=str)
    else:
        print("\n[INFO] Iniciando fase de web scraping...")
        if all_locations:
            locations = get_available_locations(base_url)
            if max_locations:
                locations = locations[: max_locations]
        else:
            locations = [location]

        if not locations:
            print("No se encontraron ubicaciones para procesar.")
            return # Cambiamos el SystemExit por un simple return para no matar el pipeline entero

        all_frames = []
        for i, loc in enumerate(locations, start=1):
            loc_encoded = urllib.parse.quote_plus(loc)
            target_url = f"{base_url}?location={loc_encoded}"

            df = extract_gamedev_data(target_url, location=loc)
            if not df.empty:
                all_frames.append(df)

            if delay and i < len(locations):
                time.sleep(delay)

        if all_frames:
            raw_data = pd.concat(all_frames, ignore_index=True)
        else:
            print("[INFO] No se extrajeron datos de la web. Se creará un dataset solo con notables.")
            raw_data = pd.DataFrame(columns=['Company_Name', 'City', 'Country', 'Location'])

    # --- 3. INYECCIÓN Y GUARDADO ---
    print("\n[INFO] Inyectando lista de estudios notables y limpiando duplicados...")
    raw_data = pd.concat([raw_data, df_notable], ignore_index=True)
    
    # Eliminamos duplicados dando prioridad a los notables (keep='last')
    raw_data.drop_duplicates(subset=['Company_Name', 'City'], keep='last', inplace=True)
    
    raw_data.to_csv(output, index=False, encoding='utf-8')
    print(f"[INFO] Se han guardado {len(raw_data)} filas en: {output}")

    # --- 4. FASE DE GEOCODIFICACIÓN ---
    if not skip_geocode:
        geo_output = str(output).replace('.csv', '_geocoded.csv')
        processed_df = geocode_studios(output, geo_output)
        print(f"\n[INFO] Geocodificación completada. Archivo generado: {geo_output}")
    else:
        print("\n[INFO] La geocodificación fue omitida (usar skip_geocode=True para desactivar).")

# --- Mantenemos la capacidad de ejecutarlo suelto desde la terminal ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extrae y geocodifica estudios de GameDevMap.")
    parser.add_argument("--location", default="Tucson", help="Nombre de la ubicación (ej: Tucson, Berlin, ...)")
    parser.add_argument("--all-locations", action="store_true", help="Extrae todas las ubicaciones.")
    parser.add_argument("--max-locations", type=int, default=None, help="Límite de ubicaciones (pruebas).")
    parser.add_argument("--output", default=config.RAW_GAMEDEVMAP_CSV, help="Ruta del CSV de salida.")
    parser.add_argument("--skip-geocode", action="store_true", help="No geocodificar (solo extraer).")
    parser.add_argument("--delay", type=float, default=1.0, help="Espera entre solicitudes.")
    parser.add_argument("--force-scrape", action="store_true", help="Fuerza el scraping aunque el CSV exista.")

    args = parser.parse_args()

    # Llamamos a nuestra nueva función pasándole los argumentos
    obtener_datos_gamedevmap(
        location=args.location,
        all_locations=args.all_locations,
        max_locations=args.max_locations,
        output=args.output,
        skip_geocode=args.skip_geocode,
        delay=args.delay,
        force_scrape=args.force_scrape
    )

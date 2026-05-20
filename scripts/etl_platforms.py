import json
import os
import sqlite3
import requests
import time
import sys
import pandas as pd
from pathlib import Path

# Agregamos el directorio raíz
root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

# Aliases para asegurar que el nombre de RAWG haga match con el de nuestro JSON
RAWG_ALIASES = {
    "SNES": "Super Nintendo",
    "Genesis": "Sega Genesis (Mega Drive)",
    "SEGA Mega Drive": "Sega Genesis (Mega Drive)"
}

def infer_manufacturer(name):
    """Infiere el fabricante de plataformas secundarias basándose en su nombre."""
    name_l = name.lower()
    if any(x in name_l for x in ['playstation', 'ps vita', 'psp']): return 'Sony'
    if any(x in name_l for x in ['xbox']): return 'Microsoft'
    if any(x in name_l for x in ['nintendo', 'wii', 'game boy', 'ds', 'gamecube', 'snes', 'nes']): return 'Nintendo'
    if any(x in name_l for x in ['sega', 'genesis', 'dreamcast', 'game gear', 'saturn']): return 'Sega'
    if 'atari' in name_l: return 'Atari'
    if any(x in name_l for x in ['mac', 'ios', 'apple']): return 'Apple'
    if any(x in name_l for x in ['pc', 'windows', 'linux']): return 'PC'
    if 'android' in name_l: return 'Google'
    if any(x in name_l for x in ['commodore', 'amiga']): return 'Commodore'
    if any(x in name_l for x in ['neo geo', 'snk']): return 'SNK'
    return 'Other'

def run_platforms_etl():
    config.init_environment()
    print("🕹️ Iniciando ETL de Plataformas (RAWG API + JSON)...")
    
    rawg_key = os.environ.get("RAWG_API_KEY")
    if not rawg_key:
        print("❌ ERROR: No se encontró RAWG_API_KEY en las variables de entorno.")
        print("Ejecuta en tu terminal: export RAWG_API_KEY='tu_clave'")
        return

    # 1. Cargar metadatos manuales (Ventas e Imágenes)
    manual_data = {}
    if config.PLATFORMS_JSON.exists():
        with open(config.PLATFORMS_JSON, 'r', encoding='utf-8') as f:
            for item in json.load(f):
                manual_data[item['name']] = item

    # 2. Extraer TODAS las plataformas de RAWG (Paginación)
    print("\nDescargando plataformas desde RAWG API...")
    url = f"https://api.rawg.io/api/platforms?key={rawg_key}&page_size=40"
    rawg_platforms = []
    
    while url:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            rawg_platforms.extend(data.get("results", []))
            url = data.get("next")
            time.sleep(0.5) # Respetar rate limits
        except Exception as e:
            print(f"❌ Error al consultar RAWG: {e}")
            break

    print(f"✅ Se encontraron {len(rawg_platforms)} plataformas en RAWG.")

    # 3. Fusionar datos y procesar imágenes
    headers = {'User-Agent': 'VideoGameIndustryDashboard/1.0'}
    final_platforms = []
    
    print("\nCruzando datos y descargando imágenes de Wikimedia Commons...")
    for rp in rawg_platforms:
        rawg_name = rp['name']
        json_name = RAWG_ALIASES.get(rawg_name, rawg_name)
        manual_info = manual_data.get(json_name, {})
        
        final_name = manual_info.get('name', rawg_name)
        manufacturer = manual_info.get('manufacturer') or infer_manufacturer(final_name)
        release_year = manual_info.get('release_year') or rp.get('year_start')
        
        local_image = None
        wiki_image = manual_info.get('wiki_image')
        
        # Si la consola está en nuestra lista VIP, descargamos el PNG sin fondo
        if wiki_image:
            safe_name = final_name.replace(" ", "_").replace("/", "_")
            img_filename = f"{safe_name}.png"
            local_image = img_filename
            filepath = config.CONSOLES_DIR / img_filename
            
            if not filepath.exists():
                wiki_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{wiki_image}?width=600"
                try:
                    res = requests.get(wiki_url, headers=headers, stream=True, allow_redirects=True)
                    if res.status_code == 200:
                        with open(filepath, 'wb') as img_file:
                            for chunk in res.iter_content(8192):
                                img_file.write(chunk)
                        print(f"   📸 Descargado render transparente: {img_filename}")
                        time.sleep(0.5)
                except Exception as e:
                    print(f"   ❌ Error con imagen de {final_name}: {e}")

        final_platforms.append({
            "id_api": rp['id'],
            "name": final_name,
            "manufacturer": manufacturer,
            "release_year": release_year,
            "discontinued_year": manual_info.get('discontinued_year'),
            "units_sold_millions": manual_info.get('units_sold_millions'),
            "games_count": rp.get('games_count', 0),
            "generation": manual_info.get('generation', 'Desconocida / Software'),
            "form_factor": manual_info.get('form_factor', 'home'),
            "local_image": local_image,
            "rawg_image": rp.get("image_background")
        })

    # 4. Guardar en SQLite
    df = pd.DataFrame(final_platforms)
    
    # Limpieza final: Eliminar plataformas de las que RAWG no sabe el año de salida y no tenemos manual
    df = df.dropna(subset=['release_year'])
    # Convertir el año a entero
    df['release_year'] = df['release_year'].astype(int)
    
    engine = sqlite3.connect(config.DATABASE_PATH)
    df.to_sql('platforms', con=engine, if_exists='replace', index=False)
    engine.close()
    print(f"\n✅ ETL Completo: {len(df)} plataformas guardadas en SQLite ('platforms').")

if __name__ == "__main__":
    run_platforms_etl()
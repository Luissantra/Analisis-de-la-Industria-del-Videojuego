import sqlite3
import requests
import re
import time
import sys
from pathlib import Path

root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

def search_wikipedia_for_year(studio_name):
    session = requests.Session()
    search_url = "https://en.wikipedia.org/w/api.php"
    
    # 1. Buscar la página del estudio en Wikipedia
    search_params = {
        "action": "query",
        "list": "search",
        "srsearch": f"{studio_name} video game developer",
        "utf8": "",
        "format": "json"
    }
    try:
        r = session.get(search_url, params=search_params, timeout=10)
        results = r.json().get("query", {}).get("search", [])
        if not results:
            return None
        
        pageid = results[0]["pageid"]
        
        # 2. Extraer el primer párrafo (extract) de la página
        extract_params = {
            "action": "query",
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "pageids": pageid,
            "format": "json"
        }
        r2 = session.get(search_url, params=extract_params, timeout=10)
        pages = r2.json().get("query", {}).get("pages", {})
        snippet = pages.get(str(pageid), {}).get("extract", "")
        
        if not snippet:
            return None
            
        # 3. Buscar patrones de fundación o adquisición seguidos de un año
        match = re.search(r'\b(?:founded|established|formed|acquired|bought|created).*?(19\d{2}|20\d{2})\b', snippet, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Fallback: Extraer el primer año de 4 dígitos plausible que aparezca en el resumen
        years = re.findall(r'\b(19[7-9]\d|20[0-2]\d)\b', snippet)
        if years:
            return years[0]
            
    except Exception as e:
        print(f"Error con {studio_name}: {e}")
    return None

def run_scraper():
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM notable_studios WHERE acquisition_year IS NULL OR acquisition_year IN ('No registrado', 'N/A', 'Desconocido', '')")
    studios = cursor.fetchall()
    
    print(f"🌐 Iniciando Wikipedia Scraping para {len(studios)} estudios...\n")
    for studio_id, name in studios:
        year = search_wikipedia_for_year(name)
        if year:
            print(f"✅ {name}: {year}")
            cursor.execute("UPDATE notable_studios SET acquisition_year = ? WHERE id = ?", (year, studio_id))
            conn.commit()
        else:
            print(f"❌ {name}: No encontrado")
        time.sleep(0.5) # Respetar a Wikipedia
        
    conn.close()
    print("\n🏁 Proceso completado.")

if __name__ == "__main__":
    run_scraper()
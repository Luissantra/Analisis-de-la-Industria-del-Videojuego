import os
import requests
import json
import sqlite3
import pandas as pd
from dotenv import load_dotenv
import time
import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

load_dotenv()

# Constants
TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/token"
IGDB_API_URL = "https://api.igdb.com/v4"

class IGDBClient:
    def __init__(self):
        self.client_id = os.getenv("IGDB_CLIENT_ID")
        self.client_secret = os.getenv("IGDB_CLIENT_SECRET")
        self.access_token = None
        self._authenticate()

    def _authenticate(self):
        """Autenticación OAuth2 con Twitch para obtener el Bearer Token."""
        if not self.client_id or not self.client_secret:
            raise ValueError("Las credenciales IGDB_CLIENT_ID y IGDB_CLIENT_SECRET deben estar en el archivo .env")

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        response = requests.post(TWITCH_AUTH_URL, params=payload)
        response.raise_for_status()
        data = response.json()
        self.access_token = data.get("access_token")
        print("✅ Autenticado exitosamente en IGDB.")

    def _get_headers(self):
        return {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }

    def query_companies(self, company_name):
        """Busca una compañía por nombre en IGDB y devuelve metadatos detallados."""
        # Se solicita la fecha de creación (start_date), el logo, el país, 
        # la empresa matriz (parent) y los juegos desarrollados con su valoración.
        body = f"""
            where name ~ *"{company_name}"*;
            fields name, description, start_date, url, 
                   country, parent.name, logo.url, 
                   developed.name, developed.rating, developed.first_release_date,
                   published.name;
            limit 5;
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(f"{IGDB_API_URL}/companies", headers=self._get_headers(), data=body)
                
                if response.status_code == 401:
                     print("⚠️ Token expirado. Reautenticando...")
                     self._authenticate()
                     response = requests.post(f"{IGDB_API_URL}/companies", headers=self._get_headers(), data=body)
        
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Error de conexión: {e}. Reintentando ({attempt + 1}/{max_retries})...")
                    time.sleep(2)
                else:
                    raise


def process_studios_to_mdm():
    """Lee la lista de estudios actual de SQLite, consulta IGDB y genera un Master Data CSV."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    
    # 1. Extraer todos los estudios y conglomerados actuales de la BD
    query = """
        SELECT s.id as internal_id, s.name as studio_name, c.name as parent_conglomerate
        FROM notable_studios s
        JOIN conglomerates c ON s.parent_id = c.id
    """
    df_studios = pd.read_sql_query(query, conn)
    conn.close()

    igdb = IGDBClient()
    master_data = []

    print(f"🔍 Procesando {len(df_studios)} estudios para crear el Golden Record MDM...")

    for index, row in df_studios.iterrows():
        studio_name = row['studio_name']
        print(f"[{index + 1}/{len(df_studios)}] Buscando: {studio_name}")
        
        try:
            results = igdb.query_companies(studio_name)
            
            # Estrategia de Match (Podemos refinar esto luego, por ahora tomamos el primero si coincide razonablemente)
            best_match = None
            if results:
                # Priorizar si el nombre exacto está en los resultados (ignorando mayúsculas)
                exact_matches = [r for r in results if r.get('name', '').lower() == studio_name.lower()]
                if exact_matches:
                    best_match = exact_matches[0]
                else:
                    best_match = results[0] # Fallback al primer resultado relevante de la búsqueda de texto de IGDB
            
            if best_match:
                # Parsear los juegos para el futuro
                developed_games = best_match.get('developed', [])
                top_game_name = None
                top_game_rating = None
                
                # Encontrar el mejor juego desarrollado
                if developed_games:
                    valid_games = [g for g in developed_games if g.get('rating')]
                    if valid_games:
                        best_game = max(valid_games, key=lambda x: x.get('rating', 0))
                        top_game_name = best_game.get('name')
                        top_game_rating = best_game.get('rating')

                logo_url = best_match.get('logo', {}).get('url')
                if logo_url and logo_url.startswith('//'):
                    logo_url = 'https:' + logo_url

                master_data.append({
                    'internal_id': row['internal_id'],
                    'original_studio_name': studio_name,
                    'parent_conglomerate': row['parent_conglomerate'],
                    'igdb_company_id': best_match.get('id'),
                    'igdb_company_name': best_match.get('name'),
                    'igdb_parent_name': best_match.get('parent', {}).get('name'),
                    'igdb_start_date': best_match.get('start_date'),
                    'igdb_country': best_match.get('country'),
                    'igdb_logo_url': logo_url,
                    'igdb_top_game': top_game_name,
                    'igdb_top_game_rating': top_game_rating,
                    'igdb_description': best_match.get('description')
                })
                print(f"  ✅ Match IGDB: {best_match.get('name')} (ID: {best_match.get('id')})")
            else:
                 master_data.append({
                    'internal_id': row['internal_id'],
                    'original_studio_name': studio_name,
                    'parent_conglomerate': row['parent_conglomerate'],
                    'igdb_company_id': None,
                    'igdb_company_name': None,
                    'igdb_parent_name': None,
                    'igdb_start_date': None,
                    'igdb_country': None,
                    'igdb_logo_url': None,
                    'igdb_top_game': None,
                    'igdb_top_game_rating': None,
                    'igdb_description': None
                })
                 print(f"  ⚠️ No se encontró match en IGDB.")
            
            time.sleep(0.3) # Respeta los rate limits de Twitch API (4 req/sec max)

        except Exception as e:
            print(f"  ❌ Error consultando {studio_name}: {e}")

    # Guardar el Golden Record
    df_master = pd.DataFrame(master_data)
    
    # Nos aseguramos de que el directorio de salida exista
    mdm_dir = config.PROCESSED_DATA_DIR / "mdm"
    mdm_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = mdm_dir / "master_studios.csv"
    df_master.to_csv(output_path, index=False)
    
    print(f"\n🎉 Proceso completado. Master Data guardado en: {output_path}")
    print(f"   Matches exitosos: {df_master['igdb_company_id'].notna().sum()} de {len(df_master)}")


if __name__ == "__main__":
    process_studios_to_mdm()

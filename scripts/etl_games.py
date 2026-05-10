import requests
import os
import sys
from pathlib import Path
import time
import sqlite3
import argparse
import re

# Agregamos el directorio raíz al path para que Python encuentre el módulo 'config'
root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

def clean_single_game_name_for_api(name):
    """Limpia un nombre individual antes de pasarlo a la API."""
    # 1. Si hay paréntesis con contenido útil (ej. Franquicia Halo (Halo Infinite)), lo extraemos
    match = re.search(r'\((.*?)\)', name)
    if match:
        inside = match.group(1).split(',')[0] # Tomar el primero si hay comas
        if not any(x in inside.lower() for x in ['soporte', 'en desarrollo', 'remake', 'publisher', 'holding']):
            name = inside
        else:
            name = re.sub(r'\(.*?\)', '', name)
    else:
        name = re.sub(r'\(.*?\)', '', name)
        
    # 2. Quitar prefijos de texto descriptivo
    name = re.sub(r'(?i)^(Franquicias?\s+|Nuevo título de\s+|Ports a\s+|Ports de\s+)', '', name)
    return name.strip()

def run_games_etl(force=False):
    # Leer clave API de entorno
    rawg_key = os.environ.get("RAWG_API_KEY")
    if not rawg_key:
        print("⚠️ ERROR: No se encontró la variable de entorno RAWG_API_KEY.")
        print("Configúrala en tu terminal ejecutando: export RAWG_API_KEY='tu_clave_aqui'")
        return

    print("🎮 Iniciando extracción de datos de juegos desde RAWG API hacia SQLite...")

    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()
    
    if force:
        cursor.execute("SELECT id, name FROM games_metadata")
        print("⚠️ Modo forzado: Se volverán a descargar los datos de todos los juegos.")
    else:
        # Seleccionamos solo los juegos que no hemos buscado en la API aún 
        # o que les falten datos clave (metacritic nulo o géneros desconocidos)
        cursor.execute("SELECT id, name FROM games_metadata WHERE name_api IS NULL OR name_api = '' OR metacritic IS NULL OR genres = 'Desconocido' OR genres IS NULL")

    juegos_a_procesar = cursor.fetchall()

    if not juegos_a_procesar:
        print("✅ Todos los juegos en la base de datos ya tienen sus metadatos. No hay nada nuevo que descargar.")
        conn.close()
        return

    print(f"📊 Se han encontrado {len(juegos_a_procesar)} juegos pendientes de procesar.")

    nuevos_juegos = 0
    for game_id, game_name in juegos_a_procesar:
        if not game_name or game_name in ["", "No registrado", "N/A", "Desconocido"]:
            continue

        juegos_separados = [g.strip() for g in game_name.split('/')]
        print(f"🔍 Analizando portfolio: '{game_name}' ({len(juegos_separados)} franquicias)")
        
        nombres_api = []
        all_genres = set()
        metacritics = []
        fechas_lanzamiento = []
        
        for sub_name in juegos_separados:
            cleaned_name = clean_single_game_name_for_api(sub_name)
            url = f"https://api.rawg.io/api/games?key={rawg_key}&search={requests.utils.quote(cleaned_name)}&page_size=1"
            
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("results"):
                        result = data["results"][0]
                        nombres_api.append(result.get("name", ""))
                        if result.get("released"):
                            fechas_lanzamiento.append(result.get("released"))
                        if result.get("metacritic"):
                            metacritics.append(result.get("metacritic"))
                            
                        genres_list = [g["name"] for g in result.get("genres", [])]
                        all_genres.update(genres_list)
                        print(f"   ✅ Encontrado: {result.get('name')} (Meta: {result.get('metacritic', 'N/A')})")
                    else:
                        print(f"   ⚠️ No encontrado: {cleaned_name}")
                else:
                    print(f"   ❌ Error HTTP {response.status_code} para {cleaned_name}")
                
                time.sleep(0.5) # Respetar rate limits
            except Exception as e:
                print(f"   ❌ Excepción: {e}")

        # Consolidamos los datos de todos los juegos del estudio
        final_name_api = " / ".join(nombres_api) if nombres_api else "No encontrado"
        final_released = max(fechas_lanzamiento) if fechas_lanzamiento else "" # Fecha más reciente
        final_meta = round(sum(metacritics) / len(metacritics)) if metacritics else None
        final_genres = ", ".join(sorted(all_genres)) if all_genres else "Desconocido"

        cursor.execute("""
            UPDATE games_metadata 
            SET name_api = ?, released = ?, metacritic = ?, genres = ?
            WHERE id = ?
        """, (final_name_api, final_released, final_meta, final_genres, game_id))
            
        conn.commit()
        nuevos_juegos += 1

    conn.close()
    print(f"\n✅ Proceso completado. Se actualizaron {nuevos_juegos} juegos en SQLite.")
    print("Siguiente paso sugerido: Fase 3 (Refactorizar view_corporate.py para que lea de SQLite y eliminar JSONs).")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrae metadatos de juegos desde RAWG API a SQLite.")
    parser.add_argument("--force", action="store_true", help="Fuerza la descarga de todos los juegos, ignorando los ya guardados.")
    args = parser.parse_args()
    
    run_games_etl(force=args.force)
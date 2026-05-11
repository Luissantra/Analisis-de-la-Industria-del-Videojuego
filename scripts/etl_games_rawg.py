"""
etl_games_rawg.py — Extracción masiva de juegos desde RAWG API.

Para cada notable_studio:
  1. Busca el developer en RAWG → obtiene rawg_developer_id y slug.
  2. Pagina por /games?developers=<slug> para descargar TODOS sus juegos.
  3. Almacena los resultados en las tablas `developers_rawg` y `games`.

Diseñado para ejecución incremental: solo procesa estudios/juegos que faltan.
"""

import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd
import requests

root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

log = config.get_logger("etl_games_rawg")

RAWG_BASE = "https://api.rawg.io/api"
PAGE_SIZE = 40
MAX_PAGES_PER_DEV = 10  # 10 pages × 40 = 400 games max per studio
REQUEST_DELAY = 0.28  # ~3.5 req/s (RAWG limit is ~5/s)


def _init_tables(conn: sqlite3.Connection):
    """Crea las tablas si no existen."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS developers_rawg (
            rawg_developer_id INTEGER PRIMARY KEY,
            rawg_slug TEXT UNIQUE,
            rawg_name TEXT,
            games_count INTEGER DEFAULT 0,
            studio_id INTEGER,
            FOREIGN KEY (studio_id) REFERENCES notable_studios(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            rawg_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            slug TEXT,
            release_date TEXT,
            release_year INTEGER,
            metacritic INTEGER,
            rawg_rating REAL,
            rawg_ratings_count INTEGER DEFAULT 0,
            playtime_hours INTEGER DEFAULT 0,
            genres TEXT,
            platforms TEXT,
            esrb_rating TEXT,
            developer_rawg_id INTEGER,
            FOREIGN KEY (developer_rawg_id) REFERENCES developers_rawg(rawg_developer_id)
        )
    """)
    conn.commit()


def _search_developer(studio_name: str, api_key: str) -> dict | None:
    """Busca un estudio en RAWG /developers y devuelve el mejor match."""
    url = f"{RAWG_BASE}/developers"
    params = {"key": api_key, "search": studio_name, "page_size": 5}

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        results = resp.json().get("results", [])

        if not results:
            return None

        # Priorizar coincidencia exacta (case-insensitive)
        for r in results:
            if r.get("name", "").lower() == studio_name.lower():
                return r

        # Fallback: primer resultado
        return results[0]

    except Exception as e:
        log.warning("Error buscando developer '%s': %s", studio_name, e)
        return None


def _fetch_games_for_developer(dev_slug: str, api_key: str) -> list[dict]:
    """Pagina por todos los juegos de un developer slug."""
    all_games = []
    url = f"{RAWG_BASE}/games"

    for page in range(1, MAX_PAGES_PER_DEV + 1):
        params = {
            "key": api_key,
            "developers": dev_slug,
            "page_size": PAGE_SIZE,
            "page": page,
            "ordering": "-metacritic",
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 404:
                break
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])

            if not results:
                break

            for g in results:
                release_date = g.get("released") or ""
                release_year = None
                if release_date and len(release_date) >= 4:
                    try:
                        release_year = int(release_date[:4])
                    except ValueError:
                        pass

                all_games.append({
                    "rawg_id": g["id"],
                    "title": g.get("name", ""),
                    "slug": g.get("slug", ""),
                    "release_date": release_date,
                    "release_year": release_year,
                    "metacritic": g.get("metacritic"),
                    "rawg_rating": g.get("rating"),
                    "rawg_ratings_count": g.get("ratings_count", 0),
                    "playtime_hours": g.get("playtime", 0),
                    "genres": ", ".join(
                        x["name"] for x in (g.get("genres") or [])
                    ),
                    "platforms": ", ".join(
                        (p.get("platform") or {}).get("name", "")
                        for p in (g.get("platforms") or [])
                    ),
                    "esrb_rating": (g.get("esrb_rating") or {}).get("name"),
                    "developer_rawg_id": None,  # Se asigna después
                })

            if not data.get("next"):
                break

            time.sleep(REQUEST_DELAY)

        except Exception as e:
            log.warning("Error en página %d para '%s': %s", page, dev_slug, e)
            break

    return all_games


def run_games_etl(force: bool = False):
    """Ejecuta el ETL completo: developer matching + game fetching."""
    api_key = config.RAWG_API_KEY
    if not api_key:
        log.error("RAWG_API_KEY no encontrada. Añádela al archivo .env")
        return

    conn = sqlite3.connect(config.DATABASE_PATH)
    _init_tables(conn)
    cursor = conn.cursor()

    # ── 1. Obtener estudios pendientes ─────────────────────────────
    df_studios = pd.read_sql_query(
        "SELECT id, name FROM notable_studios", conn
    )

    if not force:
        # Solo estudios sin developer RAWG mapeado
        already_mapped = set()
        try:
            result = cursor.execute(
                "SELECT studio_id FROM developers_rawg WHERE studio_id IS NOT NULL"
            ).fetchall()
            already_mapped = {r[0] for r in result}
        except Exception:
            pass
        df_studios = df_studios[~df_studios["id"].isin(already_mapped)]

    if df_studios.empty:
        log.info("Todos los estudios ya tienen developer RAWG mapeado.")
        conn.close()
        return

    total = len(df_studios)
    log.info("Procesando %d estudios...", total)

    total_games_added = 0

    for idx, row in df_studios.iterrows():
        studio_id = row["id"]
        studio_name = row["name"]
        progress = f"[{list(df_studios['id']).index(studio_id) + 1}/{total}]"

        log.info("%s Buscando developer RAWG: %s", progress, studio_name)

        # ── Developer matching ──────────────────────────────────
        dev = _search_developer(studio_name, api_key)
        time.sleep(REQUEST_DELAY)

        if not dev:
            log.warning("%s  ⚠️ No encontrado en RAWG: %s", progress, studio_name)
            continue

        rawg_dev_id = dev["id"]
        rawg_slug = dev.get("slug", "")
        rawg_name = dev.get("name", "")
        games_count = dev.get("games_count", 0)

        # Insertar o actualizar developer
        cursor.execute("""
            INSERT OR REPLACE INTO developers_rawg 
            (rawg_developer_id, rawg_slug, rawg_name, games_count, studio_id)
            VALUES (?, ?, ?, ?, ?)
        """, (rawg_dev_id, rawg_slug, rawg_name, games_count, studio_id))
        conn.commit()

        log.info(
            "%s  ✅ Match: %s (ID: %d, %d juegos)",
            progress, rawg_name, rawg_dev_id, games_count,
        )

        # ── Game fetching ───────────────────────────────────────
        if games_count == 0:
            continue

        # Comprobar cuántos juegos ya tenemos de este developer
        existing_count = cursor.execute(
            "SELECT COUNT(*) FROM games WHERE developer_rawg_id = ?",
            (rawg_dev_id,),
        ).fetchone()[0]

        if existing_count >= games_count and not force:
            log.info("%s  ⏭️ Ya tenemos %d juegos, saltando.", progress, existing_count)
            continue

        games = _fetch_games_for_developer(rawg_slug, api_key)

        if games:
            new_count = 0
            for g in games:
                g["developer_rawg_id"] = rawg_dev_id
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO games 
                        (rawg_id, title, slug, release_date, release_year,
                         metacritic, rawg_rating, rawg_ratings_count,
                         playtime_hours, genres, platforms, esrb_rating,
                         developer_rawg_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        g["rawg_id"], g["title"], g["slug"],
                        g["release_date"], g["release_year"],
                        g["metacritic"], g["rawg_rating"],
                        g["rawg_ratings_count"], g["playtime_hours"],
                        g["genres"], g["platforms"], g["esrb_rating"],
                        g["developer_rawg_id"],
                    ))
                    if cursor.rowcount > 0:
                        new_count += 1
                except Exception as e:
                    log.warning("Error insertando juego %s: %s", g.get("title"), e)

            conn.commit()
            total_games_added += new_count
            log.info(
                "%s  🎮 %d juegos nuevos insertados (de %d descargados)",
                progress, new_count, len(games),
            )

    # ── Resumen final ──────────────────────────────────────────────
    total_devs = cursor.execute("SELECT COUNT(*) FROM developers_rawg").fetchone()[0]
    total_games = cursor.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    conn.close()

    log.info("=" * 60)
    log.info("ETL completado.")
    log.info("  Developers mapeados: %d", total_devs)
    log.info("  Total juegos en BD:  %d", total_games)
    log.info("  Juegos nuevos:       %d", total_games_added)
    log.info("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch games from RAWG API per developer.")
    parser.add_argument("--force", action="store_true", help="Re-fetch all studios.")
    args = parser.parse_args()
    run_games_etl(force=args.force)

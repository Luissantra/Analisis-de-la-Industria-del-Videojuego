"""
fetch_company_size.py — Descarga company_size de IGDB para estudios existentes.

Script auxiliar que NO re-ejecuta el ETL completo de IGDB.
Usa los igdb_company_id ya guardados en master_studios para hacer
batch queries y actualizar solo la columna company_size.
"""

import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests
import sqlite3

root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

log = config.get_logger("fetch_company_size")

# ── IGDB company_size → tier mapping ─────────────────────────────────
COMPANY_SIZE_MAP = {
    1: "0-1 employees",
    2: "2-10 employees",
    3: "11-50 employees",
    4: "51-200 employees",
    5: "201-500 employees",
    6: "501-1000 employees",
    7: "1001-5000 employees",
    8: "5000+ employees",
}


def _get_igdb_token() -> tuple:
    """Authenticate with Twitch OAuth2 and return (token, client_id)."""
    client_id = os.getenv("IGDB_CLIENT_ID")
    client_secret = os.getenv("IGDB_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError("IGDB_CLIENT_ID and IGDB_CLIENT_SECRET must be set in .env")

    resp = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    return token, client_id


def fetch_company_sizes():
    """Fetch company_size from IGDB for all notable studios with known igdb_company_id."""
    log.info("Descargando company_size de IGDB para estudios existentes...")

    conn = sqlite3.connect(config.DATABASE_PATH)

    # 1. Get existing IGDB IDs from master_studios
    df = pd.read_sql_query(
        "SELECT internal_id, original_studio_name, igdb_company_id "
        "FROM master_studios WHERE igdb_company_id IS NOT NULL",
        conn,
    )
    igdb_ids = [int(x) for x in df["igdb_company_id"].dropna().tolist()]
    log.info("Estudios con IGDB ID: %d", len(igdb_ids))

    if not igdb_ids:
        log.warning("No hay IDs de IGDB para consultar. Abortando.")
        conn.close()
        return

    # 2. Authenticate
    token, client_id = _get_igdb_token()
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}",
    }

    # 3. Batch query (IGDB allows up to 500 IDs per request)
    all_results = {}
    batch_size = 500
    for i in range(0, len(igdb_ids), batch_size):
        batch = igdb_ids[i : i + batch_size]
        ids_str = ",".join(str(x) for x in batch)
        body = f"fields id, company_size; where id = ({ids_str}); limit {batch_size};"

        resp = requests.post(
            "https://api.igdb.com/v4/companies",
            headers=headers,
            data=body,
        )
        resp.raise_for_status()

        for item in resp.json():
            if "company_size" in item:
                all_results[item["id"]] = item["company_size"]

        log.info(
            "  Batch %d-%d: %d resultados con company_size",
            i, min(i + batch_size, len(igdb_ids)), len(all_results),
        )
        time.sleep(0.3)

    log.info("Total estudios con company_size: %d / %d", len(all_results), len(igdb_ids))

    # 4. Check if column exists, add if not
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(master_studios)")
    columns = [row[1] for row in cursor.fetchall()]

    if "igdb_company_size" not in columns:
        cursor.execute("ALTER TABLE master_studios ADD COLUMN igdb_company_size INTEGER")
        log.info("Columna 'igdb_company_size' añadida a master_studios.")

    # 5. Update the database
    updated = 0
    for _, row in df.iterrows():
        igdb_id = int(row["igdb_company_id"])
        if igdb_id in all_results:
            size_val = all_results[igdb_id]
            cursor.execute(
                "UPDATE master_studios SET igdb_company_size = ? WHERE igdb_company_id = ?",
                (size_val, igdb_id),
            )
            updated += 1

    conn.commit()

    # 6. Also update the CSV if it exists
    csv_path = config.PROCESSED_DATA_DIR / "mdm" / "master_studios.csv"
    if csv_path.exists():
        df_csv = pd.read_csv(csv_path)
        if "igdb_company_size" not in df_csv.columns:
            df_csv["igdb_company_size"] = None

        for igdb_id, size_val in all_results.items():
            mask = df_csv["igdb_company_id"] == igdb_id
            df_csv.loc[mask, "igdb_company_size"] = size_val

        df_csv.to_csv(csv_path, index=False)
        log.info("CSV actualizado: %s", csv_path)

    conn.close()

    # 7. Print summary
    log.info("=" * 50)
    log.info("Resumen de company_size:")
    for size_id, label in sorted(COMPANY_SIZE_MAP.items()):
        count = sum(1 for v in all_results.values() if v == size_id)
        if count > 0:
            log.info("  %s: %d estudios", label, count)
    log.info("  Sin dato: %d estudios", len(igdb_ids) - len(all_results))
    log.info("Actualización completada: %d registros actualizados.", updated)


if __name__ == "__main__":
    fetch_company_sizes()

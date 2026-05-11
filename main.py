"""
main.py — Orquestador central del pipeline de datos.

Controla la ejecución ordenada de todos los scripts ETL.
Permite saltarse fases específicas para facilitar el desarrollo
(por ejemplo, no volver a descargar todos los datos en pruebas).
"""

import argparse
import sys
from pathlib import Path

# Agregar los subdirectorios al path
root_dir = Path(__file__).resolve().parent
sys.path.append(str(root_dir))

import config
from scripts import (
    audit_data,
    build_db,
    download_logos,
    enrich_studios,
    etl_gameDevMap,
    etl_games_rawg,
    etl_igdb,
    etl_platforms,
    geocode_notables,
    get_gameDevMap,
    get_market_data,
)

log = config.get_logger("main_pipeline")


def run_pipeline(
    skip_extract: bool = False,
    skip_transform: bool = False,
    skip_games: bool = False,
    force_games: bool = False,
):
    """
    Ejecuta el pipeline completo de ingeniería de datos en orden.
    """
    log.info("=" * 60)
    log.info("🚀 INICIANDO PIPELINE DE DATOS 🚀")
    log.info("=" * 60)

    # ─── FASE 1: EXTRACCIÓN (Raw Data) ────────────────────────────────
    if not skip_extract:
        log.info("\n--- FASE 1: EXTRACCIÓN ---")
        try:
            log.info("1.1 Descargando datos bursátiles (yfinance)...")
            get_market_data.obtener_datos_preparados()

            log.info("1.2 Ejecutando scraping de GameDevMap...")
            get_gameDevMap.obtener_datos_gamedevmap()

            log.info("1.3 Descargando logotipos de empresas...")
            download_logos.descargar_logos()
        except Exception as e:
            log.error("Error en la fase de EXTRACCIÓN: %s", e)
            sys.exit(1)
    else:
        log.info("\n--- FASE 1: EXTRACCIÓN (SALTADA) ---")

    # ─── FASE 2: ENRIQUECIMIENTO (APIs & Matching) ────────────────────
    if not skip_transform:
        log.info("\n--- FASE 2: ENRIQUECIMIENTO ---")
        try:
            log.info("2.1 Construyendo capa MDM con IGDB...")
            etl_igdb.process_studios_to_mdm()

            log.info("2.2 Enriqueciendo ubicaciones de estudios...")
            enrich_studios.run_enrichment()

            if not skip_games:
                log.info("2.3 Obteniendo catálogo de juegos desde RAWG...")
                etl_games_rawg.run_games_etl(force=force_games)
            else:
                log.info("2.3 Extracción de juegos de RAWG saltada (--skip-games).")
                
        except Exception as e:
            log.error("Error en la fase de ENRIQUECIMIENTO: %s", e)
            sys.exit(1)
    else:
        log.info("\n--- FASE 2: ENRIQUECIMIENTO (SALTADA) ---")

    # ─── FASE 3: TRANSFORMACIÓN LOCAL ─────────────────────────────────
    if not skip_transform:
        log.info("\n--- FASE 3: TRANSFORMACIÓN ---")
        try:
            log.info("3.1 Transformando datos geográficos...")
            etl_gameDevMap.run_geo_etl()
            log.info("3.2 Procesando plataforma y consolas...")
            etl_platforms.run_platforms_etl()
            
            log.info("3.3 Geocodificando estudios notables faltantes...")
            geocode_notables.run_geocode_notables()
        except Exception as e:
            log.error("Error en la fase de TRANSFORMACIÓN: %s", e)
            sys.exit(1)
    else:
        log.info("\n--- FASE 3: TRANSFORMACIÓN (SALTADA) ---")

    # ─── FASE 4: CARGA & CAPA SEMÁNTICA ───────────────────────────────
    log.info("\n--- FASE 4: CONSTRUCCIÓN DE BASE DE DATOS ---")
    try:
        build_db.build_database()
    except Exception as e:
        log.error("Error construyendo la base de datos: %s", e)
        sys.exit(1)

    # ─── FASE 5: AUDITORÍA ──────────────────────────────────────────
    log.info("\n--- FASE 5: AUDITORÍA DE CALIDAD DE DATOS ---")
    try:
        audit_data.run_audit()
    except Exception as e:
        log.error("Error durante la auditoría de datos: %s", e)

    log.info("=" * 60)
    log.info("✅ PIPELINE COMPLETADO EXITOSAMENTE ✅")
    log.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data Pipeline Orchestrator")
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Salta la descarga de datos nuevos (usa los raw/ existentes)",
    )
    parser.add_argument(
        "--skip-transform",
        action="store_true",
        help="Salta las transformaciones y actualizaciones de APIs (fases 2 y 3)",
    )
    parser.add_argument(
        "--skip-games",
        action="store_true",
        help="Salta específicamente la llamada a RAWG para juegos",
    )
    parser.add_argument(
        "--force-games",
        action="store_true",
        help="Fuerza a descargar de nuevo todos los juegos en RAWG",
    )

    args = parser.parse_args()

    # Inicializar directorios por si acaso
    config.init_environment()

    run_pipeline(
        skip_extract=args.skip_extract,
        skip_transform=args.skip_transform,
        skip_games=args.skip_games,
        force_games=args.force_games,
    )

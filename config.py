"""
config.py — Configuración centralizada del proyecto.

Carga automáticamente las variables de entorno desde .env,
define todas las rutas de datos y provee un logger reutilizable.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# ─── Variables de entorno ───────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parent / ".env")

RAWG_API_KEY = os.getenv("RAWG_API_KEY", "")
IGDB_CLIENT_ID = os.getenv("IGDB_CLIENT_ID", "")
IGDB_CLIENT_SECRET = os.getenv("IGDB_CLIENT_SECRET", "")

# ─── Directorios base ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
DATABASE_DIR = DATA_DIR / "database"
MDM_DIR = PROCESSED_DATA_DIR / "mdm"

# ─── Rutas a archivos de configuración ─────────────────────────────
TICKERS_JSON = BASE_DIR / "config_data" / "tickers.json"
PLATFORMS_JSON = BASE_DIR / "config_data" / "platforms.json"
MARKET_VISUALS_JSON = BASE_DIR / "config_data" / "market_visuals.json"

# ─── Rutas a archivos de datos ─────────────────────────────────────
RAW_GAMEDEVMAP_CSV = RAW_DATA_DIR / "raw_studios.csv"
GAMEDEVMAP_CSV = PROCESSED_DATA_DIR / "studios_geocoded.csv"

RAW_MARKETDATA_CSV = RAW_DATA_DIR / "raw_market_data.csv"
MARKETDATA_CSV = PROCESSED_DATA_DIR / "market_data.csv"

DATABASE_PATH = DATABASE_DIR / "videogames.db"

# ─── Recursos estáticos (UI) ──────────────────────────────────────
ASSETS_DIR = BASE_DIR / "dashboard" / "assets"
LOGOS_DIR = ASSETS_DIR / "logos"
CONSOLES_DIR = ASSETS_DIR / "consoles"


# ─── Funciones de inicialización ───────────────────────────────────
def init_environment():
    """Crea la estructura de directorios necesaria si no existe."""
    for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, DATABASE_DIR,
                      MDM_DIR, ASSETS_DIR, LOGOS_DIR, CONSOLES_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger configurado con formato estándar del proyecto."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


if __name__ == "__main__":
    print("Inicializando entorno de directorios...")
    init_environment()
    print("¡Estructura de carpetas lista!")
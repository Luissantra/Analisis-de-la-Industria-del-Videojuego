from pathlib import Path

# Calcula dinámicamente la ruta al directorio raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent

# Directorios de datos
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
DATABASE_DIR = DATA_DIR / "database"

# Rutas a archivos específicos
TICKERS_JSON = BASE_DIR / "config_data" / "tickers.json"
PLATFORMS_JSON = BASE_DIR / "config_data" / "platforms.json"
MARKET_VISUALS_JSON = BASE_DIR / "config_data" / "market_visuals.json"

RAW_GAMEDEVMAP_CSV = RAW_DATA_DIR / "raw_studios_geocoded.csv"
GAMEDEVMAP_CSV = PROCESSED_DATA_DIR / "studios_geocoded.csv"

RAW_MARKETDATA_CSV = RAW_DATA_DIR / "raw_market_data.csv"
MARKETDATA_CSV = PROCESSED_DATA_DIR / "market_data.csv"

DATABASE_PATH = DATABASE_DIR / "videogames.db"

# Recursos estáticos (UI)
ASSETS_DIR = BASE_DIR / "dashboard" / "assets"
LOGOS_DIR = ASSETS_DIR / "logos"
CONSOLES_DIR = ASSETS_DIR / "consoles"

def init_environment():
    """Crea la estructura de directorios necesaria si no existe."""
    for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, DATABASE_DIR, ASSETS_DIR, LOGOS_DIR, CONSOLES_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    print("Inicializando entorno de directorios...")
    init_environment()
    print("¡Estructura de carpetas lista!")
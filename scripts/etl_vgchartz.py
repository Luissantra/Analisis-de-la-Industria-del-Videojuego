"""
etl_vgchartz.py — ETL de datos de ventas desde VGChartz.

Lee el CSV crudo de VGChartz (~64K filas), limpia y transforma los datos,
cruza títulos con la tabla `games` existente (RAWG) y carga tres objetos
en la base de datos SQLite:

  1. `game_sales`     — ventas por consola (detalle).
  2. `game_sales_agg` — ventas agregadas por título (suma entre consolas).
  3. `v_games_sales`  — vista que une `games` con `game_sales_agg`.
"""

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

log = config.get_logger("etl_vgchartz")

# ─── Ruta al CSV crudo ─────────────────────────────────────────────
VGCHARTZ_CSV = config.RAW_DATA_DIR / "vgchartz-2024.csv"


# ── Extracción & limpieza ──────────────────────────────────────────
def _extract(csv_path: Path) -> pd.DataFrame:
    """Lee el CSV crudo y devuelve un DataFrame sin procesar."""
    log.info("Leyendo CSV: %s", csv_path)
    df = pd.read_csv(csv_path, encoding="utf-8")
    log.info("Filas leídas: %d | Columnas: %s", len(df), list(df.columns))
    return df


def _transform(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica todas las transformaciones de limpieza al DataFrame."""

    filas_iniciales = len(df)

    # 1. Eliminar filas sin ventas totales o con ventas = 0
    df = df.dropna(subset=["total_sales"])
    df = df[df["total_sales"] > 0].copy()
    log.info(
        "Filas tras filtrar total_sales > 0: %d (eliminadas: %d)",
        len(df),
        filas_iniciales - len(df),
    )

    # 2. Normalizar título (strip + proper case)
    df["title"] = df["title"].astype(str).str.strip().str.title()

    # 3. Extraer release_year desde release_date
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    df["release_year"] = df["release_date"].dt.year
    df["release_year"] = df["release_year"].where(df["release_year"].notna(), None)
    # Convertir a Int64 (nullable integer) para evitar floats
    df["release_year"] = df["release_year"].astype("Int64")

    fechas_nulas = df["release_year"].isna().sum()
    log.info("Fechas parseadas — sin año válido: %d", fechas_nulas)

    # 4. Convertir critic_score de escala 0-10 → 0-100
    df["critic_score"] = pd.to_numeric(df["critic_score"], errors="coerce") * 10

    # 5. Limpiar columnas de texto opcionales
    for col in ["console", "genre", "publisher", "developer"]:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"nan": None, "": None})

    # 6. Seleccionar y ordenar columnas finales
    columnas = [
        "title", "console", "genre", "publisher", "developer",
        "critic_score", "total_sales", "na_sales", "jp_sales",
        "pal_sales", "other_sales", "release_year",
    ]
    df = df[columnas].reset_index(drop=True)

    log.info("Transformación completada — filas resultantes: %d", len(df))
    return df


# ── Matching con tabla games (RAWG) ───────────────────────────────
def _match_rawg_ids(df: pd.DataFrame, engine) -> pd.DataFrame:
    """Cruza títulos de VGChartz con la tabla `games` por LOWER(title)."""

    log.info("Iniciando matching con tabla `games` (RAWG)...")

    with engine.connect() as conn:
        # Verificar que la tabla games existe
        check = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
        ).fetchone()
        if not check:
            log.warning("La tabla `games` no existe — se omite el matching.")
            df["rawg_game_id"] = None
            return df

        # Leer pares (rawg_id, title) de la tabla games
        df_games = pd.read_sql(
            "SELECT rawg_id, title FROM games", conn
        )

    if df_games.empty:
        log.warning("La tabla `games` está vacía — se omite el matching.")
        df["rawg_game_id"] = None
        return df

    # Crear diccionario LOWER(title) → rawg_id para lookup rápido
    rawg_lookup = (
        df_games
        .drop_duplicates(subset=["title"], keep="first")
        .set_index(df_games["title"].str.lower())["rawg_id"]
        .to_dict()
    )

    # Matching por LOWER(title)
    df["rawg_game_id"] = df["title"].str.lower().map(rawg_lookup)

    matched = df["rawg_game_id"].notna().sum()
    log.info(
        "Matching completado — %d de %d juegos enlazados (%.1f%%)",
        matched, len(df), 100 * matched / len(df) if len(df) else 0,
    )
    return df


# ── Agregación por título ──────────────────────────────────────────
def _aggregate_by_title(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega ventas por título (sumando consolas)."""

    log.info("Agregando ventas por título...")

    # Columnas numéricas a sumar
    sum_cols = ["total_sales", "na_sales", "jp_sales", "pal_sales", "other_sales"]

    agg_dict = {col: "sum" for col in sum_cols}
    agg_dict["genre"] = "first"
    agg_dict["publisher"] = "first"
    agg_dict["developer"] = "first"
    agg_dict["release_year"] = "min"
    agg_dict["critic_score"] = "max"
    agg_dict["rawg_game_id"] = lambda x: x.dropna().iloc[0] if x.dropna().any() else None

    df_agg = df.groupby("title", as_index=False).agg(agg_dict)

    # Renombrar para claridad
    df_agg = df_agg.rename(columns={
        "release_year": "first_release_year",
        "critic_score": "best_critic_score",
    })

    log.info("Títulos únicos agregados: %d", len(df_agg))
    return df_agg


# ── Carga en SQLite ────────────────────────────────────────────────
def _load(df_detail: pd.DataFrame, df_agg: pd.DataFrame, engine):
    """Carga las tablas game_sales, game_sales_agg y la vista v_games_sales."""

    with engine.begin() as conn:
        # ── game_sales (detalle por consola) ───────────────────
        log.info("Cargando tabla `game_sales` (%d filas)...", len(df_detail))
        df_detail.to_sql("game_sales", conn, if_exists="replace", index=False)

        # Agregar id autoincremental y FK (SQLite lo hace con ROWID)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS _game_sales_tmp (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                console     TEXT,
                genre       TEXT,
                publisher   TEXT,
                developer   TEXT,
                critic_score REAL,
                total_sales REAL,
                na_sales    REAL,
                jp_sales    REAL,
                pal_sales   REAL,
                other_sales REAL,
                release_year INTEGER,
                rawg_game_id INTEGER REFERENCES games(rawg_id)
            )
        """))
        conn.execute(text("INSERT INTO _game_sales_tmp SELECT rowid, * FROM game_sales"))
        conn.execute(text("DROP TABLE game_sales"))
        conn.execute(text("ALTER TABLE _game_sales_tmp RENAME TO game_sales"))
        log.info("Tabla `game_sales` creada con PRIMARY KEY AUTOINCREMENT.")

        # ── game_sales_agg (agregado por título) ──────────────
        log.info("Cargando tabla `game_sales_agg` (%d filas)...", len(df_agg))
        df_agg.to_sql("game_sales_agg", conn, if_exists="replace", index=False)
        log.info("Tabla `game_sales_agg` creada.")

        # ── Vista v_games_sales ────────────────────────────────
        conn.execute(text("DROP VIEW IF EXISTS v_games_sales"))
        conn.execute(text("""
            CREATE VIEW v_games_sales AS
            SELECT
                g.rawg_id,
                g.title           AS rawg_title,
                g.slug,
                g.metacritic,
                g.rawg_rating,
                g.rawg_ratings_count,
                g.playtime_hours,
                g.genres          AS rawg_genres,
                g.platforms       AS rawg_platforms,
                g.esrb_rating,
                a.title           AS vgc_title,
                a.total_sales,
                a.na_sales,
                a.jp_sales,
                a.pal_sales,
                a.other_sales,
                a.genre           AS vgc_genre,
                a.publisher       AS vgc_publisher,
                a.developer       AS vgc_developer,
                a.first_release_year,
                a.best_critic_score
            FROM games g
            INNER JOIN game_sales_agg a
                ON g.rawg_id = a.rawg_game_id
        """))
        log.info("Vista `v_games_sales` creada.")


# ── Función principal ──────────────────────────────────────────────
def run_vgchartz_etl():
    """Ejecuta el pipeline ETL completo de VGChartz."""

    log.info("=" * 60)
    log.info("Iniciando ETL de VGChartz...")
    log.info("=" * 60)

    config.init_environment()

    if not VGCHARTZ_CSV.exists():
        log.error("No se encontró el CSV: %s", VGCHARTZ_CSV)
        return

    engine = create_engine(f"sqlite:///{config.DATABASE_PATH}")

    # ── E: Extracción ──────────────────────────────────────────
    df = _extract(VGCHARTZ_CSV)

    # ── T: Transformación ──────────────────────────────────────
    df = _transform(df)

    # ── Matching con RAWG ──────────────────────────────────────
    df = _match_rawg_ids(df, engine)

    # ── Agregación ─────────────────────────────────────────────
    df_agg = _aggregate_by_title(df)

    # ── L: Carga ───────────────────────────────────────────────
    _load(df, df_agg, engine)

    # ── Resumen final ──────────────────────────────────────────
    log.info("=" * 60)
    log.info("ETL de VGChartz completado exitosamente.")
    log.info("  Filas en game_sales:     %d", len(df))
    log.info("  Filas en game_sales_agg: %d", len(df_agg))
    log.info("  Juegos con rawg_game_id: %d", df["rawg_game_id"].notna().sum())
    log.info("=" * 60)

    engine.dispose()


if __name__ == "__main__":
    run_vgchartz_etl()

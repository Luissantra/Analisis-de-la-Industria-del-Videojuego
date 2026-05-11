"""
enrich_studios.py — Enriquece notable_studios con city/country reales.

Fuentes de datos (en orden de prioridad):
  1. Curated fallback dictionary (datos manuales verificados)
  2. IGDB country code (ISO 3166-1 numérico → nombre de país)
  3. IGDB description text mining (extrae city/country de descripciones)
"""

import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

log = config.get_logger("enrich_studios")

# ─── ISO 3166-1 Numeric → Country Name ────────────────────────────
ISO_COUNTRY_MAP = {
    32: "Argentina", 36: "Australia", 40: "Austria", 56: "Belgium",
    76: "Brazil", 100: "Bulgaria", 124: "Canada", 152: "Chile",
    156: "China", 170: "Colombia", 191: "Croatia", 196: "Cyprus",
    203: "Czech Republic", 208: "Denmark", 233: "Estonia", 246: "Finland",
    250: "France", 276: "Germany", 300: "Greece", 344: "Hong Kong",
    348: "Hungary", 352: "Iceland", 356: "India", 360: "Indonesia",
    372: "Ireland", 376: "Israel", 380: "Italy", 392: "Japan",
    410: "South Korea", 428: "Latvia", 440: "Lithuania", 442: "Luxembourg",
    458: "Malaysia", 484: "Mexico", 528: "Netherlands", 554: "New Zealand",
    578: "Norway", 616: "Poland", 620: "Portugal", 642: "Romania",
    643: "Russia", 702: "Singapore", 703: "Slovakia", 705: "Slovenia",
    710: "South Africa", 724: "Spain", 752: "Sweden", 756: "Switzerland",
    158: "Taiwan", 764: "Thailand", 792: "Turkey", 804: "Ukraine",
    826: "United Kingdom", 840: "United States", 858: "Uruguay",
    862: "Venezuela", 704: "Vietnam",
}

# ─── Curated Fallback: manual city/country for studios IGDB doesn't cover well
CURATED_STUDIOS = {
    "Arkane Studios": ("Lyon", "France"),
    "Beenox": ("Québec City", "Canada"),
    "Bethesda Game Studios": ("Rockville", "United States"),
    "Blizzard Entertainment": ("Irvine", "United States"),
    "Compulsion Games": ("Montréal", "Canada"),
    "Demonware": ("Dublin", "Ireland"),
    "Double Fine Productions": ("San Francisco", "United States"),
    "Halo Studios": ("Redmond", "United States"),
    "High Moon Studios": ("Carlsbad", "United States"),
    "id Software": ("Richardson", "United States"),
    "Infinity Ward": ("Woodland Hills", "United States"),
    "InXile Entertainment": ("Tustin", "United States"),
    "King": ("Stockholm", "Sweden"),
    "MachineGames": ("Uppsala", "Sweden"),
    "Mojang Studios": ("Stockholm", "Sweden"),
    "Ninja Theory": ("Cambridge", "United Kingdom"),
    "Obsidian Entertainment": ("Irvine", "United States"),
    "Playground Games": ("Leamington Spa", "United Kingdom"),
    "Rare": ("Twycross", "United Kingdom"),
    "Raven Software": ("Madison", "United States"),
    "Sledgehammer Games": ("Foster City", "United States"),
    "The Coalition": ("Vancouver", "Canada"),
    "Treyarch": ("Santa Monica", "United States"),
    "Turn 10 Studios": ("Redmond", "United States"),
    "Undead Labs": ("Orlando", "United States"),
    "World's Edge": ("Redmond", "United States"),
    "Xbox Game Studios Publishing": ("Redmond", "United States"),
    "Guerrilla Games": ("Amsterdam", "Netherlands"),
    "Naughty Dog": ("Santa Monica", "United States"),
    "Insomniac Games": ("Burbank", "United States"),
    "Santa Monica Studio": ("Los Angeles", "United States"),
    "Sucker Punch Productions": ("Bellevue", "United States"),
    "Polyphony Digital": ("Tokyo", "Japan"),
    "Media Molecule": ("Guildford", "United Kingdom"),
    "Housemarque": ("Helsinki", "Finland"),
    "Bluepoint Games": ("Austin", "United States"),
    "Firesprite": ("Liverpool", "United Kingdom"),
    "Bungie": ("Bellevue", "United States"),
    "Haven Studios": ("Montréal", "Canada"),
    "Bend Studio": ("Bend", "United States"),
    "Valkyrie Entertainment": ("Seattle", "United States"),
    "Riot Games": ("Los Angeles", "United States"),
    "Supercell": ("Helsinki", "Finland"),
    "Grinding Gear Games": ("Auckland", "New Zealand"),
    "Funcom": ("Oslo", "Norway"),
    "Klei Entertainment": ("Vancouver", "Canada"),
    "Digital Extremes": ("London", "Canada"),
    "Miniclip": ("Neuchâtel", "Switzerland"),
    "Sharkmob": ("Malmö", "Sweden"),
    "10 Chambers": ("Stockholm", "Sweden"),
    "Turtle Rock Studios": ("Lake Forest", "United States"),
    "1-UP Studio": ("Tokyo", "Japan"),
    "Nintendo EPD": ("Kyoto", "Japan"),
    "Retro Studios": ("Austin", "United States"),
    "Intelligent Systems": ("Kyoto", "Japan"),
    "HAL Laboratory": ("Tokyo", "Japan"),
    "Monolith Soft": ("Tokyo", "Japan"),
    "Game Freak": ("Tokyo", "Japan"),
    "Next Level Games": ("Vancouver", "Canada"),
    "Rockstar Games": ("New York City", "United States"),
    "Rockstar North": ("Edinburgh", "United Kingdom"),
    "2K Games": ("Novato", "United States"),
    "Firaxis Games": ("Sparks", "United States"),
    "Hangar 13": ("Novato", "United States"),
    "Visual Concepts": ("Novato", "United States"),
    "Cloud Chamber": ("Novato", "United States"),
    "31st Union": ("San Mateo", "United States"),
    "Ubisoft Montréal": ("Montréal", "Canada"),
    "Ubisoft Paris": ("Montreuil", "France"),
    "Ubisoft Toronto": ("Toronto", "Canada"),
    "Massive Entertainment": ("Malmö", "Sweden"),
    "Blue Byte": ("Düsseldorf", "Germany"),
    "Ubisoft Annecy": ("Annecy", "France"),
    "Ubisoft Québec": ("Québec City", "Canada"),
    "Ubisoft Bordeaux": ("Bordeaux", "France"),
    "Ubisoft San Francisco": ("San Francisco", "United States"),
    "Ubisoft Bucharest": ("Bucharest", "Romania"),
    "Ubisoft Pune": ("Pune", "India"),
    "Amplitude Studios": ("Paris", "France"),
    "Creative Assembly": ("Horsham", "United Kingdom"),
    "Ryu Ga Gotoku Studio": ("Tokyo", "Japan"),
    "Atlus": ("Tokyo", "Japan"),
    "Sports Interactive": ("London", "United Kingdom"),
    "Capcom": ("Osaka", "Japan"),
    "Bandai Namco Studios": ("Tokyo", "Japan"),
    "FromSoftware": ("Tokyo", "Japan"),
    "Respawn Entertainment": ("Sherman Oaks", "United States"),
    "Criterion Games": ("Guildford", "United Kingdom"),
    "EA Motive": ("Montréal", "Canada"),
    "EA Sports": ("Redwood City", "United States"),
    "Maxis": ("Redwood City", "United States"),
    "Codemasters": ("Southam", "United Kingdom"),
    "BioWare": ("Edmonton", "Canada"),
    "DICE": ("Stockholm", "Sweden"),
    "Ripple Effect Studios": ("Los Angeles", "United States"),
    "Cliffhanger Games": ("Seattle", "United States"),
    "Epic Games": ("Cary", "United States"),
    "Psyonix": ("San Diego", "United States"),
    "NetherRealm Studios": ("Chicago", "United States"),
    "TT Games": ("Maidenhead", "United Kingdom"),
    "Monolith Productions": ("Kirkland", "United States"),
    "Rocksteady Studios": ("London", "United Kingdom"),
    "Avalanche Software": ("Salt Lake City", "United States"),
    "Back 4 Blood": ("Lake Forest", "United States"),
    "Krafton": ("Seoul", "South Korea"),
    "PUBG Studios": ("Seoul", "South Korea"),
    "Bluehole Studio": ("Seoul", "South Korea"),
    "Striking Distance Studios": ("San Ramon", "United States"),
    "Unknown Worlds Entertainment": ("San Francisco", "United States"),
    "Dreamhaven": ("Irvine", "United States"),
    "Eidos-Montréal": ("Montréal", "Canada"),
    "Crystal Dynamics": ("San Mateo", "United States"),
    "Square Enix": ("Tokyo", "Japan"),
    "IO Interactive": ("Copenhagen", "Denmark"),
    "Dontnod Entertainment": ("Paris", "France"),
    "Asobo Studio": ("Bordeaux", "France"),
    "Larian Studios": ("Ghent", "Belgium"),
    "CD Projekt Red": ("Warsaw", "Poland"),
    "Techland": ("Wrocław", "Poland"),
    "Wargaming": ("Nicosia", "Cyprus"),
    "Remedy Entertainment": ("Espoo", "Finland"),
    "Paradox Interactive": ("Stockholm", "Sweden"),
    "Avalanche Studios": ("Stockholm", "Sweden"),
    "Starbreeze Studios": ("Stockholm", "Sweden"),
    "Coffee Stain Studios": ("Skövde", "Sweden"),
    "Bohemia Interactive": ("Prague", "Czech Republic"),
    "ChopUp": ("New York City", "United States"),
    "Aquiris": ("Porto Alegre", "Brazil"),
}

# ─── Regex para extraer ciudad de descripciones IGDB ───────────────
# Patrones comunes: "based in <City>, <Country>" / "located in <City>"
CITY_PATTERNS = [
    re.compile(r"(?:based|located|headquartered|situated)\s+in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", re.IGNORECASE),
    re.compile(r"in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s+(California|Texas|Washington|New York|Florida|Oregon|Maryland|Massachusetts|Virginia|Illinois|Pennsylvania|Georgia|Ohio|Michigan|Colorado|Arizona|Minnesota|Wisconsin|North Carolina|Tennessee|Connecticut|Indiana|Missouri|Iowa|Utah|Nevada|Kansas|Nebraska|Oklahoma|Louisiana|Kentucky|Alabama|Maine|Hawaii|Idaho|Arkansas|Montana|Wyoming|Vermont|Delaware|Rhode Island|New Hampshire|South Dakota|North Dakota|West Virginia|Mississippi|Alaska|South Carolina|New Mexico)", re.IGNORECASE),
]


def _extract_city_from_description(description: str) -> tuple:
    """Intenta extraer (city, country) de una descripción de IGDB."""
    if not description or pd.isna(description):
        return None, None
    for pattern in CITY_PATTERNS:
        match = pattern.search(description)
        if match:
            return match.group(1).strip(), match.group(2).strip()
    return None, None


def run_enrichment():
    """Enriquece notable_studios con city/country reales."""
    log.info("Iniciando enriquecimiento de estudios notables...")

    conn = sqlite3.connect(config.DATABASE_PATH)

    # Leer estudios que necesitan enriquecimiento
    df_studios = pd.read_sql_query(
        "SELECT id, name, city, country FROM notable_studios", conn
    )
    # Leer datos IGDB disponibles
    try:
        df_igdb = pd.read_sql_query(
            "SELECT internal_id, igdb_country, igdb_description FROM master_studios",
            conn,
        )
    except Exception:
        df_igdb = pd.DataFrame()
        log.warning("No se encontró la tabla master_studios. Solo se usará el diccionario curado.")

    total = len(df_studios)
    enriched = 0
    cursor = conn.cursor()

    for _, row in df_studios.iterrows():
        studio_id = row["id"]
        name = row["name"]
        current_city = row["city"]
        current_country = row["country"]

        # Saltar si ya tiene datos válidos
        if (
            current_city
            and current_country
            and current_city not in ("Desconocida", "N/A", "")
            and current_country not in ("Desconocido", "N/A", "")
        ):
            continue

        new_city, new_country = None, None

        # ── Fuente 1: Diccionario curado ───────────────────────
        if name in CURATED_STUDIOS:
            new_city, new_country = CURATED_STUDIOS[name]

        # ── Fuente 2: IGDB country code ────────────────────────
        if not new_country and not df_igdb.empty:
            igdb_row = df_igdb[df_igdb["internal_id"] == studio_id]
            if not igdb_row.empty:
                country_code = igdb_row.iloc[0].get("igdb_country")
                if pd.notna(country_code):
                    country_code = int(float(country_code))
                    new_country = ISO_COUNTRY_MAP.get(country_code)

                # ── Fuente 3: Descripción IGDB ─────────────────
                if not new_city:
                    desc = igdb_row.iloc[0].get("igdb_description", "")
                    desc_city, desc_country = _extract_city_from_description(desc)
                    if desc_city:
                        new_city = desc_city
                    if desc_country and not new_country:
                        new_country = desc_country

        # Aplicar la actualización si encontramos algo
        if new_city or new_country:
            final_city = new_city or current_city
            final_country = new_country or current_country
            cursor.execute(
                "UPDATE notable_studios SET city = ?, country = ? WHERE id = ?",
                (final_city, final_country, studio_id),
            )
            enriched += 1
            log.info("  ✅ %s → %s, %s", name, final_city, final_country)

    conn.commit()
    conn.close()

    log.info(
        "Enriquecimiento completado. %d de %d estudios actualizados (%d ya tenían datos).",
        enriched, total, total - enriched - (total - enriched),
    )


if __name__ == "__main__":
    run_enrichment()

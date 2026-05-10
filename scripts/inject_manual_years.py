import sqlite3
import sys
from pathlib import Path

root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import config

# Base de conocimiento manual masiva (Año de Adquisición o Fundación)
YEARS_DATA = {
    # 🟢 MICROSOFT XBOX & ZENIMAX & ACTIVISION
    "Bethesda": "2021",
    "Obsidian": "2018",
    "Playground": "2018",
    "Ninja Theory": "2018",
    "Double Fine": "2019",
    "InXile": "2018",
    "Compulsion": "2018",
    "Undead Labs": "2018",
    "Turn 10": "2001",
    "Halo Studios": "2007",
    "The Coalition": "2010",
    "Mojang": "2014",
    "Rare": "2002",
    "MachineGames": "2021",
    "Arkane": "2021",
    "id Software": "2021",
    "Tango Gameworks": "2021",
    "ZeniMax Online": "2021",
    "Blizzard": "2023",
    "King": "2023",
    "Infinity Ward": "2023",
    "Treyarch": "2023",
    "Sledgehammer": "2023",
    "Raven Software": "2023",
    "High Moon": "2023",
    "Beenox": "2023",
    "Demonware": "2023",
    
    # 🔵 SONY PLAYSTATION
    "Naughty Dog": "2001",
    "Santa Monica": "1999",
    "Polyphony": "1998",
    "Guerrilla": "2005",
    "Sucker Punch": "2011",
    "Insomniac": "2019",
    "Bend Studio": "2000",
    "Media Molecule": "2010",
    "Housemarque": "2021",
    "Bluepoint": "2021",
    "Firesprite": "2021",
    "Team Asobi": "2012",
    "Valkyrie": "2021",
    "Haven": "2022",
    "Bungie": "2022",

    # 🔴 NINTENDO
    "Retro Studios": "2002",
    "Monolith Soft": "2007",
    "NDcube": "2001",
    "Next Level Games": "2021",
    "SRD": "2022",
    "Shiver": "2024",
    "1-UP Studio": "2013",

    # 🟠 ELECTRONIC ARTS (EA)
    "BioWare": "2007",
    "DICE": "2006",
    "Respawn": "2017",
    "Criterion": "2004",
    "Codemasters": "2021",
    "Maxis": "1997",
    "EA Motive": "2015",
    "Ripple Effect": "2000",
    "Cliffhanger": "2021",

    # ⚪ TAKE-TWO INTERACTIVE
    "Rockstar": "1998",
    "Firaxis": "2005",
    "Ghost Story": "2017",
    "Hangar 13": "2014",
    "Visual Concepts": "2005",
    "31st Union": "2019",
    "Cloud Chamber": "2019",
    "Zynga": "2022",
    "Gearbox": "2024",

    # 🟣 TENCENT
    "Riot Games": "2011",
    "Supercell": "2016",
    "Epic Games": "2012",
    "Funcom": "2020",
    "Sharkmob": "2019",
    "Klei": "2021",
    "Fatshark": "2021",
    "Grinding Gear": "2018",
    "Digital Extremes": "2020",
    "Splash Damage": "2020",
    "Turtle Rock": "2021"
}

def run_injection():
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()
    print("💉 Inyectando base de conocimiento histórico en la Base de Datos...\n")
    for studio, year in YEARS_DATA.items():
        cursor.execute("UPDATE notable_studios SET acquisition_year = ? WHERE name LIKE ?", (year, f"%{studio}%"))
    conn.commit()
    conn.close()
    print("✅ Inyección completada con éxito.")

if __name__ == "__main__":
    run_injection()
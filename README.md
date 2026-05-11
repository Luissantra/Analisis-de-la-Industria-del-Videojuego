# Industria del Videojuego: Análisis de Datos (v3)

Este proyecto es un pipeline de datos end-to-end y un dashboard interactivo que analiza la industria global de los videojuegos. Ha sido refactorizado para utilizar esquemas relacionales consolidados (pasando de un prototipo de resumen a una arquitectura de granularidad por juego).

## Características Principales

1. **Catálogo Real de Juegos:** Extrae hasta ~15,000 juegos en detalle de la API de RAWG utilizando IDs de desarrolladores (metacritic, géneros, calificaciones comunitarias).
2. **Mapa Geográfico:** +6,400 estudios geolocalizados a nivel mundial.
3. **Capa Corporativa Consolidada:** Mapeo de Master Data Management (MDM) usando IGDB para reconstruir la jerarquía corporativa (Conglomerado -> Estudio).
4. **Análisis de Discrepancias:** Cuantificación del fenómeno de *Review Bombing* cruzando puntajes de crítica experta vs. votos de usuarios.
5. **Dashboard Interactivo:** UI diseñada en Streamlit con visualizaciones avanzadas en Plotly (Sunburst, Treemaps, Mapas base folium).

## Diagrama de la Base de Datos

La base de datos SQLite generada (`videogames.db`) sigue un esquema de copo de nieve:

- `conglomerates`: Principales publishers de la industria (Ej: Microsoft Gaming).
- `notable_studios`: Estudios vinculados a un conglomerado.
- `developers_rawg`: Puente de mapeo (ID local -> API externa).
- `games`: Catálogo granular de títulos por desarrollador.
- `studio_locations`: Coordenadas geográficas globales.
- `stock_prices`: Datos bursátiles históricos.
- `platforms`: Metadatos sobre consolas y ciclos de vida.
- **`dim_studios_corporate`**: Vista materializada para el Dashboard que pre-calcula métricas de juegos y geografía por estudio.

## Requisitos y Configuración

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Crea un archivo `.env` en la raíz con las siguientes variables (obtenidas del portal de desarrolladores de IGDB y RAWG):

```env
IGDB_CLIENT_ID=tu_client_id
IGDB_CLIENT_SECRET=tu_client_secret
RAWG_API_KEY=tu_api_key
```

## Ejecución del Pipeline

Para generar la base de datos desde cero:

```bash
python main.py
```

Flags disponibles para desarrollo rápido:
- `--skip-extract`: Salta el scraping base (usa lo que esté en `/data/raw/`).
- `--skip-games`: Evita llamar a RAWG (ideal para pruebas rápidas).
- `--force-games`: Obliga a re-descargar todos los juegos mapeados.

## Lanzar el Dashboard

Una vez construida la base de datos, ejecuta:

```bash
streamlit run dashboard/app.py
```
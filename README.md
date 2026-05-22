# 🎮 Análisis de la Industria del Videojuego — Dashboard Interactivo

Dashboard analítico interactivo construido con **Streamlit** y **Plotly** que explora la industria global del videojuego desde 7 dimensiones complementarias, alimentado por un pipeline ETL end-to-end que integra 6 fuentes de datos heterogéneas en una base de datos relacional SQLite.

---

## 📋 Índice

- [Características Principales](#-características-principales)
- [Dimensiones de Análisis](#-dimensiones-de-análisis)
- [Arquitectura del Pipeline ETL](#-arquitectura-del-pipeline-etl)
- [Fuentes de Datos](#-fuentes-de-datos)
- [Esquema de Base de Datos](#-esquema-de-base-de-datos)
- [Requisitos y Configuración](#-requisitos-y-configuración)
- [Ejecución](#-ejecución)
- [Estructura del Repositorio](#-estructura-del-repositorio)
- [Documentación](#-documentación)

---

## ✨ Características Principales

1. **Pipeline ETL Completo**: Extracción automatizada desde 6 fuentes (RAWG, IGDB, VGChartz, GameDevMap, yfinance, datos sectoriales), con geocodificación, enriquecimiento corporativo y carga en SQLite.
2. **+200.000 Registros Integrados**: 17.570 registros de ventas, 6.642 estudios geolocalizados, 4.499 juegos catalogados, 163.709 cotizaciones bursátiles.
3. **7 Módulos Analíticos**: Visión Global, Mapa Geográfico, Plataformas, Mercado Financiero, Estructura Corporativa, Comunidad y Recepción, Salón de la Fama.
4. **Diseño Premium**: Glassmorfismo oscuro, paletas semánticas, animaciones dinámicas (Bar Chart Race), cuadrantes estratégicos tipo Gartner.
5. **Interactividad Avanzada**: Filtros dinámicos, tooltips enriquecidos, zoom en mapas, animaciones temporales con Play/Pause.

---

## 🔍 Dimensiones de Análisis

| Dimensión | Módulo | Visualizaciones principales |
|---|---|---|
| 🌍 **Visión Global** | `view_global.py` | Comparativa intersectorial, Stacked Area Chart de géneros, Scatter de portfolio, **Bar Chart Race de ventas acumuladas** |
| 🗺️ **Mapa de Estudios** | `view_map.py` | Mapa Folium con clusters (6.642 estudios), Choropleth de ingresos (Tealgrn), Treemap regional, ARPU heatmap (YlOrRd), KPIs semánticos |
| 🕹️ **Plataformas** | `view_platforms.py` | Timeline Gantt de consolas, Ranking de ventas, Distribución de catálogo |
| 📈 **Mercado Financiero** | `view_market.py` | Series temporales OHLCV, Retorno acumulado, Benchmarks (S&P 500, Nasdaq Composite) |
| 🏢 **Estructura Corporativa** | `view_corporate.py` | Sunburst jerárquico, Galería de logos, **Cuadrante Mágico** (12 conglomerados), Treemap de portfolio |
| 🗣️ **Comunidad** | `view_community.py` | Scatter Crítica vs. Usuario, Review Bombing Index, **Cuadrante del Hype** (ventas × calidad × popularidad) |
| 🏆 **Salón de la Fama** | `view_hall_of_fame.py` | Tarjetas con carátulas RAWG, rankings de excelencia |

---

## 🏗️ Arquitectura del Pipeline ETL

```
                         main.py (Orquestador)
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
    FASE 1: Extracción   FASE 2: Enriquecimiento  FASE 3: Transformación
    ┌─────────────┐      ┌─────────────────┐      ┌─────────────────┐
    │ yfinance    │      │ IGDB API (MDM)  │      │ Geocodificación │
    │ GameDevMap  │      │ RAWG API (juegos)│     │ Normalización   │
    │ Logos       │      │ Enrich studios  │      │ Plataformas     │
    └─────────────┘      └─────────────────┘      └─────────────────┘
                              │
                    ┌─────────┼─────────┐
                    ▼                   ▼
             FASE 4: Carga       FASE 5: Auditoría
             ┌───────────┐       ┌───────────────┐
             │ build_db  │       │ audit_data    │
             │ → SQLite  │       │ → Validación  │
             └───────────┘       └───────────────┘
```

---

## 📊 Fuentes de Datos

| Fuente | Tipo | Script | Registros | Descripción |
|---|---|---|---|---|
| **RAWG** | API REST | `etl_games_rawg.py` | 4.499 | Catálogo de juegos: metadatos, géneros, Metacritic, ratings, playtime |
| **IGDB** | API REST (Twitch) | `etl_igdb.py` | 197 | Jerarquía corporativa: empresa matriz, logo, descripción, juego estrella |
| **VGChartz** | CSV (Kaggle) | `etl_vgchartz.py` | 17.570 | Ventas históricas por consola con desglose regional (NA/JP/PAL/Other) |
| **GameDevMap** | Web Scraping | `get_gameDevMap.py` | 6.642 | Geolocalización GPS de estudios de desarrollo worldwide |
| **Yahoo Finance** | API (yfinance) | `get_market_data.py` | 163.709 | Cotizaciones diarias OHLCV de 26 empresas gaming + 2 índices benchmark |
| **Manual/Config** | JSON curado | — | — | Datos de mercado global, plataformas, comparativas sectoriales |

---

## 🗄️ Esquema de Base de Datos

La base de datos SQLite (`data/database/videogames.db`) sigue un **esquema de copo de nieve**:

| Tabla | Filas | Rol |
|---|---:|---|
| `conglomerates` | 12 | Dimensión: grupos corporativos principales |
| `notable_studios` | 197 | Dimensión: estudios vinculados a conglomerados |
| `developers_rawg` | 193 | Puente: mapeo interno → RAWG developer ID |
| `games` | 4.499 | Hechos: catálogo granular con metadatos RAWG |
| `game_sales` | 17.570 | Hechos: ventas por título/consola (VGChartz) |
| `game_sales_agg` | 11.999 | Agregado: ventas consolidadas por título |
| `studio_locations` | 6.642 | Dimensión geográfica: coordenadas GPS |
| `stock_prices` | 163.709 | Serie temporal: cotizaciones diarias OHLCV |
| `platforms` | 27 | Dimensión: consolas con ventas y generación |
| `dim_studios_corporate` | 201 | Vista materializada: métricas pre-calculadas |

---

## ⚙️ Requisitos y Configuración

### Prerequisitos

- **Python 3.10+**
- **pip** (gestor de paquetes)

### Instalación

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd "Análisis de la industria del videojuego"

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

### Configuración de APIs

Crear un archivo `.env` en la raíz con las siguientes variables (necesarias solo para ejecutar el pipeline de extracción):

```env
IGDB_CLIENT_ID=tu_client_id
IGDB_CLIENT_SECRET=tu_client_secret
RAWG_API_KEY=tu_api_key
```

> **Nota**: Si la base de datos `videogames.db` ya está generada, no necesitas las claves API para lanzar el dashboard.

---

## 🚀 Ejecución

### Pipeline ETL (Generación de datos)

```bash
python main.py                        # Pipeline completo
python main.py --skip-extract         # Reutilizar datos crudos existentes
python main.py --skip-games           # Saltar la descarga de RAWG
python main.py --skip-transform       # Saltar transformaciones (fases 2 y 3)
python main.py --force-games          # Forzar re-descarga de todos los juegos
```

### Dashboard (Visualización)

```bash
streamlit run dashboard/app.py
```

El dashboard se abrirá automáticamente en `http://localhost:8501`.

---

## 📁 Estructura del Repositorio

```
.
├── config.py                 # Configuración centralizada (rutas, logger, API keys)
├── main.py                   # Orquestador del pipeline ETL (5 fases)
├── requirements.txt          # Dependencias Python
├── .env                      # Variables de entorno (no versionado)
│
├── scripts/                  # Módulos ETL
│   ├── get_gameDevMap.py     # Scraper de GameDevMap (geolocalización)
│   ├── get_market_data.py    # Descarga de datos bursátiles (yfinance)
│   ├── etl_igdb.py           # ETL de jerarquía corporativa (IGDB/Twitch)
│   ├── etl_games_rawg.py     # ETL de catálogo de juegos (RAWG API)
│   ├── etl_vgchartz.py       # ETL de ventas históricas (VGChartz CSV)
│   ├── etl_gameDevMap.py     # Transformación de datos geográficos
│   ├── etl_platforms.py      # ETL de plataformas/consolas
│   ├── enrich_studios.py     # Enriquecimiento de estudios (RAWG × IGDB)
│   ├── geocode_notables.py   # Geocodificación de estudios notables
│   ├── build_db.py           # Constructor de la base de datos SQLite
│   ├── download_logos.py     # Descarga de logos corporativos
│   └── audit_data.py         # Auditoría de calidad de datos
│
├── dashboard/                # Módulos de visualización (Streamlit + Plotly)
│   ├── app.py                # Punto de entrada del dashboard
│   ├── view_global.py        # Visión Global de la Industria
│   ├── view_map.py           # Mapa Geográfico (Producción + Mercado)
│   ├── view_platforms.py     # Evolución de Plataformas
│   ├── view_market.py        # Análisis de Mercado Financiero
│   ├── view_corporate.py     # Estructura Corporativa
│   ├── view_community.py     # Comunidad y Recepción
│   ├── view_hall_of_fame.py  # Salón de la Fama
│   ├── charts.py             # Gráficos compartidos
│   ├── charts_global.py      # Gráficos de Visión Global
│   ├── charts_corporate.py   # Gráficos Corporativos (Sunburst, Cuadrante)
│   ├── charts_community.py   # Gráficos de Comunidad (Hype, Review Bombing)
│   ├── charts_market.py      # Gráficos de Mercado Financiero
│   ├── charts_platforms.py   # Gráficos de Plataformas
│   ├── models.py             # Capa de acceso a datos
│   ├── model_corporate.py    # Queries corporativas
│   └── assets/               # Logos, imágenes de consolas
│
├── data/
│   ├── raw/                  # Datos crudos descargados
│   ├── processed/            # Datos transformados (MDM, geocoded)
│   └── database/             # videogames.db (SQLite ~25MB)
│
├── config_data/              # Archivos de configuración JSON
│   ├── tickers.json          # Tickers bursátiles y categorías
│   ├── platforms.json        # Metadatos de consolas
│   ├── market_visuals.json   # Datos de mercado global curados
│   ├── gaming_markets_geo.json # Coordenadas y metadatos de mercados geográficos
│   ├── goty_winners.json     # Listado histórico de ganadores del GOTY
│   └── industry_comparison.json # Comparativa intersectorial histórica
│
└── docs/                     # Documentación académica (Local, excluida en .gitignore)
    ├── memoria.tex           # Fuente LaTeX de la memoria académica
    └── memoria.pdf           # Memoria compilada (PDF)

```

---

## 💅 Últimas Mejoras y Refinamientos (Mayo 2026)

Se han implementado una serie de mejoras críticas para optimizar la usabilidad del dashboard y la fidelidad de sus análisis:
- **Gráfico Combinado de Expansión Corporativa:** Rediseño completo de la línea de tiempo corporativa (`charts_corporate.py`), combinando barras de incorporaciones anuales de estudios con una capa de área translúcida (15% de opacidad) que representa el crecimiento acumulado del grupo a lo largo del tiempo, bajo una experiencia interactiva `hovermode="x unified"`.
- **Resolución de Incompatibilidad de PyArrow:** Corrección del error de Pandas/PyArrow (`NotImplementedError`) que bloqueaba la renderización del gráfico al llamar a `.values.reshape` en tooltips con tipos de datos de Arrow. Ahora se maneja mediante `.to_numpy().reshape`, garantizando el correcto funcionamiento en el 100% de los conglomerados.
- **Rendimiento Bursátil por Defecto:** Modificación en el módulo financiero (`view_market.py`) para activar por defecto la métrica de **Rendimiento (%)** en lugar de Precio (USD), lo que simplifica la visualización comparativa de activos de distinta valoración nominal.
- **Visualización de Mapas Corregida:** Ampliación del margen izquierdo y habilitación de `automargin=True` en la gráfica horizontal de gasto medio anual por jugador (ARPU en `view_map.py`), impidiendo que nombres de países como **Japan** se vean recortados en el eje Y.
- **Comparativa Sectorial Aséptica:** Eliminación del recuadro informativo y de la anotación flotante del "Efecto pandemia" de 2020 en el gráfico intersectorial global (`charts_global.py` / `view_global.py`), priorizando una lectura macroeconómica libre de ruido visual.

---

## 📄 Documentación

La memoria académica completa del proyecto está disponible en [`docs/memoria.pdf`](docs/memoria.pdf). Incluye:

- Planteamiento del problema y objetivos
- Preparación de los datos (preprocesado)
- Procesado y análisis de cada dimensión
- Decisiones de diseño visual justificadas
- Discusión, conclusiones y posibles mejoras

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Framework UI | Streamlit |
| Gráficos interactivos | Plotly (Express + Graph Objects) |
| Mapas | Folium + streamlit-folium |
| Base de datos | SQLite |
| Pipeline ETL | Python (pandas, requests, BeautifulSoup, geopy, yfinance, SQLAlchemy) |
| Diseño visual | Glassmorfismo oscuro, paletas semánticas |

---

*Proyecto desarrollado para la asignatura de Visualización de Datos — Mayo 2026*

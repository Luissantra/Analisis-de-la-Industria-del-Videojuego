# 🎮 Análisis de la Industria del Videojuego

## 📖 Descripción General
Este proyecto es una herramienta de análisis de datos diseñada para estudiar la industria del videojuego desde dos dimensiones principales:
1. **Dimensión Geográfica:** Un mapa interactivo que visualiza la distribución y ubicación global de cientos de estudios de desarrollo.
2. **Dimensión de Mercado:** Un panel de análisis financiero avanzado que evalúa el rendimiento bursátil de las empresas más grandes del sector.

## 🏗️ Arquitectura y Estructura del Proyecto
El proyecto sigue una arquitectura clásica de tubería de datos ETL (Extracción, Transformación y Carga) que alimenta un dashboard analítico:

* **`main.py`**: El orquestador principal. Al ejecutarlo, corre todo el pipeline ETL y construye la base de datos local.
* **`config.py`**: Script de configuración que centraliza la creación de directorios y rutas a archivos clave (datos y base de datos).
* **`config_data/`**: Directorio con archivos estáticos en formato JSON que contienen diccionarios de tickers financieros, relación de estudios matrices, colores corporativos e hitos históricos para los gráficos.
* **`scripts/`**: Contiene la lógica del backend (ETL):
    * `get_gameDevMap.py` y `etl_gameDevMap.py`: Realizan scraping web, geocodificación mediante Nominatim y limpieza de datos geográficos.
    * `get_market_data.py`: Automatiza la descarga y el cálculo de rendimientos bursátiles utilizando la API de Yahoo Finance.
    * `build_db.py`: Toma los datos procesados en CSV y genera una base de datos SQLite (`videogames.db`).
* **`dashboard/`**: Contiene el código frontend desarrollado en Streamlit.
    * `app.py`: Punto de entrada a la interfaz web.
    * `view_map.py` y `charts.py`: Lógica para renderizar los mapas de clusters interactivos mediante Folium.
    * `view_market.py` y `charts_market.py`: Construcción de gráficas financieras complejas (comparativas y velas japonesas) utilizando Plotly.

## 🚀 Instalación y Uso

### 1. Preparar el Entorno
Se recomienda el uso de un entorno virtual para instalar las dependencias requeridas.
```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno (En Linux/Mac)
source venv/bin/activate
# Activar entorno (En Windows)
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Análisis de la Industria del Videojuego - Dashboard

Esta plataforma de Business Intelligence permite explorar la evolución histórica y comercial de la industria de los videojuegos. El sistema procesa datos de ventas y catálogos para ofrecer visualizaciones interactivas sobre el ciclo de vida de las consolas y el rendimiento de los fabricantes.

## 🚀 Características

- **Roadmap de Plataformas:** Visualización interactiva tipo línea de tiempo que organiza las consolas por fabricante.
- **Identidad Visual Consistente:** Sistema de colores predefinido para los principales actores de la industria (Sony, Nintendo, Microsoft, Sega, etc.).
- **Métricas Dinámicas:** Representación visual del éxito de mercado mediante el tamaño de burbujas, integrando ventas en millones y conteo de títulos disponibles.
- **Interfaz Profesional:** Gráficos optimizados con temas oscuros (`plotly_dark`), ejes limpios y tooltips informativos.

## 🛠️ Tecnologías Utilizadas

*   **Python 3.12+**
*   **Pandas:** Manipulación y limpieza de estructuras de datos.
*   **Plotly Express:** Creación de gráficos dinámicos y responsivos.

## 📂 Estructura del Proyecto

```text
├── dashboard/
│   ├── charts_platforms.py   # Generación de Roadmap y visualizaciones de hardware
│   └── config.py             # Configuraciones globales
├── data/                     # Datasets de la industria (Ventas, fechas, fabricantes)
└── README.md
```

## 📊 Visualizaciones Principales

### Roadmap Timeline
El módulo `charts_platforms.py` genera una línea de tiempo donde el eje Y segmenta a los fabricantes y el eje X representa el año de lanzamiento. El tamaño de cada punto se calcula dinámicamente:
1. Si existen datos de ventas, se utiliza `units_sold_millions`.
2. Si no hay ventas registradas, se normaliza según el `games_count` (cantidad de juegos).

## 📝 Requisitos

Instala las dependencias necesarias con:
`pip install pandas plotly`
"""
charts_global.py — Gráficos Plotly para la dimensión «Visión Global»

Contiene dos funciones de visualización:
  • create_intersectoral_chart  → Barras agrupadas comparando ingresos de la industria del entretenimiento.
  • create_genre_race_chart     → Bar-chart race animado de lanzamientos acumulados por género.

Estilo visual:
  - Plantilla base: plotly_dark
  - Fondos transparentes (glassmorphism)
  - Paleta vibrante y etiquetas en español
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ──────────────────────────────────────────────
#  Constantes de estilo compartidas
# ──────────────────────────────────────────────
_TRANSPARENT = "rgba(0,0,0,0)"

_LAYOUT_DEFAULTS = dict(
    template="plotly_dark",
    paper_bgcolor=_TRANSPARENT,
    plot_bgcolor=_TRANSPARENT,
    font=dict(family="Inter, Segoe UI, sans-serif", color="#E2E8F0"),
    margin=dict(l=60, r=30, t=60, b=80),
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. Comparativa intersectorial de ingresos
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def create_intersectoral_chart(df: pd.DataFrame) -> go.Figure:
    """Crea un gráfico de barras agrupadas que compara los ingresos anuales
    de las principales industrias del entretenimiento.

    Parámetros
    ----------
    df : pd.DataFrame
        Columnas esperadas:
          - ``year``             (int)   — Año.
          - ``gaming``           (float) — Ingresos de videojuegos (miles de millones USD).
          - ``box_office``       (float) — Ingresos de taquilla de cine.
          - ``recorded_music``   (float) — Ingresos de música grabada.
          - ``streaming_video``  (float) — Ingresos de streaming de vídeo.

    Devuelve
    --------
    go.Figure
        Figura Plotly lista para renderizar en Streamlit.
    """

    # Mapeo: columna → (etiqueta en español, color)
    series_config = {
        "gaming":          ("Videojuegos",          "#8B5CF6"),
        "box_office":      ("Taquilla (Cine)",      "#F59E0B"),
        "recorded_music":  ("Música Grabada",       "#EC4899"),
        "streaming_video": ("Streaming de Vídeo",   "#06B6D4"),
    }

    fig = go.Figure()

    for col, (label, color) in series_config.items():
        fig.add_trace(
            go.Bar(
                x=df["year"],
                y=df[col],
                name=label,
                marker=dict(
                    color=color,
                    line_width=0,                       # sin borde → esquinas limpias
                    cornerradius=4,                     # bordes redondeados (Plotly ≥ 5.19)
                ),
                hovertemplate=(
                    f"<b>{label}</b><br>"
                    "Año: %{x}<br>"
                    "Ingresos: $%{y:.1f} Bn"
                    "<extra></extra>"
                ),
            )
        )



    # ── Layout ──
    fig.update_layout(
        **_LAYOUT_DEFAULTS,
        title=dict(
            text="Comparativa Intersectorial de Ingresos del Entretenimiento",
            font=dict(size=18, color="#F8FAFC"),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(
            title="Año",
            dtick=1,
            gridcolor="rgba(148,163,184,0.08)",
            showline=False,
        ),
        yaxis=dict(
            title="Revenue (Miles de Millones USD)",
            gridcolor="rgba(148,163,184,0.12)",
            zeroline=False,
            showline=False,
        ),
        barmode="group",
        bargap=0.20,
        bargroupgap=0.06,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
            font=dict(size=12),
            bgcolor=_TRANSPARENT,
        ),
        hoverlabel=dict(
            bgcolor="rgba(15,23,42,0.85)",
            bordercolor="rgba(148,163,184,0.25)",
            font_size=13,
        ),
    )

    return fig


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. Bar-chart race de géneros de videojuegos
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def create_genre_race_chart(df: pd.DataFrame, color_map: dict = None) -> go.Figure:
    """Crea un bar-chart race animado que muestra la evolución acumulada
    de ventas de videojuegos por género a lo largo del tiempo (1990-2020).

    Parámetros
    ----------
    df : pd.DataFrame
        Columnas esperadas:
          - ``Año``                 (int) — Año del frame de animación.
          - ``Género``              (str) — Nombre del género.
          - ``Ventas_Acumuladas``   (float) — Ventas acumuladas en millones de copias.

    Devuelve
    --------
    go.Figure
        Figura Plotly animada lista para renderizar en Streamlit.
    """

    # ── Calcular Rank por frame ──
    # Para que las barras se muevan verticalmente de forma fluida, el eje Y debe ser numérico (el rango).
    df["Rank"] = df.groupby("Año")["Ventas_Acumuladas"].rank(method="first", ascending=False)
    
    # ── Filtrar Top-10 géneros por frame ──
    df_top = df[df["Rank"] <= 10].copy()
    
    # Crear texto personalizado (Género + Ventas)
    df_top["Texto_Barra"] = df_top["Género"] + " (" + df_top["Ventas_Acumuladas"].map(lambda x: f"{x:,.1f}M") + ")"

    # ── Figura animada con Plotly Express ──
    fig = px.bar(
        df_top,
        x="Ventas_Acumuladas",
        y="Rank",
        color="Género",
        orientation="h",
        animation_frame="Año",
        text="Texto_Barra",
        color_discrete_map=color_map if color_map else {},
        color_discrete_sequence=px.colors.qualitative.Vivid if not color_map else None,
        labels={
            "Ventas_Acumuladas": "Ventas Acumuladas (Millones)",
            "Género": "Género",
            "Año": "Año",
            "Rank": "Ranking",
        },
    )

    # ── Estilo de las barras y etiquetas ──
    fig.update_traces(
        textposition="outside",
        textfont=dict(size=13, color="#E2E8F0"), # Aumentado el tamaño de la etiqueta
        marker_line_width=0,
        marker_cornerradius=4,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Ventas acumuladas: %{x:,.1f}M copias"
            "<extra></extra>"
        ),
        customdata=df_top[["Género"]],
    )

    # ── Escala dinámica del eje X frame por frame ──
    for frame in fig.frames:
        frame_year = float(frame.name)
        max_val = df_top[df_top["Año"] == frame_year]["Ventas_Acumuladas"].max()
        # Dar un 15% de margen a la derecha
        x_max = max_val * 1.15 if max_val > 0 else 10
        frame.layout.update(xaxis=dict(range=[0, x_max]))

    # Configurar el rango del primer frame en la vista inicial del layout
    first_year = df_top["Año"].min()
    first_max = df_top[df_top["Año"] == first_year]["Ventas_Acumuladas"].max()
    first_x_max = first_max * 1.15 if first_max > 0 else 10
    fig.update_layout(xaxis=dict(range=[0, first_x_max]))

    # ── Configurar tiempos de animación más fluidos ──
    fig.layout.updatemenus[0].buttons[0].args[1]["frame"] = dict(
        duration=150,
        redraw=True,
    )
    fig.layout.updatemenus[0].buttons[0].args[1]["transition"] = dict(
        duration=100,
        easing="linear", # linear es más suave para interpolaciones de tiempo continuas
    )

    # Estilizar botones Play / Pause
    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                x=0.02,
                y=-0.18, # Bajamos más los botones
                xanchor="left",
                yanchor="top",
                font=dict(size=13, color="#E2E8F0"),
                bgcolor="rgba(139,92,246,0.25)",
                bordercolor="#8B5CF6",
                buttons=[
                    dict(
                        label="▶  Reproducir",
                        method="animate",
                        args=[
                            None,
                            dict(
                                frame=dict(duration=150, redraw=True),
                                transition=dict(duration=100, easing="linear"),
                                fromcurrent=True,
                                mode="immediate",
                            ),
                        ],
                    ),
                    dict(
                        label="⏸  Pausar",
                        method="animate",
                        args=[
                            [None],
                            dict(
                                frame=dict(duration=0, redraw=False),
                                mode="immediate",
                            ),
                        ],
                    ),
                ],
            )
        ],
    )

    # ── Slider de años ──
    if fig.layout.sliders and len(fig.layout.sliders) > 0:
        slider = fig.layout.sliders[0]
        
        # Ocultar las etiquetas de los pasos intermedios (ej. 1990.2)
        for step in slider.steps:
            frame_name = step.args[0][0]
            try:
                val = float(frame_name)
                # Evitar errores de precisión flotante comparando con el entero más cercano
                if abs(val - round(val)) < 0.01:
                    step.label = str(int(round(val)))  # Mostrar etiqueta en años enteros
                else:
                    step.label = ""  # Ocultar etiqueta en los frames interpolados
            except (ValueError, TypeError):
                pass
                
        slider.update(
            currentvalue=dict(
                prefix="Año: ",
                font=dict(size=14, color="#C4B5FD"),
            ),
            font=dict(size=10, color="#94A3B8"),  # Tamaño 10 para que quepan todos los años
            activebgcolor="#8B5CF6",
            bordercolor="rgba(148,163,184,0.15)",
            bgcolor="rgba(30,41,59,0.5)",
        )

    # ── Layout general ──
    fig.update_layout(
        **_LAYOUT_DEFAULTS,
        title=dict(
            text="La Carrera Comercial por Género — Ventas Acumuladas (VGChartz)",
            font=dict(size=18, color="#F8FAFC"),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(
            title="Ventas Acumuladas (Millones de Copias)",
            gridcolor="rgba(148,163,184,0.10)",
            showline=False,
            zeroline=False,
        ),
        yaxis=dict(
            title="",
            range=[10.5, 0.5], # 1 arriba, 10 abajo
            showgrid=False,
            showline=False,
            showticklabels=False, # Ocultamos los números del 1 al 10, ya usamos el texto de la barra
        ),
        showlegend=False,
        height=600, # Un poco más alto para dejar espacio a los botones abajo
        hoverlabel=dict(
            bgcolor="rgba(15,23,42,0.85)",
            bordercolor="rgba(148,163,184,0.25)",
            font_size=13,
        ),
    )

    return fig

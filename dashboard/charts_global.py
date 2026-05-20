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

    # ── Anotación: efecto pandemia en 2020 ──
    if 2020 in df["year"].values:
        gaming_2020 = df.loc[df["year"] == 2020, "gaming"].iloc[0]
        fig.add_annotation(
            x=2020,
            y=gaming_2020,
            text="Efecto pandemia",
            showarrow=True,
            arrowhead=2,
            arrowsize=1.2,
            arrowwidth=2,
            arrowcolor="#8B5CF6",
            ax=50,
            ay=-50,
            font=dict(size=13, color="#C4B5FD", family="Inter, sans-serif"),
            bgcolor="rgba(139,92,246,0.15)",
            bordercolor="#8B5CF6",
            borderwidth=1,
            borderpad=6,
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
def create_genre_race_chart(df: pd.DataFrame) -> go.Figure:
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

    # ── Filtrar Top-10 géneros por frame ──
    frames: list[pd.DataFrame] = []
    for year, group in df.groupby("Año"):
        top10 = (
            group
            .nlargest(10, "Ventas_Acumuladas")
            .sort_values("Ventas_Acumuladas", ascending=True)   # ascendente para que el mayor quede arriba
        )
        frames.append(top10)

    df_top = pd.concat(frames, ignore_index=True)

    # Asegurar tipo categórico ordenado para eje Y consistente
    df_top["Género"] = df_top["Género"].astype(str)

    # ── Figura animada con Plotly Express ──
    fig = px.bar(
        df_top,
        x="Ventas_Acumuladas",
        y="Género",
        color="Género",
        orientation="h",
        animation_frame="Año",
        text="Ventas_Acumuladas",
        color_discrete_sequence=px.colors.qualitative.Vivid,
        labels={
            "Ventas_Acumuladas": "Ventas Acumuladas (Millones de Copias)",
            "Género": "Género",
            "Año": "Año",
        },
    )

    # ── Estilo de las barras y etiquetas ──
    fig.update_traces(
        texttemplate="%{text:,.1f}M",
        textposition="outside",
        textfont=dict(size=11, color="#E2E8F0"),
        marker_line_width=0,
        marker_cornerradius=4,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Ventas acumuladas: %{x:,.1f}M copias"
            "<extra></extra>"
        ),
    )

    # ── Escala dinámica del eje X frame por frame ──
    for frame in fig.frames:
        frame_year = int(frame.name)
        max_val = df_top[df_top["Año"] == frame_year]["Ventas_Acumuladas"].max()
        # Dar un 12% de margen a la derecha para que las etiquetas "outside" de texto no se solapen o corten
        x_max = max_val * 1.15 if max_val > 0 else 10
        frame.layout.update(xaxis=dict(range=[0, x_max]))

    # Configurar el rango del primer frame en la vista inicial del layout
    first_year = df_top["Año"].min()
    first_max = df_top[df_top["Año"] == first_year]["Ventas_Acumuladas"].max()
    first_x_max = first_max * 1.15 if first_max > 0 else 10
    fig.update_layout(xaxis=dict(range=[0, first_x_max]))

    # ── Configurar tiempos de animación más fluidos ──
    fig.layout.updatemenus[0].buttons[0].args[1]["frame"] = dict(
        duration=650,
        redraw=True,
    )
    fig.layout.updatemenus[0].buttons[0].args[1]["transition"] = dict(
        duration=450,
        easing="cubic-in-out",
    )

    # Estilizar botones Play / Pause
    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                x=0.02,
                y=-0.06,
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
                                frame=dict(duration=650, redraw=True),
                                transition=dict(duration=450, easing="cubic-in-out"),
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
        fig.layout.sliders[0].update(
            currentvalue=dict(
                prefix="Año: ",
                font=dict(size=14, color="#C4B5FD"),
            ),
            font=dict(color="#94A3B8"),
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
            showgrid=False,
            showline=False,
            categoryorder="total ascending",   # mayor arriba
        ),
        showlegend=False,                       # el color + etiqueta basta
        height=560,
        hoverlabel=dict(
            bgcolor="rgba(15,23,42,0.85)",
            bordercolor="rgba(148,163,184,0.25)",
            font_size=13,
        ),
    )

    return fig

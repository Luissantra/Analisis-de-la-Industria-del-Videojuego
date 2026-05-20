import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import config

# Cargar configuraciones visuales
try:
    with open(config.MARKET_VISUALS_JSON, 'r', encoding='utf-8') as f:
        visual_config = json.load(f)
    BRAND_COLORS = visual_config.get("brand_colors", {})
except Exception:
    BRAND_COLORS = {}

# Mapeador para enlazar las claves del JSON de matriz con las del JSON de colores
PARENT_COLOR_MAP = {
    "Microsoft Gaming (Xbox, ZeniMax, Activision Blizzard)": BRAND_COLORS.get("Microsoft Corporation", "#107C11"),
    "Sony Interactive Entertainment (PlayStation Studios)": "#003791", # Usamos el Azul PlayStation para que no colisione con el negro de Take-Two
    "Tencent": BRAND_COLORS.get("Tencent Holdings", "#3458B0"),
    "Nintendo": BRAND_COLORS.get("Nintendo Co., Ltd.", "#E60012"),
    "Electronic Arts (EA)": BRAND_COLORS.get("Electronic Arts", "#FF4545"),
    "Take-Two Interactive": BRAND_COLORS.get("Take-Two Interactive", "#000000"),
    "Ubisoft": BRAND_COLORS.get("Ubisoft Entertainment", "#0070FF"),
    "Sega Sammy": BRAND_COLORS.get("Sega Sammy", "#0060A8"),
    "Krafton": "#1B2A40",
    "Warner Bros. Games": "#002B5C",
    "Epic Games": "#313131",
    "Independent & Other Publishers": "#444444" # Color gris genérico
}

def create_sunburst_chart(df):
    """
    Crea el gráfico Sunburst interactivo.
    El tamaño del segmento se basará en el conteo (1 por estudio).
    """
    # Asignamos valor 1 para que el tamaño dependa de la cantidad de estudios filiales
    df['Tamaño'] = 1

    # Creamos un mapa de colores local para asegurar que los no registrados sean grises y no amarillos
    local_color_map = PARENT_COLOR_MAP.copy()
    for parent in df['Parent'].unique():
        if parent not in local_color_map:
            local_color_map[parent] = "#444444"

    fig = px.sunburst(
        df,
        path=['Parent','Studio Name'], 
        values='Tamaño',
        color='Parent',
        color_discrete_map=local_color_map,
        hover_data=['City', 'Country', 'Top_Game', 'Acquisition_Year'],
        template="plotly_dark"
    )

    fig.update_traces(
        # Añade un borde oscuro/claro delgado entre los segmentos para separarlos limpiamente
        marker=dict(line=dict(color='#0E1117', width=1.5)),
        # Muestra el texto y el porcentaje que representa del nodo padre
        textinfo="label+percent parent",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "📍 Ubicación: %{customdata[0]}, %{customdata[1]}<br>"
            "🎮 Juego Notable: %{customdata[2]}<br>"
            "🗓️ Adquisición: %{customdata[3]}<extra></extra>"
        )
    )
    
    # Añadir trazas invisibles (Scatter) para generar una leyenda personalizada
    for parent in df['Parent'].unique():
        color = local_color_map.get(parent, "#444444")
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=15, color=color, symbol='square'),
            name=parent,
            showlegend=True,
            hoverinfo='none' # Para que esta traza fantasma no interfiera con los tooltips
        ))

    fig.update_layout(
        margin=dict(t=20, l=0, r=0, b=80),
        height=750,
        # Fondo transparente para que se integre perfectamente con Streamlit
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.05,
            xanchor="center",
            x=0.5,
            itemclick=False,
            itemdoubleclick=False
        ),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False)
    )
    return fig

def create_treemap_chart(df):
    """
    Crea un gráfico Tree Map para visualizar la jerarquía de los estudios
    de un solo conglomerado agrupados por País. 
    El tamaño es la cantidad de juegos, y el color es la nota media.
    """
    df_clean = df.copy()
    
    # Convertir Metacritic a numérico (los que no tienen nota se ignoran temporalmente para la media)
    df_clean['Metacritic_Num'] = pd.to_numeric(df_clean['Metacritic'], errors='coerce')
    
    # Agrupar por Estudio para calcular cantidad de juegos y nota media
    df_grouped = df_clean.groupby(['Country', 'City', 'Studio Name', 'Acquisition_Year']).agg(
        Game_Count=('Total_Games', 'max') if 'Total_Games' in df_clean.columns else ('Top_Game', 'count'),
        Avg_Metacritic=('Metacritic_Num', 'mean'),
        Top_Games=('Top_Game', lambda x: '<br> • '.join([g for g in x.unique() if str(g) != 'No registrado'][:4]))
    ).reset_index()
    
    # No rellenamos con media neutra para que Plotly los deje grises transparentes/heredados naturalmente
    # Añadimos una columna en texto para el tooltip
    df_grouped['Avg_Metacritic_Str'] = df_grouped['Avg_Metacritic'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
    
    fig = px.treemap(
        df_grouped,
        path=[px.Constant("Portfolio Global"), 'Country', 'Studio Name'],
        values='Game_Count',
        color='Avg_Metacritic',
        color_continuous_scale='RdYlGn',
        range_color=[40, 95], # Rango estándar para notas
        hover_data=['City', 'Top_Games', 'Acquisition_Year', 'Avg_Metacritic_Str'],
        template="plotly_dark"
    )
    
    fig.update_traces(
        marker=dict(line=dict(color='#0E1117', width=1.5)),
        textinfo="label",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "📍 Sede: %{customdata[0]}, %{parent}<br>"
            "🎮 Juegos:<br> • %{customdata[1]}<br>"
            "🗓️ Adquisición: %{customdata[2]}<br>"
            "⭐ Nota Media: %{customdata[3]}<extra></extra>"
        )
    )
    
    fig.update_layout(
        margin=dict(t=20, l=0, r=0, b=20),
        height=500,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(title="Nota<br>Media")
    )
    return fig

def create_genre_and_score_chart(df, color="#0070FF"):
    """
    Crea una matriz de portfolio (Gráfico de Burbujas) cruzando el volumen 
    de juegos por género con su calidad promedio (Metacritic).
    """
    if 'genres' not in df.columns or df['genres'].eq('Desconocido').all() or df['genres'].eq('').all():
        return None
        
    # Explotar la columna de géneros (ya que un juego puede tener varios separados por coma)
    df_genres = df.copy()
    df_genres = df_genres[df_genres['genres'] != 'Desconocido']
    df_genres = df_genres[df_genres['genres'] != '']
    df_genres['Genre_List'] = df_genres['genres'].str.split(', ')
    df_exploded = df_genres.explode('Genre_List')
    
    if df_exploded.empty:
        return None
        
    # Convertir a numérico, ordenar por nota para el tooltip y agrupar por género
    df_exploded['Metacritic_Num'] = pd.to_numeric(df_exploded['metacritic'], errors='coerce')
    df_exploded = df_exploded.sort_values('Metacritic_Num', ascending=False)
    
    genre_stats = df_exploded.groupby('Genre_List').agg(
        Count=('title', 'count'),
        Avg_Metacritic=('Metacritic_Num', 'mean'),
        Top_Games=('title', lambda x: '<br> • '.join(x.unique()[:3])) # Guardar top 3 juegos del género
    ).reset_index()
    
    # Limpiar nulos para el gráfico 2D
    genre_stats = genre_stats.dropna(subset=['Avg_Metacritic'])
    if genre_stats.empty:
        return None
    
    # Matriz de Portfolio (Bubble Chart)
    fig = px.scatter(
        genre_stats, x='Count', y='Avg_Metacritic', size='Count',
        color='Avg_Metacritic', color_continuous_scale='RdYlGn', range_color=[40, 95],
        text='Genre_List', custom_data=['Genre_List', 'Top_Games'],
        template="plotly_dark"
    )
    
    fig.update_traces(
        textposition='top center',
        marker=dict(line=dict(color='#0E1117', width=1)),
        hovertemplate="<b>%{customdata[0]}</b><br>Juegos: %{x}<br>Nota Media: %{y:.1f}<br><br><b>Destacados:</b><br> • %{customdata[1]}<extra></extra>"
    )
    
    fig.update_layout(
        margin=dict(t=20, l=0, r=0, b=20),
        xaxis_title="Cantidad de Juegos (Volumen)",
        yaxis_title="Nota Media Metacritic (Calidad)",
        coloraxis_showscale=False # Redundante con el eje Y
    )
    
    # Línea base de calidad "Aceptable"
    fig.add_hline(y=75, line_dash="dash", line_color="rgba(255,255,255,0.2)", annotation_text="Calidad Standard (75+)")
    
    return fig

def create_genre_pie_chart(df, color="#0070FF"):
    """
    Crea un gráfico de tarta (Pie Chart) para la distribución de géneros
    de un conglomerado específico, limitado a 5 categorías (Top 4 + Otros).
    """
    if 'Genres' not in df.columns or df['Genres'].eq('Desconocido').all():
        return None
        
    df_genres = df.copy()
    df_genres = df_genres[df_genres['Genres'] != 'Desconocido']
    
    # Calculamos el total de portfolios/estudios analizados reales (antes de explotar la lista)
    total_estudios = len(df_genres)
    
    df_genres['Genre_List'] = df_genres['Genres'].str.split(', ')
    df_exploded = df_genres.explode('Genre_List')
    
    if df_exploded.empty:
        return None
        
    genre_counts = df_exploded['Genre_List'].value_counts().reset_index()
    genre_counts.columns = ['Genre', 'Count']
    
    # Limitar a 5 categorías (Top 4 + "Otros")
    if len(genre_counts) > 5:
        top_4 = genre_counts.iloc[:4]
        otros_count = genre_counts.iloc[4:]['Count'].sum()
        otros_df = pd.DataFrame([{'Genre': 'Otros', 'Count': otros_count}])
        genre_counts = pd.concat([top_4, otros_df], ignore_index=True)
        
    fig = px.pie(
        genre_counts, names='Genre', values='Count', hole=0.65,
        template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Vivid
    )
    
    fig.update_traces(
        textposition='outside', 
        textinfo='label+percent',
        textfont=dict(family="system-ui, Arial, sans-serif", size=16, color='white'),
        marker=dict(line=dict(color='#0E1117', width=2.5)),
        hovertemplate="<b>%{label}</b><br>Frecuencia: %{value} etiquetas<extra></extra>",
        pull=[0.015] * len(genre_counts) # Separación sutil entre los gajos (Efecto "Exploded Donut")
    )
    
    # Añadir la métrica central (Total de Estudios) con el color de la marca y fuente mejorada
    fig.add_annotation(
        text=f"<span style='font-family: system-ui, Arial, sans-serif; font-size:46px; font-weight:900; color:{color};'>{total_estudios}</span><br><span style='font-family: system-ui, Arial, sans-serif; font-size:14px; font-weight:500; color:#B0B0B0; letter-spacing: 1px;'>ESTUDIOS<br>EVALUADOS</span>",
        x=0.5, y=0.5,
        showarrow=False,
        align="center"
    )
    
    fig.update_layout(
        margin=dict(t=30, l=60, r=60, b=30), # Ampliamos aún más el margen lateral por el aumento de fuente
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

def create_acquisition_timeline_chart(df, color="#0070FF"):
    """
    Crea un gráfico de línea de tiempo de los años de adquisición/fundación de los estudios.
    """
    # 1. Filtrar valores no válidos o desconocidos
    df_time = df[~df['Acquisition_Year'].isin(['No registrado', 'N/A', 'Desconocido', None])].copy()
    if df_time.empty:
        return None

    # 2. Asegurar que el año es numérico
    df_time['Acquisition_Year'] = pd.to_numeric(df_time['Acquisition_Year'], errors='coerce')
    df_time = df_time.dropna(subset=['Acquisition_Year'])
    df_time['Acquisition_Year'] = df_time['Acquisition_Year'].astype(int)

    # 3. Agrupar por año contando estudios y guardando sus nombres para el tooltip
    timeline_stats = df_time.groupby('Acquisition_Year').agg(
        Count=('Studio Name', 'count'),
        Studios=('Studio Name', lambda x: '<br> • '.join(x))
    ).reset_index()

    # 4. Crear el gráfico de barras (Timeline)
    fig = px.bar(
        timeline_stats,
        x='Acquisition_Year',
        y='Count',
        template="plotly_dark",
        custom_data=['Studios']
    )

    fig.update_traces(
        marker_color=color,
        hovertemplate="<b>Año: %{x}</b><br>Adquisiciones/Fundaciones: %{y}<br><br><b>Estudios:</b><br> • %{customdata[0]}<extra></extra>"
    )

    fig.update_layout(
        margin=dict(t=20, l=0, r=0, b=20),
        xaxis_title="Año",
        yaxis_title="Cantidad de Estudios",
        xaxis=dict(type='category') # Tratar el eje X como categoría para evitar decimales en los años
    )
    return fig

def create_score_distribution_chart(df, color="#0070FF", is_global=False):
    """
    Crea un gráfico de Violín (Violin Plot) para evaluar la consistencia y dispersión
    de las notas de Metacritic de un conglomerado.
    """
    df_scores = df.copy()
    df_scores['Metacritic_Num'] = pd.to_numeric(df_scores['Metacritic'], errors='coerce')
    df_scores = df_scores.dropna(subset=['Metacritic_Num'])

    if df_scores.empty:
        return None

    if is_global:
        df_scores['Ecosistema'] = 'Industria Global'
        fig = px.violin(
            df_scores,
            x='Ecosistema',
            y='Metacritic_Num',
            box=True,
            points="all",
            custom_data=['Studio Name', 'Top_Game', 'Parent'],
            color_discrete_sequence=["#888888"],
            template="plotly_dark"
        )
        fig.update_traces(
            hovertemplate="<b>%{customdata[0]}</b> (%{customdata[2]})<br>Juego: %{customdata[1]}<br>Nota: %{y}<extra></extra>",
            meanline_visible=True
        )
    else:
        fig = px.violin(
            df_scores,
            y='Metacritic_Num',
            box=True,
            points="all",
            custom_data=['Studio Name', 'Top_Game'],
            color_discrete_sequence=[color],
            template="plotly_dark"
        )
        fig.update_traces(
            hovertemplate="<b>%{customdata[0]}</b><br>Juego: %{customdata[1]}<br>Nota: %{y}<extra></extra>",
            meanline_visible=True
        )

    fig.update_layout(
        margin=dict(t=20, l=0, r=0, b=20),
        xaxis_title="",
        yaxis_title="Metacritic Score",
        xaxis=dict(showticklabels=False),
        showlegend=False
    )
    return fig

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def plot_critic_vs_user(df):
    """
    Crea un Scatter Plot comparando la nota de la crítica profesional (X)
    con la nota de los usuarios (Y).
    Destaca en rojo aquellos juegos con un alto Review Bombing Index.
    """
    # 1. Limpieza y conversión de tipos
    df_clean = df.copy()
    df_clean['Metacritic'] = pd.to_numeric(df_clean['metacritic'], errors='coerce')
    df_clean['User_Score_100'] = pd.to_numeric(df_clean['rawg_rating'], errors='coerce') * 20
    
    # 2. Filtrado: Solo necesitamos Metacritic y User Score para poder pintar el punto.
    df_clean = df_clean.dropna(subset=['Metacritic', 'User_Score_100'])
    
    # 3. Descartar falsos positivos donde la API devolvió 0 porque no hay reseñas de usuarios reales
    df_clean = df_clean[df_clean['User_Score_100'] > 0]

    # Clasificación bidireccional de la discrepancia
    def get_status(row):
        val = row['Review_Bombing_Index']
        if pd.isna(val):
            return 'Recepción Consistente'
        try:
            val_float = float(val)
        except Exception:
            return 'Recepción Consistente'
            
        if val_float >= 20:
            return 'Review Bombing (Divergencia Negativa)'
        elif val_float <= -20:
            return 'Aclamación Popular (Divergencia Positiva)'
        else:
            return 'Recepción Consistente'
            
    # Recalculamos el índice aquí para asegurar consistencia tras la limpieza
    df_clean['Review_Bombing_Index'] = df_clean['Metacritic'] - df_clean['User_Score_100']
    df_clean = df_clean.dropna(subset=['Review_Bombing_Index'])
    df_clean['Estado'] = df_clean.apply(get_status, axis=1)

    # El nombre del juego (título) siempre está presente en la nueva tabla
    df_clean['hover_name'] = df_clean['title']

    fig = px.scatter(
        df_clean,
        x='Metacritic',
        y='User_Score_100',
        color='Estado',
        color_discrete_map={
            'Review Bombing (Divergencia Negativa)': '#EF5350', # Rojo
            'Aclamación Popular (Divergencia Positiva)': '#42A5F5', # Azul
            'Recepción Consistente': '#26A69A' # Verde/Teal
        },
        hover_name='hover_name',
        custom_data=['studio', 'release_year', 'Review_Bombing_Index'],
        template="plotly_dark",
        title="Crítica Profesional vs. Recepción de Usuarios"
    )

    # Añadir línea diagonal de referencia (X = Y)
    fig.add_shape(
        type="line",
        x0=0, y0=0, x1=100, y1=100,
        line=dict(color="rgba(255,255,255,0.4)", width=2, dash="dot")
    )

    fig.update_traces(
        marker=dict(size=12, line=dict(width=1, color='#0E1117')),
        hovertemplate=(
            "<b>%{hovertext}</b><br><br>"
            "Estudio: %{customdata[0]}<br>"
            "Lanzamiento: %{customdata[1]}<br>"
            "Nota Crítica: %{x}<br>"
            "Nota Usuarios: %{y}<br>"
            "Índice de Divergencia: %{customdata[2]:.1f}<extra></extra>"
        )
    )

    fig.update_layout(
        xaxis_title="Nota de la Crítica (Metacritic)",
        yaxis_title="Nota de Usuarios (Base 100)",
        xaxis=dict(range=[0, 105]),
        yaxis=dict(range=[0, 105]),
        legend_title="Recepción",
        margin=dict(t=50, l=20, r=20, b=20)
    )

    return fig

def plot_top_controversies(df):
    """
    Crea un gráfico de barras horizontales (Diverging Bar Chart) 
    con el Top 15 de juegos con mayor índice de Review Bombing.
    """
    df_clean = df.copy()
    df_clean['Metacritic'] = pd.to_numeric(df_clean['metacritic'], errors='coerce')
    df_clean['User_Score_100'] = pd.to_numeric(df_clean['rawg_rating'], errors='coerce') * 20
    df_clean['Review_Bombing_Index'] = df_clean['Metacritic'] - df_clean['User_Score_100']
    
    df_clean = df_clean.dropna(subset=['Review_Bombing_Index', 'title'])
    df_clean['Review_Bombing_Index'] = pd.to_numeric(df_clean['Review_Bombing_Index'], errors='coerce')
    df_clean = df_clean.dropna(subset=['Review_Bombing_Index'])
    
    # Descartar falsos positivos donde la API devolvió 0 porque no hay reseñas reales
    if 'User_Score_100' in df_clean.columns:
        df_clean['User_Score_100'] = pd.to_numeric(df_clean['User_Score_100'], errors='coerce')
        df_clean = df_clean[df_clean['User_Score_100'] > 0]

    # Obtener el Top 15 con mayor review bombing
    df_top = df_clean.sort_values(by='Review_Bombing_Index', ascending=False).head(15)
    
    # Plotly traza de abajo hacia arriba en barras horizontales, por lo que invertimos el orden
    df_top = df_top.sort_values(by='Review_Bombing_Index', ascending=True)

    fig = px.bar(
        df_top,
        x='Review_Bombing_Index',
        y='title',
        orientation='h',
        text='Review_Bombing_Index',
        custom_data=['studio', 'Metacritic', 'User_Score_100'],
        template="plotly_dark",
        color='Review_Bombing_Index',
        color_continuous_scale=['#FFCDD2', '#D32F2F'], # Gradiente de rojo claro a oscuro
        title="Top 15: Mayor Review Bombing (Crítica superior a Usuarios)"
    )

    fig.update_traces(
        texttemplate='%{text:.1f} pts',
        textposition='outside',
        hovertemplate=(
            "<b>%{y}</b><br><br>"
            "Estudio: %{customdata[0]}<br>"
            "Nota Crítica: %{customdata[1]}<br>"
            "Nota Usuarios: %{customdata[2]}<br>"
            "Discrepancia: %{x:.1f} pts<extra></extra>"
        )
    )

    fig.update_layout(
        xaxis_title="Índice de Discrepancia (Puntos de diferencia)",
        yaxis_title="",
        coloraxis_showscale=False, # Redundante porque el Eje X ya es el valor
        margin=dict(t=50, l=20, r=50, b=20)
    )

    return fig

def plot_top_acclaimed(df):
    """
    Crea un gráfico de barras horizontales (Diverging Bar Chart) 
    con el Top 15 de juegos con mayor aclamación popular (User Score > Metacritic).
    """
    df_clean = df.copy()
    df_clean['Metacritic'] = pd.to_numeric(df_clean['metacritic'], errors='coerce')
    df_clean['User_Score_100'] = pd.to_numeric(df_clean['rawg_rating'], errors='coerce') * 20
    # En este caso, la divergencia positiva es User Score - Metacritic
    df_clean['Aclamacion_Index'] = df_clean['User_Score_100'] - df_clean['Metacritic']
    
    df_clean = df_clean.dropna(subset=['Aclamacion_Index', 'title'])
    df_clean['Aclamacion_Index'] = pd.to_numeric(df_clean['Aclamacion_Index'], errors='coerce')
    df_clean = df_clean.dropna(subset=['Aclamacion_Index'])
    
    # Descartar falsos positivos donde la API devolvió 0 porque no hay reseñas reales
    if 'User_Score_100' in df_clean.columns:
        df_clean['User_Score_100'] = pd.to_numeric(df_clean['User_Score_100'], errors='coerce')
        df_clean = df_clean[df_clean['User_Score_100'] > 0]

    # Obtener el Top 15 con mayor aclamación (mayor diferencia positiva a favor del usuario)
    df_top = df_clean.sort_values(by='Aclamacion_Index', ascending=False).head(15)
    
    # Plotly traza de abajo hacia arriba en barras horizontales, por lo que invertimos el orden
    df_top = df_top.sort_values(by='Aclamacion_Index', ascending=True)

    fig = px.bar(
        df_top,
        x='Aclamacion_Index',
        y='title',
        orientation='h',
        text='Aclamacion_Index',
        custom_data=['studio', 'Metacritic', 'User_Score_100'],
        template="plotly_dark",
        color='Aclamacion_Index',
        color_continuous_scale=['#E3F2FD', '#1976D2'], # Gradiente de azul claro a oscuro
        title="Top 15: Mayor Aclamación Popular (Usuarios superior a Crítica)"
    )

    fig.update_traces(
        texttemplate='+%{text:.1f} pts',
        textposition='outside',
        hovertemplate=(
            "<b>%{y}</b><br><br>"
            "Estudio: %{customdata[0]}<br>"
            "Nota Crítica: %{customdata[1]}<br>"
            "Nota Usuarios: %{customdata[2]}<br>"
            "Aclamación: +%{x:.1f} pts<extra></extra>"
        )
    )

    fig.update_layout(
        xaxis_title="Puntos a favor de los usuarios",
        yaxis_title="",
        coloraxis_showscale=False,
        margin=dict(t=50, l=20, r=50, b=20)
    )

    return fig

def plot_social_traction(df):
    """
    Crea un Bubble Chart (Scatter) para analizar el volumen de interacción (Hype) 
    frente a la recepción crítica.
    """
    df_clean = df.copy()
    df_clean['Metacritic'] = pd.to_numeric(df_clean['metacritic'], errors='coerce')
    df_clean['rawg_ratings_count'] = pd.to_numeric(df_clean['rawg_ratings_count'], errors='coerce')
    df_clean = df_clean.dropna(subset=['Metacritic', 'rawg_ratings_count'])
    
    if df_clean.empty:
        return None

    # Filtrar solo juegos con interacción real para ver el 'Hype' verdadero
    df_clean = df_clean[df_clean['rawg_ratings_count'] > 10]
    
    if df_clean.empty:
        return None
    
    # Color por conglomerado si hay más de uno, sino por estudio
    color_col = 'conglomerate' if 'conglomerate' in df_clean.columns and len(df_clean['conglomerate'].unique()) > 1 else 'studio'
    if color_col not in df_clean.columns:
        color_col = None
    
    fig = px.scatter(
        df_clean,
        x='Metacritic',
        y='rawg_ratings_count',
        size='rawg_ratings_count',
        color=color_col,
        hover_name='title',
        custom_data=['studio', 'release_year'],
        template="plotly_dark",
        title="Tracción Social vs Calidad (Hype Analysis)",
        size_max=40,
        opacity=0.7
    )

    fig.update_traces(
        marker=dict(line=dict(width=1, color='#0E1117')),
        hovertemplate=(
            "<b>%{hovertext}</b><br><br>"
            "Estudio: %{customdata[0]}<br>"
            "Lanzamiento: %{customdata[1]}<br>"
            "Nota Crítica: %{x}<br>"
            "Volumen Reseñas: %{y}<extra></extra>"
        )
    )

    fig.update_layout(
        xaxis_title="Nota Crítica (Metacritic)",
        yaxis_title="Volumen de Conversación (Ratings Count)",
        margin=dict(t=50, l=20, r=20, b=20)
    )

    return fig

def create_esrb_distribution_chart(df):
    """
    Crea un gráfico de barras apiladas 100% mostrando la distribución de edades (ESRB)
    por cada conglomerado (o estudio si es global).
    """
    if 'esrb_rating' not in df.columns or df.empty:
        return None
        
    df_esrb = df.copy()
    valid_ratings = ['Everyone', 'Everyone 10+', 'Teen', 'Mature', 'Adults Only']
    df_esrb = df_esrb[df_esrb['esrb_rating'].isin(valid_ratings)]
    
    if df_esrb.empty:
        return None
        
    group_col = 'conglomerate' if 'conglomerate' in df.columns and len(df['conglomerate'].unique()) > 1 else 'studio'
    if group_col not in df_esrb.columns:
        group_col = 'title' # fallback
    
    counts = df_esrb.groupby([group_col, 'esrb_rating']).size().reset_index(name='count')
    totals = counts.groupby(group_col)['count'].transform('sum')
    counts['percentage'] = (counts['count'] / totals) * 100
    
    category_order = ['Everyone', 'Everyone 10+', 'Teen', 'Mature', 'Adults Only']
    color_map = {
        'Everyone': '#4CAF50',
        'Everyone 10+': '#8BC34A',
        'Teen': '#FFC107',
        'Mature': '#FF5722',
        'Adults Only': '#B71C1C'
    }
    
    fig = px.bar(
        counts, 
        x='percentage', 
        y=group_col, 
        color='esrb_rating',
        orientation='h',
        category_orders={'esrb_rating': category_order},
        color_discrete_map=color_map,
        template="plotly_dark",
        title="Target de Audiencia (Distribución ESRB)",
        hover_data={'count': True, 'percentage': ':.1f%'}
    )
    
    fig.update_layout(
        xaxis_title="Porcentaje del Portfolio (%)",
        yaxis_title="",
        barmode='stack',
        legend_title="Clasificación",
        margin=dict(t=50, l=0, r=0, b=0)
    )
    
    return fig

def create_playtime_scatter_chart(df):
    """
    Crea un scatter plot de Horas de Juego (X) vs Metacritic (Y)
    para medir la 'Eficiencia de Diversión'.
    """
    if 'playtime_hours' not in df.columns or 'metacritic' not in df.columns or df.empty:
        return None
        
    df_clean = df.dropna(subset=['playtime_hours', 'metacritic']).copy()
    df_clean['playtime_hours'] = pd.to_numeric(df_clean['playtime_hours'], errors='coerce')
    df_clean['metacritic'] = pd.to_numeric(df_clean['metacritic'], errors='coerce')
    
    df_clean = df_clean[(df_clean['playtime_hours'] > 0) & (df_clean['playtime_hours'] < 300)]
    
    if df_clean.empty:
        return None

    df_clean['main_genre'] = df_clean['genres'].astype(str).str.split(',').str[0]
    
    fig = px.scatter(
        df_clean,
        x='playtime_hours',
        y='metacritic',
        color='main_genre',
        hover_name='title',
        hover_data=['studio', 'metacritic', 'playtime_hours'],
        template="plotly_dark",
        title="Compromiso del Jugador: Duración vs Calidad",
        opacity=0.7
    )
    
    fig.update_layout(
        xaxis_title="Horas de Juego Promedio (Playtime)",
        yaxis_title="Nota Crítica (Metacritic)",
        legend_title="Género Principal",
        margin=dict(t=50, l=0, r=0, b=0)
    )
    
    median_playtime = df_clean['playtime_hours'].median()
    median_meta = df_clean['metacritic'].median()
    
    fig.add_vline(x=median_playtime, line_dash="dash", line_color="rgba(255,255,255,0.3)", annotation_text=f"Mediana: {median_playtime:.1f}h")
    fig.add_hline(y=median_meta, line_dash="dash", line_color="rgba(255,255,255,0.3)", annotation_text=f"Mediana: {median_meta:.1f}")
    
    return fig
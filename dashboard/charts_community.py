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
        if row['Review_Bombing_Index'] >= 20:
            return 'Review Bombing (Divergencia Negativa)'
        elif row['Review_Bombing_Index'] <= -20:
            return 'Aclamación Popular (Divergencia Positiva)'
        else:
            return 'Recepción Consistente'
            
    # Recalculamos el índice aquí para asegurar consistencia tras la limpieza
    df_clean['Review_Bombing_Index'] = df_clean['Metacritic'] - df_clean['User_Score_100']
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
    Muestra el volumen de reseñas (Popularidad Social) de los juegos.
    """
    df_top = df.sort_values(by='rawg_ratings_count', ascending=False).head(15)
    df_top = df_top.sort_values(by='rawg_ratings_count', ascending=True)

    fig = px.bar(
        df_top,
        x='rawg_ratings_count',
        y='title',
        orientation='h',
        color='rawg_ratings_count',
        color_continuous_scale='Viridis',
        template="plotly_dark",
        title="Tracción Social: Volumen de Conversación (Ratings Count)"
    )

    fig.update_layout(
        xaxis_title="Número de Reseñas / Usuarios Interactuando",
        yaxis_title="",
        coloraxis_showscale=False,
        margin=dict(t=50, l=20, r=50, b=20)
    )

    return fig
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import config

PLATFORM_COLORS = {
    "Sony": "#003791",        # Azul PlayStation
    "Nintendo": "#E60012",    # Rojo Nintendo
    "Microsoft": "#107C11",   # Verde Xbox
    "Sega": "#0060A8",        # Azul Sega
    "Atari": "#E32636",       # Rojo Atari
    "SNK": "#FFD700",         # Dorado Neo Geo
    "Apple": "#A3AAAE",       # Plata
    "PC": "#FF8C00",          # Naranja PC
    "Google": "#3DDC84",      # Verde Android
    "Commodore": "#8E512F",   # Marrón retro
    "Other": "#888888"        # Gris
}

def create_roadmap_timeline(df):
    """Crea una línea de tiempo tipo Roadmap separando por carril (Fabricante)"""
    df = df.sort_values(by="release_year")
    
    if 'games_count' not in df.columns:
        df['games_count'] = 0

    max_games = df['games_count'].max() if df['games_count'].max() > 0 else 1
    df['bubble_size'] = df['units_sold_millions'].fillna((df['games_count'] / max_games) * 50 + 5)
    df['bubble_size'] = df['bubble_size'].clip(lower=2)
    
    fig = px.scatter(
        df,
        x="release_year",
        y="manufacturer",
        size="bubble_size",
        color="manufacturer",
        color_discrete_map=PLATFORM_COLORS,
        text="name",
        custom_data=["name", "generation", "units_sold_millions", "games_count"],
        template="plotly_dark",
        size_max=40, # Ligeramente más grande el máximo
        opacity=0.85 # Añadir transparencia para ver cuando se solapan
    )

    fig.update_traces(
        textposition='bottom center', # Cambiar a bottom para que no colisione con el tooltip y haya más espacio
        textfont=dict(color='rgba(255,255,255,0.8)', size=11),
        marker=dict(line=dict(width=2, color='rgba(255,255,255,0.5)')), # Borde más claro y grueso para distinguir solapamientos
        hovertemplate="<b>%{customdata[0]}</b><br>Año: %{x}<br>Juegos: %{customdata[3]}<extra></extra>"
    )

    fig.update_layout(
        xaxis_title="Año de Lanzamiento", yaxis_title="",
        margin=dict(t=20, l=20, r=20, b=20), height=450,
        showlegend=False
    )

    generaciones = [
        (1977, 1983, "2ª Gen", "rgba(255, 255, 255, 0.0)"),
        (1983, 1987, "3ª Gen", "rgba(255, 255, 255, 0.03)"),
        (1987, 1993, "4ª Gen", "rgba(255, 255, 255, 0.0)"),
        (1993, 1998, "5ª Gen", "rgba(255, 255, 255, 0.03)"),
        (1998, 2004, "6ª Gen", "rgba(255, 255, 255, 0.0)"),
        (2004, 2011, "7ª Gen", "rgba(255, 255, 255, 0.03)"),
        (2011, 2020, "8ª Gen", "rgba(255, 255, 255, 0.0)"),
        (2020, 2030, "9ª Gen", "rgba(255, 255, 255, 0.03)")
    ]

    for start, end, label, color in generaciones:
        fig.add_vrect(
            x0=start, x1=end, 
            fillcolor=color, opacity=1, 
            layer="below", line_width=0,
            annotation_text=label, 
            annotation_position="top left",
            annotation_font=dict(size=10, color="rgba(255, 255, 255, 0.2)")
        )
    
    return fig

def create_sales_ranking_chart(df):
    df_sorted = df.dropna(subset=["units_sold_millions"]).sort_values("units_sold_millions", ascending=True).tail(10)
    fig = px.bar(
        df_sorted,
        x="units_sold_millions",
        y="name",
        color="manufacturer",
        color_discrete_map=PLATFORM_COLORS,
        text="units_sold_millions",
        custom_data=["generation", "release_year", "games_count"],
        template="plotly_dark",
        title="Top 10 Consolas más Vendidas"
    )
    fig.update_traces(
        texttemplate="%{text:.1f}M", textposition="outside",
        hovertemplate="<b>%{y}</b><br>Ventas: %{x}M<br>Generación: %{customdata[0]}<br>Lanzamiento: %{customdata[1]}<br>Juegos: %{customdata[2]}<extra></extra>"
    )
    fig.update_layout(xaxis_title="Millones de Unidades", yaxis_title="", margin=dict(l=0, r=20, t=40, b=20), showlegend=False)
    return fig

def create_generation_market_share_chart(df):
    df_gen = df.groupby(["generation", "manufacturer"])["units_sold_millions"].sum().reset_index()
    gen_order = ["2da Gen", "3ra Gen", "4ta Gen", "5ta Gen", "6ta Gen", "7ma Gen", "8va Gen", "9na Gen"]
    
    fig = px.bar(
        df_gen,
        x="generation",
        y="units_sold_millions",
        color="manufacturer",
        color_discrete_map=PLATFORM_COLORS,
        template="plotly_dark",
        category_orders={"generation": gen_order},
        title="Cuota de Mercado por Generación"
    )
    fig.update_traces(hovertemplate="<b>%{x}</b><br>%{color}: %{y:.1f}M<extra></extra>")
    fig.update_layout(xaxis_title="", yaxis_title="Ventas (Millones)", barmode="stack", margin=dict(l=0, r=0, t=40, b=20), legend_title="Fabricante")
    return fig

def create_catalog_distribution_chart(df_games):
    from collections import Counter
    platform_counts = Counter()
    for (platforms,) in zip(df_games['platforms']):
        if not platforms: continue
        for p in str(platforms).split(', '):
            platform_counts[p.strip()] += 1
            
    df_cat = pd.DataFrame(platform_counts.most_common(15), columns=['Platform', 'Games'])
    df_cat = df_cat.sort_values("Games", ascending=True)
    
    def get_manuf(plat):
        plat_lower = plat.lower()
        if any(x in plat_lower for x in ['playstation', 'ps']): return 'Sony'
        if any(x in plat_lower for x in ['xbox']): return 'Microsoft'
        if any(x in plat_lower for x in ['nintendo', 'wii', 'game boy', 'ds', 'gamecube', 'snes', 'nes', 'switch']): return 'Nintendo'
        if any(x in plat_lower for x in ['sega', 'genesis', 'dreamcast']): return 'Sega'
        if 'pc' in plat_lower: return 'PC'
        if 'mac' in plat_lower or 'ios' in plat_lower: return 'Apple'
        if 'android' in plat_lower: return 'Google'
        return 'Other'
        
    df_cat['Manufacturer'] = df_cat['Platform'].apply(get_manuf)
    
    fig = px.bar(
        df_cat,
        x="Games",
        y="Platform",
        color="Manufacturer",
        color_discrete_map=PLATFORM_COLORS,
        text="Games",
        template="plotly_dark",
        title="Plataformas con mayor volumen de catálogo"
    )
    fig.update_traces(textposition="outside", hovertemplate="<b>%{y}</b><br>Juegos: %{x}<extra></extra>")
    fig.update_layout(xaxis_title="Cantidad de Juegos", yaxis_title="", margin=dict(l=0, r=20, t=40, b=20), showlegend=False)
    return fig
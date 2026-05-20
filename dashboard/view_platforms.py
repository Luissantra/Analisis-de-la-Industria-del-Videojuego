import streamlit as st
import pandas as pd
import sqlite3
import base64
import os
import json
from pathlib import Path
import config
from charts_platforms import (
    create_roadmap_timeline, 
    PLATFORM_COLORS, 
    create_sales_ranking_chart,
    create_generation_market_share_chart,
    create_catalog_distribution_chart,
    create_lifespan_gantt_chart
)


@st.cache_data(show_spinner="Cargando plataformas...")
def load_platforms_data():
    # Cache busted on 2026-05-20 v4
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        df = pd.read_sql_query("SELECT * FROM platforms", conn)
        conn.close()
        
        # Cruzamos dinámicamente con platforms.json para obtener discontinued_year y form_factor
        if os.path.exists(config.PLATFORMS_JSON):
            with open(config.PLATFORMS_JSON, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            df_json = pd.DataFrame(json_data)[['name', 'discontinued_year', 'form_factor']]
            
            # Quitar duplicados
            df_json = df_json.drop_duplicates(subset=['name'])
            
            # Limpiar columnas de la tabla de la BD si ya existían para evitar colisión en merge
            for col in ['discontinued_year', 'form_factor']:
                if col in df.columns:
                    df = df.drop(columns=[col])
                    
            df = pd.merge(df, df_json, on='name', how='left')
            
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(show_spinner="Cargando catálogo...")
def load_games_platforms_data():
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        df = pd.read_sql_query("SELECT platforms FROM games WHERE platforms IS NOT NULL", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def render_platforms_module():
    st.title("🕹️ Evolución y Roadmap de Consolas")
    st.markdown("Explora la histórica 'Guerra de Consolas'. Cada carril representa a un fabricante. El tamaño de los puntos indica el éxito comercial (ventas globales).")
    
    df_platforms = load_platforms_data()
    if df_platforms.empty:
        st.warning("⚠️ No se encontraron datos. Ejecuta primero 'python scripts/etl_platforms.py'")
        return

    # Sidebar Filtros
    st.sidebar.header("Filtros de Plataformas")
    
    fabricantes = sorted(df_platforms['manufacturer'].unique())
    selected_fabricantes = st.sidebar.multiselect("Fabricante:", fabricantes, default=fabricantes)
    
    generaciones = sorted(df_platforms['generation'].unique())
    selected_generaciones = st.sidebar.multiselect("Generación:", generaciones, default=generaciones)
    
    form_filter = st.sidebar.radio("Factor de forma:", ["Todas", "Sobremesa", "Portátiles"], horizontal=True)
    st.sidebar.info("💡 **Nota:** Estos filtros afectan a los Capítulos 1, 2 y a la Ficha Técnica. El Capítulo 3 (Catálogo Global) es independiente para mostrar el contexto completo de la industria.")

    # Filtrar datos
    df_filtered = df_platforms[
        (df_platforms['manufacturer'].isin(selected_fabricantes)) &
        (df_platforms['generation'].isin(selected_generaciones))
    ].copy()
    
    if form_filter == "Sobremesa":
        if 'form_factor' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['form_factor'] == 'home']
    elif form_filter == "Portátiles":
        if 'form_factor' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['form_factor'] == 'portable']

    if df_filtered.empty:
        st.warning("⚠️ No hay plataformas con los filtros seleccionados.")
        return

    # KPIs Agregados Superiores (Dinámicos)
    total_consolas = len(df_filtered)
    ventas_totales = df_filtered['units_sold_millions'].sum()
    df_sorted_sales = df_filtered.sort_values(by='units_sold_millions', ascending=False)
    top_consola = df_sorted_sales.iloc[0]['name'] if not df_sorted_sales.empty else "N/A"
    total_catalogo = df_filtered['games_count'].sum() if 'games_count' in df_filtered.columns else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Plataformas", f"{total_consolas}")
    with col2:
        st.metric("Ventas Totales", f"{ventas_totales:,.1f} M")
    with col3:
        st.metric("Consola Más Vendida", top_consola)
    with col4:
        st.metric("Catálogo Total (Juegos)", f"{total_catalogo:,.0f}")
        
    st.divider()

    # Capítulo 1
    st.markdown("### 📖 Capítulo 1: El Campo de Batalla")
    
    tab_roadmap, tab_gantt = st.tabs(["🚀 Línea de Tiempo de Lanzamiento", "📅 Duración del Ciclo de Vida (Gantt)"])
    
    with tab_roadmap:
        st.markdown("Cada carril representa un fabricante. El tamaño de los puntos indica el éxito comercial (ventas globales).")
        fig_roadmap = create_roadmap_timeline(df_filtered)
        evento = st.plotly_chart(fig_roadmap, use_container_width=True, on_select="rerun", key="roadmap_chart")
        
    with tab_gantt:
        st.markdown("""
        Esta visualización Gantt interactiva muestra el **ciclo de vida útil** de cada consola desde su lanzamiento 
        hasta su descontinuación. Permite analizar el solapamiento comercial entre generaciones y la longevidad de cada plataforma.
        """)
        
        # Calcular y añadir las métricas de tiempo mínimo, medio y máximo de ciclo de vida
        df_lifespan = df_filtered.dropna(subset=["release_year", "discontinued_year"])
        df_lifespan = df_lifespan[df_lifespan["generation"] != "Desconocida / Software"]
        
        if not df_lifespan.empty:
            lifespans = df_lifespan["discontinued_year"].astype(int) - df_lifespan["release_year"].astype(int)
            min_life = int(lifespans.min())
            max_life = int(lifespans.max())
            avg_life = float(lifespans.mean())
            
            # Identificar consolas correspondientes
            min_consoles = df_lifespan[df_lifespan["discontinued_year"].astype(int) - df_lifespan["release_year"].astype(int) == min_life]["name"].tolist()
            max_consoles = df_lifespan[df_lifespan["discontinued_year"].astype(int) - df_lifespan["release_year"].astype(int) == max_life]["name"].tolist()
            
            st.markdown("#### 📊 Duración y Longevidad del Ciclo de Vida")
            col_g1, col_g2, col_g3 = st.columns(3)
            with col_g1:
                st.metric(
                    label="Ciclo de Vida Mínimo", 
                    value=f"{min_life} años", 
                    delta=f"Menor duración: {min_consoles[0]}" if min_consoles else None,
                    delta_color="off",
                    help=f"Consola(s) con menor duración comercial: {', '.join(min_consoles)}"
                )
            with col_g2:
                st.metric(
                    label="Ciclo de Vida Promedio", 
                    value=f"{avg_life:.1f} años",
                    help="Duración media general de la vida comercial de las consolas seleccionadas."
                )
            with col_g3:
                st.metric(
                    label="Ciclo de Vida Máximo", 
                    value=f"{max_life} años", 
                    delta=f"Mayor longevidad: {max_consoles[0]}" if max_consoles else None,
                    delta_color="off",
                    help=f"Consola(s) con mayor duración comercial activa: {', '.join(max_consoles)}"
                )
            st.markdown("<br>", unsafe_allow_html=True)
            
        fig_gantt = create_lifespan_gantt_chart(df_filtered)
        st.plotly_chart(fig_gantt, use_container_width=True)
    
    st.divider()
    
    # Capítulo 4 (Detalle On-click reubicado aquí)
    # Si el usuario hace clic en una consola
    if evento and "selection" in evento and evento["selection"].get("points"):
        punto = evento["selection"]["points"][0]
        nombre_consola = punto["customdata"][0]
        
        consola_data = df_filtered[df_filtered['name'] == nombre_consola].iloc[0]
        color_marca = PLATFORM_COLORS.get(consola_data['manufacturer'], "white")
        
        # Panel expandido mejorado
        st.markdown(f"### 🔍 Detalle: {nombre_consola}")
        
        c1, c2, c3 = st.columns([1, 1.5, 1])
        
        with c1:
            img_name = consola_data['local_image']
            
            if pd.notna(img_name) and bool(img_name):
                consoles_dir = getattr(config, 'CONSOLES_DIR', Path(__file__).resolve().parent / "assets" / "consoles")
                img_path = consoles_dir / str(img_name)
                if img_path.exists():
                    with open(img_path, "rb") as img_file:
                        encoded = base64.b64encode(img_file.read()).decode()
                    st.markdown(f'<div style="text-align:center; padding: 20px; background-color: rgba(255,255,255,0.05); border-radius: 15px;"><img src="data:image/png;base64,{encoded}" style="max-width: 100%; max-height: 250px; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.5));"></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="text-align:center; padding: 60px 20px; background-color: rgba(255,255,255,0.02); border-radius: 15px; border: 1px dashed rgba(255,255,255,0.1);"><h1 style="color: rgba(255,255,255,0.2); font-size: 80px; margin:0;">🎮</h1><p style="color: rgba(255,255,255,0.3); font-style: italic;">Sin imagen disponible</p></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="text-align:center; padding: 60px 20px; background-color: rgba(255,255,255,0.02); border-radius: 15px; border: 1px dashed rgba(255,255,255,0.1);"><h1 style="color: rgba(255,255,255,0.2); font-size: 80px; margin:0;">🎮</h1><p style="color: rgba(255,255,255,0.3); font-style: italic;">Sin imagen disponible</p></div>', unsafe_allow_html=True)
                
        with c2:
            st.markdown(f"<h2 style='color:{color_marca};'>{consola_data['name']}</h2>", unsafe_allow_html=True)
            st.markdown(f"**Fabricante:** {consola_data['manufacturer']}")
            st.markdown(f"**Lanzamiento:** {consola_data['release_year']}")
            st.markdown(f"**Generación:** {consola_data['generation']}")
            
            # Progress bar visual para ventas
            ventas = consola_data['units_sold_millions']
            ventas_str = f"{ventas} M" if pd.notna(ventas) and ventas > 0 else "N/A"
            max_ventas_historico = 155.0 # PS2
            pct = min(100, int((ventas / max_ventas_historico) * 100)) if pd.notna(ventas) else 0
            
            st.markdown(f"**Ventas Totales:** {ventas_str}")
            st.markdown(
                f"""
                <div style="width: 100%; background-color: rgba(255,255,255,0.1); border-radius: 5px; height: 10px; margin-top: 5px;">
                  <div style="width: {pct}%; background-color: {color_marca}; height: 100%; border-radius: 5px;"></div>
                </div>
                <div style="font-size: 11px; color: gray; margin-top: 5px;">Ventas vs PS2 (récord histórico)</div>
                """, unsafe_allow_html=True
            )
            
        with c3:
            st.markdown("### Rendimiento Competitivo")
            # Contexto competitivo
            gen = consola_data['generation']
            df_comp = df_platforms[df_platforms['generation'] == gen].sort_values("units_sold_millions", ascending=False)
            rank = list(df_comp['name']).index(consola_data['name']) + 1 if consola_data['name'] in list(df_comp['name']) else "N/A"
            total_in_gen = len(df_comp)
            
            st.metric("Posición en su Generación", f"#{rank} de {total_in_gen}")
            
            cat = consola_data.get('games_count', 0)
            st.metric("Juegos en Catálogo", f"{cat:,.0f}")
            
            if cat > 0 and pd.notna(ventas) and ventas > 0:
                ratio = (ventas * 1_000_000) / cat
                st.metric("Ventas por Juego", f"{ratio:,.0f} unds")
    else:
        st.info("👆 Haz clic en cualquier consola en la línea de tiempo superior para ver sus detalles.")

    st.divider()

    # Capítulo 2
    st.markdown("### 📖 Capítulo 2: La Guerra por Números")
    st.markdown("¿Quién domina cada era? Visualiza el top histórico y la cuota de mercado por generación.")
    c2_1, c2_2 = st.columns(2)
    with c2_1:
        fig_ranking = create_sales_ranking_chart(df_filtered)
        st.plotly_chart(fig_ranking, use_container_width=True)
    with c2_2:
        fig_market_share = create_generation_market_share_chart(df_filtered)
        st.plotly_chart(fig_market_share, use_container_width=True)

    st.divider()

    # Capítulo 3
    st.markdown("### 📖 Capítulo 3: El Poder del Catálogo")
    st.markdown("El tamaño del ecosistema de juegos es tan importante como las ventas de hardware.")
    st.info("💡 **Contexto:** En esta métrica se incluye PC, que aunque no es una consola con ciclo de vida definido, domina masivamente el volumen de catálogo global.")
    
    df_games_platforms = load_games_platforms_data()
    if not df_games_platforms.empty:
        fig_catalog = create_catalog_distribution_chart(df_games_platforms)
        st.plotly_chart(fig_catalog, use_container_width=True)
    else:
        st.warning("⚠️ No se encontraron datos de catálogo. Ejecuta primero 'python scripts/etl_games_rawg.py'")
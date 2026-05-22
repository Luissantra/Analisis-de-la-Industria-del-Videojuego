import streamlit as st
import pandas as pd
import base64
import sqlite3
import config
from pathlib import Path
from charts_corporate import (
    create_sunburst_chart, 
    create_treemap_chart, 
    create_genre_and_score_chart, 
    create_genre_pie_chart, 
    create_acquisition_timeline_chart, 
    create_score_distribution_chart, 
    create_magic_quadrant_chart,
    PARENT_COLOR_MAP
)
from charts_community import create_esrb_distribution_chart
from model_corporate import get_all_corporate_data, get_conglomerate_data, get_all_games_data

# Nombres abreviados para evitar saltos de línea en las tarjetas
SHORT_NAMES = {
    "Microsoft Gaming (Xbox, ZeniMax, Activision Blizzard)": "Microsoft Gaming",
    "Sony Interactive Entertainment (PlayStation Studios)": "Sony Interactive",
    "Electronic Arts (EA)": "Electronic Arts",
    "Take-Two Interactive": "Take-Two",
    "Independent & Other Publishers": "Indies & Otros"
}

@st.cache_data
def get_base64_image(empresa_name):
    """Lee el logo local y lo convierte a base64 para inyectarlo en HTML."""
    safe_name = "".join([c if c.isalnum() or c in " &()_-" else "_" for c in empresa_name])
    logos_dir = getattr(config, 'LOGOS_DIR', Path(__file__).resolve().parent / "assets" / "logos")
    img_path = logos_dir / f"{safe_name}.png"
    
    if img_path.exists():
        with open(img_path, "rb") as img_file:
            encoded = base64.b64encode(img_file.read()).decode()
            return f"data:image/png;base64,{encoded}"
    return None


# Función Callback para actualizar el estado instantáneamente
def seleccionar_matriz(matriz):
    st.session_state.selected_parent = matriz

def render_corporate_module():
    st.title("🏢 Estructura Corporativa de la Industria")
    
    # CSS Inyectado para interacciones profesionales (Efecto Hover en las tarjetas)
    st.markdown("""
    <style>
    .corp-card {
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    }
    .corp-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(255, 255, 255, 0.15) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Extraemos solo los nombres únicos para la galería de navegación usando la vista global
    df_corp_all = get_all_corporate_data()
    if 'selected_parent' not in st.session_state:
        st.session_state.selected_parent = "Global"

    # Forzamos el orden de las empresas basándonos en nuestro mapa de colores predefinido
    raw_empresas = list(df_corp_all['Parent'].unique())
    empresas = [p for p in PARENT_COLOR_MAP.keys() if p in raw_empresas]
    
    # Añadimos cualquier empresa que pudiera faltar (por seguridad)
    for p in raw_empresas:
        if p not in empresas:
            empresas.append(p)
            
    seleccion = st.session_state.selected_parent
    
    # 1. Galería de Logos con Interacción Visual (Opacidad)
    st.markdown("##### Selecciona un conglomerado:")
    cols = st.columns(6)
    
    for i, empresa in enumerate(empresas):
        with cols[i % 6]:
            with st.container(border=False):
                # Calcular estilos dependiendo de si está seleccionada o no
                is_selected = (seleccion == empresa)
                is_global = (seleccion == "Global")
                
                # Si estamos en Global, todos brillan. Si hay uno seleccionado, los demás se atenúan (30% opacidad).
                opacity = "1.0" if is_selected or is_global else "0.3"
                brand_color = PARENT_COLOR_MAP.get(empresa, "#444444")
                img_b64 = get_base64_image(empresa)
                display_name = SHORT_NAMES.get(empresa, empresa)
                
                bg_color = "rgba(240, 242, 246, 0.92)" # Blanco suavizado para menos contraste con el fondo oscuro
                div_style = (
                    f"display: flex; justify-content: center; align-items: center; height: 95px; "
                    f"opacity: {opacity}; transition: 0.3s; background-color: {bg_color}; "
                    f"border: 3px solid {brand_color}; border-radius: 10px; padding: 10px; margin-bottom: 10px;"
                )

                if img_b64:
                    st.markdown(
                        f'<div class="corp-card" style="{div_style}">'
                        f'<img src="{img_b64}" style="max-height: 100%; max-width: 100%; object-fit: contain;">'
                        f'</div>', 
                        unsafe_allow_html=True
                    )
                else:
                    # Fallback por si falta el logo local
                    st.markdown(f'<div class="corp-card" style="{div_style}"><span style="color:#000000; font-weight:bold; font-size:12px; text-align:center;">{empresa}</span></div>', unsafe_allow_html=True)
                
                # Botón terciario (sin fondo ni bordes) para que actúe como una etiqueta de texto clicable
                if is_selected:
                    st.button(f"**{display_name}**", key=f"btn_{i}", help=empresa, disabled=True, width="stretch", type="primary")
                else:
                    st.button(display_name, key=f"btn_{i}", help=empresa, on_click=seleccionar_matriz, args=(empresa,), width="stretch", type="tertiary")

    # 2. Control Superior
    col_v, col_btn = st.columns([4, 1])
    with col_btn:
        if seleccion != "Global":
            if st.button("🔄 Ver Todas", width="stretch"):
                seleccionar_matriz("Global")
                st.rerun()
                
    st.divider()

    # 3. Representación Gráfica
    # 3. Representación Gráfica
    if seleccion == "Global":
        st.subheader("🌍 Visión Macro (Ecosistema Completo)")
        
        st.markdown("### 🏛️ Capítulo 1: La Arquitectura del Monopolio")
        st.markdown("""
        La industria del videojuego está viviendo una era de **consolidación masiva**. Este gráfico *Sunburst* permite visualizar 
        la jerarquía de propiedad: desde los grandes conglomerados (capa interna) hasta los estudios filiales (capa externa).
        """)
        
        fig = create_sunburst_chart(df_corp_all)
        # Capturamos el evento de clic nativo (soportado en Streamlit >= 1.35)
        try:
            evento = st.plotly_chart(fig, width="stretch", on_select="rerun")
            if evento and "selection" in evento and evento["selection"].get("points"):
                clicked_label = evento["selection"]["points"][0].get("label")
                # Si el usuario hace clic en un conglomerado, sincronizamos la tarjeta
                if clicked_label in empresas and clicked_label != seleccion:
                    st.session_state.selected_parent = clicked_label
                    st.rerun()
        except TypeError:
            # Fallback por si la versión de Streamlit es antigua y no soporta on_select
            st.plotly_chart(fig, width="stretch")
            
        st.write("---")
        
        st.markdown("### 🎯 Capítulo 2: Distribución de Calidad Crítica")
        st.markdown("""
        Este gráfico de violín representa la distribución y dispersión de las valoraciones de Metacritic a nivel global. 
        Nos permite observar la consistencia general del ecosistema, revelando si la producción de la industria se concentra 
        en títulos promedio o si cuenta con una distribución equilibrada hacia la excelencia crítica.
        """)
        fig_dist_global = create_score_distribution_chart(df_corp_all, is_global=True)
        if fig_dist_global:
            st.plotly_chart(fig_dist_global, width="stretch")
            
        st.write("---")
        
        st.markdown("### 👥 Capítulo 3: Target de Audiencia Global")
        st.markdown("""
        ¿A quién venden los gigantes? La distribución por edades (ESRB) nos da pistas sobre 
        la estrategia de segmentación demográfica de cada compañía en su portfolio global.
        """)
        df_games_all = get_all_games_data()
        fig_esrb = create_esrb_distribution_chart(df_games_all)
        if fig_esrb: st.plotly_chart(fig_esrb, width="stretch")
        
        st.write("---")
        
        st.markdown("### 📊 Capítulo 4: El Cuadrante Mágico de los Publishers")
        st.markdown("""
        ¿Dónde se posiciona cada gigante en el mapa competitivo global? Este gráfico, inspirado en los cuadrantes de Gartner, 
        cruza la **popularidad social media promedio** de sus juegos (eje X) con su **calidad crítica promedio** (eje Y). 
        El tamaño de las burbujas es proporcional al **volumen total de juegos producidos** en su portfolio.
        """)
        
        # Filtro dinámico para excluir a los indies e independientes
        excluir_indies = st.checkbox(
            "Excluir 'Independent & Other Publishers' para enfocar el análisis en los competidores puros", 
            value=False,
            help="Al activar esta opción, eliminamos el grupo catch-all de indies y otros publicadores pequeños. Esto redistribuye la escala visual y las medias críticas, revelando con total claridad las posiciones competitivas de los restantes gigantes de la industria."
        )
        
        df_magic_input = df_corp_all.copy()
        if excluir_indies:
            df_magic_input = df_magic_input[df_magic_input['Parent'] != "Independent & Other Publishers"]
            
        fig_magic = create_magic_quadrant_chart(df_magic_input)
        if fig_magic is not None:
            st.plotly_chart(fig_magic, width="stretch")
    else:
        st.subheader(f"🔍 Análisis Estructural: {seleccion}")
        df_filtrado = get_conglomerate_data(seleccion)
        brand_color = PARENT_COLOR_MAP.get(seleccion, "#444444")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Estudios Filiales", len(df_filtrado))
        c2.metric("Total de Juegos", int(df_filtrado['Total_Games'].sum()) if 'Total_Games' in df_filtrado.columns else "N/A")
        c3.metric("Presencia (Países)", df_filtrado['Country'].nunique())
        c4.metric("Ciudades Diferentes", df_filtrado['City'].nunique())
        
        st.write("---")
        
        st.markdown("### 🏺 Capítulo 1: El ADN del Conglomerado")
        st.markdown(f"Exploramos la composición interna de **{seleccion}**. La jerarquía nos muestra qué estudios tienen mayor peso en la producción total.")
        
        col_grafico, col_lista = st.columns([1, 1.3])
        
        with col_grafico:
            fig = create_treemap_chart(df_filtrado)
            st.plotly_chart(fig, width="stretch")
            
        with col_lista:
            # Preparamos el dataframe para visualización
            df_display = df_filtrado[['Studio Name', 'City', 'Country', 'Acquisition_Year', 'Total_Games', 'Top_Game', 'avg_metacritic']].copy()
            df_display.rename(columns={
                'Studio Name': 'Estudio',
                'City': 'Ciudad',
                'Country': 'País',
                'Acquisition_Year': 'Año (Adq/Fund)',
                'Total_Games': 'Juegos',
                'Top_Game': 'Mejor Juego',
                'avg_metacritic': 'Nota Media'
            }, inplace=True)
            
            st.dataframe(
                df_display,
                width="stretch",
                hide_index=True,
                height=400 
            )

        st.markdown("---")
        
        st.markdown("### 📈 Capítulo 2: Ritmo de Expansión y Dominio")
        st.markdown("¿Cuándo se consolidó este gigante? La línea de tiempo muestra los hitos de adquisición y fundación de sus estudios actuales.")
        
        col_timeline, col_dist = st.columns([1.2, 1])
        
        with col_timeline:
            fig_timeline = create_acquisition_timeline_chart(df_filtrado, color=brand_color)
            if fig_timeline:
                st.plotly_chart(fig_timeline, width="stretch")
            else:
                st.info("ℹ️ No hay suficientes datos de años registrados para este conglomerado.")
                
        with col_dist:
            st.markdown("##### 🎯 Consistencia de Calidad")
            fig_dist = create_score_distribution_chart(df_filtrado, color=brand_color)
            if fig_dist:
                st.plotly_chart(fig_dist, width="stretch")
            else:
                st.info("ℹ️ Ejecuta `etl_games_rawg.py` para obtener datos de Metacritic.")
                
        fig_pie = create_genre_pie_chart(df_filtrado, color=brand_color)
        if fig_pie:
            st.markdown("##### 🎭 Diversificación por Género")
            st.plotly_chart(fig_pie, width="stretch")

        # Para el top 10 necesitamos los juegos de ese conglomerado
        df_games_all = get_all_games_data()
        # Robust case-insensitive comparison to avoid string format issues
        df_games_filt = df_games_all[df_games_all['conglomerate'].astype(str).str.strip().str.lower() == seleccion.strip().lower()]

        st.write("---")
        
        st.markdown("### 👥 Capítulo 3: Target de Audiencia Específico")
        st.markdown(f"Analizamos el perfil de edad y el público objetivo del portfolio de **{seleccion}**.")
        fig_esrb_spec = create_esrb_distribution_chart(df_games_filt)
        if fig_esrb_spec: st.plotly_chart(fig_esrb_spec, width="stretch")
        else: st.info("ℹ️ No hay datos suficientes de clasificación ESRB para este conglomerado.")

        st.write("---")
        st.markdown("### 🏆 Capítulo 4: Los 10 Títulos Más Aclamados")
        if not df_games_filt.empty:
            df_top_10 = df_games_filt.sort_values(by='metacritic', ascending=False).head(10)
            df_top_10 = df_top_10[['title', 'studio', 'metacritic', 'release_date']]
            df_top_10.rename(columns={
                'title': 'Título',
                'studio': 'Desarrollador',
                'metacritic': 'Metacritic',
                'release_date': 'Lanzamiento'
            }, inplace=True)
            st.table(df_top_10)
        else:
            st.info("ℹ️ No hay datos de juegos disponibles para mostrar el Top 10.")
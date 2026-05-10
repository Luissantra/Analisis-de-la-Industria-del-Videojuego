import streamlit as st
import pandas as pd
import base64
import sqlite3
import config
from pathlib import Path
from charts_corporate import create_sunburst_chart, create_treemap_chart, create_genre_and_score_chart, create_genre_pie_chart, create_acquisition_timeline_chart, create_score_distribution_chart, PARENT_COLOR_MAP
from model_corporate import get_all_corporate_data, get_conglomerate_data

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
    img_path = config.LOGOS_DIR / f"{safe_name}.png"
    
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
                    st.button(f"**{display_name}**", key=f"btn_{i}", help=empresa, disabled=True, use_container_width=True, type="primary")
                else:
                    st.button(display_name, key=f"btn_{i}", help=empresa, on_click=seleccionar_matriz, args=(empresa,), use_container_width=True, type="tertiary")

    # 2. Control Superior
    col_v, col_btn = st.columns([4, 1])
    with col_btn:
        if seleccion != "Global":
            if st.button("🔄 Ver Todas", use_container_width=True):
                seleccionar_matriz("Global")
                st.rerun()
                
    st.divider()

    # 3. Representación Gráfica
    if seleccion == "Global":
        st.subheader("🌍 Visión Macro (Ecosistema Completo)")
        fig = create_sunburst_chart(df_corp_all)
        
        # Capturamos el evento de clic nativo (soportado en Streamlit >= 1.35)
        try:
            evento = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
            if evento and "selection" in evento and evento["selection"].get("points"):
                clicked_label = evento["selection"]["points"][0].get("label")
                # Si el usuario hace clic en un conglomerado, sincronizamos la tarjeta
                if clicked_label in empresas and clicked_label != seleccion:
                    st.session_state.selected_parent = clicked_label
                    st.rerun()
        except TypeError:
            # Fallback por si la versión de Streamlit es antigua y no soporta on_select
            st.plotly_chart(fig, use_container_width=True)
            
        st.write("---")
        st.markdown("#### 🏆 Análisis Global del Ecosistema")
        
        st.markdown("##### 🎯 Consistencia y Distribución de Calidad Global (Metacritic)")
        fig_dist_global = create_score_distribution_chart(df_corp_all, is_global=True)
        if fig_dist_global:
            st.plotly_chart(fig_dist_global, use_container_width=True)
            
        st.write("---")
        st.markdown("##### 🎲 Matriz de Portfolio (Volumen vs Calidad por Género)")
        fig_genres_global = create_genre_and_score_chart(df_corp_all)
        if fig_genres_global:
            st.plotly_chart(fig_genres_global, use_container_width=True)
        else:
            st.info("ℹ️ Ejecuta `etl_games.py` para habilitar gráficos de géneros y valoraciones.")
    else:
        st.subheader(f"🔍 Análisis Estructural: {seleccion}")
        df_filtrado = get_conglomerate_data(seleccion)
        brand_color = PARENT_COLOR_MAP.get(seleccion, "#444444")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Estudios Filiales", len(df_filtrado))
        c2.metric("Presencia (Países)", df_filtrado['Country'].nunique())
        c3.metric("Ciudades Diferentes", df_filtrado['City'].nunique())
        
        st.write("---")
        
        col_grafico, col_lista = st.columns([1, 1.3])
        
        with col_grafico:
            st.markdown("#### Jerarquía y Presencia Global")
            fig = create_treemap_chart(df_filtrado)
            st.plotly_chart(fig, use_container_width=True)
            
        with col_lista:
            st.markdown("### 🎮 Directorio de Estudios")
            
            # Preparamos el dataframe para visualización
            df_display = df_filtrado[['Studio Name', 'City', 'Country', 'Acquisition_Year', 'Top_Game', 'Metacritic']].copy()
            df_display.rename(columns={
                'Studio Name': 'Estudio',
                'City': 'Ciudad',
                'Country': 'País',
                'Acquisition_Year': 'Año (Adq/Fund)',
                'Top_Game': 'Juego Destacado',
                'Metacritic': 'Nota'
            }, inplace=True)
            
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                height=400 # Altura ajustada para alinear con el gráfico Sunburst
            )

        st.markdown("---")
        
        st.markdown("#### 🏆 Análisis de Portfolio e Histórico de Expansión")
        
        col_timeline, col_dist = st.columns([1.2, 1])
        
        with col_timeline:
            st.markdown("##### 📈 Expansión (Adquisiciones/Fundaciones)")
            fig_timeline = create_acquisition_timeline_chart(df_filtrado, color=brand_color)
            if fig_timeline:
                st.plotly_chart(fig_timeline, use_container_width=True)
            else:
                st.info("ℹ️ No hay suficientes datos de años registrados para este conglomerado.")
                
        with col_dist:
            st.markdown("##### 🎯 Consistencia de Calidad (Metacritic)")
            fig_dist = create_score_distribution_chart(df_filtrado, color=brand_color)
            if fig_dist:
                st.plotly_chart(fig_dist, use_container_width=True)
            else:
                st.info("ℹ️ Ejecuta `etl_games.py` para obtener datos de Metacritic.")
                
        st.write("---")
        st.markdown("##### 🎲 Distribución de Géneros")
        fig_pie = create_genre_pie_chart(df_filtrado, color=brand_color)
        if fig_pie:
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("ℹ️ No hay suficientes datos de géneros para este conglomerado.")
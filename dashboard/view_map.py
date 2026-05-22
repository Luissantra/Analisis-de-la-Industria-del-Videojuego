import streamlit as st
import plotly.express as px
import json
import pandas as pd
import config
from pathlib import Path
from streamlit_folium import st_folium
from charts import create_interactive_map

def render_map_module(filtered_df, mode="Producción"):
    """
    Renderiza el módulo del mapa interactivo con dos modos seleccionables:
    - Producción: Ubicación de estudios filiales y tiers.
    - Mercado: Ingresos globales y población gamer por país.
    """
    
    if mode == "Mercado":
        st.subheader("Mercado Global: Ingresos y Audiencia por País")
        
        json_path = config.BASE_DIR / "config_data" / "gaming_markets_geo.json"
        if not json_path.exists():
            st.error("No se encontró el dataset de mercados gaming en config_data/gaming_markets_geo.json")
            return
            
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                market_data = json.load(f)
            df_market = pd.DataFrame(market_data)
        except Exception as e:
            st.error(f"Error al cargar datos del mercado: {e}")
            return
             # Calcular métricas dinámicas
        total_rev = df_market["revenue_bn"].sum()
        total_players = df_market["players_m"].sum()
        weighted_arpu = (total_rev * 1000) / total_players
        
        # Región líder por ingresos
        region_totals = df_market.groupby("region")["revenue_bn"].sum()
        top_region = region_totals.idxmax()
        top_region_val = region_totals.max()
        
        st.markdown("""
        <style>
        .metric-card {
            background-color: rgba(30, 41, 59, 0.45);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            border-left: 4px solid #10B981; /* Verde esmeralda para Ingresos */
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
            border: 1px solid rgba(255,255,255,0.05);
            transition: all 0.25s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            background-color: rgba(30, 41, 59, 0.6);
            border-color: rgba(255,255,255,0.1);
        }
        .metric-card.players { border-left-color: #06B6D4; } /* Cian para audiencia */
        .metric-card.arpu { border-left-color: #F59E0B; } /* Ámbar para ARPU */
        .metric-card.leader { border-left-color: #EC4899; } /* Rosa para la región líder */
        .metric-value { font-size: 22px; font-weight: 800; margin: 0; color: #F8FAFC; }
        .metric-label { font-size: 12px; color: #94A3B8; margin: 4px 0 0 0; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
        </style>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div class="metric-card"><p class="metric-value">${total_rev:.1f} Bn</p><p class="metric-label">💰 Ingresos Globales</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card players"><p class="metric-value">{total_players / 1000:.2f} Bn</p><p class="metric-label">👥 Audiencia Gamer</p></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card arpu"><p class="metric-value">${weighted_arpu:.2f}</p><p class="metric-label">📊 ARPU Medio Anual</p></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="metric-card leader"><p class="metric-value" style="font-size: 19px; padding-top: 2px;">{top_region}</p><p class="metric-label">🏆 Región Líder</p></div>', unsafe_allow_html=True)
            
        st.divider()
        
        # Agregar columna ARPU para cada país y %
        df_market["arpu"] = (df_market["revenue_bn"] * 1000) / df_market["players_m"]
        df_market["global_revenue_pct"] = (df_market["revenue_bn"] / total_rev) * 100
        
        # Mapa Choropleth con Plotly usando paleta Tealgrn
        fig = px.choropleth(
            df_market,
            locations="iso_alpha",
            color="revenue_bn",
            hover_name="country",
            color_continuous_scale="Tealgrn",
            labels={'revenue_bn': 'Ingresos ($Bn)'},
            template="plotly_dark",
            custom_data=["region", "players_m", "arpu", "global_revenue_pct"]
        )
        
        fig.update_traces(
            hovertemplate=(
                "<b>%{hovertext}</b><br><br>"
                "Región: %{customdata[0]}<br>"
                "Ingresos: $%{z:.1f} Bn (%{customdata[3]:.1f}%)<br>"
                "Jugadores: %{customdata[1]:,d}M<br>"
                "ARPU: $%{customdata[2]:.2f}/año<extra></extra>"
            )
        )
        
        fig.update_geos(
            showframe=False,
            showcoastlines=True,
            projection_type="natural earth",
            coastlinecolor="rgba(255,255,255,0.15)",
            landcolor="rgba(255,255,255,0.02)",
            showland=True,
            showocean=True,
            oceancolor="rgba(15,23,42,0.9)"
        )
        
        fig.update_layout(
            margin=dict(t=10, l=0, r=0, b=0),
            height=600,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            coloraxis_colorbar=dict(
                title="Ingresos<br>($Bn)",
                thickness=15,
                len=0.6,
                x=0.92,
                y=0.5
            )
        )
        
        st.plotly_chart(fig, width="stretch")
        
        st.divider()
        
        # --- Gráficos Analíticos de Mercado ---
        col_l, col_r = st.columns(2)
        
        with col_l:
            # Treemap de distribución por región y país usando Tealgrn
            fig_tree = px.treemap(
                df_market,
                path=["region", "country"],
                values="revenue_bn",
                color="revenue_bn",
                color_continuous_scale="Tealgrn",
                template="plotly_dark",
                title="Estructura de Ingresos por Región Geográfica"
            )
            fig_tree.update_traces(
                textinfo="label+value",
                hovertemplate="<b>%{label}</b><br>Ingresos: $%{value:.1f} Bn<extra></extra>",
                marker=dict(line=dict(color='rgba(15,23,42,0.6)', width=1))
            )
            fig_tree.update_layout(
                margin=dict(t=40, b=10, l=10, r=10),
                height=350,
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_tree, width="stretch")
            
        with col_r:
            # Bar chart de los países con mayor ARPU usando paleta YlOrRd
            top_arpu = df_market.sort_values(by="arpu", ascending=False)
            fig_bar = px.bar(
                top_arpu,
                x="arpu",
                y="country",
                orientation="h",
                color="arpu",
                color_continuous_scale="YlOrRd",
                template="plotly_dark",
                labels={'arpu': 'ARPU ($)', 'country': 'País'},
                title="Gasto Medio Anual por Jugador (ARPU en USD)",
                text="arpu"
            )
            fig_bar.update_traces(
                hovertemplate="<b>%{y}</b><br>ARPU: $%{x:.2f}<extra></extra>",
                texttemplate="$%{text:.0f}",
                textposition="outside",
                textfont=dict(size=11, color="#E2E8F0")
            )
            fig_bar.update_layout(
                margin=dict(t=40, b=10, l=70, r=10),
                height=350,
                coloraxis_showscale=False,
                yaxis=dict(categoryorder="total ascending", automargin=True),
                xaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.08)")
            )
            st.plotly_chart(fig_bar, width="stretch")
            
    else:
        # Modo Producción (actual)
        st.subheader("Mapa de Ubicación de Estudios de Videojuegos")
        
        if not filtered_df.empty:
            total_estudios = len(filtered_df)
            total_paises = filtered_df['Country'].nunique()
            
            valid_regions = filtered_df[~filtered_df['Region'].isin(['Other', 'N/A'])]
            region_top = valid_regions['Region'].mode()
            region_principal = region_top[0] if not region_top.empty else "N/A"
            
            aaa_count = len(filtered_df[filtered_df['studio_tier'] == 'AAA'])
            aa_count = len(filtered_df[filtered_df['studio_tier'] == 'AA'])
            indie_count = len(filtered_df[filtered_df['studio_tier'] == 'Indie'])
            
            st.markdown("""
            <style>
            .metric-card {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 10px;
                padding: 15px;
                text-align: center;
                border-left: 4px solid #1f77b4;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .metric-card.aaa { border-left-color: #dc3545; }
            .metric-card.aa { border-left-color: #ffc107; }
            .metric-card.indie { border-left-color: #28a745; }
            .metric-value { font-size: 24px; font-weight: bold; margin: 0; }
            .metric-label { font-size: 13px; color: #aaa; margin: 0; text-transform: uppercase; letter-spacing: 1px; }
            </style>
            """, unsafe_allow_html=True)
            
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1:
                st.markdown(f'<div class="metric-card"><p class="metric-value">{total_estudios}</p><p class="metric-label">🗺️ Total</p></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="metric-card"><p class="metric-value">{total_paises}</p><p class="metric-label">🌍 Países</p></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="metric-card"><p class="metric-value" style="font-size:18px; padding-top:4px;">{region_principal}</p><p class="metric-label">📍 Top Región</p></div>', unsafe_allow_html=True)
            with col4:
                st.markdown(f'<div class="metric-card aaa"><p class="metric-value" style="color:#dc3545;">{aaa_count}</p><p class="metric-label">🏢 AAA</p></div>', unsafe_allow_html=True)
            with col5:
                st.markdown(f'<div class="metric-card aa"><p class="metric-value" style="color:#ffc107;">{aa_count}</p><p class="metric-label">🎯 AA</p></div>', unsafe_allow_html=True)
            with col6:
                st.markdown(f'<div class="metric-card indie"><p class="metric-value" style="color:#28a745;">{indie_count}</p><p class="metric-label">🎮 Indie</p></div>', unsafe_allow_html=True)
            
            st.divider()
            
            folium_map = create_interactive_map(filtered_df)
            st_folium(
                folium_map, 
                use_container_width=True, 
                height=650,               
                returned_objects=[]       
            )
            
            st.divider()
            
            col_left, col_right = st.columns(2)
            
            with col_left:
                tier_data = filtered_df['studio_tier'].value_counts().reset_index()
                tier_data.columns = ['Tier', 'Count']
                
                color_map = {
                    'AAA': '#dc3545', 
                    'AA': '#ffc107', 
                    'Indie': '#28a745',
                    'No Clasificado': '#6c757d'
                }
                
                fig = px.treemap(
                    tier_data, 
                    path=['Tier'], 
                    values='Count',
                    color='Tier',
                    color_discrete_map=color_map,
                    title="Distribución de Tiers de Estudios"
                )
                fig.update_traces(textinfo="label+value+percent entry")
                fig.update_layout(
                    margin=dict(t=40, b=10, l=10, r=10),
                    height=350,
                    template="plotly_dark"
                )
                st.plotly_chart(fig, width="stretch")
                
            with col_right:
                region_data = filtered_df['Region'].value_counts().reset_index()
                region_data.columns = ['Region', 'Count']
                
                region_color_map = {
                    'North America': '#800080',
                    'South America': '#28a745',
                    'Europe': '#007bff',
                    'Asia': '#dc3545',
                    'Africa': '#fd7e14',
                    'Oceania': '#5f9ea0',
                    'Other': '#6c757d',
                    'N/A': '#444444'
                }
                
                fig_region = px.pie(
                    region_data,
                    names='Region',
                    values='Count',
                    hole=0.6,
                    color='Region',
                    color_discrete_map=region_color_map,
                    title="Estudios por Región Geográfica"
                )
                
                fig_region.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    hovertemplate="<b>%{label}</b><br>Estudios: %{value}<br>Porcentaje: %{percent}<extra></extra>",
                    marker=dict(line=dict(color='#0E1117', width=2))
                )
                
                total_region_estudios = region_data['Count'].sum()
                fig_region.add_annotation(
                    text=f"<span style='font-family: system-ui, Arial, sans-serif; font-size:26px; font-weight:bold; color:white;'>{total_region_estudios}</span><br><span style='font-family: system-ui, Arial, sans-serif; font-size:11px; color:#aaa; font-weight:500; letter-spacing: 0.5px;'>ESTUDIOS</span>",
                    x=0.5, y=0.5,
                    showarrow=False,
                    align="center"
                )
                
                fig_region.update_layout(
                    margin=dict(t=40, b=10, l=10, r=10),
                    height=350,
                    template="plotly_dark",
                    showlegend=False
                )
                st.plotly_chart(fig_region, width="stretch")
                
        else:
            st.info("No se encontraron estudios con los filtros actuales.")
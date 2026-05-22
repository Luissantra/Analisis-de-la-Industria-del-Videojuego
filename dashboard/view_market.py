import streamlit as st
import pandas as pd
import json
from charts_market import create_comparison_line_chart, create_candlestick_chart, BRAND_COLORS
from model_corporate import get_dynamic_market_events


def prepare_time_filtered_data(df, timeframe):
    """
    Filtra por tiempo, ajusta la granularidad dinámicamente (OHLCV) y recalcula rendimiento.
    """
    df_filtered = df.copy()
    
    # Limpieza de duplicados avanzada:
    # Priorizamos registros donde Daily_Return_% NO sea cero si hay duplicados para la misma fecha.
    df_filtered['is_zero'] = (df_filtered['Daily_Return_%'] == 0).astype(int)
    df_filtered = df_filtered.sort_values(by=['Date', 'is_zero'])
    df_filtered = df_filtered.drop_duplicates(subset=['Company Name', 'Date'], keep='first')
    df_filtered = df_filtered.drop(columns=['is_zero'])
    
    max_date = df_filtered['Date'].max()
    
    # 1. Filtro Temporal y Frecuencia de Agrupación
    freq = None # Por defecto (1M, 6M, 1Y) usamos datos diarios, no agrupamos.

    if timeframe == "1M":
        cutoff = max_date - pd.DateOffset(months=1)
    elif timeframe == "6M":
        cutoff = max_date - pd.DateOffset(months=6)
    elif timeframe == "1Y":
        cutoff = max_date - pd.DateOffset(years=1)
    elif timeframe == "5Y":
        cutoff = max_date - pd.DateOffset(years=5)
        freq = 'W-FRI' # Agrupación Semanal (Viernes)
    else: # "Max"
        cutoff = df_filtered['Date'].min()
        freq = 'BM' # Agrupación Mensual (Último día hábil/Business Month del mes)
        
    df_filtered = df_filtered[df_filtered['Date'] >= cutoff]
    
    # 2. Resampling Dinámico Financiero Avanzado (OHLCV)
    if freq:
        df_filtered = df_filtered.groupby(
            ['Company Name', pd.Grouper(key='Date', freq=freq)]
        ).agg({
            'Open': 'first',       # Apertura del periodo
            'High': 'max',         # Máximo del periodo
            'Low': 'min',          # Mínimo del periodo
            'Close': 'last',       # Cierre del periodo
            'Volume': 'sum',       # Volumen total del periodo
            'Daily_Return_%': 'last'
        }).reset_index()

    # 3. Recálculo Dinámico del Rendimiento (Base 0%)
    def calculate_period_return(series):
        if series.dropna().empty:
            return series
        primer_precio_periodo = series.dropna().iloc[0]
        return ((series / primer_precio_periodo) - 1) * 100

    df_filtered = df_filtered.sort_values(by=['Company Name', 'Date'])
    df_filtered['Period_Return_%'] = df_filtered.groupby('Company Name')['Close'].transform(calculate_period_return)
    
    return df_filtered

def render_metrics_cards(df, selected_companies):
    if df.empty or not selected_companies: return
    st.markdown("### Resumen de Mercado (Último Cierre)")
    
    # Usamos columnas dinámicas
    cols = st.columns(len(selected_companies))
    
    for i, company in enumerate(selected_companies):
        comp_data = df[df['Company Name'] == company].sort_values('Date')
        if not comp_data.empty:
            latest = comp_data.iloc[-1]
            precio_actual = latest['Close']
            var_diaria = latest['Daily_Return_%']
            var_periodo = latest['Period_Return_%'] 
            
            with cols[i]:
                # 1. Métrica principal limpia (Streamlit detectará el +/- automáticamente)
                st.metric(
                    label=f"🏢 {company}",
                    value=f"${precio_actual:.2f}",
                    delta=f"{var_periodo:+.2f}% (Rendimiento del periodo)"
                )
                
                # 2. Dato diario sutil debajo
                color_diario = "#26A69A" if var_diaria >= 0 else "#EF5350" # Verde y Rojo modernos
                flecha = "▲" if var_diaria >= 0 else "▼"
                st.markdown(
                    f"<span style='color:{color_diario}; font-size:14px;'><b>{flecha} {abs(var_diaria):.2f}%</b> en el último día de cotización</span>",
                      unsafe_allow_html=True)


def _get_event_icon(event_text):
    """Devuelve un emoji apropiado según el tipo de evento."""
    text_lower = event_text.lower()
    if "adquisición" in text_lower or "compra" in text_lower:
        return "🤝"
    elif "lanzamiento" in text_lower and ("switch" in text_lower or "xbox" in text_lower or "ps" in text_lower):
        return "🎮"
    elif "hit lanzado" in text_lower or "lanzamiento" in text_lower:
        return "🚀"
    elif "fusión" in text_lower:
        return "🔗"
    elif "inversión" in text_lower:
        return "💰"
    elif "anuncio" in text_lower:
        return "📢"
    elif "eliminación" in text_lower or "venta" in text_lower:
        return "📉"
    elif "división" in text_lower:
        return "✂️"
    else:
        return "📌"


def _get_event_type_label(event_text):
    """Devuelve una etiqueta de categoría corta para el evento."""
    text_lower = event_text.lower()
    if "adquisición" in text_lower or "compra" in text_lower:
        return "Adquisición"
    elif "hit lanzado" in text_lower:
        return "Hit"
    elif "lanzamiento" in text_lower:
        return "Lanzamiento"
    elif "fusión" in text_lower:
        return "Fusión"
    elif "inversión" in text_lower:
        return "Inversión"
    elif "anuncio" in text_lower:
        return "Anuncio"
    elif "venta" in text_lower:
        return "Venta"
    elif "división" in text_lower:
        return "Reestructuración"
    else:
        return "Evento"


def render_visual_timeline(events, selected_companies, benchmark="Ninguno"):
    """
    Renderiza una cronología de eventos con un diseño visual moderno:
    tarjetas agrupadas por año, badges de color de marca, iconos por tipo de evento
    y agrupación inteligente de adquisiciones múltiples.
    """
    # Filtrar y preparar eventos relevantes
    relevant_events = []
    for event in events:
        if event["company"] in selected_companies or event["company"] == benchmark:
            event_date = pd.to_datetime(event["date"], errors='coerce')
            if pd.notna(event_date):
                relevant_events.append({
                    **event,
                    "_parsed_date": event_date,
                    "_year": event_date.year,
                    "_month": event_date.month,
                    "_icon": _get_event_icon(event["event"]),
                    "_type": _get_event_type_label(event["event"]),
                })

    if not relevant_events:
        st.info("No hay eventos relevantes para las empresas seleccionadas en este periodo.")
        return

    # Ordenar cronológicamente
    relevant_events.sort(key=lambda x: x["_parsed_date"])

    # Agrupar adquisiciones del mismo año y empresa para compactar
    grouped_events = []
    acq_buffer = {}  # key: (year, company) -> list of studio names

    for ev in relevant_events:
        is_acquisition = "adquisición" in ev["event"].lower()
        if is_acquisition:
            key = (ev["_year"], ev["company"])
            studio_name = ev["event"].replace("Adquisición: ", "").strip()
            if key not in acq_buffer:
                acq_buffer[key] = {"base_event": ev, "studios": []}
            acq_buffer[key]["studios"].append(studio_name)
        else:
            grouped_events.append(ev)

    # Convertir adquisiciones agrupadas en eventos consolidados
    for (year, company), data in acq_buffer.items():
        studios = data["studios"]
        base = data["base_event"].copy()
        if len(studios) == 1:
            base["event"] = f"Adquisición: {studios[0]}"
        else:
            base["event"] = f"Adquisiciones ({len(studios)} estudios): {', '.join(studios)}"
        base["_icon"] = "🤝"
        base["_type"] = "Adquisición"
        grouped_events.append(base)

    # Re-ordenar después de consolidar
    grouped_events.sort(key=lambda x: x["_parsed_date"])

    # Agrupar por año
    events_by_year = {}
    for ev in grouped_events:
        year = ev["_year"]
        if year not in events_by_year:
            events_by_year[year] = []
        events_by_year[year].append(ev)

    # Inyectar CSS para la timeline visual
    st.markdown("""
    <style>
    .timeline-year-header {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-size: 16px;
        font-weight: 700;
        padding: 6px 18px;
        border-radius: 20px;
        margin: 16px 0 10px 0;
        letter-spacing: 1px;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
    }
    .timeline-card {
        background: rgba(128, 128, 128, 0.06);
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 8px;
        border-left: 4px solid #555;
        transition: all 0.2s ease;
        display: flex;
        align-items: flex-start;
        gap: 12px;
    }
    .timeline-card:hover {
        background: rgba(128, 128, 128, 0.12);
        transform: translateX(4px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
    }
    .timeline-icon {
        font-size: 22px;
        min-width: 32px;
        text-align: center;
        padding-top: 2px;
    }
    .timeline-content {
        flex: 1;
    }
    .timeline-meta {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;
        flex-wrap: wrap;
    }
    .timeline-badge {
        display: inline-block;
        font-size: 11px;
        font-weight: 600;
        padding: 2px 10px;
        border-radius: 12px;
        color: white;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .timeline-type-badge {
        display: inline-block;
        font-size: 10px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 10px;
        background: rgba(128, 128, 128, 0.15);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .timeline-date {
        font-size: 12px;
        color: #888;
        font-weight: 500;
    }
    .timeline-event-text {
        font-size: 14px;
        line-height: 1.4;
        margin: 0;
    }
    .timeline-event-text strong {
        font-weight: 700;
    }
    .timeline-count-badge {
        display: inline-block;
        background: rgba(128, 128, 128, 0.12);
        font-size: 12px;
        padding: 2px 10px;
        border-radius: 10px;
        margin-left: 6px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Renderizar la timeline visual agrupada por año
    for year in sorted(events_by_year.keys()):
        year_events = events_by_year[year]
        count_label = f'<span class="timeline-count-badge">{len(year_events)} evento{"s" if len(year_events) > 1 else ""}</span>'
        st.markdown(f'<div class="timeline-year-header">📅 {year}</div>{count_label}', unsafe_allow_html=True)
        
        for ev in year_events:
            company = ev["company"]
            brand_color = BRAND_COLORS.get(company, "#888888")
            # Asegurarse de que el color sea visible (evitar negro puro como fondo del badge)
            badge_bg = brand_color if brand_color != "#000000" else "#333333"
            
            date_display = ev["_parsed_date"].strftime("%b %Y") if ev["_parsed_date"].month != 1 or ev["_parsed_date"].day != 1 else str(year)
            icon = ev["_icon"]
            event_type = ev["_type"]
            event_text = ev["event"]

            # Separar el prefijo del contenido para mejor lectura
            if ": " in event_text:
                prefix, detail = event_text.split(": ", 1)
                formatted_text = f"<strong>{prefix}:</strong> {detail}"
            else:
                formatted_text = event_text

            card_html = f"""
            <div class="timeline-card" style="border-left-color: {brand_color};">
                <div class="timeline-icon">{icon}</div>
                <div class="timeline-content">
                    <div class="timeline-meta">
                        <span class="timeline-badge" style="background-color: {badge_bg};">{company}</span>
                        <span class="timeline-type-badge">{event_type}</span>
                        <span class="timeline-date">{date_display}</span>
                    </div>
                    <p class="timeline-event-text">{formatted_text}</p>
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)


def render_market_module(df_market, selected_companies, benchmark="Ninguno"):
    if not selected_companies or df_market.empty:
        st.info("Selecciona al menos una empresa para ver el análisis financiero.")
        return

    # 1. Controles de Visualización
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        vista = st.radio("Modo de Análisis:", ["Comparativa", "Velas Japonesas"], horizontal=True)
    with col2:
        metrica_y = st.radio("Métrica:", ["Precio (USD)", "Rendimiento (%)"], horizontal=True)
    with col3:
        # Cambiamos el slider por botones de radio horizontales, el estándar en apps de finanzas
        timeframe = st.radio(
            "Marco Temporal:", 
            options=["1M", "6M", "1Y", "5Y", "Max"], 
            index=3, # El índice 3 corresponde a "5Y" por defecto
            horizontal=True
        )
    # 2. Procesamos los datos con los filtros seleccionados
    df_processed = prepare_time_filtered_data(df_market, timeframe)

    # 3. Mostrar Tarjetas de Métricas con los datos ya procesados
    render_metrics_cards(df_processed, selected_companies)
    st.divider()

    # 4. Mostrar Gráficos
    dynamic_events = get_dynamic_market_events()
    
    if "Comparativa" in vista:
        fig_line = create_comparison_line_chart(df_processed, timeframe, benchmark, dynamic_events, metrica_y)
        st.plotly_chart(fig_line, width="stretch")
        
        # Cronología visual de hitos en expander compacto
        with st.expander("📜 Cronología de Eventos Relevantes", expanded=False):
            all_events = get_dynamic_market_events()
            render_visual_timeline(all_events, selected_companies, benchmark)
                
    else:
        if len(selected_companies) > 1:
            tabs = st.tabs(selected_companies)
            for i, company in enumerate(selected_companies):
                with tabs[i]:
                    fig_candle = create_candlestick_chart(df_processed, company, timeframe, dynamic_events)
                    st.plotly_chart(fig_candle, width="stretch")
        else:
            fig_candle = create_candlestick_chart(df_processed, selected_companies[0], timeframe, dynamic_events)
            st.plotly_chart(fig_candle, width="stretch")

    with st.expander("Ver tabla de datos puros del período"):
        st.dataframe(df_processed.sort_values(by=['Date', 'Company Name'], ascending=[False, True]), width="stretch", hide_index=True)
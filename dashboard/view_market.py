import streamlit as st
import pandas as pd
from charts_market import create_comparison_line_chart, create_candlestick_chart
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

def render_market_module(df_market, selected_companies, benchmark="Ninguno"):
    if not selected_companies or df_market.empty:
        st.info("Selecciona al menos una empresa para ver el análisis financiero.")
        return

    # 1. Controles de Visualización
    col1, col2 = st.columns([1, 1])
    with col1:
        vista = st.radio("Modo de Análisis:", ["Comparativa", "Velas Japonesas"], horizontal=True)
    with col2:
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
        fig_line = create_comparison_line_chart(df_processed, timeframe, benchmark, dynamic_events)
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        if len(selected_companies) > 1:
            tabs = st.tabs(selected_companies)
            for i, company in enumerate(selected_companies):
                with tabs[i]:
                    fig_candle = create_candlestick_chart(df_processed, company, timeframe, dynamic_events)
                    st.plotly_chart(fig_candle, use_container_width=True)
        else:
            fig_candle = create_candlestick_chart(df_processed, selected_companies[0], timeframe, dynamic_events)
            st.plotly_chart(fig_candle, use_container_width=True)

    with st.expander("Ver tabla de datos puros del período"):
        st.dataframe(df_processed.sort_values(by=['Date', 'Company Name'], ascending=[False, True]), use_container_width=True, hide_index=True)
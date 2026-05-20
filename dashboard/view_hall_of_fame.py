import streamlit as st
import json
import os
import urllib.request
import urllib.parse
from pathlib import Path

# Configuración del caché de carátulas
COVERS_CACHE_PATH = Path("data/processed/game_covers.json")

def get_game_cover_url(rawg_id, title):
    """
    Obtiene la carátula oficial de un juego desde la API de RAWG.
    Utiliza un caché en formato JSON local para evitar llamadas redundantes a la API.
    """
    if not rawg_id:
        return None
    rawg_id_str = str(rawg_id)
    
    # 1. Intentar cargar el caché local
    cache = {}
    if COVERS_CACHE_PATH.exists():
        try:
            with open(COVERS_CACHE_PATH, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            pass
            
    if rawg_id_str in cache and cache[rawg_id_str]:
        return cache[rawg_id_str]
        
    # 2. Si no está en caché, hacer petición a la API
    import config
    api_key = config.RAWG_API_KEY
    if not api_key:
        # Fallback a una imagen de marcador de posición si no hay API Key
        return "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?q=80&w=600&auto=format&fit=crop"
        
    # Endpoint por ID de RAWG
    try:
        url = f"https://api.rawg.io/api/games/{rawg_id}?key={api_key}"
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            cover_url = data.get("background_image")
            if cover_url:
                cache[rawg_id_str] = cover_url
                # Guardar caché
                os.makedirs(os.path.dirname(COVERS_CACHE_PATH), exist_ok=True)
                with open(COVERS_CACHE_PATH, "w", encoding="utf-8") as f:
                    json.dump(cache, f, ensure_ascii=False, indent=2)
                return cover_url
    except Exception:
        pass
        
    # Fallback buscando por título si el ID falló
    try:
        query = urllib.parse.quote(title)
        url = f"https://api.rawg.io/api/games?key={api_key}&search={query}&page_size=1"
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            results = data.get("results", [])
            if results:
                cover_url = results[0].get("background_image")
                if cover_url:
                    cache[rawg_id_str] = cover_url
                    # Guardar caché
                    os.makedirs(os.path.dirname(COVERS_CACHE_PATH), exist_ok=True)
                    with open(COVERS_CACHE_PATH, "w", encoding="utf-8") as f:
                        json.dump(cache, f, ensure_ascii=False, indent=2)
                    return cover_url
    except Exception:
        pass
        
    # Si todo falla, marcador de posición
    return "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?q=80&w=600&auto=format&fit=crop"

def render_hall_of_fame_module():
    st.title("🏆 Salón de la Fama (Juegos del Año - GOTY)")
    st.markdown("""
    Bienvenidos a la exhibición de los títulos consagrados con el galardón máximo de la industria: 
    el **Game of the Year (GOTY)** otorgado en **The Game Awards** desde 2014 hasta la actualidad.
    """)
    
    # CSS inyectado para los efectos hover y transición interactiva premium
    st.markdown("""
    <style>
    .netflix-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 24px;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        position: relative;
        overflow: hidden;
    }
    .netflix-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 12px 25px rgba(230, 0, 18, 0.3) !important;
        border-color: rgba(230, 0, 18, 0.5) !important;
        background: rgba(255, 255, 255, 0.05);
    }
    .netflix-img-container {
        border-radius: 8px;
        overflow: hidden;
        height: 220px;
        margin-bottom: 12px;
        position: relative;
    }
    .netflix-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.5s ease;
    }
    .netflix-card:hover .netflix-img {
        transform: scale(1.08);
    }
    .goty-badge {
        position: absolute;
        top: 10px;
        left: 10px;
        background: linear-gradient(135deg, #e60012, #ff4545);
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 11px;
        box-shadow: 0 0 10px rgba(230,0,18,0.6);
        z-index: 2;
    }
    .score-badge {
        position: absolute;
        top: 10px;
        right: 10px;
        background: rgba(0, 0, 0, 0.75);
        border: 1px solid #4caf50;
        color: #4caf50;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 11px;
        z-index: 2;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Cargar los ganadores del GOTY
    goty_path = Path("config_data/goty_winners.json")
    if not goty_path.exists():
        st.error("Error: No se encontró la configuración de ganadores de GOTY en config_data/goty_winners.json")
        return
        
    try:
        with open(goty_path, "r", encoding="utf-8") as f:
            goty_winners = json.load(f)
    except Exception as e:
        st.error(f"Error leyendo goty_winners.json: {e}")
        return
        
    # Renderizar el Grid estilo Netflix (3 columnas)
    cols = st.columns(3)
    
    for idx, goty in enumerate(goty_winners):
        with cols[idx % 3]:
            # Obtener datos del juego
            title = goty.get("title")
            year = goty.get("year")
            rawg_id = goty.get("rawg_id")
            developer = goty.get("developer")
            publisher = goty.get("publisher")
            metacritic = goty.get("metacritic") or "N/A"
            genre = goty.get("genre")
            description = goty.get("description")
            
            # Obtener carátula
            cover_url = get_game_cover_url(rawg_id, title)
            
            # Renderizar HTML Premium
            card_html = f"""
            <div class="netflix-card">
                <div class="netflix-img-container">
                    <div class="goty-badge">🏆 GOTY {year}</div>
                    <div class="score-badge">⭐ {metacritic}</div>
                    <img class="netflix-img" src="{cover_url}" alt="{title}">
                </div>
                <h4 style="margin: 0 0 6px 0; font-size: 18px; color: #fff; font-weight: 700; font-family: 'Outfit', 'Inter', sans-serif;">{title}</h4>
                <div style="font-size: 12px; color: #b3b3b3; margin-bottom: 8px; display: flex; gap: 8px; flex-wrap: wrap; font-family: 'Inter', sans-serif;">
                    <span>🏢 {developer}</span>
                    <span>•</span>
                    <span>🎮 {genre}</span>
                </div>
                <p style="font-size: 13px; color: #e0e0e0; line-height: 1.5; margin: 0; min-height: 70px; font-family: 'Inter', sans-serif;">
                    {description}
                </p>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

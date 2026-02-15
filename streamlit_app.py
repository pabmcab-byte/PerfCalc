import streamlit as st
import pandas as pd
import requests
import math
import numpy as np

# 1. CONFIGURACIÓN Y ESTILOS
st.set_page_config(page_title="PerfCalc A320 Ultra", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=B612:wght@400;700&family=B612+Mono:wght@400;700&display=swap');
    .stApp { background-color: #1a1a1a; font-family: 'B612', sans-serif; color: white; }
    [data-testid="stColumn"], [data-testid="stVerticalBlock"], .stElementContainer {
        border: none !important; background-color: transparent !important; box-shadow: none !important;
    }
    .mcdu-label { color: #FFFFFF; font-size: 12px; height: 20px; text-transform: uppercase; margin-bottom: 8px; }
    .mcdu-v-speed { color: #FFBF00; font-size: 26px; font-weight: 700; font-family: 'B612 Mono', monospace; line-height: 1.2; margin-bottom: 15px; }
    .mcdu-info-blue { color: #00FFFF; font-size: 22px; font-weight: 700; font-family: 'B612 Mono', monospace; line-height: 1.2; margin-bottom: 15px; }
    .mcdu-retrac-white { color: #FFFFFF; font-size: 20px; font-weight: 700; font-family: 'B612 Mono', monospace; text-align: center; }
    .mcdu-value-green { color: #00FF00; }
    .mcdu-title-white { color: #FFFFFF; font-size: 24px; font-weight: 700; text-align: center; margin-bottom: 35px; }
    .info-box { color: #FFBF00; background-color: #000; padding: 10px; font-family: 'B612 Mono', monospace; font-size: 12px; border: 1px solid #333; margin-bottom: 10px; }
    
    .rwy-container { position: relative; width: 100%; height: 200px; margin-top: 60px; }
    .rwy-asphalt { background-color: #333; height: 60px; width: 100%; position: relative; border: 2px solid #555; }
    .rwy-centerline { position: absolute; top: 50%; left: 30px; right: 30px; border-top: 2px dashed rgba(255,255,255,0.4); transform: translateY(-50%); }
    .rwy-number-start { position: absolute; color: rgba(255,255,255,0.7); font-size: 13px; font-weight: 700; top: 50%; left: 8px; transform: translateY(-50%) rotate(90deg); font-family: 'B612 Mono', monospace; }
    .rwy-number-end { position: absolute; color: rgba(255,255,255,0.7); font-size: 13px; font-weight: 700; top: 50%; right: 8px; transform: translateY(-50%) rotate(-90deg); font-family: 'B612 Mono', monospace; }
    .v-marker { position: absolute; border-left: 2px solid #00FFFF; transform: translateX(-50%); }
    .v-tag { color: #00FFFF; font-weight: 700; font-size: 13px; text-align: center; position: absolute; transform: translateX(-50%); width: 60px; }
    .dist-tag { color: #00FFFF; font-size: 11px; position: absolute; left: 50%; transform: translateX(-50%); white-space: nowrap; font-family: 'B612 Mono', monospace; }
    </style>
    """, unsafe_allow_html=True)

# 2. CARGA DE DATOS
@st.cache_data
def load_data():
    return pd.read_csv("https://davidmegginson.github.io/ourairports-data/runways.csv").dropna(subset=['le_ident'])

def get_metar(icao):
    api_key = "683b049120444e818ffbaee29430ff2b" 
    url = f"https://api.checkwx.com/metar/{icao}/decoded"
    headers = {"X-API-Key": api_key}
    try:
        r = requests.get(url, headers=headers, timeout=5).json()
        return r['data'][0] if 'data' in r and r['data'] else None
    except: return None

# 3. INTERFAZ
input_col, output_col = st.columns([1, 1.2], gap="large")

with input_col:
    st.subheader("Aircraft Settings")
    weight_kg = st.number_input("TOW (Kg)", 40000, 80000, 68000, step=100)
    cg_pct = st.number_input("CG %", 10.0, 45.0, 33.1)
    to_shift_m = st.number_input("TO SHIFT (m)", 0, 1000, 0, step=10)
    
    c1, c2 = st.columns(2)
    fl_sel = c1.selectbox("FLAPS", ["1+F", "2", "3"])
    rwy_cond = c2.selectbox("RWY COND", ["DRY", "WET"])
    
    c3, c4 = st.columns(2)
    packs = c3.radio("PACKS", ["OFF", "ON"], horizontal=True)
    anti_ice = c4.radio("ANTI-ICE", ["OFF", "ON"], horizontal=True)

    st.divider()
    st.subheader("Airport")
    icao = st.text_input("ICAO", "LEZL").upper()
    metar = get_metar(icao)
    oat, qnh, hw, elev_p, slope, l_m = 15.0, 1013, 0, 0, 0.0, 2500
    pista_sel, rwy_recip = "---", ""

    if metar:
        st.markdown(f'<div class="info-box">{metar.get("raw_text")}</div>', unsafe_allow_html=True)
        oat = float(metar.get('temperature', {}).get('celsius', 15))
        qnh = int(metar.get('barometer', {}).get('hpa', 1013))
        w_dir, w_spd = metar.get('wind', {}).get('degrees', 0), metar.get('wind', {}).get('speed_kts', 0)
        
        db = load_data()
        ae = db[db['airport_ident'] == icao]
        if not ae.empty:
            p_list = pd.concat([ae[['le_ident','length_ft','le_elevation_ft','he_elevation_ft']].rename(columns={'le_ident':'p', 'le_elevation_ft':'e_s', 'he_elevation_ft':'e_e'}), 
                                ae[['he_ident','length_ft','he_elevation_ft','le_elevation_ft']].rename(columns={'he_ident':'p', 'he_elevation_ft':'e_s', 'le_elevation_ft':'e_e'})]).drop_duplicates()
            pista_sel = st.selectbox("RUNWAY", p_list['p'].tolist())
            row = p_list[p_list['p'] == pista_sel].iloc[0]
            l_m, elev_p = int(row['length_ft'] * 0.3048), int(row['e_s'])
            slope = ((row['e_e'] - row['e_s']) / row['length_ft']) * 100
            hw = int(w_spd * math.cos(math.radians(w_dir - (int('0'+''.join(filter(str.isdigit, pista_sel)))*10))))
            r_num = int('0'+''.join(filter(str.isdigit, pista_sel)))
            rwy_recip = str(((r_num + 18) % 36) if (r_num + 18) % 36 != 0 else 36).zfill(2)
            st.markdown(f'<div class="info-box">LEN: {l_m}m | ELEV: {elev_p}ft | SLOPE: {slope:.1f}% | HW: {hw}kt</div>', unsafe_allow_html=True)

# 4. FÍSICA Y TRIM
weight_t = weight_kg / 1000
dens_alt = elev_p + (120 * (oat - (15 - (0.00198 * elev_p)))) + (27 * (1013 - qnh))

v1 = int(np.interp(weight_kg, [45000, 80000], [110, 155]) - (to_shift_m * 0.015) + (dens_alt / 1500))
v1 -= (8 if rwy_cond == "WET" else 0)
if hw < 0: v1 -= int(abs(hw) * 0.6)
vr = int(np.interp(weight_kg, [45000, 80000], [115, 160]) + (dens_alt / 2000))
v2 = vr + 5

flex = int(259 - (weight_t * 3.45) - (slope * 3.8) - (dens_alt / 850) - (to_shift_m * 0.02))
if packs == "ON": flex -= 3
if anti_ice == "ON": flex -= 5
flex_final = min(max(flex, int(oat)), 65)

ths_val = (cg_pct - 25) / 7.5
ths_str = ("DN" if ths_val > 0 else "UP" if ths_val < 0 else "") + f"{abs(ths_val):.1f}"
green_dot = int((2 * weight_t) + 85)

# 5. SALIDA MCDU
with output_col:
    st.markdown(f'<div class="mcdu-title-white">TAKEOFF RWY <span class="mcdu-value-green">{pista_sel}</span></div>', unsafe_allow_html=True)
    
    # FILA 1: V1 | F Speed
    c1, c2, c3 = st.columns([1, 1, 1])
    c1.markdown(f'<p class="mcdu-label">V1</p><p class="mcdu-v-speed">{v1}</p>', unsafe_allow_html=True)
    c2.markdown(f'<p class="mcdu-label" style="text-align:center;">FLP RETR</p><p class="mcdu-retrac-white">F=<span class="mcdu-value-green">{v1+20}</span></p>', unsafe_allow_html=True)

    # FILA 2: VR | S Speed | TO SHIFT (M en blanco)
    c1, c2, c3 = st.columns([1, 1, 1])
    c1.markdown(f'<p class="mcdu-label">VR</p><p class="mcdu-v-speed">{vr}</p>', unsafe_allow_html=True)
    c2.markdown(f'<p class="mcdu-label" style="text-align:center;">SLT RETR</p><p class="mcdu-retrac-white">S=<span class="mcdu-value-green">{v1+40}</span></p>', unsafe_allow_html=True)
    shift_m = "<span style='color:white;'>[M]</span>"
    shift_val = f"<span style='color:#00FFFF;'>[{to_shift_m}]*</span>" if to_shift_m > 0 else "<span style='color:#00FFFF;'>[ ]*</span>"
    c3.markdown(f'<p class="mcdu-label" style="text-align:right;">TO SHIFT</p><p class="mcdu-info-blue" style="text-align:right;">{shift_m}{shift_val}</p>', unsafe_allow_html=True)

    # FILA 3: V2 | O Speed | FLAPS-THS
    c1, c2, c3 = st.columns([1, 1, 1])
    c1.markdown(f'<p class="mcdu-label">V2</p><p class="mcdu-v-speed">{v2}</p>', unsafe_allow_html=True)
    c2.markdown(f'<p class="mcdu-label" style="text-align:center;">CLEAN</p><p class="mcdu-retrac-white">O=<span class="mcdu-value-green">{green_dot}</span></p>', unsafe_allow_html=True)
    c3.markdown(f'<p class="mcdu-label" style="text-align:right;">FLAPS/THS</p><p class="mcdu-info-blue" style="text-align:right;">{fl_sel[0]}/{ths_str}</p>', unsafe_allow_html=True)

    # FILA 4: TRANS ALT | FLEX
    c1, c2, c3 = st.columns([1, 1, 1])
    t_alt = 13000 if icao=="LEMD" else 7000 if icao=="LEGR" else 6000 if icao.startswith("LE") else 5000
    c1.markdown(f'<p class="mcdu-label">TRANS ALT</p><p class="mcdu-info-blue">{t_alt}</p>', unsafe_allow_html=True)
    c3.markdown(f'<p class="mcdu-label" style="text-align:right;">FLEX TO TEMP</p><p class="mcdu-info-blue" style="text-align:right;">{flex_final}º</p>', unsafe_allow_html=True)

    # FILA 5: THR RED/ACC | ENG OUT ACC
    c1, c2, c3 = st.columns([1, 1, 1])
    c1.markdown(f'<p class="mcdu-label">THR RED/ACC</p><p class="mcdu-info-blue">{elev_p+1500}/{elev_p+1500}</p>', unsafe_allow_html=True)
    c3.markdown(f'<p class="mcdu-label" style="text-align:right;">ENG OUT ACC</p><p class="mcdu-info-blue" style="text-align:right;">{elev_p+1500}</p>', unsafe_allow_html=True)

    # 6. GRÁFICO
    fric = 1.15 if rwy_cond == "WET" else 1.0
    d_lo = 1600 * (weight_t / 68.0)**2 * (1 + (slope/7.0)) * fric
    v_lo = vr + 5
    sh = (to_shift_m / l_m) * 100
    p1, pr, p2 = sh + ((v1/v_lo)**2.1 * d_lo / l_m * 100), sh + ((vr/v_lo)**2.1 * d_lo / l_m * 100), sh + (d_lo / l_m * 100)
    
    rwy_html = f"""<div class="rwy-container"><div class="rwy-asphalt"><div class="rwy-number-start">{pista_sel}</div><div class="rwy-centerline"></div><div class="rwy-number-end">{rwy_recip}</div>
    <div class="v-marker" style="left:{p1}%;top:-10px;height:70px;"><div class="v-tag" style="top:-20px;">V1</div><div class="dist-tag" style="bottom:-20px;">{int(p1*l_m/100)}m</div></div>
    <div class="v-marker" style="left:{pr}%;top:-45px;height:105px;"><div class="v-tag" style="top:-20px;">VR</div><div class="dist-tag" style="bottom:-35px;">{int(pr*l_m/100)}m</div></div>
    <div class="v-marker" style="left:{p2}%;top:-80px;height:140px;"><div class="v-tag" style="top:-20px;">V2</div><div class="dist-tag" style="bottom:-50px;">{int(p2*l_m/100)}m</div></div>
    </div></div>"""
    st.markdown(rwy_html, unsafe_allow_html=True)

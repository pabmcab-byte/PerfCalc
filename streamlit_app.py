import streamlit as st
import pandas as pd
import requests
import math
import numpy as np

# 1. ESTILOS Y CONFIGURACIÓN
st.set_page_config(page_title="PerfCalc A320 Pro", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=B612:wght@400;700&family=B612+Mono:wght@400;700&display=swap');
    .stApp { background-color: #1a1a1a; font-family: 'B612', sans-serif; color: white; }
    
    [data-testid="stColumn"], [data-testid="stVerticalBlock"], .stElementContainer {
        border: none !important; background-color: transparent !important; box-shadow: none !important;
    }

    .mcdu-label { color: #FFFFFF; font-size: 13px; height: 15px; margin-bottom: 2px; text-transform: uppercase; }
    .mcdu-v-speed { color: #FFBF00; font-size: 26px; font-weight: 700; margin-bottom: 15px; font-family: 'B612 Mono', monospace; }
    .mcdu-info-blue { color: #00FFFF; font-size: 22px; font-weight: 700; margin-bottom: 15px; font-family: 'B612 Mono', monospace; }
    .mcdu-title-white { color: #FFFFFF; font-size: 24px; font-weight: 700; text-align: center; margin-bottom: 30px; }
    .mcdu-value-green { color: #00FF00; font-weight: 700; }
    .info-box { color: #FFBF00; background-color: #000; padding: 10px; font-family: 'B612 Mono', monospace; font-size: 13px; border-radius: 5px; border: 1px solid #333; margin-bottom: 10px; }
    
    /* GRÁFICO DE PISTA AZUL */
    .rwy-container { position: relative; width: 100%; height: 240px; margin-top: 80px; }
    .rwy-asphalt { background-color: #333; height: 60px; width: 100%; position: relative; border: 2px solid #555; }
    .rwy-centerline { position: absolute; top: 50%; left: 35px; right: 35px; border-top: 2px dashed rgba(255,255,255,0.4); transform: translateY(-50%); }
    .rwy-number-start { position: absolute; color: rgba(255,255,255,0.7); font-size: 14px; font-weight: 700; top: 50%; left: 10px; transform: translateY(-50%) rotate(90deg); font-family: 'B612 Mono', monospace; }
    .rwy-number-end { position: absolute; color: rgba(255,255,255,0.7); font-size: 14px; font-weight: 700; top: 50%; right: 10px; transform: translateY(-50%) rotate(-90deg); font-family: 'B612 Mono', monospace; }
    
    .v-marker { position: absolute; border-left: 2px solid #00FFFF; transform: translateX(-50%); }
    .v-tag { color: #00FFFF; font-weight: 700; font-size: 13px; text-align: center; position: absolute; transform: translateX(-50%); width: 60px; }
    .dist-tag { color: #00FFFF; font-size: 11px; position: absolute; left: 50%; transform: translateX(-50%); white-space: nowrap; font-family: 'B612 Mono', monospace; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<h1 style="text-align: center; color: white; margin-bottom: 40px;">PerfCalc</h1>', unsafe_allow_html=True)

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

def get_trans_alt(icao):
    if icao == "LEMD": return 13000
    if icao == "LEGR": return 7000
    if icao.startswith('K'): return 18000
    if icao.startswith('LE'): return 6000
    return 5000

runways_db = load_data()

# 3. LAYOUT
input_col, output_col = st.columns([1, 1.2], gap="large")

with input_col:
    st.subheader("Aircraft Configuration")
    # Cambio a Kilogramos
    weight_kg = st.number_input("TOW (Kg)", 40000, 80000, 68000, step=100)
    weight_t = weight_kg / 1000
    cg_pct = st.number_input("CG %", 10.0, 45.0, 33.1)
    to_shift_m = st.number_input("TO SHIFT (meters)", 0, 1000, 0, step=10)
    
    c_fl, c_pk, c_ai = st.columns(3)
    fl_sel = c_fl.selectbox("FLAPS", ["1+F", "2", "3"])
    fl_val = "1" if fl_sel == "1+F" else fl_sel
    packs = c_pk.radio("PACKS", ["OFF", "ON"], horizontal=True)
    anti_ice = c_ai.radio("ANTI-ICE", ["OFF", "ON"], horizontal=True)

    st.divider()
    st.subheader("Airport & Weather")
    icao = st.text_input("AIRPORT ICAO", "LEZL").upper()
    metar_data = get_metar(icao)
    oat, w_dir, w_spd = 15.0, 0, 0
    if metar_data:
        st.markdown(f'<div class="info-box">{metar_data.get("raw_text")}</div>', unsafe_allow_html=True)
        oat, w_dir, w_spd = float(metar_data.get('temperature', {}).get('celsius', 15)), metar_data.get('wind', {}).get('degrees', 0), metar_data.get('wind', {}).get('speed_kts', 0)

    pistas_ae = runways_db[runways_db['airport_ident'] == icao]
    pista_sel, l_m, elev_p, hw, rwy_recip = "---", 2500, 0, 0, ""
    if not pistas_ae.empty:
        p_list = pd.concat([pistas_ae[['le_ident','length_ft','le_elevation_ft']].rename(columns={'le_ident':'p', 'le_elevation_ft':'e_s'}), 
                            pistas_ae[['he_ident','length_ft','he_elevation_ft']].rename(columns={'he_ident':'p', 'he_elevation_ft':'e_s'})]).drop_duplicates()
        pista_sel = st.selectbox("RUNWAY", p_list['p'].tolist())
        row_p = p_list[p_list['p'] == pista_sel].iloc[0]
        l_m, elev_p = int(row_p['length_ft'] * 0.3048), int(row_p['e_s'])
        r_num = int('0'+''.join(filter(str.isdigit, pista_sel)))
        rwy_recip = str(((r_num + 18) % 36) if (r_num + 18) % 36 != 0 else 36).zfill(2)
        hw = int(w_spd * math.cos(math.radians(w_dir - (r_num*10))))
        st.markdown(f'<div class="info-box">LEN: {l_m}m | ELEV: {elev_p}ft | WIND COMP: {hw}kt</div>', unsafe_allow_html=True)

# 4. CÁLCULO
weight_lbs = weight_kg * 2.20462
v1 = int(np.interp(weight_lbs, [100000, 190000], [105, 156]))
if hw < 0: v1 -= int(abs(hw) * 0.5)
vr, v2 = v1 + 3, v1 + 7
f_spd, s_spd = int(np.interp(weight_lbs, [130000, 170000], [142, 163])), int(np.interp(weight_lbs, [130000, 170000], [186, 213]))

# Green Dot / Clean Speed (O)
green_dot = int((2 * weight_t) + 85)

flex = int(259 - (3.333 * weight_t))
if packs == "ON": flex -= 3
if anti_ice == "ON": flex -= 5
flex_final = max(flex, int(oat))

# 5. SALIDA MCDU
with output_col:
    st.markdown(f'<div class="mcdu-title-white">TAKEOFF RWY <span class="mcdu-value-green">{pista_sel}</span></div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    with m1:
        for lbl, val in [("V1", v1), ("VR", vr), ("V2", v2)]: st.markdown(f'<p class="mcdu-label">{lbl}</p><p class="mcdu-v-speed">{val}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="mcdu-label">TRANS ALT</p><p class="mcdu-info-blue">{get_trans_alt(icao)}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="mcdu-label">THR RED/ACC</p><p class="mcdu-info-blue">{elev_p+1500}/{elev_p+1500}</p>', unsafe_allow_html=True)
    with m2:
        for lbl, v in [("FLP RETR", f"F={f_spd}"), ("SLT RETR", f"S={s_spd}"), ("CLEAN", f"O={green_dot}")]:
            st.markdown(f'<p class="mcdu-label" style="text-align:center;">{lbl}</p><p class="mcdu-info-blue" style="text-align:center;">{v[:2]}<span class="mcdu-value-green">{v[2:]}</span></p>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div style="height:58px;"></div><p class="mcdu-label" style="text-align:right;">TO SHIFT</p><p class="mcdu-info-blue" style="text-align:right;">[M][{to_shift_m if to_shift_m>0 else ""}]*</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="mcdu-label" style="text-align:right;">FLAPS/THS</p><p class="mcdu-info-blue" style="text-align:right;">{fl_val}/{(cg_pct-25)/7.5:+.1f}</p><p class="mcdu-label" style="text-align:right;">FLEX TO TEMP</p><p class="mcdu-info-blue" style="text-align:right;">{flex_final}º</p><p class="mcdu-label" style="text-align:right;">ENG OUT ACC</p><p class="mcdu-info-blue" style="text-align:right;">{elev_p+1500}</p>', unsafe_allow_html=True)

    # 6. GRÁFICO DINÁMICO
    d_lo = 1600 * (weight_t / 68.0)**2
    v_lo = vr + 5
    p1, pr, p2 = ((v1/v_lo)**2 * d_lo / l_m) * 100, ((vr/v_lo)**2 * d_lo / l_m) * 100, (d_lo / l_m) * 100

    rwy_html = f"""
    <div class="rwy-container">
        <div class="rwy-asphalt">
            <div class="rwy-number-start">{pista_sel}</div>
            <div class="rwy-centerline"></div>
            <div class="rwy-number-end">{rwy_recip}</div>
            <div class="v-marker" style="left: {p1}%; top: -10px; height: 70px;">
                <div class="v-tag" style="top: -20px;">V1</div>
                <div class="dist-tag" style="bottom: -20px;">{int(p1*l_m/100)}m</div>
            </div>
            <div class="v-marker" style="left: {pr}%; top: -45px; height: 105px;">
                <div class="v-tag" style="top: -20px;">VR</div>
                <div class="dist-tag" style="bottom: -35px;">{int(pr*l_m/100)}m</div>
            </div>
            <div class="v-marker" style="left: {p2}%; top: -80px; height: 140px;">
                <div class="v-tag" style="top: -20px;">V2</div>
                <div class="dist-tag" style="bottom: -50px;">{int(p2*l_m/100)}m</div>
            </div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 10px; color: #888; margin-top: 15px;">
            <span>START (0m)</span><span>END ({l_m}m)</span>
        </div>
    </div>
    """
    st.markdown(rwy_html, unsafe_allow_html=True)

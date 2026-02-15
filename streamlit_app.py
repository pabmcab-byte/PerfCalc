import streamlit as st
import pandas as pd
import requests
import math
import numpy as np

# 1. CONFIGURACIÓN Y ESTILOS
st.set_page_config(page_title="PerfCalc Ultra Pro v16.4", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=B612:wght@400;700&family=B612+Mono:wght@400;700&display=swap');
    .stApp { background-color: #1a1a1a; font-family: 'B612', sans-serif; color: white; }
    [data-testid="stColumn"], [data-testid="stVerticalBlock"], .stElementContainer { border: none !important; background-color: transparent !important; }
    .app-title { color: #FFFFFF; font-size: 42px; font-weight: 700; text-align: center; margin-bottom: 25px; }

    /* BOTONES DE FASE */
    .stButton > button {
        width: 140px !important; border-radius: 4px; height: 42px; font-weight: 700;
        background-color: #262626; color: #888; border: 1px solid #444; transition: 0.2s;
    }
    .stButton > button:hover { border-color: #00FFFF !important; color: #00FFFF !important; }

    /* MCDU ESTÉTICA COMPACTA */
    .mcdu-row { margin-bottom: 4px; } 
    .mcdu-label { color: #FFFFFF; font-size: 11px; text-transform: uppercase; margin-bottom: 1px; font-family: 'B612', sans-serif; }
    .mcdu-v-speed { color: #FFBF00; font-size: 28px; font-weight: 700; font-family: 'B612 Mono', monospace; line-height: 1; }
    .mcdu-info-blue { color: #00FFFF; font-size: 24px; font-weight: 700; font-family: 'B612 Mono', monospace; line-height: 1; }
    .mcdu-value-green { color: #00FF00 !important; font-weight: 700; }
    .mcdu-retrac-white { color: #FFFFFF; font-size: 22px; font-weight: 700; font-family: 'B612 Mono', monospace; }
    .mcdu-title-white { color: #FFFFFF; font-size: 24px; font-weight: 700; text-align: center; margin-bottom: 30px; }
    
    .info-box { color: #FFBF00; background-color: #000; padding: 10px; font-family: 'B612 Mono', monospace; font-size: 12px; border: 1px solid #333; margin-bottom: 15px; }

    /* GRÁFICO DINÁMICO */
    .rwy-container { position: relative; width: 100%; height: 280px; margin-top: 60px; }
    .rwy-asphalt { background-color: #222; height: 60px; width: 100%; position: relative; border: 2px solid #555; z-index: 5; box-shadow: inset 0 0 20px #000; }
    .rwy-centerline { position: absolute; top: 50%; left: 60px; right: 60px; border-top: 2px dashed rgba(255,255,255,0.4); transform: translateY(-50%); }
    .rwy-number-start { position: absolute; color: rgba(255,255,255,0.7); font-size: 14px; font-weight: 700; top: 50%; left: 15px; transform: translateY(-50%) rotate(90deg); font-family: 'B612 Mono', monospace; }
    .rwy-number-end { position: absolute; color: rgba(255,255,255,0.7); font-size: 14px; font-weight: 700; top: 50%; right: 15px; transform: translateY(-50%) rotate(-90deg); font-family: 'B612 Mono', monospace; }
    
    .v-marker-line { position: absolute; border-left: 2px solid rgba(0, 255, 255, 0.2); width: 0; z-index: 10; transform: translateX(-50%); }
    .v-tag-top { color: #00FFFF; font-weight: 700; font-size: 13px; text-align: center; position: absolute; transform: translateX(-50%); width: 60px; z-index: 15; }
    .v-tag-bottom { color: #00FFFF; font-size: 11px; position: absolute; transform: translateX(-50%); width: 80px; text-align: center; font-family: 'B612 Mono', monospace; z-index: 15; }
    </style>
    """, unsafe_allow_html=True)

# 2. CORE HELPERS
@st.cache_data
def load_db():
    return pd.read_csv("https://davidmegginson.github.io/ourairports-data/runways.csv").dropna(subset=['le_ident'])

def get_metar(icao):
    api_key = "683b049120444e818ffbaee29430ff2b" 
    try:
        r = requests.get(f"https://api.checkwx.com/metar/{icao}/decoded", headers={"X-API-Key": api_key}, timeout=5).json()
        return r['data'][0] if 'data' in r and r['data'] else None
    except: return None

def get_reciprocal(rwy):
    if not rwy or rwy == "---": return "---"
    num = ''.join(filter(str.isdigit, rwy)); let = ''.join(filter(str.isalpha, rwy)).upper()
    opp_num = str(((int(num) + 18 - 1) % 36) + 1).zfill(2)
    mapping = {"L": "R", "R": "L", "C": "C", "": ""}; return f"{opp_num}{mapping.get(let, '')}"

# 3. HEADER & SELECTOR
st.markdown('<div class="app-title">PerfCalc</div>', unsafe_allow_html=True)
if 'phase' not in st.session_state: st.session_state.phase = "TAKEOFF"

nav_c1, nav_c2, _ = st.columns([0.15, 0.15, 0.7])
with nav_c1:
    if st.button("TAKEOFF", key="btn_to"): st.session_state.phase = "TAKEOFF"
with nav_c2:
    if st.button("LANDING", key="btn_ld"): st.session_state.phase = "LANDING"

st.markdown(f"<style>#btn_to {{ {'background-color: #00FFFF; color: black;' if st.session_state.phase == 'TAKEOFF' else ''} }} #btn_ld {{ {'background-color: #00FFFF; color: black;' if st.session_state.phase == 'LANDING' else ''} }}</style>", unsafe_allow_html=True)
mode = st.session_state.phase

# 4. INPUTS (SISTEMAS REINTEGRADOS)
input_col, output_col = st.columns([1, 1.2], gap="large")

with input_col:
    st.subheader(f"{mode} Configuration")
    weight_kg = st.number_input("Weight (Kg)", 40000, 80000, 68000, step=100)
    
    if mode == "TAKEOFF":
        cg_pct = st.number_input("CG %", 10.0, 45.0, 33.1)
        to_shift = st.number_input("TO SHIFT (m)", 0, 1000, 0, step=10)
        c1, c2 = st.columns(2); fl_sel = c1.selectbox("FLAPS", ["1+F", "2", "3"]); cond = c2.selectbox("RWY COND", ["DRY", "WET"])
        s1, s2 = st.columns(2); packs = s1.radio("PACKS", ["OFF", "ON"], horizontal=True); ai = s2.radio("ANTI-ICE", ["OFF", "ON"], horizontal=True)
    else:
        c1, c2 = st.columns(2); fl_sel = c1.selectbox("LDG FLAPS", ["FULL", "CONF 3"]); ab_sel = c2.selectbox("AUTOBRAKE", ["AUTO", "LO", "MED", "MAX"])
        r_cond = st.selectbox("RWY COND", ["DRY", "WET", "CONTAMINATED"])
        s1, s2, s3 = st.columns(3); packs = s1.radio("PACKS", ["OFF", "ON"], horizontal=True); ai = s2.radio("ANTI-ICE", ["OFF", "ON"], horizontal=True); rev = s3.radio("REVERSERS", ["OFF", "ON"], horizontal=True)

    st.divider()
    col_icao, col_rwy = st.columns([0.6, 0.4])
    icao = col_icao.text_input("ICAO AIRPORT", "LEZL").upper()
    metar = get_metar(icao); oat, hw, l_m, pista_sel, rwy_recip, elev_p, qnh = 15, 0, 2500, "---", "---", 0, 1013
    if metar:
        oat = float(metar.get('temperature', {}).get('celsius', 15)); qnh = float(metar.get('barometer', {}).get('hpa', 1013))
        w_dir, w_spd = metar.get('wind', {}).get('degrees', 0), metar.get('wind', {}).get('speed_kts', 0)
        ae = load_db()[load_db()['airport_ident'] == icao]
        if not ae.empty:
            p_list = pd.concat([ae[['le_ident','length_ft','le_elevation_ft','he_elevation_ft']].rename(columns={'le_ident':'p','le_elevation_ft':'e_s','he_elevation_ft':'e_e'}), ae[['he_ident','length_ft','he_elevation_ft','le_elevation_ft']].rename(columns={'he_ident':'p','he_elevation_ft':'e_s','le_elevation_ft':'e_e'})]).drop_duplicates()
            pista_sel = col_rwy.selectbox("RUNWAY", p_list['p'].tolist())
            row = p_list[p_list['p'] == pista_sel].iloc[0]; l_m, elev_p = int(row['length_ft']*0.3048), int(row['e_s'])
            hw = int(w_spd * math.cos(math.radians(w_dir - int('0'+''.join(filter(str.isdigit, pista_sel)))*10)))
            rwy_recip = get_reciprocal(pista_sel)
        pres_alt = elev_p + (1013 - qnh) * 27; isa_t = 15 - (elev_p / 1000 * 2); dens_alt = pres_alt + 120 * (oat - isa_t)
        st.markdown(f'<div class="info-box">LEN: {l_m}m | ELEV: {elev_p}ft | HW: {hw}kt | DA: {int(dens_alt)}ft</div>', unsafe_allow_html=True)

# 5. MOTOR DE FÍSICA BLOQUEADO (HIGH CONF 3 PENALTY)
vls_ref_weight = 66000
vls_ref_speed_ldg, vls_ref_speed_to = 128, 124
da_factor = 1 + (max(0, dens_alt) / 1000 * 0.01)
sys_penalty = (3 if packs == "ON" else 0) + (5 if ai == "ON" else 0)

if mode == "TAKEOFF":
    vls_base = vls_ref_speed_to * math.sqrt(weight_kg / vls_ref_weight) * da_factor
    fl_factor = 1.08 if fl_sel == "1+F" else 1.10 if fl_sel == "2" else 1.13
    vr = int(vls_base * 1.08 * fl_factor)
    v1 = min(int((vls_base * 1.06 * fl_factor) - (to_shift * 0.02) + (hw * 0.4)), vr)
    v2, f_s, s_s, gd_s = int(vls_base * 1.15 * fl_factor), int(vls_base * 1.25), int(vls_base * 1.45), int(vls_base * 1.65)
    flex = min(max(int(255 - (weight_kg/1000 * 3.4) - (to_shift * 0.015) - (dens_alt/1000 * 2) - sys_penalty), int(oat)), 65)
    ths = f"UP{(cg_pct-25)/7.5:.1f}"
    accel = (v2**2) / (2 * l_m * 0.65); sh_p = (to_shift / l_m) * 100
    p1, pr, p2 = sh_p + (v1**2/(2*accel*l_m))*100, sh_p + (vr**2/(2*accel*l_m))*100, sh_p + (v2**2/(2*accel*l_m))*100
    t1, t2, t3, d1, d2, d3 = "V1", "VR", "V2", int(v1*12.2), int(vr*12.2), int(v2*12.2)
else:
    vls_base = vls_ref_speed_ldg * math.sqrt(weight_kg / vls_ref_weight) * da_factor
    # BLOQUEO CONF 3 REFORZADO: +10kt sobre base FULL
    vls = int(vls_base + (10 if fl_sel == "CONF 3" else 0))
    hw_corr = max(10, hw) if hw > 0 else 0
    vapp = int(min(vls + 20, vls + 5 + (hw_corr / 3))); mini_gs = vapp - max(0, hw)
    dist_b = (weight_kg * 0.019) * (1 - (hw * 0.01)) * (1 + (dens_alt/10000))
    if ab_sel == "AUTO":
        rem = l_m - dist_b; ab_sug, ab_m = ("LO", 1.6) if rem > 800 else ("MED", 1.2) if rem > 300 else ("MAX", 0.9); ab_txt = f"AUTO: {ab_sug}"
    else: ab_m = 1.6 if ab_sel=="LO" else 1.2 if ab_sel=="MED" else 0.9; ab_txt = ab_sel
    dist_t = int(dist_b * ab_m * (0.88 if rev=="ON" else 1.0)); p_act = (dist_t / l_m) * 100
    p1, pr, p2 = 5, 5+p_act, 5+p_act*1.15; t1, t2, t3, d1, d2, d3 = "TDZ", "STOP", "SAFETY", 0, dist_t, int(dist_t*1.15)

# 6. SALIDA MCDU
with output_col:
    st.markdown(f'<div class="mcdu-title-white">{mode} PERF <span class="mcdu-value-green">{pista_sel}</span></div>', unsafe_allow_html=True)
    if mode == "TAKEOFF":
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f'<div class="mcdu-row"><p class="mcdu-label">V1</p><p class="mcdu-v-speed">{v1}</p></div>', 1)
        with c2: st.markdown(f'<div class="mcdu-row" style="text-align:center;"><p class="mcdu-label">FLP RETR</p><p class="mcdu-retrac-white">F=<span class="mcdu-value-green">{f_s}</span></p></div>', 1)
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f'<div class="mcdu-row"><p class="mcdu-label">VR</p><p class="mcdu-v-speed">{vr}</p></div>', 1)
        with c2: st.markdown(f'<div class="mcdu-row" style="text-align:center;"><p class="mcdu-label">SLT RETR</p><p class="mcdu-retrac-white">S=<span class="mcdu-value-green">{s_s}</span></p></div>', 1)
        with c3: st.markdown(f'<div class="mcdu-row" style="text-align:right;"><p class="mcdu-label">TO SHIFT</p><p class="mcdu-info-blue"><span style="color:white;">[M]</span><span style="color:#00FFFF;">[{to_shift if to_shift > 0 else ""}]*</span></p></div>', 1)
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f'<div class="mcdu-row"><p class="mcdu-label">V2</p><p class="mcdu-v-speed">{v2}</p></div>', 1)
        with c2: st.markdown(f'<div class="mcdu-row" style="text-align:center;"><p class="mcdu-label">CLEAN</p><p class="mcdu-retrac-white">O=<span class="mcdu-value-green">{gd_s}</span></p></div>', 1)
        with c3: st.markdown(f'<div class="mcdu-row" style="text-align:right;"><p class="mcdu-label">FLAPS/THS</p><p class="mcdu-info-blue">{"1" if fl_sel == "1+F" else fl_sel}/{ths}</p></div>', 1)
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f'<div class="mcdu-row"><p class="mcdu-label">TRANS ALT</p><p class="mcdu-info-blue">{6000 if icao.startswith("LE") else 5000}</p></div>', 1)
        with c3: st.markdown(f'<div class="mcdu-row" style="text-align:right;"><p class="mcdu-label">FLEX TO TEMP</p><p class="mcdu-info-blue">{flex}º</p></div>', 1)
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f'<div class="mcdu-row"><p class="mcdu-label">THR RED/ACC</p><p class="mcdu-info-blue">{elev_p+1500}/{elev_p+1500}</p></div>', 1)
        with c3: st.markdown(f'<div class="mcdu-row" style="text-align:right;"><p class="mcdu-label">ENG OUT ACC</p><p class="mcdu-info-blue">{elev_p+1500}</p></div>', 1)
    else:
        c1, c2 = st.columns(2); c1.markdown(f'<div class="mcdu-row"><p class="mcdu-label">VLS (VREF)</p><p class="mcdu-v-speed">{vls}</p></div>', 1); c2.markdown(f'<div class="mcdu-row" style="text-align:right;"><p class="mcdu-label">VAPP (TARGET)</p><p class="mcdu-info-blue">{vapp}</p></div>', 1)
        c1, c2 = st.columns(2); c1.markdown(f'<div class="mcdu-row"><p class="mcdu-label">MINI GS</p><p class="mcdu-info-blue">{mini_gs}</p></div>', 1); c2.markdown(f'<div class="mcdu-row" style="text-align:right;"><p class="mcdu-label">LDG DIST (FLD)</p><p class="mcdu-info-blue">{int(dist_t*1.15)}m</p></div>', 1)
        c1, c2 = st.columns(2); c1.markdown(f'<div class="mcdu-row"><p class="mcdu-label">AUTOBRAKE</p><p class="mcdu-info-blue">{ab_txt}</p></div>', 1); c2.markdown(f'<div class="mcdu-row" style="text-align:right;"><p class="mcdu-label">LDG FLAPS</p><p class="mcdu-info-blue">{fl_sel}</p></div>', 1)

    # GRÁFICO
    st.markdown(f"""<div class="rwy-container"><div class="rwy-asphalt"><div class="rwy-number-start">{pista_sel}</div><div class="rwy-centerline"></div><div class="rwy-number-end">{rwy_recip}</div></div>
    <div class="v-marker-line" style="left:{p1}%; top:-30px; height:120px;"></div><div class="v-tag-top" style="left:{p1}%; top:-50px;">{t1}</div><div class="v-tag-bottom" style="left:{p1}%; top:95px;">{d1}m</div>
    <div class="v-marker-line" style="left:{pr}%; top:-60px; height:180px;"></div><div class="v-tag-top" style="left:{pr}%; top:-80px;">{t2}</div><div class="v-tag-bottom" style="left:{pr}%; top:125px;">{d2}m</div>
    <div class="v-marker-line" style="left:{p2}%; top:-90px; height:240px;"></div><div class="v-tag-top" style="left:{p2}%; top:-110px;">{t3}</div><div class="v-tag-bottom" style="left:{p2}%; top:155px;">{d3}m</div></div>""", unsafe_allow_html=True)

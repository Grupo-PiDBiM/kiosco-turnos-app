import streamlit as st
import pandas as pd
import datetime as dt
import calendar
from pathlib import Path

# ================== APP ==================
st.set_page_config(page_title="Calendario 24/7 – La Lucy", layout="wide")
st.title("📅 Calendario de Turnos – La Lucy")

# --- Sidebar dinámico: ancho chico/grande según si se está editando ---
is_editing = bool(st.session_state.get("selected_day"))
SIDEBAR_W = 520 if is_editing else 320  # ajustá a gusto (px)

st.markdown(f"""
<style>
/* Fuerza ancho del sidebar */
section[data-testid="stSidebar"] {{
  width: {SIDEBAR_W}px !important;
  min-width: {SIDEBAR_W}px !important;
  max-width: {SIDEBAR_W}px !important;
}}
section[data-testid="stSidebar"] > div {{
  width: {SIDEBAR_W}px !important;
}}
/* Widgets legibles dentro del sidebar */
section[data-testid="stSidebar"] .stSelectbox > div {{ width: 100%; }}
section[data-testid="stSidebar"] div[data-baseweb="select"] {{ min-width: 100%; }}
section[data-testid="stSidebar"] .stButton > button {{
  width: 100%;
  white-space: nowrap;     /* que no corte el texto en vertical */
  font-size: .95rem;
  padding: 6px 10px;
}}
</style>
""", unsafe_allow_html=True)

# ================== PERSISTENCIA ==================
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
OV_PATH = DATA_DIR / "overrides.csv"   # ediciones persistentes

# ================== ESTILOS ==================
st.markdown("""
<style>
/* Grilla mensual compacta */
.daybox{border:1px solid #e5e7eb;border-radius:12px;padding:8px 10px;background:#fff;
        min-height:120px; box-shadow:0 1px 2px rgba(0,0,0,.04)}
.dayhead{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}
.daynum{font-weight:700;color:#111827}
.editbtn{font-size:13px;color:#374151;border:1px solid #e5e7eb;border-radius:8px;padding:2px 6px;background:#f9fafb}
.editbtn:hover{background:#f3f4f6}

/* línea de turno */
.row{margin-top:6px; display:flex; align-items:center; gap:6px; flex-wrap:wrap}
.ttl{font-weight:600; font-size:.88rem; color:#111827}
.horas{color:#6b7280; font-size:.82rem}

/* Chips por persona */
.chip{display:inline-block;padding:2px 8px;border-radius:999px;font-size:.88rem;white-space:nowrap}
.chip-hugo{background:#DBEAFE}
.chip-moira{background:#EDE9FE}
.chip-brisa{background:#FEF3C7}
.chip-jere{background:#FFE4D6}
.chip-alina{background:#FCE7F3;border:1px dashed #f472b6}
.chip-jony{background:#D1FAE5}
.chip-dianela{background:#FCE7E7}
.chip-warn{background:#fee2e2;border:1px dashed #ef4444}

.nav{display:flex;justify-content:space-between;align-items:center;margin:6px 0 10px}
.nav h3{margin:0}
.navbtn{border:1px solid #e5e7eb;border-radius:10px;padding:6px 10px;background:#fff}
.navbtn:hover{background:#f9fafb}
.small{font-size:.85rem;color:#6b7280}
</style>
""", unsafe_allow_html=True)

# ================== CONSTANTES ==================
DIAS = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
MESES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
PERSONAS = ["Hugo","Moira","Brisa","Jere","Alina","Jony","Dianela"]
FLOTANTE = "Alina"

ASIGN_DEF = { "Mañana": ["Hugo","Moira"], "Tarde": ["Brisa","Jere"], "Noche": ["Jony","Dianela"] }
HORAS_DEF = { "Mañana": ("06:00","14:00"), "Tarde": ("14:00","22:00"), "Noche": ("22:00","06:00 (+1)") }

# ================== HELPERS ==================
def chip_cls(nombre: str) -> str:
    n = str(nombre).lower()
    if "falta cubrir" in n: return "chip-warn"
    return {
        "hugo":"chip-hugo","moira":"chip-moira","brisa":"chip-brisa","jere":"chip-jere",
        "alina":"chip-alina","jony":"chip-jony","dianela":"chip-dianela"
    }.get(n, "chip")

def primer_lunes(d: dt.date) -> dt.date:
    return d - dt.timedelta(days=d.weekday())

def add_months(d: dt.date, m: int) -> dt.date:
    y = d.year + (d.month - 1 + m) // 12
    mo = (d.month - 1 + m) % 12 + 1
    return dt.date(y, mo, 1)

def rango_mes(year: int, month: int):
    first = dt.date(year, month, 1)
    last = dt.date(year, month, calendar.monthrange(year, month)[1])
    return first, last

# ================== GENERADOR ROTATIVO ==================
def generar_rango(anchor_lunes: dt.date, dias: int,
                  asign=ASIGN_DEF, horas=HORAS_DEF, offset_base=0, dia_libre_flot=6) -> pd.DataFrame:
    titulares = asign["Mañana"] + asign["Tarde"] + asign["Noche"]  # 6 personas
    rows = []
    for i in range(dias):
        fecha = anchor_lunes + dt.timedelta(days=i)
        dow = fecha.weekday()
        descansa = titulares[(offset_base + i) % 6] if dow <= 5 else None
        flo_trab = (dow != dia_libre_flot)
        for t in ["Mañana","Tarde","Noche"]:
            a, b = asign[t]; hi, hf = horas[t]
            if descansa in (a,b):
                titular = b if descansa == a else a
                pa, pb = (titular, FLOTANTE) if flo_trab else (titular, "⚠ Falta cubrir")
            else:
                pa, pb = a, b
            rows.append({
                "Fecha": fecha, "Día": DIAS[dow], "Turno": t,
                "Hora Inicio": hi, "Hora Fin": hf,
                "Persona A": pa, "Persona B": pb,
                "Descansa": descansa if descansa in (a,b) else ""
            })
    df = pd.DataFrame(rows)
    orden = {"Mañana":0,"Tarde":1,"Noche":2}
    df["__o__"] = df["Turno"].map(orden)
    return df.sort_values(["Fecha","__o__"]).drop(columns="__o__").reset_index(drop=True)

# ================== OVERRIDES (PERSISTENCIA) ==================
def load_overrides() -> pd.DataFrame:
    if OV_PATH.exists():
        df = pd.read_csv(OV_PATH)
        df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
        return df
    return pd.DataFrame(columns=["Fecha","Turno","Persona A","Persona B"])

def apply_overrides(cal: pd.DataFrame, ov: pd.DataFrame) -> pd.DataFrame:
    if ov.empty:
        return cal
    m = cal.merge(ov, on=["Fecha","Turno"], how="left", suffixes=("","_ov"))
    for col in ["Persona A","Persona B"]:
        m[col] = m[f"{col}_ov"].fillna(m[col])
        m.drop(columns=[f"{col}_ov"], inplace=True)
    return m

def save_overrides_for_day(fecha: dt.date, valores: dict):
    ov = load_overrides()
    for t in ["Mañana","Tarde","Noche"]:
        row = {"Fecha": fecha, "Turno": t,
               "Persona A": valores[t]["A"], "Persona B": valores[t]["B"]}
        mask = (ov["Fecha"]==fecha) & (ov["Turno"]==t)
        if mask.any():
            ov.loc[mask, ["Persona A","Persona B"]] = row["Persona A"], row["Persona B"]
        else:
            ov = pd.concat([ov, pd.DataFrame([row])], ignore_index=True)
    ov.to_csv(OV_PATH, index=False)
    st.session_state.overrides = ov

# ================== CONFIG ==================
c1,c2,c3 = st.columns([1.6,1,1])
with c1:
    hoy = dt.date.today()
    fecha_inicio = st.date_input("Inicio de rotación (usa el lunes de esa semana)", value=hoy, key="cfg_fecha")
    meses_prec = st.number_input("Meses a generar hacia delante", 1, 12, 6, 1, key="cfg_meses")
with c2:
    offset_rot = st.number_input("Offset rotación", 0, 100, 0, key="cfg_offset")
with c3:
    dia_flo = st.selectbox("Día libre de Alina", DIAS, index=6, key="cfg_dia_flo")
    dia_flo_idx = DIAS.index(dia_flo)

if "config" not in st.session_state:
    st.session_state.config = {}

cfg = dict(anchor=primer_lunes(fecha_inicio), meses=int(meses_prec), offset=int(offset_rot), dia_flo=int(dia_flo_idx))
if (st.session_state.config != cfg) or ("cal" not in st.session_state):
    st.session_state.config = cfg
    anchor = cfg["anchor"]
    dias = 31 * cfg["meses"] + 14
    base_cal = generar_rango(anchor, dias, ASIGN_DEF, HORAS_DEF, cfg["offset"], cfg["dia_flo"])
    st.session_state.overrides = load_overrides()
    st.session_state.cal = apply_overrides(base_cal, st.session_state.overrides)

# Estado de mes actual
if "cur_month" not in st.session_state:
    st.session_state.cur_month = dt.date(hoy.year, hoy.month, 1)

# ================== NAV MENSUAL ==================
cur = st.session_state.cur_month
first, last = rango_mes(cur.year, cur.month)

nav_l, nav_c, nav_r = st.columns([1,6,1])
with nav_l:
    if st.button("◀ Mes anterior"):
        st.session_state.cur_month = add_months(cur, -1)
        st.rerun()
with nav_c:
    st.markdown(f"<div class='nav'><h3>{MESES[cur.month-1].capitalize()} {cur.year}</h3></div>", unsafe_allow_html=True)
with nav_r:
    if st.button("Mes siguiente ▶"):
        st.session_state.cur_month = add_months(cur, +1)
        st.rerun()

# ================== EDITOR LATERAL ==================
def aplicar_guardado(fecha, valores):
    df = st.session_state.cal
    for t in ["Mañana","Tarde","Noche"]:
        a = valores[t]["A"]; b = valores[t]["B"]
        idx = df[(df["Fecha"]==fecha) & (df["Turno"]==t)].index
        if not idx.empty:
            df.at[idx[0],"Persona A"] = a
            df.at[idx[0],"Persona B"] = b
    st.session_state.cal = df

def cubrir_o_falta(fecha: dt.date, nombre: str) -> str:
    """Si puede, cubre Alina; si no, '⚠ Falta cubrir'."""
    if (nombre != FLOTANTE) and (fecha.weekday() != st.session_state.config["dia_flo"]):
        return FLOTANTE
    return "⚠ Falta cubrir"

if "selected_day" in st.session_state and st.session_state.selected_day:
    sel: dt.date = st.session_state.selected_day
    iso = sel.isoformat()
    st.sidebar.header(f"Editar {sel.strftime('%d/%m/%Y')}")
    df_day = st.session_state.cal[st.session_state.cal["Fecha"]==sel]
    if not df_day.empty:
        valores = {}
        opts = PERSONAS + ["⚠ Falta cubrir"]
        for t in ["Mañana","Tarde","Noche"]:
            row = df_day[df_day["Turno"]==t].iloc[0]
            st.sidebar.subheader(t)

            # Persona A
            keyA = f"sb_{iso}_{t}_A"
            if keyA not in st.session_state:
                st.session_state[keyA] = str(row["Persona A"]) if str(row["Persona A"]) in opts else opts[0]
            cA, cA_btn = st.sidebar.columns([3,1])  # más aire al botón
            with cA:
                st.caption("A")
                st.selectbox(f"A_{t}", opts, key=keyA, label_visibility="collapsed")
            with cA_btn:
                if st.button("Falta A", key=f"faltA_{iso}_{t}"):
                    st.session_state[keyA] = cubrir_o_falta(sel, str(row["Persona A"]))
                    st.rerun()

            # Persona B
            keyB = f"sb_{iso}_{t}_B"
            if keyB not in st.session_state:
                st.session_state[keyB] = str(row["Persona B"]) if str(row["Persona B"]) in opts else opts[0]
            cB, cB_btn = st.sidebar.columns([3,1])
            with cB:
                st.caption("B")
                st.selectbox(f"B_{t}", opts, key=keyB, label_visibility="collapsed")
            with cB_btn:
                if st.button("Falta B", key=f"faltB_{iso}_{t}"):
                    st.session_state[keyB] = cubrir_o_falta(sel, str(row["Persona B"]))
                    st.rerun()

            valores[t] = {"A": st.session_state[keyA], "B": st.session_state[keyB]}

        if st.sidebar.button("💾 Guardar cambios", key=f"save_{iso}"):
            aplicar_guardado(sel, valores)          # memoria
            save_overrides_for_day(sel, valores)    # persistencia CSV
            st.sidebar.success("Guardado.")
            st.rerun()

    if st.sidebar.button("Cerrar editor", key=f"close_{iso}"):
        st.session_state.selected_day = None
        st.rerun()

# ================== RENDER DEL MES (solo días del mes) ==================
cal = apply_overrides(
    st.session_state.cal,
    st.session_state.overrides if "overrides" in st.session_state else load_overrides()
)

day = first
while day <= last:
    cols = st.columns(7)
    # huecos iniciales de la fila (si el mes no empieza lunes) — NO pintamos recuadros vacíos
    start_wd = day.weekday()
    i = 0
    for _ in range(start_wd):
        _ = cols[i].empty(); i += 1

    # pintar días reales
    while i < 7 and day <= last:
        with cols[i]:
            try:
                card = st.container(border=True)
            except TypeError:
                card = st.container()
            with card:
                numero = day.day

                # Editar día
                if st.button("✎ Editar", key=f"edit_{day.isoformat()}"):
                    st.session_state.selected_day = day
                    st.rerun()

                st.markdown(
                    f"<div class='dayhead'><span class='daynum'>{numero}</span></div>",
                    unsafe_allow_html=True
                )

                sub = cal[cal["Fecha"]==day]
                if sub.empty:
                    st.caption("—")
                else:
                    for t in ["Mañana","Tarde","Noche"]:
                        row = sub[sub["Turno"]==t]
                        if row.empty:
                            continue
                        a = str(row.iloc[0]["Persona A"]); b = str(row.iloc[0]["Persona B"])
                        hi = row.iloc[0]["Hora Inicio"]; hf = row.iloc[0]["Hora Fin"]
                        st.markdown(
                            f"<div class='row'><span class='ttl'>{t}</span> "
                            f"<span class='horas'>({hi}–{hf})</span></div>",
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f"<div class='row'>"
                            f"<span class='chip {chip_cls(a)}'>{a}</span>"
                            f"<span class='chip {chip_cls(b)}'>{b}</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                # Info de libres
                if not sub.empty and any(sub["Descansa"].astype(str).str.len() > 0):
                    quien = sub["Descansa"].replace("", pd.NA).dropna().iloc[0]
                    st.markdown(f"<div class='small'>🟢 Libre (titular): {quien}</div>", unsafe_allow_html=True)
                if day.weekday() == st.session_state.config["dia_flo"]:
                    st.markdown(f"<div class='small'>🟡 Libre flotante: {FLOTANTE}</div>", unsafe_allow_html=True)

        i += 1
        day += dt.timedelta(days=1)

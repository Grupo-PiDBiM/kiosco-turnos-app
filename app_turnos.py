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
SIDEBAR_W = 520 if is_editing else 320
st.markdown(f"""
<style>
/* Sidebar dinámico */
section[data-testid="stSidebar"] {{
  width: {SIDEBAR_W}px !important; min-width:{SIDEBAR_W}px !important; max-width:{SIDEBAR_W}px !important;
}}
section[data-testid="stSidebar"] > div {{ width:{SIDEBAR_W}px !important; }}
section[data-testid="stSidebar"] .stSelectbox > div {{ width:100%; }}
section[data-testid="stSidebar"] div[data-baseweb="select"]{{ min-width:100%; }}
section[data-testid="stSidebar"] .stButton > button{{ width:100%; white-space:nowrap; font-size:.95rem; padding:6px 10px; }}

/* ====== Estilos generales calendario ====== */
.daybox{{border:1px solid #e5e7eb;border-radius:12px;padding:10px 12px;background:#fff;
        min-height:120px; box-shadow:0 1px 2px rgba(0,0,0,.05)}}
.dayhead{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}}
.daynum{{font-weight:700;color:#111827}}
.row{{margin-top:6px; display:flex; align-items:center; gap:6px; flex-wrap:wrap}}
.ttl{{font-weight:600; font-size:.88rem; color:#111827}}
.horas{{color:#6b7280; font-size:.82rem}}
.chip{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:.88rem;white-space:nowrap}}
.chip-hugo{{background:#DBEAFE}} .chip-moira{{background:#EDE9FE}} .chip-brisa{{background:#FEF3C7}}
.chip-jere{{background:#FFE4D6}} .chip-alina{{background:#FCE7F3;border:1px dashed #f472b6}}
.chip-jony{{background:#D1FAE5}} .chip-dianela{{background:#FCE7E7}}
.chip-warn{{background:#fee2e2;border:1px dashed #ef4444}}
.nav{{display:flex;justify-content:space-between;align-items:center;margin:6px 0 10px}}
.nav h3{{margin:0}}
.small{{font-size:.85rem;color:#6b7280}}

/* Ajustes SOLO móvil */
@media (max-width: 768px) {{
  section[data-testid="stSidebar"]{{ width:100% !important; min-width:100% !important; max-width:100% !important; }}
  section[data-testid="stSidebar"] > div{{ width:100% !important; }}
  .daybox{{ min-height:88px; padding:8px 10px; border-radius:14px; }}
  .daynum{{ font-size:1rem; }}
  .ttl{{ font-size:.9rem; }}
  .horas{{ font-size:.78rem; }}
  .chip{{ font-size:.8rem; padding:2px 7px; }}
}}
</style>
""", unsafe_allow_html=True)

# ================== PERSISTENCIA ==================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
OV_PATH      = DATA_DIR / "overrides.csv"   # cambios manuales (A/B/Libre)
ABS_PATH     = DATA_DIR / "absences.csv"    # faltas (log)
TASKS_PATH   = DATA_DIR / "tasks.csv"       # gestor de tareas
TIMELOG_PATH = DATA_DIR / "timelog.csv"     # fichadas (ingreso/salida)

# ================== CONSTANTES ==================
PERSONAS = ["Hugo","Moira","Brisa","Jere","Alina","Jony","Dianela"]
DIAS      = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
DIAS_ABBR = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]
MESES     = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
HORAS_DEF = { "Mañana": ("06:00","14:00"), "Tarde": ("14:00","22:00"), "Noche": ("22:00","06:00 (+1)") }

# Titulares fijos por turno
ASIGN_DEF = {"Mañana":["Moira","Brisa"], "Tarde":["Jere","Dianela"], "Noche":["Hugo","Jony"]}

# ================== HELPERS ==================
def chip_cls(nombre: str) -> str:
    n = str(nombre).lower()
    if "falta cubrir" in n: return "chip-warn"
    return {
        "hugo":"chip-hugo","moira":"chip-moira","brisa":"chip-brisa",
        "jere":"chip-jere","alina":"chip-alina","jony":"chip-jony","dianela":"chip-dianela"
    }.get(n,"chip")

def monday_of_week(d: dt.date) -> dt.date:
    return d - dt.timedelta(days=d.weekday())

def add_months(d: dt.date, m: int) -> dt.date:
    y = d.year + (d.month - 1 + m) // 12
    mo = (d.month - 1 + m) % 12 + 1
    return dt.date(y, mo, 1)

def rango_mes(year: int, month: int):
    first = dt.date(year, month, 1)
    last  = dt.date(year, month, calendar.monthrange(year, month)[1])
    return first, last

# ================== GENERADOR: 1 libre/día rotando entre 7 ==================
def generar_rango_rotativo(anchor_monday: dt.date, dias: int, offset_week: int) -> pd.DataFrame:
    """
    - Libre = orden[(semana + dia + offset) % 7] (incluye a Alina).
    - Si el libre del día es titular del turno, Alina lo cubre en ese turno.
    - Si el libre es Alina, titulares trabajan normal.
    """
    orden = ["Moira","Brisa","Jere","Dianela","Hugo","Jony","Alina"]
    rows = []
    for i in range(dias):
        fecha = anchor_monday + dt.timedelta(days=i)
        wd = fecha.weekday()
        wk = (fecha - anchor_monday).days // 7
        libre = orden[(wk + wd + offset_week) % 7]
        for turno in ["Mañana","Tarde","Noche"]:
            a,b = ASIGN_DEF[turno]; hi,hf = HORAS_DEF[turno]
            if libre == a: pa,pb = "Alina", b
            elif libre == b: pa,pb = a, "Alina"
            else: pa,pb = a,b
            rows.append({"Fecha":fecha,"Día":DIAS[wd],"Turno":turno,"Hora Inicio":hi,"Hora Fin":hf,
                         "Persona A":pa,"Persona B":pb,"Libre":libre})
    df = pd.DataFrame(rows)
    df["__o__"] = df["Turno"].map({"Mañana":0,"Tarde":1,"Noche":2})
    return df.sort_values(["Fecha","__o__"]).drop(columns="__o__").reset_index(drop=True)

# ================== OVERRIDES / FALTAS / TAREAS / FICHADAS ==================
def load_overrides() -> pd.DataFrame:
    if OV_PATH.exists():
        df = pd.read_csv(OV_PATH)
        if "Fecha" in df: df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
        return df
    return pd.DataFrame(columns=["Fecha","Turno","Persona A","Persona B","Libre"])

def apply_overrides(cal: pd.DataFrame, ov: pd.DataFrame) -> pd.DataFrame:
    if ov.empty: return cal
    m = cal.merge(ov, on=["Fecha","Turno"], how="left", suffixes=("","_ov"))
    for col in ["Persona A","Persona B","Libre"]:
        if f"{col}_ov" in m.columns:
            m[col] = m[f"{col}_ov"].fillna(m[col])
            m.drop(columns=[f"{col}_ov"], inplace=True)
    return m

def save_overrides_for_day(fecha: dt.date, valores: dict, libre_override=None):
    ov = load_overrides()
    for t in ["Mañana","Tarde","Noche"]:
        row = {"Fecha":fecha,"Turno":t,"Persona A":valores[t]["A"],"Persona B":valores[t]["B"]}
        if libre_override is not None: row["Libre"]=libre_override
        mask = (ov["Fecha"]==fecha)&(ov["Turno"]==t)
        if mask.any():
            for k,v in row.items(): ov.loc[mask,k]=v
        else:
            ov = pd.concat([ov,pd.DataFrame([row])], ignore_index=True)
    ov.to_csv(OV_PATH, index=False)
    st.session_state.overrides = ov

def set_libre_override_for_day(fecha: dt.date, nuevo_libre: str):
    ov = load_overrides()
    for t in ["Mañana","Tarde","Noche"]:
        mask=(ov["Fecha"]==fecha)&(ov["Turno"]==t)
        if mask.any(): ov.loc[mask,"Libre"]=nuevo_libre
        else: ov = pd.concat([ov,pd.DataFrame([{"Fecha":fecha,"Turno":t,"Libre":nuevo_libre}])], ignore_index=True)
    ov.to_csv(OV_PATH, index=False)
    st.session_state.overrides = ov

def load_absences() -> pd.DataFrame:
    if ABS_PATH.exists():
        df = pd.read_csv(ABS_PATH)
        df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
        return df
    return pd.DataFrame(columns=["Fecha","Turno","Slot","Persona","Motivo","LoggedAt"])

def append_absence(rec: dict):
    df = load_absences()
    df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True)
    df.to_csv(ABS_PATH, index=False)
    st.session_state.absences = df

def remove_absences_for_day_if_present(fecha: dt.date, personas_presentes: set):
    df = load_absences()
    if df.empty: return
    keep = ~((df["Fecha"]==fecha) & (df["Persona"].isin(list(personas_presentes))))
    df = df[keep].copy()
    df.to_csv(ABS_PATH, index=False)
    st.session_state.absences = df

def load_tasks() -> pd.DataFrame:
    if TASKS_PATH.exists():
        df = pd.read_csv(TASKS_PATH)
        if "Fecha" in df: df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
        if "Due" in df: df["Due"] = pd.to_datetime(df["Due"], errors="coerce").dt.date
        return df
    return pd.DataFrame(columns=["id","Fecha","Turno","Persona","Titulo","Estado","Due","CreatedAt"])

def save_tasks(df: pd.DataFrame):
    df.to_csv(TASKS_PATH, index=False)
    st.session_state.tasks = df

def load_timelog() -> pd.DataFrame:
    if TIMELOG_PATH.exists():
        df = pd.read_csv(TIMELOG_PATH)
        if "Fecha" in df: df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
        if "Timestamp" in df: df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        return df
    return pd.DataFrame(columns=["id","Fecha","Persona","Tipo","Timestamp","Turno","Fuente"])

def save_timelog(df: pd.DataFrame):
    df.to_csv(TIMELOG_PATH, index=False)
    st.session_state.timelog = df

def append_timelog(row: dict):
    """Normaliza Timestamp a datetime y agrega una fila al timelog."""
    df = load_timelog()
    # 🔒 normalizar timestamp a datetime
    if "Timestamp" in row:
        row["Timestamp"] = pd.to_datetime(row["Timestamp"], errors="coerce")
    else:
        row["Timestamp"] = pd.Timestamp.now()

    # id incremental robusto
    if df.empty or "id" not in df.columns:
        new_id = 1
    else:
        _ids = pd.to_numeric(df["id"], errors="coerce")
        new_id = (int(_ids.max()) if _ids.notna().any() else 0) + 1

    row["id"] = new_id
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_timelog(df)

# ================== CONFIG ==================
c1,c2,c3 = st.columns([1.6,1,1])
with c1:
    hoy = dt.date.today()
    fecha_anchor = st.date_input("Inicio de rotación (usa el lunes de esa semana)", value=hoy, key="cfg_fecha")
    meses_prec = st.number_input("Meses a generar hacia delante", 1, 12, 6, 1, key="cfg_meses")
with c2:
    offset_week = st.number_input("Offset rotación semanal (0–6)", 0, 100, 0, key="cfg_offset_week")
with c3:
    st.caption("1 libre por día (entre los 7). Alina cubre al titular libre del día.")

if "config" not in st.session_state:
    st.session_state.config = {}

cfg = dict(anchor=monday_of_week(fecha_anchor), meses=int(meses_prec), offset=int(offset_week))

if (st.session_state.config != cfg) or ("cal" not in st.session_state):
    st.session_state.config = cfg
    anchor = cfg["anchor"]
    dias = 31 * cfg["meses"] + 14
    base_cal = generar_rango_rotativo(anchor, dias, cfg["offset"])
    st.session_state.overrides = load_overrides()
    st.session_state.absences = load_absences()
    st.session_state.tasks = load_tasks()
    st.session_state.timelog = load_timelog()
    st.session_state.cal = apply_overrides(base_cal, st.session_state.overrides)

# Estado de mes actual
if "cur_month" not in st.session_state:
    st.session_state.cur_month = dt.date(hoy.year, hoy.month, 1)

# ================== NAV / RANGOS ==================
cur = st.session_state.cur_month
first, last = rango_mes(cur.year, cur.month)

# ================== APLICAR CAMBIOS PENDIENTES ==================
_pending = st.session_state.get("_pending_set", {})
if _pending:
    for _k,_v in _pending.items(): st.session_state[_k]=_v
    st.session_state["_pending_set"] = {}
_pending_abs = st.session_state.get("_pending_abs", [])
if _pending_abs:
    for rec in _pending_abs: append_absence(rec)
    st.session_state["_pending_abs"] = []

# ================== TABS ==================
tab_cal, tab_stats, tab_tasks, tab_clock = st.tabs(["📆 Calendario", "📊 Faltas & Horas", "🗂️ Tareas", "⏱️ Fichadas"])

# ================== CALENDARIO ==================
with tab_cal:
    # NAV
    nav_l, nav_c, nav_r = st.columns([1,6,1])
    with nav_l:
        if st.button("◀ Mes anterior"):
            st.session_state.cur_month = add_months(cur, -1); st.rerun()
    with nav_c:
        st.markdown(f"<div class='nav'><h3>{MESES[cur.month-1].capitalize()} {cur.year}</h3></div>", unsafe_allow_html=True)
    with nav_r:
        if st.button("Mes siguiente ▶"):
            st.session_state.cur_month = add_months(cur, +1); st.rerun()

    # Helpers editor
    def libre_del_dia(fecha: dt.date) -> str:
        sub = st.session_state.cal[st.session_state.cal["Fecha"]==fecha]
        return "" if sub.empty else str(sub.iloc[0]["Libre"])

    # Editor lateral (✎)
    if "selected_day" in st.session_state and st.session_state.selected_day:
        sel: dt.date = st.session_state.selected_day
        iso = sel.isoformat()
        st.sidebar.header(f"Editar {DIAS[sel.weekday()]} {sel.strftime('%d/%m/%Y')}")
        df_day = st.session_state.cal[st.session_state.cal["Fecha"]==sel]
        if not df_day.empty:
            valores = {}
            opts = PERSONAS + ["⚠ Falta cubrir"]
            libre_hoy = libre_del_dia(sel)
            st.sidebar.caption(f"Libre hoy (planificado): **{libre_hoy}** — Si alguien falta, cubre el libre y el libre pasa a ser el ausente.")
            for t in ["Mañana","Tarde","Noche"]:
                row = df_day[df_day["Turno"]==t].iloc[0]
                st.sidebar.subheader(t)

                # A
                keyA = f"sb_{iso}_{t}_A"
                if keyA not in st.session_state:
                    st.session_state[keyA] = str(row["Persona A"]) if str(row["Persona A"]) in opts else opts[0]
                cA,cA_btn = st.sidebar.columns([3,1])
                with cA:
                    st.caption("A")
                    st.selectbox(f"A_{t}", opts, key=keyA, label_visibility="collapsed")
                with cA_btn:
                    if st.button("Falta A", key=f"faltA_{iso}_{t}"):
                        aus = str(row["Persona A"])
                        st.session_state.setdefault("_pending_set", {})[keyA] = libre_hoy if libre_hoy else "⚠ Falta cubrir"
                        if aus: set_libre_override_for_day(sel, aus)
                        st.session_state.setdefault("_pending_abs", []).append({
                            "Fecha": sel, "Turno": t, "Slot":"A", "Persona": aus,
                            "Motivo":"FALTA", "LoggedAt": dt.datetime.now().isoformat(timespec="seconds")
                        }); st.rerun()

                # B
                keyB = f"sb_{iso}_{t}_B"
                if keyB not in st.session_state:
                    st.session_state[keyB] = str(row["Persona B"]) if str(row["Persona B"]) in opts else opts[0]
                cB,cB_btn = st.sidebar.columns([3,1])
                with cB:
                    st.caption("B")
                    st.selectbox(f"B_{t}", opts, key=keyB, label_visibility="collapsed")
                with cB_btn:
                    if st.button("Falta B", key=f"faltB_{iso}_{t}"):
                        aus = str(row["Persona B"])
                        st.session_state.setdefault("_pending_set", {})[keyB] = libre_hoy if libre_hoy else "⚠ Falta cubrir"
                        if aus: set_libre_override_for_day(sel, aus)
                        st.session_state.setdefault("_pending_abs", []).append({
                            "Fecha": sel, "Turno": t, "Slot":"B", "Persona": aus,
                            "Motivo":"FALTA", "LoggedAt": dt.datetime.now().isoformat(timespec="seconds")
                        }); st.rerun()

                valores[t] = {"A":st.session_state[keyA], "B":st.session_state[keyB]}

            if st.sidebar.button("💾 Guardar cambios", key=f"save_{iso}"):
                df = st.session_state.cal
                for t in ["Mañana","Tarde","Noche"]:
                    a,b = valores[t]["A"], valores[t]["B"]
                    idx = df[(df["Fecha"]==sel)&(df["Turno"]==t)].index
                    if not idx.empty: df.at[idx[0],"Persona A"]=a; df.at[idx[0],"Persona B"]=b
                st.session_state.cal = df
                libre_actual = libre_del_dia(sel)
                save_overrides_for_day(sel, valores, libre_override=libre_actual)
                presentes = {valores[t]["A"] for t in ["Mañana","Tarde","Noche"]} | {valores[t]["B"] for t in ["Mañana","Tarde","Noche"]}
                presentes.discard("⚠ Falta cubrir"); presentes.discard("")
                remove_absences_for_day_if_present(sel, presentes)
                st.sidebar.success("Guardado."); st.rerun()

        if st.sidebar.button("Cerrar editor", key=f"close_{iso}"):
            st.session_state.selected_day = None; st.rerun()

    # --------- DATAFRAME del mes (con overrides) ---------
    cal = apply_overrides(st.session_state.cal, st.session_state.overrides if "overrides" in st.session_state else load_overrides())

    # --- RENDER DEL MES SIN ENCABEZADO DE DÍAS ---
    day = first
    while day <= last:
        cols = st.columns(7)
        start_wd = day.weekday()
        i = 0
        # Huecos iniciales
        for _ in range(start_wd):
            cols[i].empty()
            i += 1

        # Pintar días
        while i < 7 and day <= last:
            with cols[i]:
                try:
                    card = st.container(border=True)
                except TypeError:
                    card = st.container()
                with card:
                    numero = day.day

                    # Botón editar
                    if st.button("✎ Editar", key=f"edit_{day.isoformat()}"):
                        st.session_state.selected_day = day
                        st.rerun()

                    # Título del casillero (día abreviado + número)
                    st.markdown(
                        f"<div class='dayhead'><span class='daynum'>{DIAS_ABBR[day.weekday()]} {numero}</span></div>",
                        unsafe_allow_html=True
                    )

                    sub = cal[cal["Fecha"] == day]
                    if sub.empty:
                        st.caption("—")
                    else:
                        libre_hoy = str(sub.iloc[0]["Libre"])
                        st.markdown(f"<div class='small'>🟢 Libre: {libre_hoy}</div>", unsafe_allow_html=True)

                        for t in ["Mañana", "Tarde", "Noche"]:
                            row = sub[sub["Turno"] == t]
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
            i += 1
            day += dt.timedelta(days=1)

# ================== FALTAS & HORAS ==================
with tab_stats:
    st.subheader("Registro de faltas")
    abs_df = st.session_state.absences if "absences" in st.session_state else load_absences()
    if not abs_df.empty:
        mask = (abs_df["Fecha"]>=first) & (abs_df["Fecha"]<=last)
        st.dataframe(abs_df[mask].sort_values(["Fecha","Turno","Slot"]), use_container_width=True)
    else:
        st.info("Aún no hay faltas registradas.")

    st.markdown("---")
    st.subheader("Horas trabajadas (mes visible)")
    cal_mes = apply_overrides(st.session_state.cal, st.session_state.overrides if "overrides" in st.session_state else load_overrides())
    cal_mes = cal_mes[(cal_mes["Fecha"]>=first) & (cal_mes["Fecha"]<=last)].copy()
    if cal_mes.empty:
        st.info("Sin datos del mes.")
    else:
        longA = cal_mes[["Fecha","Turno","Persona A"]].rename(columns={"Persona A":"Persona"})
        longB = cal_mes[["Fecha","Turno","Persona B"]].rename(columns={"Persona B":"Persona"})
        long = pd.concat([longA,longB], ignore_index=True)
        long = long[long["Persona"].notna()]
        long = long[long["Persona"]!="⚠ Falta cubrir"]
        long["Horas"] = 8
        horas = long.groupby("Persona", as_index=False)["Horas"].sum().sort_values("Horas", ascending=False)
        st.dataframe(horas, use_container_width=True)

# ================== TAREAS ==================
with tab_tasks:
    st.subheader("Gestor de tareas")
    tasks = st.session_state.tasks if "tasks" in st.session_state else load_tasks()

    c_add, c_list = st.columns([1,2])
    with c_add:
        st.markdown("**Nueva tarea**")
        default_date = st.session_state.get("selected_day", st.session_state.cur_month)
        t_fecha = st.date_input("Fecha", value=default_date, key="task_fecha")
        t_turno = st.selectbox("Turno (opcional)", ["", "Mañana","Tarde","Noche"], index=0, key="task_turno")
        t_persona = st.selectbox("Persona (opcional)", [""] + PERSONAS, index=0, key="task_persona")
        t_titulo = st.text_input("Título de la tarea", key="task_titulo")
        t_due = st.date_input("Vence (opcional)", value=default_date, key="task_due")
        if st.button("➕ Agregar tarea"):
            if not t_titulo.strip():
                st.warning("Poné un título para la tarea.")
            else:
                if tasks.empty or "id" not in tasks.columns:
                    new_id = 1
                else:
                    _ids = pd.to_numeric(tasks["id"], errors="coerce")
                    new_id = (int(_ids.max()) if _ids.notna().any() else 0) + 1

                row = {"id":new_id,"Fecha":t_fecha,"Turno":t_turno if t_turno else "","Persona":t_persona if t_persona else "",
                       "Titulo":t_titulo.strip(),"Estado":"Pendiente","Due":t_due if t_due else pd.NaT,
                       "CreatedAt":dt.datetime.now().isoformat(timespec="seconds")}
                tasks = pd.concat([tasks, pd.DataFrame([row])], ignore_index=True)
                save_tasks(tasks); st.success("Tarea agregada."); st.rerun()

    with c_list:
        st.markdown("**Tareas del mes**")
        if tasks.empty:
            st.info("No hay tareas.")
        else:
            mask = (pd.to_datetime(tasks["Fecha"]).dt.date>=first) & (pd.to_datetime(tasks["Fecha"]).dt.date<=last)
            tshow = tasks[mask].sort_values(["Fecha","Turno","Persona","Estado","id"]).copy()
            for _, r in tshow.iterrows():
                c1,c2,c3,c4,c5 = st.columns([2,2,4,2,1])
                with c1: st.caption(r["Fecha"])
                with c2: st.caption(r["Turno"] if r["Turno"] else "—")
                with c3: st.write(f"**{r['Titulo']}**  —  {r['Persona'] if r['Persona'] else 'Sin asignar'}")
                with c4:
                    done = (r["Estado"]=="Hecho")
                    if st.checkbox("Hecha", value=done, key=f"task_done_{int(r['id'])}"):
                        tasks.loc[tasks["id"]==r["id"], "Estado"] = "Hecho"; save_tasks(tasks)
                with c5:
                    if st.button("🗑️", key=f"task_del_{int(r['id'])}"):
                        tasks = tasks[tasks["id"]!=r["id"]]; save_tasks(tasks); st.rerun()

# ================== FICHADAS (Ingreso/Salida) ==================
with tab_clock:
    st.subheader("⏱️ Fichadas (Ingreso / Salida)")

    timelog = st.session_state.timelog if "timelog" in st.session_state else load_timelog()
    # 🔒 normalizar tipos siempre antes de operar
    if not timelog.empty:
        timelog["Timestamp"] = pd.to_datetime(timelog["Timestamp"], errors="coerce")

    cal_all = st.session_state.cal

    csel, cdate = st.columns([2,1])
    with csel:
        emp = st.selectbox("Empleado", PERSONAS, index=0, key="clock_emp")
    with cdate:
        fch = st.date_input("Fecha", value=dt.date.today(), key="clock_date")

    # Turnos planificados para ese empleado en esa fecha (si los hay)
    plan = cal_all[(cal_all["Fecha"]==fch) & ((cal_all["Persona A"]==emp) | (cal_all["Persona B"]==emp))]
    turnos_plan = ", ".join(plan["Turno"].tolist()) if not plan.empty else "—"
    st.caption(f"Turnos planificados ese día: **{turnos_plan}**")

    # Estado actual del día (último evento)
    day_logs = timelog[(timelog["Persona"]==emp) & (timelog["Fecha"]==fch)].sort_values(
        "Timestamp", na_position="last"
    )
    last_type = day_logs.iloc[-1]["Tipo"] if not day_logs.empty else None
    can_in  = (last_type != "Ingreso")   # si el último no fue "Ingreso", se puede ingresar
    can_out = (last_type == "Ingreso")   # si el último fue "Ingreso", corresponde salida

    cbtn1, cbtn2 = st.columns([1,1])
    now = dt.datetime.now()

    with cbtn1:
        if can_in:
            if st.button("🟢 Marcar ingreso"):
                append_timelog({
                    "Fecha": fch, "Persona": emp, "Tipo": "Ingreso",
                    "Timestamp": now,
                    "Turno": turnos_plan, "Fuente": "boton"
                })
                st.success(f"Ingreso registrado {now.strftime('%H:%M')}.")
                st.rerun()
        else:
            st.info("Ya hay un ingreso pendiente de salida.")

    with cbtn2:
        if can_out:
            if st.button("🔴 Marcar salida"):
                append_timelog({
                    "Fecha": fch, "Persona": emp, "Tipo": "Salida",
                    "Timestamp": now,
                    "Turno": turnos_plan, "Fuente": "boton"
                })
                st.success(f"Salida registrada {now.strftime('%H:%M')}.")
                st.rerun()
        else:
            st.caption("Esperando ingreso o ya cerró el ciclo.")

    # Mostrar fichadas del día y duración (suma de todos los pares Ingreso→Salida)
    st.markdown("---")
    st.markdown("**Fichadas del día**")

    def _sumar_intervalos(logs: pd.DataFrame, time_col: str = "Timestamp") -> pd.Timedelta:
        """Suma pares Ingreso→Salida ordenados por time_col."""
        if logs.empty:
            return pd.Timedelta(0)
        logs = logs.sort_values(time_col)
        total = pd.Timedelta(0)
        current_in = None
        for _, r in logs.iterrows():
            ts = r[time_col]
            if r["Tipo"] == "Ingreso":
                current_in = ts
            elif r["Tipo"] == "Salida" and current_in is not None:
                if pd.notna(ts) and pd.notna(current_in) and ts > current_in:
                    total += (ts - current_in)
                current_in = None
        return total

    if day_logs.empty:
        st.caption("No hay fichadas.")
    else:
        show = day_logs.copy()
        show["Hora"] = pd.to_datetime(show["Timestamp"]).dt.strftime("%H:%M")
        st.dataframe(show[["Hora","Tipo","Turno","Fuente"]], use_container_width=True, hide_index=True)

        total_td = _sumar_intervalos(day_logs, time_col="Timestamp")
        if total_td.total_seconds() > 0:
            h = int(total_td.total_seconds()//3600)
            m = int((total_td.total_seconds()%3600)//60)
            st.success(f"Total trabajado en el día: **{h:02d}h {m:02d}m**")
        else:
            st.caption("Aún no hay pares Ingreso→Salida completos.")

    # Resumen mensual (suma de intervalos por persona y fecha)
    st.markdown("---")
    st.markdown("**Resumen mensual (horas por persona)**")
    month_logs = timelog[(timelog["Fecha"]>=first) & (timelog["Fecha"]<=last)].copy()
    if month_logs.empty:
        st.caption("No hay fichadas en el mes.")
    else:
        # usar columna 'ts' para evitar duplicar nombre con 'Timestamp'
        month_logs["ts"] = pd.to_datetime(month_logs["Timestamp"], errors="coerce")
        resumen = []
        for (p, d), g in month_logs.groupby(["Persona","Fecha"]):
            total_td = _sumar_intervalos(g, time_col="ts")
            if total_td.total_seconds() > 0:
                resumen.append({"Persona":p,"Fecha":d,"Horas":round(total_td.total_seconds()/3600.0,2)})
        if resumen:
            dfres = pd.DataFrame(resumen)
            byp = dfres.groupby("Persona", as_index=False)["Horas"].sum().sort_values("Horas", ascending=False)
            st.dataframe(byp, use_container_width=True, hide_index=True)
        else:
            st.caption("Aún no hay días completos (ingreso y salida) para calcular.")

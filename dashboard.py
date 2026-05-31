import streamlit as st
import pandas as pd
import plotly.express as px

# ─────────────────────────────────────────────
# ⚙️ SEITEN-KONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="KPI Dashboard",
    page_icon="📊",
    layout="wide"
)

# ─────────────────────────────────────────────
# 📁 DATEN LADEN
# ─────────────────────────────────────────────
def load_data():
    df = pd.read_excel(
        "Liste_Aufgabe 2026 fuer KPis.xlsx",
        sheet_name="2026",
        header=0
    )
    df.columns = df.columns.str.strip()
    df["Eingang"]     = pd.to_datetime(df["Eingang"],     errors="coerce")
    df["Lieferdatum"] = pd.to_datetime(df["Lieferdatum"], errors="coerce")
    df["Deadline"]    = pd.to_datetime(df["Deadline"],    errors="coerce")
    df["Monat"]       = df["Eingang"].dt.to_period("M").astype(str)
    df["Dringend"]    = df["Dringend"].fillna(0).astype(int)
    df["Eingehalten?"] = df["Eingehalten?"].astype(str).str.replace("✅", "").str.replace("❌", "").str.strip()
    return df

df = load_data()

# ─────────────────────────────────────────────
# 🎛️ SEITENLEISTE – FILTER
# ─────────────────────────────────────────────
st.sidebar.title("🎛️ Filter")

abteilungen = ["Alle"] + sorted(df["Abteilung"].dropna().unique().tolist())
abt_filter = st.sidebar.selectbox("Abteilung", abteilungen)

dringend_filter = st.sidebar.radio("Dringend", ["Alle", "Ja", "Nein"])

min_datum = df["Eingang"].min().date()
max_datum = df["Eingang"].max().date()
datum_range = st.sidebar.date_input(
    "Zeitraum",
    value=(min_datum, max_datum),
    min_value=min_datum,
    max_value=max_datum
)

# ─────────────────────────────────────────────
# 🔍 FILTER ANWENDEN
# ─────────────────────────────────────────────
df_filtered = df.copy()

if abt_filter != "Alle":
    df_filtered = df_filtered[df_filtered["Abteilung"] == abt_filter]

if dringend_filter == "Ja":
    df_filtered = df_filtered[df_filtered["Dringend"] == 1]
elif dringend_filter == "Nein":
    df_filtered = df_filtered[df_filtered["Dringend"] == 0]

if len(datum_range) == 2:
    df_filtered = df_filtered[
        (df_filtered["Eingang"].dt.date >= datum_range[0]) &
        (df_filtered["Eingang"].dt.date <= datum_range[1])
    ]

# ─────────────────────────────────────────────
# 🧮 KPIs BERECHNEN
# ─────────────────────────────────────────────
total_auftraege     = len(df_filtered)
puenktlich          = df_filtered["Eingehalten?"].str.lower() == "ja"
puenktlichkeitsrate = puenktlich.sum() / total_auftraege * 100 if total_auftraege > 0 else 0
zu_spaet            = (~puenktlich).sum()
dringend_anz        = (df_filtered["Dringend"] == 1).sum()

df_filtered = df_filtered.copy()
df_filtered["Durchlaufzeit_h"] = (
    df_filtered["Lieferdatum"] - df_filtered["Eingang"]
).dt.total_seconds() / 3600
avg_bearbeitungszeit = df_filtered["Durchlaufzeit_h"].mean()

# ─────────────────────────────────────────────
# 🏠 TITEL
# ─────────────────────

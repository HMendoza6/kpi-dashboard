
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
        header=0  # Zeile 0 = Spaltennamen
    )
    df.columns = df.columns.str.strip()
    df["Eingang"]     = pd.to_datetime(df["Eingang"],     errors="coerce")
    df["Lieferdatum"] = pd.to_datetime(df["Lieferdatum"], errors="coerce")
    df["Deadline"]    = pd.to_datetime(df["Deadline"],    errors="coerce")
    df["Monat"]       = df["Eingang"].dt.to_period("M").astype(str)

    # Dringend: 1 = Ja, 0 = Nein
    df["Dringend"] = df["Dringend"].fillna(0).astype(int)

    # Eingehalten?: ✅ Ja / ❌ Nein → normalisieren
    df["Eingehalten?"] = df["Eingehalten?"].astype(str).str.replace("✅", "").str.replace("❌", "").str.strip()

    return df

df = load_data()

# ─────────────────────────────────────────────
# 🎛️ SEITENLEISTE – FILTER
# ─────────────────────────────────────────────
st.sidebar.title("🎛️ Filter")

# Abteilung
abteilungen = ["Alle"] + sorted(df["Abteilung"].dropna().unique().tolist())
abt_filter = st.sidebar.selectbox("Abteilung", abteilungen)

# Dringend
dringend_filter = st.sidebar.radio("Dringend", ["Alle", "Ja", "Nein"])

# Zeitraum
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
# ─────────────────────────────────────────────
st.title("📊 KPI Dashboard – Mein Team")
st.markdown("---")

# ─────────────────────────────────────────────
# 📌 ZEILE 1 – KPI KARTEN
# ─────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("📦 Aufträge gesamt",     total_auftraege)
k2.metric("✅ Pünktlichkeitsrate",  f"{puenktlichkeitsrate:.1f}%")
k3.metric("❌ Zu spät geliefert",   int(zu_spaet))
k4.metric("⏱️ Ø Bearbeitungszeit", f"{avg_bearbeitungszeit:.1f}h")
k5.metric("🚨 Dringende Aufträge",  int(dringend_anz))

st.markdown("---")

# ─────────────────────────────────────────────
# 📊 ZEILE 2 – DIAGRAMME OBEN
# ─────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("📅 Aufträge pro Monat")
    auftraege_monat = df_filtered.groupby("Monat")["Auftragsname"].count().reset_index()
    auftraege_monat.columns = ["Monat", "Anzahl"]
    fig1 = px.bar(auftraege_monat, x="Monat", y="Anzahl",
                  color_discrete_sequence=["#4C9BE8"])
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("🏢 Wörter pro Abteilung")
    woerter_abt = df_filtered.groupby("Abteilung")["Wörter"].sum().reset_index()
    fig2 = px.bar(woerter_abt, x="Abteilung", y="Wörter",
                  color_discrete_sequence=["#56C596"])
    st.plotly_chart(fig2, use_container_width=True)

# ─────────────────────────────────────────────
# 📊 ZEILE 3 – DIAGRAMME UNTEN
# ─────────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("🕐 Stunden pro Abteilung")
    stunden_abt = df_filtered.groupby("Abteilung")["Stunden"].sum().reset_index()
    fig3 = px.pie(stunden_abt, names="Abteilung", values="Stunden",
                  color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("✅ Pünktlich vs. ❌ Zu spät")
    status_data = pd.DataFrame({
        "Status": ["Pünktlich", "Zu spät"],
        "Anzahl": [int(puenktlich.sum()), int(zu_spaet)]
    })
    fig4 = px.pie(status_data, names="Status", values="Anzahl",
                  color_discrete_sequence=["#56C596", "#E8604C"])
    st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# ─────────────────────────────────────────────
# 👤 ZEILE 4 – PRODUKTIVITÄT PRO MITARBEITER
# ─────────────────────────────────────────────
st.subheader("👤 Produktivität pro Mitarbeiter")

produktivitaet = df_filtered.groupby("Translator").agg(
    Aufträge      = ("Auftragsname", "count"),
    Gesamtwörter  = ("Wörter", "sum"),
    Gesamtstunden = ("Stunden", "sum")
).reset_index()

produktivitaet["Wörter_pro_Stunde"] = (
    produktivitaet["Gesamtwörter"] / produktivitaet["Gesamtstunden"]
).round(1)

fig5 = px.bar(produktivitaet, x="Translator", y="Wörter_pro_Stunde",
              color="Translator", title="Wörter pro Stunde je Mitarbeiter")
st.plotly_chart(fig5, use_container_width=True)

st.markdown("---")

# ─────────────────────────────────────────────
# 🔁 ZEILE 5 – WIEDERHOLUNGSRATE PRO ABTEILUNG
# ─────────────────────────────────────────────
st.subheader("🔁 Wiederholungsrate pro Abteilung")

wiederholungen = df_filtered[
    df_filtered.duplicated(subset=["Auftragsname", "Abteilung"], keep=False)
]
total_abt   = df_filtered.groupby("Abteilung")["Auftragsname"].count()
wieder_abt  = wiederholungen.groupby("Abteilung")["Auftragsname"].count()
wieder_rate = (wieder_abt / total_abt * 100).fillna(0).reset_index()
wieder_rate.columns = ["Abteilung", "Wiederholungsrate (%)"]

fig6 = px.bar(wieder_rate, x="Abteilung", y="Wiederholungsrate (%)",
              color_discrete_sequence=["#F4A261"])
st.plotly_chart(fig6, use_container_width=True)

st.markdown("---")

# ─────────────────────────────────────────────
# 📋 ZEILE 6 – ROHDATEN TABELLE
# ─────────────────────────────────────────────
st.subheader("📋 Rohdaten")
st.dataframe(df_filtered, use_container_width=True)

st.markdown("---")

# ─────────────────────────────────────────────
# 💾 EXPORT
# ─────────────────────────────────────────────
st.subheader("💾 Bericht exportieren")

@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode("utf-8")

csv = convert_df(df_filtered)
st.download_button(
    label="⬇️ CSV herunterladen",
    data=csv,
    file_name="KPI_Bericht.csv",
    mime="text/csv"
)

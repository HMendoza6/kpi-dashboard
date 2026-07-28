import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ─────────────────────────────────────────────
# ⚙️ SEITEN-KONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="KPI Dashboard – Language Services",
    page_icon="📊",
    layout="wide"
)

# ─────────────────────────────────────────────
# 📁 DATEN LADEN 2026
# ─────────────────────────────────────────────
def load_data_2026():
    df = pd.read_excel(
        "Liste_Aufgabe 2026 fuer KPis.xlsx",
        sheet_name="2026",
        header=0
    )
    df.columns = df.columns.str.strip()
    df["Eingang"]      = pd.to_datetime(df["Eingang"],      errors="coerce")
    df["Lieferdatum"]  = pd.to_datetime(df["Lieferdatum"],  errors="coerce")
    df["Deadline"]     = pd.to_datetime(df["Deadline"],     errors="coerce")
    df["Monat"]        = df["Eingang"].dt.strftime("%Y-%m")
    df["Dringend"]     = df["Dringend"].fillna(0).astype(int)
    df["Eingehalten?"] = df["Eingehalten?"].astype(str).str.replace("✅", "").str.replace("❌", "").str.strip()
    df["Jahr"]         = "2026"
    return df

# ─────────────────────────────────────────────
# 📁 DATEN LADEN 2025
# ─────────────────────────────────────────────
def load_data_2025():
    df = pd.read_excel(
        "Liste_Aufgabe 2025 fuer KPis.xlsx",
        sheet_name="2025",
        header=0
    )
    df.columns = df.columns.str.strip()
    df["Datum"]     = pd.to_datetime(df["Datum"],     errors="coerce")
    df["Lieferung"] = pd.to_datetime(df["Lieferung"], errors="coerce")
    df["Deadline"]  = pd.to_datetime(df["Deadline"],  errors="coerce")
    df["Monat"]     = df["Datum"].dt.strftime("%Y-%m")
    df["Jahr"]      = "2025"
    df = df.rename(columns={
        "Aufträge"       : "Auftragsname",
        "Datum"          : "Eingang",
        "Lieferung"      : "Lieferdatum",
        "Verantwortlich" : "Verantwörtlich"
    })
    return df

df_2026 = load_data_2026()
df_2025 = load_data_2025()

# ─────────────────────────────────────────────
# 🎛️ SEITENLEISTE – NAVIGATION
# ─────────────────────────────────────────────
st.sidebar.title("🎛️ Navigation")

seite = st.sidebar.radio(
    "Seite auswählen:",
    ["📊 KPI Dashboard 2026", "📈 Jahresvergleich 2025 vs 2026"]
)

st.sidebar.markdown("---")

# ─────────────────────────────────────────────
# 📊 SEITE 1 – KPI DASHBOARD 2026
# ─────────────────────────────────────────────
if seite == "📊 KPI Dashboard 2026":

    # Filter
    st.sidebar.title("🎛️ Filter")

    abteilungen = ["Alle"] + sorted(df_2026["Abteilung"].dropna().unique().tolist())
    abt_filter = st.sidebar.selectbox("Abteilung", abteilungen)

    kanäle = ["Alle"] + sorted(df_2026["Kanal"].dropna().unique().tolist())
    kanal_filter = st.sidebar.selectbox("Kanal", kanäle)

    min_datum = df_2026["Eingang"].min().date()
    max_datum = df_2026["Eingang"].max().date()
    datum_range = st.sidebar.date_input(
        "Zeitraum 2026",
        value=(min_datum, max_datum),
        min_value=min_datum,
        max_value=max_datum
    )

    # Filter anwenden
    df_filtered = df_2026.copy()

    if abt_filter != "Alle":
        df_filtered = df_filtered[df_filtered["Abteilung"] == abt_filter]

    if kanal_filter != "Alle":
        df_filtered = df_filtered[df_filtered["Kanal"] == kanal_filter]

    if len(datum_range) == 2:
        df_filtered = df_filtered[
            (df_filtered["Eingang"].dt.date >= datum_range[0]) &
            (df_filtered["Eingang"].dt.date <= datum_range[1])
        ]

    # KPIs berechnen
    total_auftraege      = len(df_filtered)
    puenktlich           = df_filtered["Eingehalten?"].str.lower() == "ja"
    puenktlichkeitsrate  = puenktlich.sum() / total_auftraege * 100 if total_auftraege > 0 else 0
    zu_spaet             = (~puenktlich).sum()
    verzoegerungsrate    = zu_spaet / total_auftraege * 100 if total_auftraege > 0 else 0
    vor_deadline_kpi     = (df_filtered["Lieferdatum"] < df_filtered["Deadline"]).sum()
    vor_deadline_rate    = vor_deadline_kpi / total_auftraege * 100 if total_auftraege > 0 else 0
    dringend_anz         = (df_filtered["Dringend"] == 1).sum()

    df_filtered = df_filtered.copy()
    df_filtered["Durchlaufzeit_h"] = (
        df_filtered["Lieferdatum"] - df_filtered["Eingang"]
    ).dt.total_seconds() / 3600

    # Titel
    st.title("📊 KPI Dashboard – TCO-Language Services")
    stand = datetime.today().strftime("%d.%m.%Y")
    st.markdown(f"📅 **Stand: {stand}**")
    st.markdown("---")

    # KPI Karten
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📦 Aufträge gesamt",        total_auftraege)
    k2.metric("✅ Pünktlichkeitsrate",     f"{puenktlichkeitsrate:.1f}%")
    k3.metric("🎯 Vor Deadline geliefert", f"{vor_deadline_rate:.1f}%")
    k4.metric("📉 Verzögerungsrate",       f"{verzoegerungsrate:.1f}%")
    k5.metric("🚨 Dringende Aufträge",     int(dringend_anz))

    st.markdown("---")

    # Diagramme Zeile 2
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📅 Aufträge pro Monat 2026")
        df_2026_filtered = df_filtered[df_filtered["Eingang"].dt.year == 2026]
        auftraege_monat = df_2026_filtered.groupby("Monat")["Auftragsname"].count().reset_index()
        auftraege_monat.columns = ["Monat", "Anzahl"]
        auftraege_monat = auftraege_monat.sort_values("Monat")
        fig1 = px.bar(auftraege_monat, x="Monat", y="Anzahl",
                      color_discrete_sequence=["#4C9BE8"],
                      category_orders={"Monat": sorted(auftraege_monat["Monat"].tolist())})
        fig1.update_xaxes(type="category")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("🏢 Aufträge pro Abteilung")
        auftraege_abt = df_filtered.groupby("Abteilung")["Auftragsname"].count().reset_index()
        auftraege_abt.columns = ["Abteilung", "Anzahl"]
        fig2 = px.bar(auftraege_abt, x="Abteilung", y="Anzahl",
                      color_discrete_sequence=["#56C596"])
        st.plotly_chart(fig2, use_container_width=True)

    # Diagramme Zeile 3
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("📬 Anzahl Aufträge pro Kanal")
        auftraege_kanal = df_filtered.groupby("Kanal")["Auftragsname"].count().reset_index()
        auftraege_kanal.columns = ["Kanal", "Anzahl"]
        fig3 = px.pie(auftraege_kanal, names="Kanal", values="Anzahl",
                      color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.subheader("✅ Lieferstatus")
        vor_deadline   = (df_filtered["Lieferdatum"] < df_filtered["Deadline"]).sum()
        puenktlich_anz = (df_filtered["Lieferdatum"] == df_filtered["Deadline"]).sum()
        zu_spaet_anz   = (df_filtered["Lieferdatum"] > df_filtered["Deadline"]).sum()

        status_data = pd.DataFrame({
            "Status": ["Vor Deadline", "Pünktlich", "Zu spät"],
            "Anzahl": [int(vor_deadline), int(puenktlich_anz), int(zu_spaet_anz)]
        })
        fig4 = px.pie(status_data, names="Status", values="Anzahl",
                      color_discrete_sequence=["#4C9BE8", "#56C596", "#E8604C"])
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")

    # Aufträge pro Sprache
    st.subheader("🌍 Anzahl Aufträge pro Sprache")
    auftraege_sprache = df_filtered.groupby("Sprache").agg(
        Aufträge = ("Auftragsname", "count")
    ).reset_index()
    fig5 = px.bar(auftraege_sprache, x="Sprache", y="Aufträge",
                  color="Sprache", title="Anzahl Aufträge pro Sprache")
    st.plotly_chart(fig5, use_container_width=True)

    st.markdown("---")

    # Rohdaten
    st.subheader("📋 Rohdaten 2026")
    st.dataframe(df_filtered, use_container_width=True)

    st.markdown("---")

    # Export
    st.subheader("💾 Bericht exportieren")

    def convert_df(df):
        return df.to_csv(index=False).encode("utf-8")

    csv = convert_df(df_filtered)
    st.download_button(
        label="⬇️ CSV herunterladen",
        data=csv,
        file_name="KPI_Bericht_2026.csv",
        mime="text/csv"
    )

# ─────────────────────────────────────────────
# 📈 SEITE 2 – JAHRESVERGLEICH 2025 VS 2026
# ─────────────────────────────────────────────
elif seite == "📈 Jahresvergleich 2025 vs 2026":

    st.title("📈 Jahresvergleich 2025 vs 2026")
    stand = datetime.today().strftime("%d.%m.%Y")
    st.markdown(f"📅 **Stand: {stand}**")
    st.markdown("---")

    # Aufträge gesamt Vergleich
    total_2025 = len(df_2025)
    total_2026 = len(df_2026)

    v1, v2 = st.columns(2)
    v1.metric("📦 Aufträge 2025", total_2025)
    v2.metric("📦 Aufträge 2026", total_2026,
              delta=f"{total_2026 - total_2025:+d}")

    st.markdown("---")

    # Sprachen Vergleich
    col5, col6 = st.columns(2)

    with col5:
        st.subheader("🌍 Sprachen 2025")
        sprachen_2025 = df_2025.groupby("Sprache")["Auftragsname"].count().reset_index()
        sprachen_2025.columns = ["Sprache", "Anzahl"]
        sprachen_2025 = sprachen_2025.sort_values("Anzahl", ascending=False)
        fig6 = px.bar(sprachen_2025, x="Sprache", y="Anzahl",
                      color="Sprache", title="Aufträge pro Sprache 2025")
        st.plotly_chart(fig6, use_container_width=True)

    with col6:
        st.subheader("🌍 Sprachen 2026")
        sprachen_2026 = df_2026.groupby("Sprache")["Auftragsname"].count().reset_index()
        sprachen_2026.columns = ["Sprache", "Anzahl"]
        sprachen_2026 = sprachen_2026.sort_values("Anzahl", ascending=False)
        fig7 = px.bar(sprachen_2026, x="Sprache", y="Anzahl",
                      color="Sprache", title="Aufträge pro Sprache 2026")
        st.plotly_chart(fig7, use_container_width=True)

    st.markdown("---")

    # Abteilungen Vergleich
    col7, col8 = st.columns(2)

    with col7:
        st.subheader("🏢 Abteilungen 2025")
        abt_2025 = df_2025.groupby("Abteilung")["Auftragsname"].count().reset_index()
        abt_2025.columns = ["Abteilung", "Anzahl"]
        fig8 = px.bar(abt_2025, x="Abteilung", y="Anzahl",
                      color_discrete_sequence=["#F4A261"],
                      title="Aufträge pro Abteilung 2025")
        st.plotly_chart(fig8, use_container_width=True)

    with col8:
        st.subheader("🏢 Abteilungen 2026")
        abt_2026 = df_2026.groupby("Abteilung")["Auftragsname"].count().reset_index()
        abt_2026.columns = ["Abteilung", "Anzahl"]
        fig9 = px.bar(abt_2026, x="Abteilung", y="Anzahl",
                      color_discrete_sequence=["#56C596"],
                      title="Aufträge pro Abteilung 2026")
        st.plotly_chart(fig9, use_container_width=True)

    st.markdown("---")

    # Monatsvergleich
    st.subheader("📅 Aufträge pro Monat – 2025 vs 2026")

    monat_2025 = df_2025.groupby("Monat")["Auftragsname"].count().reset_index()
    monat_2025.columns = ["Monat", "Anzahl"]
    monat_2025["Jahr"] = "2025"

    monat_2026 = df_2026.groupby("Monat")["Auftragsname"].count().reset_index()
    monat_2026.columns = ["Monat", "Anzahl"]
    monat_2026["Jahr"] = "2026"

    monat_vergleich = pd.concat([monat_2025, monat_2026])
    monat_vergleich["Monat_kurz"] = monat_vergleich["Monat"].str[-2:]

    fig10 = px.bar(monat_vergleich, x="Monat_kurz", y="Anzahl",
                   color="Jahr", barmode="group",
                   title="Aufträge pro Monat 2025 vs 2026",
                   color_discrete_sequence=["#F4A261", "#4C9BE8"])
    st.plotly_chart(fig10, use_container_width=True)
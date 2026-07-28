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

# ─────────────────────────────────────────────
# 📁 DATEN LADEN KOSTEN 2025
# ─────────────────────────────────────────────
# NEU ✅
def load_kosten_2025():
    df = pd.read_excel(
        "Ueberblick_LS.xlsx",
        sheet_name="2025",
        header=0
    )
    df.columns = df.columns.str.strip()
    # Leere Zeilen entfernen
    df = df.dropna(subset=["Datum"])
    df = df[df["Datum"].astype(str).str.strip() != ""]
    df["Datum"] = pd.to_datetime(df["Datum"], errors="coerce")
    df = df.dropna(subset=["Datum"])
    df["Monat"] = df["Datum"].dt.strftime("%Y-%m")
    df["Jahr"]  = "2025"
    sprachen_2025 = ["EN", "IT", "ES", "NL", "PL", "PT", "CZ", "SL"]
    for s in sprachen_2025:
        if s in df.columns:
            df[s] = pd.to_numeric(df[s], errors="coerce").fillna(0)
    return df

# ─────────────────────────────────────────────
# 📁 DATEN LADEN KOSTEN 2026
# ─────────────────────────────────────────────
def load_kosten_2026():
    df = pd.read_excel(
        "Ueberblick_LS.xlsx",
        sheet_name="2026",
        header=0
    )
    df.columns = df.columns.str.strip()
    df["Datum"] = pd.to_datetime(df["Datum"], errors="coerce")
    df["Monat"] = df["Datum"].dt.strftime("%Y-%m")
    df["Jahr"]  = "2026"
    df = df.rename(columns={"Bereich": "Abteilung"})
    sprachen_2026 = ["EN", "IT", "ES", "NL", "PL", "PT", "CZ", "SL",
                     "SV", "FI", "NW", "DA", "GR"]
    for s in sprachen_2026:
        if s in df.columns:
            df[s] = pd.to_numeric(df[s], errors="coerce").fillna(0)
    return df

df_2026     = load_data_2026()
df_2025     = load_data_2025()
kosten_2025 = load_kosten_2025()
kosten_2026 = load_kosten_2026()

# ─────────────────────────────────────────────
# 🎛️ SEITENLEISTE – NAVIGATION
# ─────────────────────────────────────────────
st.sidebar.title("🎛️ Navigation")

seite = st.sidebar.radio(
    "Seite auswählen:",
    [
        "📊 KPI Dashboard 2026",
        "📈 Jahresvergleich 2025 vs 2026",
        "💰 Kosten Übersicht"
    ]
)

st.sidebar.markdown("---")

# ─────────────────────────────────────────────
# 📊 SEITE 1 – KPI DASHBOARD 2026
# ─────────────────────────────────────────────
if seite == "📊 KPI Dashboard 2026":

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

    st.title("📊 KPI Dashboard – TCO-Language Services")
    stand = datetime.today().strftime("%d.%m.%Y")
    st.markdown(f"📅 **Stand: {stand}**")
    st.markdown("---")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📦 Aufträge gesamt",        total_auftraege)
    k2.metric("✅ Pünktlichkeitsrate",     f"{puenktlichkeitsrate:.1f}%")
    k3.metric("🎯 Vor Deadline geliefert", f"{vor_deadline_rate:.1f}%")
    k4.metric("📉 Verzögerungsrate",       f"{verzoegerungsrate:.1f}%")
    k5.metric("🚨 Dringende Aufträge",     int(dringend_anz))

    st.markdown("---")

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

    st.subheader("🌍 Anzahl Aufträge pro Sprache")
    auftraege_sprache = df_filtered.groupby("Sprache").agg(
        Aufträge = ("Auftragsname", "count")
    ).reset_index()
    fig5 = px.bar(auftraege_sprache, x="Sprache", y="Aufträge",
                  color="Sprache", title="Anzahl Aufträge pro Sprache")
    st.plotly_chart(fig5, use_container_width=True)

    st.markdown("---")

    st.subheader("📋 Rohdaten 2026")
    st.dataframe(df_filtered, use_container_width=True)

    st.markdown("---")

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

    total_2025 = len(df_2025)
    total_2026 = len(df_2026)

    v1, v2 = st.columns(2)
    v1.metric("📦 Aufträge 2025", total_2025)
    v2.metric("📦 Aufträge 2026", total_2026,
              delta=f"{total_2026 - total_2025:+d}")

    st.markdown("---")

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

# ─────────────────────────────────────────────
# 💰 SEITE 3 – KOSTEN ÜBERSICHT
# ─────────────────────────────────────────────
elif seite == "💰 Kosten Übersicht":

    st.title("💰 Kosten Übersicht – TCO-Language Services")
    stand = datetime.today().strftime("%d.%m.%Y")
    st.markdown(f"📅 **Stand: {stand}**")
    st.markdown("---")

    jahr_filter = st.sidebar.radio("Jahr", ["2026", "2025", "2025 vs 2026"])
    st.sidebar.markdown("---")

    if jahr_filter == "2026":
        kosten_df = kosten_2026.copy()
        sprachen  = ["EN", "IT", "ES", "NL", "PL", "PT", "CZ", "SL",
                     "SV", "FI", "NW", "DA", "GR"]
    elif jahr_filter == "2025":
        kosten_df = kosten_2025.copy()
        sprachen  = ["EN", "IT", "ES", "NL", "PL", "PT", "CZ", "SL"]
    else:
        kosten_2025_copy = kosten_2025.copy()
        kosten_2026_copy = kosten_2026.copy()
        kosten_df = pd.concat([kosten_2025_copy, kosten_2026_copy])
        sprachen  = ["EN", "IT", "ES", "NL", "PL", "PT", "CZ", "SL"]

    sprachen = [s for s in sprachen if s in kosten_df.columns]

    # ── Gesamtkosten KPI ──
    kosten_df["Gesamt"] = kosten_df[sprachen].sum(axis=1)
    gesamtkosten = kosten_df["Gesamt"].sum()

    st.metric("💰 Gesamtkosten", f"{gesamtkosten:,.2f} €")

    st.markdown("---")

    # ── Kosten pro Sprache ──
    st.subheader(f"🌍 Kosten pro Sprache – {jahr_filter}")

    kosten_sprache = kosten_df[sprachen].sum().reset_index()
    kosten_sprache.columns = ["Sprache", "Kosten (€)"]
    kosten_sprache = kosten_sprache[kosten_sprache["Kosten (€)"] > 0]
    kosten_sprache = kosten_sprache.sort_values("Kosten (€)", ascending=False)

    fig11 = px.bar(kosten_sprache, x="Sprache", y="Kosten (€)",
                   color="Sprache",
                   title=f"Kosten pro Sprache – {jahr_filter}")
    st.plotly_chart(fig11, use_container_width=True)

    st.markdown("---")

    # ── Kosten pro Abteilung ──
    st.subheader(f"🏢 Kosten pro Abteilung – {jahr_filter}")

    kosten_abt = kosten_df.groupby("Abteilung")["Gesamt"].sum().reset_index()
    kosten_abt.columns = ["Abteilung", "Kosten (€)"]
    kosten_abt = kosten_abt[kosten_abt["Kosten (€)"] > 0]
    kosten_abt = kosten_abt.sort_values("Kosten (€)", ascending=False)

    fig12 = px.bar(kosten_abt, x="Abteilung", y="Kosten (€)",
                   color_discrete_sequence=["#56C596"],
                   title=f"Kosten pro Abteilung – {jahr_filter}")
    st.plotly_chart(fig12, use_container_width=True)

    st.markdown("---")

    # ── Kosten pro Monat ──
    st.subheader(f"📅 Kosten pro Monat – {jahr_filter}")

    kosten_monat = kosten_df.groupby(["Monat", "Jahr"])["Gesamt"].sum().reset_index()
    kosten_monat.columns = ["Monat", "Jahr", "Kosten (€)"]
    kosten_monat["Monat_kurz"] = kosten_monat["Monat"].str[-2:]
    kosten_monat = kosten_monat.sort_values("Monat")

    if jahr_filter == "2025 vs 2026":
        fig13 = px.bar(kosten_monat, x="Monat_kurz", y="Kosten (€)",
                       color="Jahr", barmode="group",
                       title="Kosten pro Monat 2025 vs 2026",
                       color_discrete_sequence=["#F4A261", "#4C9BE8"])
    else:
        fig13 = px.bar(kosten_monat, x="Monat_kurz", y="Kosten (€)",
                       color_discrete_sequence=["#4C9BE8"],
                       title=f"Kosten pro Monat – {jahr_filter}")

    fig13.update_xaxes(type="category")
    st.plotly_chart(fig13, use_container_width=True)

    st.markdown("---")

    # ── Kosten pro Übersetzer ──
    st.subheader(f"👤 Kosten pro Übersetzer – {jahr_filter}")

    kosten_uebersetzer = kosten_df.groupby("Übersetzer")["Gesamt"].sum().reset_index()
    kosten_uebersetzer.columns = ["Übersetzer", "Kosten (€)"]
    kosten_uebersetzer = kosten_uebersetzer[kosten_uebersetzer["Kosten (€)"] > 0]
    kosten_uebersetzer = kosten_uebersetzer.sort_values("Kosten (€)", ascending=False)

    fig14 = px.bar(kosten_uebersetzer, x="Übersetzer", y="Kosten (€)",
                   color="Übersetzer",
                   title=f"Kosten pro Übersetzer – {jahr_filter}")
    st.plotly_chart(fig14, use_container_width=True)

    st.markdown("---")

    # ── Rohdaten ──
    st.subheader("📋 Rohdaten Kosten")
    st.dataframe(kosten_df, use_container_width=True)
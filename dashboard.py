from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# KONFIGURATION
# ============================================================
st.set_page_config(
    page_title="KPI Dashboard - Language Services",
    page_icon="📊",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
FILE_2026 = BASE_DIR / "Liste_Aufgabe Doku_UeM_NEU-2026(2026).csv"
FILE_2025 = BASE_DIR / "Liste_Aufgabe 2025 fuer KPis.xlsx"
FILE_COSTS = BASE_DIR / "Ueberblick_LS.xlsx"

STANDARD_ORDER_COLUMNS = [
    "Auftragsname", "Auftraggeber", "Abteilung", "Auftragstyp", "Sprache",
    "Wörter", "Stunden", "Dringend", "Kanal", "Eingang", "Lieferdatum",
    "Durchlaufzeit", "Deadline", "Eingehalten?", "Translator",
    "Korrektur", "Verantwörtlich", "Status", "Ablageort", "Bemerkungen",
]

LANGUAGES_2025 = ["EN", "IT", "ES", "NL", "PL", "PT", "CZ", "SL"]
LANGUAGES_2026 = LANGUAGES_2025 + ["SV", "FI", "NW", "DA", "GR"]


# ============================================================
# HILFSFUNKTIONEN
# ============================================================
def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )
    return df


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    df = df.copy()
    for column in columns:
        if column not in df.columns:
            df[column] = pd.NA
    return df


def parse_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    df = df.copy()
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def normalize_channel_values(series: pd.Series) -> pd.Series:
    """Fasst alle rein numerischen Kanalwerte unter 'jazz' zusammen."""
    values = series.astype("string").str.strip()
    numeric = (
        values.notna()
        & values.ne("")
        & pd.to_numeric(values, errors="coerce").notna()
    )
    values.loc[numeric] = "jazz"
    return values


def parse_currency_series(series: pd.Series) -> pd.Series:
    """Wandelt Zahlen wie '€ 1.234,56' oder '1,234.56 €' in Eurobeträge um."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    text = series.astype("string").str.strip()
    text = text.str.replace("€", "", regex=False).str.replace("\\u00a0", "", regex=False)
    text = text.str.replace(r"[^0-9,.-]", "", regex=True)

    def convert(value):
        if pd.isna(value) or value == "":
            return np.nan
        value = str(value)
        if "," in value and "." in value:
            # Das letzte Trennzeichen ist das Dezimaltrennzeichen.
            if value.rfind(",") > value.rfind("."):
                value = value.replace(".", "").replace(",", ".")
            else:
                value = value.replace(",", "")
        elif "," in value:
            value = value.replace(",", ".")
        try:
            return float(value)
        except ValueError:
            return np.nan

    return text.map(convert)


def parse_currency_series(series: pd.Series) -> pd.Series:
    """Wandelt Zahlen wie '€ 1.234,56' oder '1,234.56 €' in Eurobeträge um."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    text = series.astype("string").str.strip()
    text = text.str.replace("€", "", regex=False).str.replace("\u00a0", "", regex=False)
    text = text.str.replace(r"[^0-9,.-]", "", regex=True)

    def convert(value):
        if pd.isna(value) or value == "":
            return np.nan
        value = str(value)
        if "," in value and "." in value:
            if value.rfind(",") > value.rfind("."):
                value = value.replace(".", "").replace(",", ".")
            else:
                value = value.replace(",", "")
        elif "," in value:
            value = value.replace(",", ".")
        try:
            return float(value)
        except ValueError:
            return np.nan

    return text.map(convert)


def parse_dates(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    df = df.copy()
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")
    return df


def normalize_orders(df: pd.DataFrame, year: str) -> pd.DataFrame:
    df = clean_columns(df)
    df = ensure_columns(df, STANDARD_ORDER_COLUMNS)

    # Deadline-Rohwert vor der Datumsumwandlung sichern.
    # Leere Deadline bleibt leer; ASAP bleibt als eigener Sonderfall erhalten.
    deadline_raw = df["Deadline"].astype("string").str.strip()
    df["Deadline_Kategorie"] = "Konkrete Deadline"
    df.loc[deadline_raw.isna() | deadline_raw.eq(""), "Deadline_Kategorie"] = (
        "Keine Deadline"
    )
    df.loc[deadline_raw.str.upper().eq("ASAP"), "Deadline_Kategorie"] = "ASAP"

    df = parse_dates(df, ["Eingang", "Lieferdatum", "Deadline"])
    df = parse_numeric(df, ["Wörter", "Stunden", "Durchlaufzeit"])

    for column in [
        "Auftragsname", "Auftraggeber", "Abteilung", "Auftragstyp", "Sprache",
        "Kanal", "Translator", "Korrektur", "Verantwörtlich", "Status",
    ]:
        if column in df.columns:
            df[column] = df[column].astype("string").str.strip()
    # Zentrale Kanalnormalisierung direkt nach dem String-Cleanup.
    # Alle rein numerischen Werte - auch Werte, die pandas als Zahl einliest -
    # werden zuverlässig unter "jazz" zusammengefasst.
    df["Kanal"] = normalize_channel_values(df["Kanal"])

    # Fehlende Dringlichkeitsangaben bleiben unbekannt und werden nicht zu 0.
    if "Dringend" in df.columns:
        df["Dringend"] = pd.to_numeric(df["Dringend"], errors="coerce")

    # Einheitliche, automatisch berechnete Zeitfelder.
    df["Monat"] = df["Eingang"].dt.to_period("M").astype("string")
    df["Jahr"] = year

    # Einzelne Aufträge entsprechen einzelnen Zielsprachen.
    df["Auftragsebene"] = "Zielsprache"

    # Nicht zugeordnete Abteilungen bleiben sichtbar.
    df["Abteilung_Anzeige"] = (
        df["Abteilung"].fillna("Nicht zugeordnet").replace("", "Nicht zugeordnet")
    )

    # Gültiger Zeitbereich: bewusst weit genug für historische Korrekturen,
    # aber 1970-/Excel-Fehlwerte werden ausgeschlossen.
    df["Gueltiger_Eingang"] = df["Eingang"].between(
        pd.Timestamp("2024-01-01"), pd.Timestamp("2027-12-31")
    )

    df["Durchlaufzeit_Tage"] = (
        df["Lieferdatum"] - df["Eingang"]
    ).dt.total_seconds() / 86400

    df["Gueltige_Durchlaufzeit"] = (
        df["Durchlaufzeit_Tage"].notna()
        & (df["Durchlaufzeit_Tage"] >= 0)
        & (df["Durchlaufzeit_Tage"] <= 365)
    )

    # Termintreue nur bei Lieferung und konkreter Kalender-Deadline berechnen.
    # Leere Deadline und ASAP bleiben in der Gesamtzahl, sind aber nicht bewertbar.
    df["Lieferstatus"] = "Nicht bewertbar"
    geliefert = df["Lieferdatum"].notna()
    konkrete_deadline = (
        df["Deadline_Kategorie"].eq("Konkrete Deadline")
        & df["Deadline"].notna()
    )
    bewertbar = geliefert & konkrete_deadline

    df.loc[~geliefert & df["Deadline_Kategorie"].eq("Konkrete Deadline"), "Lieferstatus"] = (
        "Noch nicht geliefert"
    )
    df.loc[~geliefert & df["Deadline_Kategorie"].eq("Keine Deadline"), "Lieferstatus"] = (
        "Nicht bewertbar - keine Deadline"
    )
    df.loc[~geliefert & df["Deadline_Kategorie"].eq("ASAP"), "Lieferstatus"] = (
        "Noch nicht geliefert - ASAP"
    )
    df.loc[geliefert & df["Deadline_Kategorie"].eq("Keine Deadline"), "Lieferstatus"] = (
        "Geliefert - keine Deadline"
    )
    df.loc[geliefert & df["Deadline_Kategorie"].eq("ASAP"), "Lieferstatus"] = (
        "Geliefert - ASAP"
    )
    df.loc[
        bewertbar & (df["Lieferdatum"] <= df["Deadline"]),
        "Lieferstatus",
    ] = "Fristgerecht geliefert"
    df.loc[
        bewertbar & (df["Lieferdatum"] > df["Deadline"]),
        "Lieferstatus",
    ] = "Verspätet geliefert"

    df["Frist_bewertbar"] = bewertbar
    df["Fristgerecht"] = np.where(
        bewertbar,
        df["Lieferdatum"] <= df["Deadline"],
        pd.NA,
    )

    return df


@st.cache_data(show_spinner=False)
def load_orders_2026() -> pd.DataFrame:
    # Die korrigierte 2026-Quelle ist eine CP1252-CSV-Datei.
    df = pd.read_csv(FILE_2026, encoding="cp1252")
    df = clean_columns(df)
    # Vollständig leere Zeilen sind keine Aufträge und werden nicht gezählt.
    df = df.dropna(how="all").copy()
    return normalize_orders(df, "2026")


@st.cache_data(show_spinner=False)
def load_orders_2025() -> pd.DataFrame:
    df = pd.read_excel(FILE_2025, sheet_name="2025", header=0)
    df = clean_columns(df)
    df = df.rename(
        columns={
            "Aufträge": "Auftragsname",
            "Datum": "Eingang",
            "Lieferung": "Lieferdatum",
            "Verantwortlich": "Verantwörtlich",
        }
    )
    return normalize_orders(df, "2025")


@st.cache_data(show_spinner=False)
def load_costs(sheet_name: str, year: str) -> pd.DataFrame:
    df = pd.read_excel(FILE_COSTS, sheet_name=sheet_name, header=0)
    df = clean_columns(df)
    df = df.rename(columns={"Bereich": "Abteilung"})
    if "Datum" not in df.columns:
        raise KeyError("Die Kostentabelle enthält keine Spalte 'Datum'.")

    df["Datum"] = pd.to_datetime(df["Datum"], errors="coerce")
    df = df.dropna(subset=["Datum"]).copy()
    df["Monat"] = df["Datum"].dt.to_period("M").astype("string")
    df["Jahr"] = year

    languages = LANGUAGES_2026 if year == "2026" else LANGUAGES_2025
    available_languages = [language for language in languages if language in df.columns]
    for language in available_languages:
        df[language] = parse_currency_series(df[language]).fillna(0)

    # Die Quelldatei enthält TOTAL teilweise leer; deshalb wird der Gesamtbetrag
    # zuverlässig aus den normalisierten Sprachspalten berechnet.
    df["Gesamt"] = df[available_languages].sum(axis=1)

    return df


def format_number(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_euro(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return (
        f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        + " €"
    )


def show_load_error(label: str, error: Exception) -> None:
    st.error(f"{label} konnte nicht geladen werden: {error}")
    st.stop()


# ============================================================
# DATEN LADEN
# ============================================================
try:
    df_2026 = load_orders_2026()
    df_2025 = load_orders_2025()
except FileNotFoundError as exc:
    show_load_error(
        "Eine benötigte Excel-Datei wurde nicht gefunden. Prüfe Dateinamen und Speicherort",
        exc,
    )
except (KeyError, ValueError) as exc:
    show_load_error("Die Excel-Struktur ist nicht wie erwartet", exc)


# ============================================================
# NAVIGATION
# ============================================================
st.sidebar.title("Navigation")
seite = st.sidebar.radio(
    "Seite auswählen:",
    [
        "📊 KPI Dashboard 2026",
        "📈 Jahresvergleich 2025 vs 2026",
        "💰 Kosten Übersicht",
        "📘 KPI-Methodik & Anleitung",
    ],
)

if st.sidebar.button("Daten neu laden"):
    st.cache_data.clear()
    st.rerun()


# ============================================================
# SEITE 1: KPI DASHBOARD 2026
# ============================================================
if seite == "📊 KPI Dashboard 2026":
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filter")

    abteilungen = ["Alle"] + sorted(
        df_2026["Abteilung_Anzeige"].dropna().unique().tolist()
    )
    abt_filter = st.sidebar.selectbox("Abteilung", abteilungen)

    kanaele = ["Alle"] + sorted(df_2026["Kanal"].dropna().unique().tolist())
    kanal_filter = st.sidebar.selectbox("Kanal", kanaele)

    deadline_kategorien = ["Alle"] + [
        "Konkrete Deadline", "Keine Deadline", "ASAP"
    ]
    deadline_filter = st.sidebar.selectbox(
        "Deadline-Status", deadline_kategorien
    )

    gueltige_eingaenge = df_2026.loc[
        df_2026["Gueltiger_Eingang"], "Eingang"
    ].dropna()
    if gueltige_eingaenge.empty:
        st.error("Es wurden keine gültigen Eingangsdaten für 2026 gefunden.")
        st.stop()

    # Das Dashboard 2026 startet standardmäßig am 01.01.2026.
    # Frühere Datensätze bleiben in der Quelle erhalten, werden aber im
    # Standardzeitraum nicht angezeigt.
    dashboard_start = pd.Timestamp("2026-01-01").date()
    data_max_datum = gueltige_eingaenge.max().date()
    if data_max_datum < dashboard_start:
        st.error("Für 2026 wurden keine Eingänge ab dem 01.01.2026 gefunden.")
        st.stop()

    min_datum = dashboard_start
    max_datum = data_max_datum
    datum_range = st.sidebar.date_input(
        "Zeitraum Eingang",
        value=(min_datum, max_datum),
        min_value=min_datum,
        max_value=max_datum,
    )

    df_filtered = df_2026.copy()

    if abt_filter != "Alle":
        df_filtered = df_filtered[
            df_filtered["Abteilung_Anzeige"] == abt_filter
        ]

    if kanal_filter != "Alle":
        df_filtered = df_filtered[df_filtered["Kanal"] == kanal_filter]

    if deadline_filter != "Alle":
        df_filtered = df_filtered[
            df_filtered["Deadline_Kategorie"] == deadline_filter
        ]

    if isinstance(datum_range, (tuple, list)) and len(datum_range) == 2:
        start_date, end_date = datum_range
        df_filtered = df_filtered[
            df_filtered["Eingang"].dt.date.between(start_date, end_date)
        ]

    # Letzte Schutzschicht vor jeder Auswertung und Darstellung.
    # Damit werden auch ältere oder abweichende CSV-Versionen korrigiert.
    df_2026["Kanal"] = normalize_channel_values(df_2026["Kanal"])
    df_filtered["Kanal"] = normalize_channel_values(df_filtered["Kanal"])

    total_auftraege = len(df_filtered)
    deadline_konkret = df_filtered["Deadline_Kategorie"].eq("Konkrete Deadline")
    keine_deadline = df_filtered["Deadline_Kategorie"].eq("Keine Deadline")
    asap_deadline = df_filtered["Deadline_Kategorie"].eq("ASAP")
    fristbewertbar = df_filtered["Frist_bewertbar"]
    fristgerecht = df_filtered["Fristgerecht"].eq(True)
    verspätet = fristbewertbar & ~fristgerecht
    fristtreue = (
        fristgerecht[fristbewertbar].mean() * 100
        if fristbewertbar.any()
        else np.nan
    )

    offene_auftraege = (~df_filtered["Lieferdatum"].notna()).sum()
    gueltige_zeiten = df_filtered.loc[
        df_filtered["Gueltige_Durchlaufzeit"], "Durchlaufzeit_Tage"
    ]
    median_durchlaufzeit = (
        gueltige_zeiten.median() if not gueltige_zeiten.empty else np.nan
    )
    p90_durchlaufzeit = (
        gueltige_zeiten.quantile(0.90) if not gueltige_zeiten.empty else np.nan
    )
    wortvolumen = df_filtered["Wörter"].sum(min_count=1)

    st.title("KPI Dashboard - Language Services")
    st.caption(
        f"Datenstand Eingang: {df_2026['Eingang'].max():%d.%m.%Y} | "
        f"Dashboard aktualisiert: {datetime.now():%d.%m.%Y %H:%M}"
    )

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Aufträge gesamt", format_number(total_auftraege))
    k2.metric(
        "Termintreue",
        f"{fristtreue:.1f}%" if pd.notna(fristtreue) else "-",
        help="Nur gelieferte Aufträge mit konkreter Deadline werden bewertet.",
    )
    k3.metric("Keine Deadline", format_number(keine_deadline.sum()))
    k4.metric("ASAP", format_number(asap_deadline.sum()))
    k5.metric("Verspätet geliefert", format_number(verspätet.sum()))
    k6.metric("Noch nicht geliefert", format_number(offene_auftraege))

    s1, s2, s3, s4 = st.columns(4)
    s1.metric(
        "Konkrete Deadline",
        format_number(deadline_konkret.sum()),
        help="Aufträge mit einem konkreten Kalenderdatum als Deadline."
    )
    s2.metric(
        "Termintreue bewertet",
        format_number(fristbewertbar.sum()),
        help="Gelieferte Aufträge mit konkreter Deadline. Diese Aufträge bilden den Nenner der Termintreue."
    )
    s3.metric(
        "Fristgerecht",
        format_number(fristgerecht[fristbewertbar].sum()),
        help="Bewertete Aufträge, die am oder vor der Deadline geliefert wurden."
    )
    s4.metric(
        "Nicht bewertbar",
        format_number((~fristbewertbar).sum()),
        help="Aufträge ohne konkrete Deadline, mit ASAP oder noch nicht gelieferte Aufträge."
    )

    st.markdown("---")
    st.info(
        "Die Deadline wird vom Auftraggeber vorgegeben. 'Termintreue' wird nur "
        "für gelieferte Aufträge mit konkreter Deadline berechnet. Leere Deadlines "
        "und ASAP bleiben in der Gesamtzahl, sind aber nicht bewertbar."
    )

    with st.expander("Wie werden Termintreue und Fristgerecht berechnet?", expanded=False):
        st.markdown(
            "**Termintreue bewertet** = gelieferte Aufträge mit einer konkreten Deadline. "
            "Diese Zahl ist der Nenner für die Termintreue.\n\n"
            "**Fristgerecht** = bewertete Aufträge, die am oder vor der Deadline geliefert wurden.\n\n"
            "**Verspätet** = bewertete Aufträge, die nach der Deadline geliefert wurden.\n\n"
            "**Nicht bewertbar** = Aufträge ohne Deadline, mit `ASAP` oder noch nicht gelieferte Aufträge."
        )
        flow = pd.DataFrame(
            {
                "Stufe": [
                    "Aufträge gesamt",
                    "Termintreue bewertet",
                    "Fristgerecht",
                    "Verspätet",
                ],
                "Anzahl": [
                    total_auftraege,
                    int(fristbewertbar.sum()),
                    int(fristgerecht[fristbewertbar].sum()),
                    int(verspätet.sum()),
                ],
                "Erklärung": [
                    "Alle Aufträge im aktuellen Filter",
                    "Geliefert + konkrete Deadline",
                    "Lieferdatum <= Deadline",
                    "Lieferdatum > Deadline",
                ],
            }
        )
        st.dataframe(flow, use_container_width=True, hide_index=True)
        st.caption(
            "Termintreue = Fristgerecht / Termintreue bewertet. "
            "Aufträge ohne Deadline und ASAP werden nicht in diese Quote einbezogen."
        )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Aufträge pro Monat")
        monat = (
            df_filtered[df_filtered["Gueltiger_Eingang"]]
            .groupby("Monat", dropna=False)
            .size()
            .rename("Anzahl")
            .reset_index()
            .sort_values("Monat")
        )
        fig = px.bar(
            monat,
            x="Monat",
            y="Anzahl",
            labels={"Monat": "Monat des Eingangs", "Anzahl": "Aufträge"},
            color_discrete_sequence=["#4472C4"],
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Anzahl Aufträge pro Abteilung")
        department_values = (
            df_filtered["Abteilung_Anzeige"]
            .astype("string")
            .str.strip()
            .fillna("Nicht zugeordnet")
            .replace("", "Nicht zugeordnet")
        )
        by_department = (
            department_values.value_counts(dropna=False)
            .rename_axis("Abteilung")
            .reset_index(name="Anzahl")
            .sort_values("Anzahl", ascending=True)
        )
        by_department["Abteilung"] = by_department["Abteilung"].astype("string")
        by_department["Anzahl"] = pd.to_numeric(by_department["Anzahl"], errors="coerce").astype(int)
        fig = px.bar(
            by_department,
            x="Anzahl",
            y="Abteilung",
            text="Anzahl",
            orientation="h",
            labels={"Abteilung": "Abteilung", "Anzahl": "Aufträge"},
            color_discrete_sequence=["#70AD47"],
            hover_data={"Anzahl": ":,d"},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, yaxis_type="category")
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Anzahl Aufträge pro Kanal")
        channel_values = (
            df_filtered["Kanal"]
            .astype("string")
            .str.strip()
            .fillna("Nicht angegeben")
            .replace("", "Nicht angegeben")
        )
        by_channel = (
            channel_values.value_counts(dropna=False)
            .rename_axis("Kanal")
            .reset_index(name="Anzahl")
            .sort_values("Anzahl", ascending=True)
        )
        by_channel["Kanal"] = by_channel["Kanal"].astype("string")
        by_channel["Anzahl"] = pd.to_numeric(by_channel["Anzahl"], errors="coerce").astype(int)
        fig = px.bar(
            by_channel,
            x="Anzahl",
            y="Kanal",
            text="Anzahl",
            orientation="h",
            labels={"Kanal": "Kanal", "Anzahl": "Aufträge"},
            color_discrete_sequence=["#ED7D31"],
            hover_data={"Anzahl": ":,d"},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, yaxis_type="category")
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        st.subheader("Lieferstatus")
        status_data = (
            df_filtered["Lieferstatus"]
            .value_counts()
            .rename_axis("Status")
            .reset_index(name="Anzahl")
            .sort_values("Anzahl", ascending=True)
        )
        fig = px.bar(
            status_data,
            x="Anzahl",
            y="Status",
            orientation="h",
            labels={"Status": "Lieferstatus", "Anzahl": "Aufträge"},
            color="Status",
            color_discrete_map={
                "Fristgerecht geliefert": "#70AD47",
                "Verspätet geliefert": "#C00000",
                "Noch nicht geliefert": "#FFC000",
                "Geliefert - keine Deadline": "#A5A5A5",
                "Nicht bewertbar - keine Deadline": "#A5A5A5",
                "Geliefert - ASAP": "#8064A2",
                "Noch nicht geliefert - ASAP": "#8064A2",
                "Nicht bewertbar": "#A5A5A5",
            },
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Aufträge nach Kanal und Deadline-Status")

    deadline_colors = {
        "Konkrete Deadline": "#4472C4",
        "Keine Deadline": "#A5A5A5",
        "ASAP": "#8064A2",
    }

    channel_deadline = (
        df_filtered.assign(
            Kanal_Anzeige=df_filtered["Kanal"]
            .fillna("Nicht angegeben")
            .replace("", "Nicht angegeben")
        )
        .groupby(["Kanal_Anzeige", "Deadline_Kategorie"], dropna=False)
        .size()
        .rename("Anzahl")
        .reset_index()
    )
    fig = px.bar(
        channel_deadline,
        x="Anzahl",
        y="Kanal_Anzeige",
        color="Deadline_Kategorie",
        orientation="h",
        barmode="stack",
        labels={
            "Kanal_Anzeige": "Kanal",
            "Anzahl": "Aufträge",
            "Deadline_Kategorie": "Deadline",
        },
        color_discrete_map=deadline_colors,
    )
    fig.update_layout(legend_title_text="Deadline-Status")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Aufträge nach Abteilung und Deadline-Status")
    department_deadline = (
        df_filtered.groupby(["Abteilung_Anzeige", "Deadline_Kategorie"], dropna=False)
        .size()
        .rename("Anzahl")
        .reset_index()
    )
    fig = px.bar(
        department_deadline,
        x="Anzahl",
        y="Abteilung_Anzeige",
        color="Deadline_Kategorie",
        orientation="h",
        barmode="stack",
        labels={
            "Abteilung_Anzeige": "Abteilung",
            "Anzahl": "Aufträge",
            "Deadline_Kategorie": "Deadline",
        },
        color_discrete_map=deadline_colors,
    )
    fig.update_layout(legend_title_text="Deadline-Status")
    st.plotly_chart(fig, use_container_width=True)

    no_deadline = df_filtered[keine_deadline].copy()
    with st.expander("Aufträge ohne Deadline nach Kanal und Abteilung"):
        if no_deadline.empty:
            st.info("Im aktuellen Filter gibt es keine Aufträge ohne Deadline.")
        else:
            no_deadline_summary = (
                no_deadline.assign(
                    Kanal_Anzeige=no_deadline["Kanal"]
                    .fillna("Nicht angegeben")
                    .replace("", "Nicht angegeben")
                )
                .groupby(["Abteilung_Anzeige", "Kanal_Anzeige"], dropna=False)
                .size()
                .rename("Aufträge ohne Deadline")
                .reset_index()
                .sort_values("Aufträge ohne Deadline", ascending=False)
            )
            st.dataframe(no_deadline_summary, use_container_width=True, hide_index=True)

    st.markdown("---")

    col5, col6 = st.columns(2)
    with col5:
        st.subheader("Aufträge pro Zielsprache")
        by_language = (
            df_filtered.groupby("Sprache", dropna=False)
            .size()
            .rename("Aufträge")
            .reset_index()
            .sort_values("Aufträge", ascending=True)
        )
        fig = px.bar(
            by_language,
            x="Aufträge",
            y="Sprache",
            orientation="h",
            labels={"Sprache": "Zielsprache", "Aufträge": "Aufträge"},
            color_discrete_sequence=["#5B9BD5"],
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col6:
        st.subheader("Durchlaufzeit nach Zielsprache")
        duration_by_language = (
            df_filtered[df_filtered["Gueltige_Durchlaufzeit"]]
            .groupby("Sprache", dropna=False)["Durchlaufzeit_Tage"]
            .agg(Median="median", P90=lambda s: s.quantile(0.90), Anzahl="count")
            .reset_index()
            .sort_values("Median", ascending=True)
        )
        if duration_by_language.empty:
            st.info("Keine gültigen Durchlaufzeiten im aktuellen Filter.")
        else:
            fig = px.bar(
                duration_by_language,
                x="Median",
                y="Sprache",
                orientation="h",
                labels={"Sprache": "Zielsprache", "Median": "Median-Tage"},
                hover_data=["P90", "Anzahl"],
                color_discrete_sequence=["#8064A2"],
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("Datenqualität anzeigen"):
        invalid_dates = (~df_filtered["Gueltiger_Eingang"]).sum()
        invalid_durations = (~df_filtered["Gueltige_Durchlaufzeit"]).sum()
        missing_deadlines = df_filtered["Deadline_Kategorie"].eq("Keine Deadline").sum()
        asap_deadlines = df_filtered["Deadline_Kategorie"].eq("ASAP").sum()
        missing_departments = (
            df_filtered["Abteilung_Anzeige"] == "Nicht zugeordnet"
        ).sum()
        st.write(
            {
                "Ungültige Eingangsdatumswerte": int(invalid_dates),
                "Nicht auswertbare Durchlaufzeiten": int(invalid_durations),
                "Keine Deadline": int(missing_deadlines),
                "ASAP ohne Kalenderdatum": int(asap_deadlines),
                "Nicht zugeordnete Abteilungen": int(missing_departments),
                "90. Perzentil Durchlaufzeit": (
                    f"{p90_durchlaufzeit:.1f} Tage"
                    if pd.notna(p90_durchlaufzeit)
                    else "-"
                ),
            }
        )

    with st.expander("Rohdaten anzeigen"):
        export_columns = [
            "Auftragsname", "Auftraggeber", "Abteilung_Anzeige", "Auftragstyp",
            "Sprache", "Wörter", "Eingang", "Lieferdatum", "Deadline",
            "Lieferstatus", "Deadline_Kategorie", "Frist_bewertbar",
            "Durchlaufzeit_Tage", "Translator", "Kanal",
        ]
        export_df = df_filtered[
            [column for column in export_columns if column in df_filtered.columns]
        ]
        st.dataframe(export_df, use_container_width=True, hide_index=True)

        csv = export_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            "CSV herunterladen",
            data=csv,
            file_name="KPI_Bericht_2026.csv",
            mime="text/csv",
        )


# ============================================================
# SEITE 2: JAHRESVERGLEICH
# ============================================================
elif seite == "📈 Jahresvergleich 2025 vs 2026":
    st.title("Jahresvergleich 2025 vs 2026")
    st.caption(
        f"2026 ist ein laufendes Jahr; Vergleich bitte nur für gleiche Zeiträume interpretieren. "
        f"Aktualisiert: {datetime.now():%d.%m.%Y %H:%M}"
    )

    max_2025 = df_2025["Eingang"].max()
    max_2026 = df_2026["Eingang"].max()
    cutoff_month = min(
        max_2025.month if pd.notna(max_2025) else 12,
        max_2026.month if pd.notna(max_2026) else 12,
    )

    y1, y2 = st.columns(2)
    y1.metric("Aufträge 2025 gesamt", format_number(len(df_2025)))
    y2.metric("Aufträge 2026 gesamt", format_number(len(df_2026)))

    monthly = pd.concat(
        [
            df_2025.assign(Jahr_Anzeige="2025"),
            df_2026.assign(Jahr_Anzeige="2026"),
        ],
        ignore_index=True,
    )
    monthly = monthly[monthly["Gueltiger_Eingang"]].copy()
    monthly["Monat_nummer"] = monthly["Eingang"].dt.month
    monthly = (
        monthly.groupby(["Jahr_Anzeige", "Monat_nummer"])
        .size()
        .rename("Anzahl")
        .reset_index()
    )
    month_names = {
        1: "Jan", 2: "Feb", 3: "Mrz", 4: "Apr", 5: "Mai", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Dez",
    }
    monthly["Monat"] = monthly["Monat_nummer"].map(month_names)

    st.subheader("Aufträge pro Monat")
    fig = px.bar(
        monthly,
        x="Monat_nummer",
        y="Anzahl",
        color="Jahr_Anzeige",
        barmode="group",
        labels={"Monat_nummer": "Monat", "Anzahl": "Aufträge", "Jahr_Anzeige": "Jahr"},
        color_discrete_sequence=["#ED7D31", "#4472C4"],
    )
    fig.update_xaxes(
        tickmode="array",
        tickvals=list(month_names.keys()),
        ticktext=list(month_names.values()),
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Aufträge pro Zielsprache")
        language_compare = pd.concat(
            [
                df_2025.assign(Jahr_Anzeige="2025"),
                df_2026.assign(Jahr_Anzeige="2026"),
            ],
            ignore_index=True,
        )
        language_compare = (
            language_compare.groupby(["Sprache", "Jahr_Anzeige"])
            .size()
            .rename("Aufträge")
            .reset_index()
        )
        fig = px.bar(
            language_compare,
            x="Sprache",
            y="Aufträge",
            color="Jahr_Anzeige",
            barmode="group",
            labels={"Sprache": "Zielsprache", "Jahr_Anzeige": "Jahr"},
            color_discrete_sequence=["#ED7D31", "#4472C4"],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Aufträge pro Abteilung")
        department_compare = pd.concat(
            [
                df_2025.assign(Jahr_Anzeige="2025"),
                df_2026.assign(Jahr_Anzeige="2026"),
            ],
            ignore_index=True,
        )
        department_compare = (
            department_compare.groupby(["Abteilung_Anzeige", "Jahr_Anzeige"])
            .size()
            .rename("Aufträge")
            .reset_index()
            .sort_values("Aufträge", ascending=False)
        )
        fig = px.bar(
            department_compare,
            x="Aufträge",
            y="Abteilung_Anzeige",
            color="Jahr_Anzeige",
            barmode="group",
            orientation="h",
            labels={"Abteilung_Anzeige": "Abteilung", "Jahr_Anzeige": "Jahr"},
            color_discrete_sequence=["#ED7D31", "#4472C4"],
        )
        st.plotly_chart(fig, use_container_width=True)


# ============================================================
# SEITE 4: KPI-METHODIK & ANLEITUNG
# ============================================================
elif seite == "📘 KPI-Methodik & Anleitung":
    st.title("KPI-Methodik & Anleitung")
    st.caption("Was messen wir, warum messen wir es und wie sind die Kennzahlen zu lesen?")

    st.info(
        "Die KPIs beschreiben den Auftragsprozess und unterstützen die Planung. "
        "Sie sind nicht als isolierte Bewertung einzelner Personen gedacht."
    )

    st.subheader("Was messen wir?")
    methodik = pd.DataFrame(
        {
            "Bereich": [
                "Auftragsvolumen",
                "Verteilung",
                "Termintreue",
                "Deadlines",
                "Durchlaufzeit",
                "Offene Arbeit",
                "Datenqualität",
                "Kosten",
            ],
            "KPIs im Dashboard": [
                "Aufträge gesamt, pro Monat, Kanal und Abteilung",
                "Aufträge nach Kanal, Abteilung und Zielsprache",
                "Termintreue, fristgerecht, verspätet",
                "Konkrete Deadline, keine Deadline, ASAP",
                "Median und P90 der Durchlaufzeit",
                "Noch nicht geliefert",
                "Fehlende Deadlines, Lieferdaten und Zuordnungen",
                "Kosten nach Sprache, Abteilung und Monat",
            ],
            "Wofür?": [
                "Arbeitsvolumen und Entwicklung erkennen",
                "Schwerpunkte und Belastungen sichtbar machen",
                "Vereinbarte Termine nachvollziehbar prüfen",
                "Bewertbarkeit der Termintreue einschätzen",
                "Typische Dauer und Ausreißer erkennen",
                "Rückstände frühzeitig erkennen",
                "Aussagekraft der Auswertung beurteilen",
                "Aufwendungen und Entwicklungen beobachten",
            ],
        }
    )
    st.dataframe(methodik, use_container_width=True, hide_index=True)

    st.subheader("Wie wird die Termintreue berechnet?")
    st.markdown(
        "**Termintreue bewertet** sind gelieferte Aufträge mit einer konkreten Kalender-Deadline. "
        "Diese Zahl ist der Nenner.\n\n"
        "**Fristgerecht** sind bewertete Aufträge, die am oder vor der Deadline geliefert wurden.\n\n"
        "**Verspätet** sind bewertete Aufträge, die nach der Deadline geliefert wurden."
    )
    formula = pd.DataFrame(
        {
            "Kennzahl": ["Termintreue", "Termintreue bewertet", "Fristgerecht", "Nicht bewertbar"],
            "Definition": [
                "Fristgerecht / Termintreue bewertet",
                "Geliefert + konkrete Deadline",
                "Lieferdatum <= Deadline",
                "Keine Deadline, ASAP oder noch nicht geliefert",
            ],
        }
    )
    st.dataframe(formula, use_container_width=True, hide_index=True)

    st.subheader("Was erhoffen wir uns von den KPIs?")
    st.markdown(
        "- Arbeitsvolumen und Verteilung transparent machen\n"
        "- Engpässe und Rückstände früh erkennen\n"
        "- Kapazitäten und Ressourcen besser planen\n"
        "- Wiederkehrende Verzögerungen erkennen\n"
        "- Datenqualität und Prozessqualität verbessern\n"
        "- Gespräche mit Auftraggebern faktenbasiert führen\n"
        "- Verbesserungen im Prozess messbar machen"
    )

    st.subheader("Was sagen die KPIs nicht automatisch aus?")
    st.warning(
        "Eine verspätete Lieferung ist nicht automatisch ein Fehler des Übersetzungsteams. "
        "Deadlines können unrealistisch oder sehr kurzfristig sein. Vergleiche zwischen "
        "Abteilungen sind nur sinnvoll, wenn Auftragsarten und Rahmenbedingungen ähnlich sind."
    )

    st.subheader("Regeln für Deadlines")
    deadline_rules = pd.DataFrame(
        {
            "Situation": [
                "Konkrete Deadline vorhanden",
                "ASAP ausdrücklich vereinbart",
                "Keine Deadline vereinbart",
                "Deadline später bekannt geworden",
            ],
            "Eintrag": [
                "Datum eintragen",
                "ASAP eintragen",
                "Feld leer lassen",
                "Datum nachtragen",
            ],
            "Auswertung": [
                "Termintreue bewertbar, sobald geliefert",
                "Nicht als konkretes Datum bewerten",
                "In Gesamtzahl enthalten, nicht bewertbar",
                "Nach Aktualisierung regulär bewerten",
            ],
        }
    )
    st.dataframe(deadline_rules, use_container_width=True, hide_index=True)


# ============================================================
# SEITE 3: KOSTEN
# ============================================================
elif seite == "💰 Kosten Übersicht":
    st.title("Kosten Übersicht - Language Services")
    st.caption(f"Aktualisiert: {datetime.now():%d.%m.%Y %H:%M}")

    jahr_filter = st.sidebar.radio("Jahr", ["2026", "2025", "2025 vs 2026"])

    try:
        costs_2025 = load_costs("2025", "2025")
        costs_2026 = load_costs("2026", "2026")
    except (FileNotFoundError, KeyError, ValueError) as exc:
        show_load_error("Die Kostendaten", exc)

    if jahr_filter == "2026":
        costs = costs_2026.copy()
    elif jahr_filter == "2025":
        costs = costs_2025.copy()
    else:
        costs = pd.concat([costs_2025, costs_2026], ignore_index=True)

    all_languages = sorted(set(LANGUAGES_2025 + LANGUAGES_2026))
    languages = [language for language in all_languages if language in costs.columns]
    if not languages:
        st.warning("Keine Sprachspalten in den Kostendaten gefunden.")
        st.stop()

    costs["Gesamt"] = costs[languages].sum(axis=1)
    total_costs = costs["Gesamt"].sum()
    st.metric("Gesamtkosten", format_euro(total_costs))

    cost_by_language = (
        costs[languages]
        .sum()
        .rename_axis("Sprache")
        .reset_index(name="Kosten")
    )
    cost_by_language = cost_by_language[cost_by_language["Kosten"] > 0]

    st.subheader(f"Kosten pro Zielsprache - {jahr_filter}")
    fig = px.bar(
        cost_by_language.sort_values("Kosten", ascending=True),
        x="Kosten",
        y="Sprache",
        orientation="h",
        labels={"Kosten": "Kosten (€)", "Sprache": "Zielsprache"},
        color_discrete_sequence=["#4472C4"],
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    if "Abteilung" in costs.columns:
        st.subheader(f"Kosten pro Abteilung - {jahr_filter}")
        costs["Abteilung_Anzeige"] = (
            costs["Abteilung"].fillna("Nicht zugeordnet")
        )
        cost_by_department = (
            costs.groupby("Abteilung_Anzeige", dropna=False)["Gesamt"]
            .sum()
            .rename("Kosten")
            .reset_index()
            .query("Kosten > 0")
            .sort_values("Kosten", ascending=True)
        )
        fig = px.bar(
            cost_by_department,
            x="Kosten",
            y="Abteilung_Anzeige",
            orientation="h",
            labels={"Kosten": "Kosten (€)", "Abteilung_Anzeige": "Abteilung"},
            color_discrete_sequence=["#70AD47"],
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader(f"Kosten pro Monat - {jahr_filter}")
    cost_by_month = (
        costs.groupby(["Monat", "Jahr"], dropna=False)["Gesamt"]
        .sum()
        .rename("Kosten")
        .reset_index()
        .sort_values("Monat")
    )
    cost_by_month["Monat_nummer"] = cost_by_month["Monat"].str[-2:].astype(int)
    fig = px.bar(
        cost_by_month,
        x="Monat_nummer",
        y="Kosten",
        color="Jahr" if jahr_filter == "2025 vs 2026" else None,
        barmode="group" if jahr_filter == "2025 vs 2026" else None,
        labels={"Kosten": "Kosten (€)", "Monat_nummer": "Monat", "Jahr": "Jahr"},
        color_discrete_sequence=["#ED7D31", "#4472C4"],
    )
    fig.update_xaxes(tickmode="linear", dtick=1)
    st.plotly_chart(fig, use_container_width=True)

    if "Übersetzer" in costs.columns:
        st.subheader(f"Kostenvolumen pro Übersetzer/Dienstleister - {jahr_filter}")
        cost_by_translator = (
            costs.groupby("Übersetzer", dropna=False)["Gesamt"]
            .sum()
            .rename("Kosten")
            .reset_index()
            .sort_values("Kosten", ascending=True)
        )
        cost_by_translator["Übersetzer"] = cost_by_translator["Übersetzer"].fillna(
            "Unbekannt"
        )
        fig = px.bar(
            cost_by_translator,
            x="Kosten",
            y="Übersetzer",
            orientation="h",
            labels={"Kosten": "Kosten (€)", "Übersetzer": "Übersetzer/Dienstleister"},
            color_discrete_sequence=["#8064A2"],
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Rohdaten Kosten anzeigen"):
        st.dataframe(costs, use_container_width=True, hide_index=True)

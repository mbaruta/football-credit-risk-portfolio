import re
import time
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


YEARS = range(2016, 2026)
DIVISIONS = {"a": 1, "b": 2, "c": 3, "d": 4}

CBF_BASE = "https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro"
RSSSF_BASE = "https://www.rsssfbrasil.com/tablesae"

UOL_2016_B_URL = "https://www.uol.com.br/esporte/futebol/campeonatos/serie-b/2016/jogos/"

OUTPUT_FILE = Path("data/staging/sporting_data_staging.csv")
ERROR_FILE = Path("data/staging/sporting_collection_errors.csv")
RAW_CBF_DIR = Path("data/raw/sporting/cbf")
RAW_RSSSF_DIR = Path("data/raw/sporting/rsssf")
RAW_EXCEPTION_DIR = Path("data/raw/sporting/exceptional")

COLUMNS = [
    "club",
    "season",
    "division",
    "stage",
    "group",
    "matches_played",
    "points",
    "goals_for",
    "goals_against",
    "league_position",
    "league_size",
    "promoted",
    "relegated",
    "table_source",
    "table_source_url",
    "outcome_source",
    "notes",
]


def clean_text(value):
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()


def normalize_label(value):
    value = clean_text(value).lower()
    for old, new in {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e", "í": "i",
        "ó": "o", "ô": "o", "õ": "o",
        "ú": "u", "ç": "c", "ª": "a", "º": "o",
    }.items():
        value = value.replace(old, new)
    return value



SERIE_C_PROMOTED_ROWS = {
    2016: {("A", 2), ("B", 1), ("B", 2), ("B", 4)},
    2017: {("A", 1), ("A", 2), ("A", 3), ("B", 1)},
    2018: {("B", 1), ("B", 2), ("B", 3), ("B", 4)},
    2019: {("A", 1), ("A", 2), ("A", 4), ("B", 2)},
    2020: {("A", 2), ("A", 3), ("B", 3), ("B", 4)},
    2021: {("A", 2), ("B", 1), ("B", 2), ("B", 4)},
}

SERIE_C_PROMOTED_POSITIONS = {
    2022: {1, 5, 6, 7},
    2023: {1, 3, 4, 7},
    2024: {2, 3, 5, 8},
    2025: {2, 3, 4, 5},
}

SERIE_D_PROMOTED_ROWS = {
    2016: {("A4", 2), ("A6", 1), ("A12", 1), ("A14", 1)},
    2017: {("A1", 1), ("A6", 1), ("A7", 1), ("A15", 1)},
    2018: {("A4", 1), ("A6", 2), ("A9", 1), ("A17", 1)},
    2019: {("A2", 1), ("A7", 1), ("A13", 2), ("A15", 1)},
    2020: {("A2", 1), ("A3", 3), ("A7", 2), ("A8", 1)},
    2021: {("A3", 1), ("A3", 2), ("A3", 4), ("A5", 1)},
    2022: {("A1", 1), ("A3", 2), ("A6", 1), ("A7", 1)},
    2023: {("A2", 1), ("A6", 1), ("A7", 4), ("A8", 2)},
    2024: {("A4", 1), ("A4", 2), ("A5", 2), ("A7", 1)},
    2025: {("A2", 4), ("A3", 2), ("A7", 1), ("A8", 1)},
}


def outcome_group_key(value):
    if pd.isna(value):
        return ""

    value = clean_text(value).upper()
    value = re.sub(r"[^A-Z0-9]+", "", value)

    match = re.fullmatch(r"([A-Z]+)0*(\d+)", value)
    if match:
        return f"{match.group(1)}{int(match.group(2))}"

    return value



def apply_outcomes(sporting):
    sporting = sporting.copy()
    sporting["promoted"] = 0
    sporting["relegated"] = 0
    sporting["outcome_source"] = pd.Series(pd.NA, index=sporting.index, dtype="string")

    for index, row in sporting.iterrows():
        year = int(row["season"])
        division = int(row["division"])
        position = int(row["league_position"])
        league_size = int(row["league_size"])
        club = clean_text(row["club"])
        group = "" if pd.isna(row["group"]) else clean_text(row["group"])

        if division == 1:
            sporting.at[index, "relegated"] = int(position > league_size - 4)
            sporting.at[index, "outcome_source"] = row["table_source"]

        elif division == 2:
            sporting.at[index, "promoted"] = int(position <= 4)
            sporting.at[index, "relegated"] = int(position > league_size - 4)
            sporting.at[index, "outcome_source"] = row["table_source"]

        elif division == 3:
            if year <= 2021:
                promotion_key = (outcome_group_key(group), position)
                sporting.at[index, "promoted"] = int(
                    promotion_key in SERIE_C_PROMOTED_ROWS[year]
                )
            else:
                sporting.at[index, "promoted"] = int(
                    position in SERIE_C_PROMOTED_POSITIONS[year]
                )

            season_data = sporting[
                (sporting["season"] == year) &
                (sporting["division"] == 3)
            ]
            number_of_groups = season_data["group"].fillna("").nunique()
            relegation_places = 2 if number_of_groups > 1 else 4

            sporting.at[index, "relegated"] = int(position > league_size - relegation_places)
            sporting.at[index, "outcome_source"] = "CBF"

        elif division == 4:
            promotion_key = (outcome_group_key(group), position)
            sporting.at[index, "promoted"] = int(
                promotion_key in SERIE_D_PROMOTED_ROWS[year]
            )
            sporting.at[index, "relegated"] = 0
            sporting.at[index, "outcome_source"] = "CBF"

    validate_outcomes(sporting)
    return sporting


def validate_outcomes(sporting):
    expected = {
        1: (0, 4),
        2: (4, 4),
        3: (4, 4),
        4: (4, 0),
    }

    for year in YEARS:
        for division, (expected_promoted, expected_relegated) in expected.items():
            data = sporting[
                (sporting["season"] == year) &
                (sporting["division"] == division)
            ]

            if data.empty:
                continue

            promoted = int(data["promoted"].sum())
            relegated = int(data["relegated"].sum())

            if promoted != expected_promoted or relegated != expected_relegated:
                raise ValueError(
                    f"Outcome validation failed for {year} Série {chr(64 + division)}: "
                    f"promoted={promoted}, relegated={relegated}"
                )

    if sporting["outcome_source"].isna().any():
        raise ValueError("Missing outcome_source")


def clean_validated_staging(sporting):
    sporting = sporting.copy()

    sporting["group"] = (
        sporting["group"]
        .fillna("")
        .astype(str)
        .str.replace(r"\s*\|\s*\d{4}\s*$", "", regex=True)
        .str.strip()
    )

    known_identities = {
        (2018, 4, "A03", "São Raimundo", 2): "São Raimundo-RR",
        (2018, 4, "A03", "São Raimundo", 3): "São Raimundo-PA",
        (2019, 4, "A06", "América", 1): "América-RN",
        (2019, 4, "A06", "América", 2): "América-PE",
        (2020, 1, "", "Atlético", 3): "Atlético-MG",
        (2020, 1, "", "Atlético", 13): "Atlético-GO",
        (2022, 3, "A", "Botafogo", 5): "Botafogo-SP",
        (2022, 3, "A", "Botafogo", 9): "Botafogo-PB",
        (2022, 4, "A1", "São Raimundo", 3): "São Raimundo-AM",
        (2022, 4, "A1", "São Raimundo", 4): "São Raimundo-RR",
    }

    for index, row in sporting.iterrows():
        key = (
            int(row["season"]),
            int(row["division"]),
            row["group"],
            clean_text(row["club"]),
            int(row["league_position"]),
        )
        if key in known_identities:
            sporting.at[index, "club"] = known_identities[key]

    sporting["group"] = sporting["group"].replace("", pd.NA)
    return sporting



FINANCIAL_CLUBS = {
    "América-MG", "Athletico-PR", "Atlético-GO", "Atlético-MG", "Avaí",
    "Bahia", "Botafogo", "Ceará", "Chapecoense", "Corinthians", "Coritiba",
    "Criciúma", "CSA", "Cruzeiro", "Cuiabá", "Figueirense", "Flamengo",
    "Fluminense", "Fortaleza", "Goiás", "Grêmio", "Internacional", "Juventude",
    "Mirassol", "Palmeiras", "Paraná Clube", "Ponte Preta",
    "Red Bull Bragantino", "Remo", "Santa Cruz", "Santos", "Sport",
    "São Paulo", "Vasco", "Vitória",
}

POST_OUTCOME_IDENTITY_FIXES = {
    (2018, 3, "A", "Atlético"): "Atlético-AC",
    (2018, 4, "A06", "América"): "América-RN",
    (2018, 4, "A13", "Atletico"): "Atlético-ES",
    (2019, 3, "B", "Atlético"): "Atlético-AC",
    (2020, 4, "A-03", "América"): "América-RN",
    (2021, 4, "A03", "América"): "América-RN",
    (2022, 4, "A3", "América"): "América-RN",
    (2023, 3, "", "América"): "América-RN",
    (2024, 4, "A3", "America F.c. Saf"): "América-RN",
    (2025, 4, "A3", "America F.c. Saf"): "América-RN",
    (2018, 3, "A", "Botafogo"): "Botafogo-PB",
    (2018, 3, "B", "Botafogo"): "Botafogo-SP",
    (2018, 4, "A08", "Flamengo"): "Flamengo-PE",

    (2019, 2, "", "Botafogo"): "Botafogo-SP",
    (2019, 3, "A", "Botafogo"): "Botafogo-PB",
    (2019, 4, "A01", "São Raimundo"): "São Raimundo-RR",
    (2019, 4, "A03", "São Raimundo"): "São Raimundo-PA",
    (2019, 4, "A03", "Ypiranga"): "Ypiranga-AP",
    (2019, 4, "A04", "Santa Cruz"): "Santa Cruz-RN",
    (2019, 4, "A07", "Vitória"): "Vitória-ES",
    (2019, 4, "A11", "Operário"): "Operário-MT",

    (2020, 2, "", "Botafogo"): "Botafogo-SP",
    (2020, 3, "A", "Botafogo"): "Botafogo-PB",
    (2020, 4, "A-01", "Atlético"): "Atlético-AC",
    (2020, 4, "A-02", "Santos"): "Santos-AP",
    (2020, 4, "A-05", "Operário"): "Operário-MT",
    (2020, 4, "A-06", "Atlético"): "Atlético-BA",

    (2021, 3, "A", "Botafogo"): "Botafogo-PB",
    (2021, 3, "B", "Botafogo"): "Botafogo-SP",
    (2021, 4, "A01", "Atlético"): "Atlético-AC",
    (2021, 4, "A01", "Ypiranga"): "Ypiranga-AP",
    (2021, 4, "A02", "Juventude"): "Juventude-MA",
    (2021, 4, "A04", "Atlético"): "Atlético-BA",

    (2022, 4, "A2", "Fluminense"): "Fluminense-PI",
    (2022, 4, "A2", "Juventude"): "Juventude-MA",
    (2022, 4, "A4", "Atlético"): "Atlético-BA",
    (2022, 4, "A5", "Operário"): "Operário-MT",

    (2023, 2, "", "Botafogo"): "Botafogo-SP",
    (2023, 3, "", "Botafogo"): "Botafogo-PB",
    (2023, 4, "A1", "Nacional"): "Nacional-AM",
    (2023, 4, "A2", "Fluminense"): "Fluminense-PI",
    (2023, 4, "A3", "Nacional"): "Nacional-PB",
    (2023, 4, "A4", "Atlético"): "Atlético-BA",
    (2023, 4, "A4", "Cruzeiro"): "Cruzeiro-AL",
    (2023, 4, "A7", "Operário"): "Operário-MS",

    (2024, 2, "", "Botafogo"): "Botafogo-SP",
    (2024, 3, "A", "Botafogo"): "Botafogo-PB",
    (2024, 4, "A2", "Fluminense"): "Fluminense-PI",

    (2025, 2, "", "Botafogo"): "Botafogo-SP",
    (2025, 4, "A7", "Operário"): "Operário-MS",
}

DIRECT_FINANCIAL_ALIASES = {
    "Avaí": "Avaí",
    "Avaí/SC": "Avaí",
    "Bahia": "Bahia",
    "Bahia/BA": "Bahia",
    "Ceará": "Ceará",
    "Ceará/CE": "Ceará",
    "Chapecoense": "Chapecoense",
    "Chapecoense/SC": "Chapecoense",
    "Corinthians": "Corinthians",
    "Corinthians/SP": "Corinthians",
    "Coritiba": "Coritiba",
    "Coritiba S.a.f.": "Coritiba",
    "Coritiba/PR": "Coritiba",
    "Criciúma": "Criciúma",
    "Criciúma/SC": "Criciúma",
    "CSA/AL": "CSA",
    "Csa": "CSA",
    "Cuiabá": "Cuiabá",
    "Cuiabá Saf": "Cuiabá",
    "Cuiabá/MT": "Cuiabá",
    "Figueirense": "Figueirense",
    "Figueirense Fc S.a.f": "Figueirense",
    "Figueirense Fc S.a.f.": "Figueirense",
    "Figueirense/SC": "Figueirense",
    "Fortaleza": "Fortaleza",
    "Fortaleza Ec Saf": "Fortaleza",
    "Fortaleza/CE": "Fortaleza",
    "Goiás": "Goiás",
    "Goiás/GO": "Goiás",
    "Grêmio": "Grêmio",
    "Grêmio/RS": "Grêmio",
    "Mirassol": "Mirassol",
    "Palmeiras": "Palmeiras",
    "Palmeiras/SP": "Palmeiras",
    "Parana": "Paraná Clube",
    "Paraná": "Paraná Clube",
    "Paraná Clube": "Paraná Clube",
    "Paraná/PR": "Paraná Clube",
    "Ponte Preta": "Ponte Preta",
    "Ponte Preta/SP": "Ponte Preta",
    "Remo": "Remo",
    "Remo/PA": "Remo",
    "Sport": "Sport",
    "Sport Recife": "Sport",
    "Sport/PE": "Sport",
    "São Paulo": "São Paulo",
    "São Paulo/SP": "São Paulo",
    "Vasco": "Vasco",
    "Vasco da Gama": "Vasco",
    "Vasco da Gama S.a.f.": "Vasco",
    "Vasco da Gama Saf": "Vasco",
    "Vasco da Gama/RJ": "Vasco",
}


def canonical_financial_club(row):
    year = int(row["season"])
    division = int(row["division"])
    club = clean_text(row["club"])

    if club in DIRECT_FINANCIAL_ALIASES:
        return DIRECT_FINANCIAL_ALIASES[club]

    if club == "América" and (year, division) == (2016, 1):
        return "América-MG"
    if club == "América/MG" and (year, division) == (2017, 2):
        return "América-MG"
    if club == "America Fc" and (year, division) == (2018, 1):
        return "América-MG"
    if club == "America" and (year, division) in {(2019, 2), (2020, 2), (2021, 1)}:
        return "América-MG"
    if club == "America Saf" and (year, division) in {
        (2022, 1), (2023, 1), (2024, 2), (2025, 2)
    }:
        return "América-MG"

    if club in {"Atlético/PR", "Athletico/PR", "Athletico Paranaense"}:
        return "Athletico-PR"

    if club in {"Atlético/MG", "Atlético-MG", "Atlético Mineiro", "Atlético Mineiro Saf"}:
        return "Atlético-MG"
    if club == "Atlético" and division == 1 and year in {2018, 2019}:
        return "Atlético-MG"

    if club in {"Atlético/GO", "Atlético-GO", "Atlético Goianiense Saf"}:
        return "Atlético-GO"
    if club == "Atlético" and (year, division) in {
        (2018, 2), (2019, 2), (2021, 1), (2022, 1), (2023, 2)
    }:
        return "Atlético-GO"

    if club == "Botafogo/RJ":
        return "Botafogo"
    if club == "Botafogo" and (
        (division == 1 and year in {2016, 2018, 2019, 2020, 2022, 2023, 2024, 2025})
        or (year, division) == (2021, 2)
    ):
        return "Botafogo"

    if club in {"Cruzeiro/MG", "Cruzeiro Saf"}:
        return "Cruzeiro"
    if club == "Cruzeiro" and division in {1, 2}:
        return "Cruzeiro"

    if club == "Flamengo/RJ":
        return "Flamengo"
    if club == "Flamengo" and division == 1:
        return "Flamengo"

    if club == "Fluminense/RJ":
        return "Fluminense"
    if club == "Fluminense" and division == 1:
        return "Fluminense"

    if club == "Internacional/RS":
        return "Internacional"
    if club == "Internacional" and division in {1, 2}:
        return "Internacional"

    if club == "Juventude/RS":
        return "Juventude"
    if club == "Juventude" and division in {1, 2, 3}:
        return "Juventude"

    if club == "Bragantino/SP" and (year, division) == (2017, 3):
        return "Red Bull Bragantino"
    if club == "Bragantino" and (year, division) in {(2016, 2), (2018, 3)}:
        return "Red Bull Bragantino"
    if club == "Red Bull Bragantino":
        return "Red Bull Bragantino"

    if club == "Santa Cruz/PE":
        return "Santa Cruz"
    if club == "Santa Cruz" and (year, division) in {
        (2016, 1), (2018, 3), (2019, 3), (2020, 3), (2021, 3),
        (2022, 4), (2023, 4), (2025, 4),
    }:
        return "Santa Cruz"

    if club in {"Santos/SP", "Santos Fc"}:
        return "Santos"
    if club == "Santos" and division in {1, 2}:
        return "Santos"

    if club == "Vitória/BA":
        return "Vitória"
    if club == "Vitória" and division in {1, 2, 3}:
        return "Vitória"

    return club


def normalize_club_identities(sporting):
    sporting = sporting.copy()

    for index, row in sporting.iterrows():
        group = "" if pd.isna(row["group"]) else clean_text(row["group"])
        key = (
            int(row["season"]),
            int(row["division"]),
            group,
            clean_text(row["club"]),
        )
        if key in POST_OUTCOME_IDENTITY_FIXES:
            sporting.at[index, "club"] = POST_OUTCOME_IDENTITY_FIXES[key]

    sporting["club"] = sporting.apply(canonical_financial_club, axis=1)

    validate_identity_integrity(sporting)
    validate_financial_club_continuity(sporting)
    return sporting


def validate_identity_integrity(sporting):
    repeated = sporting[
        sporting.duplicated(subset=["season", "club"], keep=False)
    ]

    if not repeated.empty:
        details = repeated[
            ["season", "division", "group", "club", "league_position"]
        ].sort_values(["season", "club", "division", "group"])
        raise ValueError(
            "Unresolved club identity collision across national divisions:\n"
            + details.to_string(index=False)
        )

    financial_rows = sporting[sporting["club"].isin(FINANCIAL_CLUBS)]
    missing_clubs = FINANCIAL_CLUBS - set(financial_rows["club"].unique())

    if missing_clubs:
        raise ValueError(
            "Financial clubs never matched in sporting staging: "
            + ", ".join(sorted(missing_clubs))
        )


def validate_financial_club_continuity(sporting):
    financial = sporting[sporting["club"].isin(FINANCIAL_CLUBS)]

    for club, club_data in financial.groupby("club"):
        seasons = {
            int(row["season"]): row
            for _, row in club_data.iterrows()
        }

        for year in range(2016, 2025):
            current = seasons.get(year)
            following = seasons.get(year + 1)

            if current is None:
                continue

            promoted = int(current["promoted"])
            relegated = int(current["relegated"])

            if following is None:
                current_division = int(current["division"])

                if current_division < 4 or promoted == 1:
                    raise ValueError(
                        f"Unexpected missing next-season national record: "
                        f"{club}, {year}"
                    )

                continue

            expected_division = int(current["division"]) - promoted + relegated
            actual_division = int(following["division"])

            if actual_division != expected_division:
                raise ValueError(
                    f"Division continuity failed for {club}: "
                    f"{year} Série {int(current['division'])} -> "
                    f"{year + 1} Série {actual_division}; "
                    f"expected Série {expected_division}"
                )



def clean_single_table_groups(sporting):
    sporting = sporting.copy()

    for _, indexes in sporting.groupby(["season", "division"]).groups.items():
        data = sporting.loc[indexes]
        groups = data["group"].fillna("").astype(str).str.strip().unique()

        if len(groups) == 1:
            sporting.loc[indexes, "group"] = pd.NA

    return sporting

def save_raw(directory, year, division, html):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{year}_serie_{division}.html"
    path.write_text(html, encoding="utf-8")


def empty_row(year, division, source, source_url, club, group, position, matches, points, gf, ga):
    return {
        "club": club,
        "season": year,
        "division": DIVISIONS[division],
        "stage": "full_season" if division in ("a", "b") else "first_stage",
        "group": group,
        "matches_played": matches,
        "points": points,
        "goals_for": gf,
        "goals_against": ga,
        "league_position": position,
        "league_size": None,
        "promoted": pd.NA,
        "relegated": pd.NA,
        "table_source": source,
        "table_source_url": source_url,
        "outcome_source": pd.NA,
        "notes": pd.NA,
    }


# CBF

def parse_cbf_position_and_club(cell):
    text = clean_text(cell.get_text(" ", strip=True))

    strong = cell.find("strong")
    if strong:
        match = re.search(r"(\d+)", strong.get_text(" ", strip=True))
    else:
        match = re.match(r"\s*(\d+)", text)

    if not match:
        raise ValueError(f"CBF position not found in: {text}")

    position = int(match.group(1))

    link = cell.find("a")
    if link and clean_text(link.get_text(" ", strip=True)):
        club = clean_text(link.get_text(" ", strip=True))
    else:
        club = re.sub(r"^\s*\d+\s*(?:[+-]\s*\d+|0)?\s*", "", text).strip()

    if not club:
        raise ValueError(f"CBF club name not found in: {text}")

    return position, club


def cbf_group_name(table):
    heading = table.find_previous(["h2", "h3", "h4", "h5", "strong"])
    if not heading:
        return ""

    text = clean_text(heading.get_text(" ", strip=True))
    label = normalize_label(text)

    if "grupo unico" in label:
        return ""
    if label.startswith("grupo"):
        return re.sub(r"(?i)^grupo\s*", "", text).strip(" :-")
    return ""


def cbf_header_index(headers, accepted):
    for index, header in enumerate(headers):
        label = normalize_label(header)
        if any(label == item or label.startswith(item + " ") for item in accepted):
            return index
    return None


def parse_cbf_html(html, year, division, source_url):
    soup = BeautifulSoup(html, "html.parser")
    rows = []

    for table in soup.find_all("table"):
        header_row = None
        for tr in table.find_all("tr"):
            if tr.find_all("th"):
                header_row = tr
                break

        if header_row is None:
            continue

        headers = [clean_text(cell.get_text(" ", strip=True)) for cell in header_row.find_all("th")]

        pos_i = cbf_header_index(headers, ["classificacao"])
        pts_i = cbf_header_index(headers, ["pts", "pontos"])
        m_i = cbf_header_index(headers, ["j", "jogos"])
        gf_i = cbf_header_index(headers, ["gp", "gols pros"])
        ga_i = cbf_header_index(headers, ["gc", "gols contras"])

        required = [pos_i, pts_i, m_i, gf_i, ga_i]
        if any(index is None for index in required):
            continue

        group = cbf_group_name(table)
        table_rows = []

        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if not cells or max(required) >= len(cells):
                continue

            try:
                position, club = parse_cbf_position_and_club(cells[pos_i])
                points = int(clean_text(cells[pts_i].get_text(" ", strip=True)))
                matches = int(clean_text(cells[m_i].get_text(" ", strip=True)))
                gf = int(clean_text(cells[gf_i].get_text(" ", strip=True)))
                ga = int(clean_text(cells[ga_i].get_text(" ", strip=True)))
            except (ValueError, TypeError):
                continue

            table_rows.append(
                empty_row(
                    year, division, "CBF", source_url,
                    club, group, position, matches, points, gf, ga,
                )
            )

        if table_rows:
            table_df = pd.DataFrame(table_rows, columns=COLUMNS)
            table_df = table_df.drop_duplicates(
                subset=["club", "league_position", "matches_played", "points", "goals_for", "goals_against"]
            )
            league_size = len(table_df)
            table_df["league_size"] = league_size
            rows.extend(table_df.to_dict("records"))

    if not rows:
        raise ValueError("CBF classification table not found after JavaScript rendering")

    data = pd.DataFrame(rows, columns=COLUMNS)
    data = data.drop_duplicates().reset_index(drop=True)

    validate_competition(data)
    return data


def phase_label_priority(text):
    label = normalize_label(text).strip(" :-")

    if re.fullmatch(r"(?:1\s*a|primeira|first)\s+(?:fase|phase|stage)", label):
        return 0

    if label == "turno":
        return 1

    return None


def extract_navigation_url(element, base_url):
    for attribute in ("href", "data-href", "data-url"):
        value = element.get_attribute(attribute)
        if value:
            return urljoin(base_url, value)

    onclick = element.get_attribute("onclick") or ""
    match = re.search(r"['\"]([^'\"]+/futebol-brasileiro/[^'\"]+)['\"]", onclick)
    if match:
        return urljoin(base_url, match.group(1))

    return None


def open_first_stage(page, base_url):
    candidates = []
    elements = page.locator("a, button, [role='tab'], [data-href], [data-url]")

    for i in range(elements.count()):
        element = elements.nth(i)
        try:
            text = clean_text(element.inner_text(timeout=800))
        except Exception:
            continue

        priority = phase_label_priority(text)
        if priority is not None:
            candidates.append((priority, i, text))

    candidates.sort(key=lambda item: item[0])

    for _, i, _ in candidates:
        element = elements.nth(i)
        target_url = extract_navigation_url(element, base_url)

        if target_url:
            goto(page, target_url)
            return page.url

        try:
            element.click(timeout=2500)
            page.wait_for_timeout(1200)
            return page.url
        except Exception:
            continue

    raise ValueError("CBF first-stage navigation was not found in the rendered page")


def goto(page, url):
    last_error = None
    for attempt in range(2):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(1200)
            return
        except Exception as error:
            last_error = error
            if attempt == 0:
                page.wait_for_timeout(1500)
    raise last_error


def collect_cbf(page, year, division):
    base_url = f"{CBF_BASE}/serie-{division}/{year}"
    goto(page, base_url)

    if division in ("c", "d"):
        open_first_stage(page, base_url)

    source_url = page.url
    html = page.content()

    try:
        data = parse_cbf_html(html, year, division, source_url)
    except Exception:
        if division in ("a", "b"):
            alternative_url = base_url + "?documento=Tabela+Detalhada"
            goto(page, alternative_url)
            source_url = page.url
            html = page.content()
            data = parse_cbf_html(html, year, division, source_url)
        else:
            raise

    save_raw(RAW_CBF_DIR, year, division, html)
    return data


# RSSSF Brasil

def rsssf_url(year, division):
    suffix = {"a": "", "b": "l2", "c": "l3", "d": "l4"}[division]
    return f"{RSSSF_BASE}/br{year}{suffix}.htm"


def get_first_phase_text(text):
    lines = text.replace("\r", "").split("\n")

    first_patterns = [
        re.compile(r"^\s*first\s+phase\s*:??\s*$", re.I),
        re.compile(r"^\s*first\s+stage\s*:??\s*$", re.I),
        re.compile(r"^\s*primeira\s+fase\s*:??\s*$", re.I),
        re.compile(r"^\s*1(?:st|a|ª)\s+(?:phase|fase)\s*:??\s*$", re.I),
    ]
    second_patterns = [
        re.compile(r"^\s*second\s+phase\b", re.I),
        re.compile(r"^\s*second\s+stage\b", re.I),
        re.compile(r"^\s*segunda\s+fase\b", re.I),
        re.compile(r"^\s*2(?:nd|a|ª)\s+(?:phase|fase)\b", re.I),
    ]

    start = None
    for i, line in enumerate(lines):
        candidate = re.sub(r"^#+\s*", "", line).strip()
        if any(pattern.match(candidate) for pattern in first_patterns):
            start = i
            break

    if start is None:
        raise ValueError("RSSSF first-phase section not found")

    end = len(lines)
    for i in range(start + 1, len(lines)):
        candidate = re.sub(r"^#+\s*", "", lines[i]).strip()
        if any(pattern.match(candidate) for pattern in second_patterns):
            end = i
            break

    return "\n".join(lines[start:end])


def rsssf_group_name(line):
    line = re.sub(r"^#+\s*", "", clean_text(line)).rstrip(":")
    match = re.match(r"^\s*(?:group|grupo)\s+(.+?)\s*$", line, re.I)
    if not match:
        return None

    group = clean_text(match.group(1))
    if normalize_label(group) in {"unico", "unica", "unique"}:
        return ""
    return group


def parse_pipe_tables(text, year, division, source_url):
    lines = text.replace("\t", " | ").splitlines()
    rows = []
    group = ""
    i = 0

    while i < len(lines):
        line = clean_text(lines[i])
        group_found = rsssf_group_name(line)
        if group_found is not None:
            group = group_found
            i += 1
            continue

        if "|" not in line:
            i += 1
            continue

        header = [clean_text(part) for part in line.split("|")]
        labels = [normalize_label(part) for part in header]

        def idx(options):
            for j, label in enumerate(labels):
                if label in options:
                    return j
            return None

        pos_i = idx({"pos", "position"})
        team_i = idx({"team", "clube", "time"})
        pts_i = idx({"pts", "pontos"})
        m_i = idx({"m", "j", "jogos"})
        gf_i = idx({"gf", "gp"})
        ga_i = idx({"ga", "gc"})

        required = [pos_i, team_i, pts_i, m_i, gf_i, ga_i]
        if any(value is None for value in required):
            i += 1
            continue

        j = i + 1
        while j < len(lines):
            row_line = clean_text(lines[j])

            if not row_line:
                j += 1
                continue

            next_group = rsssf_group_name(row_line)
            if next_group is not None:
                break

            if "|" not in row_line:
                if rows:
                    break
                j += 1
                continue

            parts = [clean_text(part) for part in row_line.split("|")]
            if max(required) >= len(parts):
                j += 1
                continue

            try:
                position_text = re.sub(r"[^0-9]", "", parts[pos_i])
                if not position_text:
                    j += 1
                    continue

                position = int(position_text)
                club = clean_text(parts[team_i])
                points = int(re.search(r"-?\d+", parts[pts_i]).group())
                matches = int(re.search(r"\d+", parts[m_i]).group())
                gf = int(re.search(r"\d+", parts[gf_i]).group())
                ga = int(re.search(r"\d+", parts[ga_i]).group())
            except (AttributeError, ValueError):
                j += 1
                continue

            rows.append(
                empty_row(
                    year, division, "RSSSF Brasil", source_url,
                    club, group, position, matches, points, gf, ga,
                )
            )
            j += 1

        i = max(i + 1, j)

    return rows


def parse_points_first_standings(text, year, division, source_url):
    rows = []
    group = ""

    pattern = re.compile(
        r"^\s*(\d+)\.\s*"
        r"(.+?)\s+"
        r"(-?\d+)\s+"
        r"(\d+)\s+"
        r"\d+\s+"
        r"\d+\s+"
        r"\d+\s+"
        r"(\d+)\s+"
        r"(\d+)\s+"
        r"[-+]?\d+\b"
    )

    for raw_line in text.splitlines():
        line = clean_text(raw_line)

        group_found = rsssf_group_name(line)
        if group_found is not None:
            group = group_found
            continue

        match = pattern.match(line)
        if not match:
            continue

        position = int(match.group(1))
        club = clean_text(match.group(2))
        points = int(match.group(3))
        matches = int(match.group(4))
        gf = int(match.group(5))
        ga = int(match.group(6))

        rows.append(
            empty_row(
                year, division, "RSSSF Brasil", source_url,
                club, group, position, matches, points, gf, ga,
            )
        )

    return rows


def parse_fixed_width_standings(text, year, division, source_url):
    lines = text.splitlines()
    rows = []
    group = ""

    pattern = re.compile(
        r"^\s*(\d+)\s*[\.]?\s*"
        r"(.+?)\s+"
        r"(\d+)\s+"
        r"(\d+)\s+"
        r"(\d+)\s+"
        r"(\d+)\s+"
        r"(\d+)\s*-\s*(\d+)\s+"
        r"(-?\d+)"
        r"(?:\s+.*)?$"
    )

    for line in lines:
        group_found = rsssf_group_name(line)
        if group_found is not None:
            group = group_found
            continue

        match = pattern.match(line)
        if not match:
            continue

        position = int(match.group(1))
        club = clean_text(match.group(2))
        matches = int(match.group(3))
        gf = int(match.group(7))
        ga = int(match.group(8))
        points = int(match.group(9))

        rows.append(
            empty_row(
                year, division, "RSSSF Brasil", source_url,
                club, group, position, matches, points, gf, ga,
            )
        )

    return rows


def assign_league_sizes(data):
    data = data.copy()

    if data["group"].fillna("").eq("").all():
        data["league_size"] = len(data)
    else:
        sizes = data.groupby("group", dropna=False)["club"].transform("size")
        data["league_size"] = sizes

    return data


def parse_rsssf_text(text, year, division, source_url):
    selected = text if division in ("a", "b") else get_first_phase_text(text)

    rows = parse_pipe_tables(selected, year, division, source_url)

    if not rows:
        rows = parse_points_first_standings(selected, year, division, source_url)

    if not rows:
        rows = parse_fixed_width_standings(selected, year, division, source_url)

    if not rows:
        raise ValueError("RSSSF standings could not be parsed")

    data = pd.DataFrame(rows, columns=COLUMNS)
    data = data.drop_duplicates().reset_index(drop=True)
    data = assign_league_sizes(data)
    validate_competition(data)
    return data


def collect_rsssf(page, year, division):
    url = rsssf_url(year, division)
    goto(page, url)

    html = page.content()
    text = page.locator("body").inner_text(timeout=10000)
    data = parse_rsssf_text(text, year, division, page.url)

    save_raw(RAW_RSSSF_DIR, year, division, html)
    return data


def parse_uol_row_cells(cells):
    values = [clean_text(cell.get_text(" ", strip=True)) for cell in cells]
    values = [value for value in values if value]

    if len(values) < 9:
        return None

    pos_match = re.match(r"^(\d+)\s*[°ºo]?\s*(.*)$", values[0], re.I)
    if not pos_match:
        return None

    position = int(pos_match.group(1))
    same_cell_club = clean_text(pos_match.group(2))

    if same_cell_club:
        club = same_cell_club
        numeric_start = 1
    else:
        if len(values) < 10:
            return None
        club = values[1]
        numeric_start = 2

    numbers = []
    for value in values[numeric_start:]:
        match = re.search(r"-?\d+", value)
        if match:
            numbers.append(int(match.group()))

    if len(numbers) < 8:
        return None

    points, matches, wins, draws, losses, gf, ga = numbers[:7]

    if matches != wins + draws + losses:
        raise ValueError(f"UOL row failed J=V+E+D check: {club}")

    if points != 3 * wins + draws:
        raise ValueError(f"UOL row failed points check: {club}")

    return position, club, points, matches, gf, ga


def parse_uol_html(html, year, division, source_url):
    soup = BeautifulSoup(html, "html.parser")
    rows = []

    for table in soup.find_all("table"):
        table_text = normalize_label(table.get_text(" ", strip=True))
        if not all(token in table_text for token in ("classificacao", "pg", "gp", "gc")):
            continue

        candidate_rows = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            parsed = parse_uol_row_cells(cells)
            if parsed is None:
                continue

            position, club, points, matches, gf, ga = parsed
            candidate_rows.append(
                empty_row(
                    year, division, "UOL Esporte", source_url,
                    club, "", position, matches, points, gf, ga,
                )
            )

        if len(candidate_rows) > len(rows):
            rows = candidate_rows

    if not rows:
        raise ValueError("UOL standings table could not be parsed")

    data = pd.DataFrame(rows, columns=COLUMNS).drop_duplicates().reset_index(drop=True)
    data["league_size"] = len(data)

    if int(data["goals_for"].sum()) != int(data["goals_against"].sum()):
        raise ValueError("UOL table failed aggregate GF=GA check")

    validate_competition(data)
    return data


def collect_uol_2016_b(page):
    goto(page, UOL_2016_B_URL)
    html = page.content()
    data = parse_uol_html(html, 2016, "b", page.url)
    data["notes"] = (
        "CBF table unavailable for automated extraction and RSSSF Brasil archive is incomplete "
        "for this edition; UOL Esporte used as exceptional fallback."
    )
    save_raw(RAW_EXCEPTION_DIR, 2016, "b", html)
    return data


# QA

def validate_competition(data):
    if data.empty:
        raise ValueError("No rows extracted")

    year = int(data["season"].iloc[0])
    division = int(data["division"].iloc[0])

    expected_group_sizes = {
        1: [20],
        2: [20],
        3: [10, 10] if year <= 2021 else [20],
        4: [4] * 17 if year <= 2019 else [8] * 8,
    }

    actual_group_sizes = sorted(
        data.groupby("group", dropna=False).size().astype(int).tolist()
    )

    if actual_group_sizes != expected_group_sizes[division]:
        raise ValueError(
            f"Unexpected competition structure for {year} Série "
            f"{chr(64 + division)}: group sizes={actual_group_sizes}"
        )

    numeric = [
        "matches_played", "points", "goals_for", "goals_against",
        "league_position", "league_size",
    ]

    for column in numeric:
        if data[column].isna().any():
            raise ValueError(f"Missing values in {column}")

    if (data["matches_played"] <= 0).any():
        raise ValueError("Invalid matches_played")
    if (data["league_position"] <= 0).any():
        raise ValueError("Invalid league_position")
    if (data["league_size"] <= 1).any():
        raise ValueError("Invalid league_size")

    duplicated_positions = data.duplicated(
        subset=["season", "division", "group", "league_position"],
        keep=False,
    )
    if duplicated_positions.any():
        raise ValueError("Duplicate league positions inside the same group")

    for _, group_data in data.groupby("group", dropna=False):
        size_values = group_data["league_size"].astype(int).unique().tolist()
        if len(size_values) != 1:
            raise ValueError("Inconsistent league_size inside a group")

        size = size_values[0]
        if size != len(group_data):
            raise ValueError("league_size does not match extracted group size")

        positions = sorted(group_data["league_position"].astype(int).tolist())
        if positions != list(range(1, size + 1)):
            raise ValueError("League positions are not contiguous from 1 to league_size")

        if int(group_data["goals_for"].sum()) != int(group_data["goals_against"].sum()):
            raise ValueError("Group failed aggregate GF=GA check")


    if division in (1, 2):
        expected_matches = 38
    elif division == 3:
        expected_matches = 18 if year <= 2021 else 19
    else:
        expected_matches = 6 if year <= 2019 else 14

    wrong_matches = data[data["matches_played"] != expected_matches]

    if year == 2016 and division == 1:
        allowed_37 = {"Atlético/MG", "Atlético-MG", "Atlético", "Chapecoense"}
        wrong_matches = data[
            (data["matches_played"] != 38)
            & ~(
                (data["matches_played"] == 37)
                & data["club"].isin(allowed_37)
            )
        ]

        if int((data["matches_played"] == 37).sum()) != 2:
            raise ValueError(
                "2016 Série A should contain exactly two 37-match records"
            )

    if not wrong_matches.empty:
        details = wrong_matches[
            ["club", "matches_played", "league_size"]
        ].to_dict("records")
        raise ValueError(
            f"Unexpected matches_played for {year} Série "
            f"{chr(64 + division)}: {details}"
        )


def collect_competition(page, year, division):
    cbf_error = None
    rsssf_error = None

    try:
        return collect_cbf(page, year, division), "CBF"
    except Exception as error:
        cbf_error = str(error)

    try:
        data = collect_rsssf(page, year, division)
        if data["notes"].isna().all():
            data["notes"] = "Official CBF table unavailable for automated extraction; RSSSF Brasil used as fallback."
        return data, "RSSSF Brasil"
    except Exception as error:
        rsssf_error = str(error)

    if year == 2016 and division == "b":
        try:
            return collect_uol_2016_b(page), "UOL Esporte"
        except Exception as uol_error:
            raise RuntimeError(
                f"CBF failed: {cbf_error} | RSSSF failed: {rsssf_error} | "
                f"Exceptional fallback failed: {uol_error}"
            ) from uol_error

    raise RuntimeError(
        f"CBF failed: {cbf_error} | RSSSF failed: {rsssf_error} | "
        "Exceptional fallback failed: No exceptional source configured for this competition"
    )


def launch_browser(playwright):
    last_error = None

    for channel in ("msedge", "chrome", None):
        try:
            kwargs = {
                "headless": True,
                "args": ["--disable-blink-features=AutomationControlled"],
            }
            if channel is not None:
                kwargs["channel"] = channel

            browser = playwright.chromium.launch(**kwargs)
            print(f"Browser OK ({channel or 'Playwright Chromium'})")
            return browser
        except Exception as error:
            last_error = error

    raise RuntimeError(f"Could not launch Edge/Chrome/Chromium: {last_error}") from last_error



def save_outputs(all_data, errors):
    if all_data:
        sporting = pd.concat(all_data, ignore_index=True)
        sporting = clean_validated_staging(sporting)
        sporting = apply_outcomes(sporting)
        sporting = normalize_club_identities(sporting)
        sporting = clean_single_table_groups(sporting)
        sporting = sporting.sort_values(
            ["season", "division", "group", "league_position"],
            na_position="last",
        ).reset_index(drop=True)

        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        sporting.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        print(f"\nStaging saved to: {OUTPUT_FILE}")
        print(f"Rows collected: {len(sporting)}")

    if errors:
        error_df = pd.DataFrame(errors)
        ERROR_FILE.parent.mkdir(parents=True, exist_ok=True)
        error_df.to_csv(ERROR_FILE, index=False, encoding="utf-8-sig")
        print(f"\nCollection errors saved to: {ERROR_FILE}")
        print(error_df.to_string(index=False))
    elif ERROR_FILE.exists():
        ERROR_FILE.unlink()


def main():
    all_data = []
    errors = []

    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1600, "height": 1000},
        )
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )

        page = context.new_page()
        page.set_default_timeout(15000)
        page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,eot}", lambda route: route.abort())

        print("\nPreflight...")
        goto(page, f"{CBF_BASE}/serie-a/2025")
        print("  CBF page reachable for 2025")
        print("Preflight OK\n")

        try:
            for year in YEARS:
                for division in DIVISIONS:
                    print(f"Collecting {year} Série {division.upper()}...")

                    try:
                        data, source = collect_competition(page, year, division)
                        all_data.append(data)
                        print(f"  OK: {len(data)} rows | source: {source}")
                    except Exception as error:
                        errors.append({
                            "season": year,
                            "division": division.upper(),
                            "error": str(error),
                        })
                        print(f"  ERROR: {error}")

                    time.sleep(0.25)

        except KeyboardInterrupt:
            print("\nInterrupted by user. Saving partial results...")
        finally:
            browser.close()

    save_outputs(all_data, errors)


if __name__ == "__main__":
    main()

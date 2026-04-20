"""
Scrape FVCC tuition & fees from the actual rate table page.
The main tuition page is useless marketing fluff — the real numbers
are on the linked 2025-2026 schedule behind tabs the website buries.

Outputs: data/tuition.json
"""

import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

TUITION_URL = "https://www.fvcc.edu/admissions-financial-aid/tuition-fees/tuition-fees-2025-2026"

# The page has 4 sections (h2 headings), each with tabbed tables.
# Tabs within each campus section are: Flathead County Resident, Montana Resident, Out-of-State
# The order of tables on the page (verified by scraping):
TABLE_LABELS = [
    # Flathead County Campus (3 tabs)
    {"campus": "Flathead County Campus", "residency": "Flathead County Resident"},
    {"campus": "Flathead County Campus", "residency": "Montana Resident"},
    {"campus": "Flathead County Campus", "residency": "Out-of-State"},
    # Lincoln County Campus (3 tabs)
    {"campus": "Lincoln County Campus", "residency": "Flathead County Resident"},
    {"campus": "Lincoln County Campus", "residency": "Montana Resident"},
    {"campus": "Lincoln County Campus", "residency": "Out-of-State"},
    # Running Start (2 tabs)
    {"campus": "Running Start", "residency": "In-State"},
    {"campus": "Running Start", "residency": "Out-of-State"},
    # WUE (1 table)
    {"campus": "Western Undergraduate Exchange (WUE)", "residency": "WUE"},
]


def parse_float(s: str) -> float:
    """Parse a currency string like '1,326.06' or '–' into a float."""
    s = s.strip().replace(",", "").replace("$", "")
    if s in ("–", "-", "", "—"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def scrape_tuition() -> dict:
    print(f"Fetching {TUITION_URL}")
    resp = requests.get(TUITION_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    tables = soup.find_all("table")
    print(f"Found {len(tables)} tables")

    all_tables = []
    for i, table in enumerate(tables):
        rows = table.find_all("tr")
        headers = []
        data_rows = []
        for row in rows:
            ths = row.find_all("th")
            tds = row.find_all("td")
            if ths and not tds:
                headers = [th.get_text(strip=True) for th in ths]
            elif tds:
                cells = [td.get_text(strip=True) for td in tds]
                data_rows.append(cells)
        all_tables.append({"headers": headers, "rows": data_rows})

    if len(tables) != len(TABLE_LABELS):
        print(f"WARNING: Expected {len(TABLE_LABELS)} tables, got {len(tables)}")

    # Build structured tuition data
    tuition_tables = []
    for i, table_data in enumerate(all_tables):
        label = TABLE_LABELS[i] if i < len(TABLE_LABELS) else {"campus": "Unknown", "residency": "Unknown"}
        has_age65 = any("65" in h for h in table_data["headers"])

        rate_rows = []
        for row in table_data["rows"]:
            if not row or not row[0]:
                continue
            try:
                credits = float(row[0])
            except ValueError:
                continue

            entry = {
                "credits": credits,
                "tuition": parse_float(row[1]) if len(row) > 1 else 0,
                "infrastructure_fee": parse_float(row[2]) if len(row) > 2 else 0,
                "technology_fee": parse_float(row[3]) if len(row) > 3 else 0,
                "activity_fee": parse_float(row[4]) if len(row) > 4 else 0,
                "equipment_fee": parse_float(row[5]) if len(row) > 5 else 0,
                "health_center_fee": parse_float(row[6]) if len(row) > 6 else 0,
            }
            # Total is second-to-last or last depending on age65 column
            if has_age65 and len(row) >= 9:
                entry["total"] = parse_float(row[7])
                entry["age_65_plus"] = parse_float(row[8])
            elif len(row) >= 8:
                entry["total"] = parse_float(row[7])
            else:
                entry["total"] = parse_float(row[-1])

            rate_rows.append(entry)

        tuition_tables.append({
            **label,
            "rates": rate_rows,
        })

    # Extract the key per-credit rates for the summary
    summary = {}
    for t in tuition_tables:
        one_credit = next((r for r in t["rates"] if r["credits"] == 1.0), None)
        if one_credit:
            key = f"{t['campus']} - {t['residency']}"
            summary[key] = {
                "tuition_per_credit": one_credit["tuition"],
                "total_per_credit": one_credit["total"],
                "fees_per_credit": round(one_credit["total"] - one_credit["tuition"], 2),
            }
            if "age_65_plus" in one_credit:
                summary[key]["age_65_plus_per_credit"] = one_credit["age_65_plus"]

    # Build the plain-English version
    plain = build_plain_english(summary)

    result = {
        "metadata": {
            "source": TUITION_URL,
            "academic_year": "2025-2026",
            "note": "Tuition is per credit. Fees are mandatory and cannot be waived.",
            "scraped_date": "2026-04-20",
        },
        "summary": summary,
        "plain_english": plain,
        "full_tables": tuition_tables,
    }

    return result


def build_plain_english(summary: dict) -> dict:
    """Translate the tuition data into what a student actually needs to know."""

    fc = summary.get("Flathead County Campus - Flathead County Resident", {})
    mt = summary.get("Flathead County Campus - Montana Resident", {})
    oos = summary.get("Flathead County Campus - Out-of-State", {})
    wue = summary.get("Western Undergraduate Exchange (WUE) - WUE", {})

    def semester_cost(per_credit, credits=15):
        return round(per_credit * credits, 2)

    def year_cost(per_credit, credits=30):
        return round(per_credit * credits, 2)

    return {
        "bottom_line": (
            f"Flathead County residents pay ${fc.get('total_per_credit', 0):.2f}/credit. "
            f"Other Montana residents pay ${mt.get('total_per_credit', 0):.2f}/credit. "
            f"Out-of-state pays ${oos.get('total_per_credit', 0):.2f}/credit. "
            f"WUE students (western states) pay ${wue.get('total_per_credit', 0):.2f}/credit."
        ),
        "typical_semester_15_credits": {
            "flathead_county": semester_cost(fc.get("total_per_credit", 0)),
            "montana_resident": semester_cost(mt.get("total_per_credit", 0)),
            "out_of_state": semester_cost(oos.get("total_per_credit", 0)),
            "wue": semester_cost(wue.get("total_per_credit", 0)),
        },
        "typical_year_30_credits": {
            "flathead_county": year_cost(fc.get("total_per_credit", 0)),
            "montana_resident": year_cost(mt.get("total_per_credit", 0)),
            "out_of_state": year_cost(oos.get("total_per_credit", 0)),
            "wue": year_cost(wue.get("total_per_credit", 0)),
        },
        "what_the_fees_are": {
            "infrastructure_fee": "Building maintenance and campus facilities",
            "technology_fee": "Computer labs, WiFi, online systems",
            "activity_fee": "Student clubs, events, student government",
            "equipment_fee": "Lab and classroom equipment",
            "health_center_fee": "On-campus health clinic (only charged at 7+ credits)",
        },
        "things_they_dont_tell_you_upfront": [
            "Some classes have extra lab fees on top of tuition — not listed on the main fee schedule.",
            "Payment is due at registration. If you can't pay in full, a deferred plan kicks in automatically — but you'll get hit with a $25 late fee if you miss an installment.",
            "A bounced check costs you $30.",
            "If you don't pay, they block your registration, hold your transcripts, and can send you to Montana Dept of Revenue collections.",
            "Age 65+? Flathead County residents pay massively reduced rates ($52.71/credit vs $205.16).",
        ],
    }


def main():
    result = scrape_tuition()
    DATA.mkdir(exist_ok=True)
    out_path = DATA / "tuition.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved tuition data to {out_path}")
    print(f"\nPlain English Summary:")
    print(result["plain_english"]["bottom_line"])
    print(f"\nTypical semester (15 credits):")
    for k, v in result["plain_english"]["typical_semester_15_credits"].items():
        print(f"  {k}: ${v:,.2f}")


if __name__ == "__main__":
    main()

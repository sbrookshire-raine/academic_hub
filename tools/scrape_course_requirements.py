"""Build a prerequisite/corequisite map from FVCC catalog course detail pages."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PROGRAMS_PATH = DATA / "program_courses.json"
OUT_PATH = DATA / "course_requirements.json"

HEADERS = {"User-Agent": "FVCC-DataCollector/1.0 (educational research)"}
SHOW_COURSE_RE = re.compile(r"showCourse\('\d+',\s*'(\d+)'", re.IGNORECASE)
COURSE_CODE_RE = re.compile(r"([A-Z]{1,6}\s+\d+[~\w]*)")
SECTION_HEADERS = {
    "Corequisite(s):",
    "Course Learning Outcomes:",
    "Course Fee:",
    "Lecture Hours:",
    "Lab Hours:",
    "Other Hours:",
    "Credits:",
    "Typically Offered:",
    "Grading:",
}


def load_programs() -> list[dict]:
    return json.loads(PROGRAMS_PATH.read_text(encoding="utf-8"))["programs"]


def fetch(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    time.sleep(0.25)
    return response.text


def extract_course_ids(program_html: str) -> list[str]:
    return sorted(set(SHOW_COURSE_RE.findall(program_html)))


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip(" ,.;")


def collect_section_values(lines: list[str], header: str) -> list[str]:
    values = []
    try:
        start = lines.index(header) + 1
    except ValueError:
        return values

    for line in lines[start:]:
        if line in SECTION_HEADERS:
            break
        norm = normalize_text(line)
        if not norm or norm in {",", "."}:
            continue
        values.append(norm)
    return values


def parse_course_page(coid: str, html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    title = ""
    if soup.title and soup.title.string:
        title = normalize_text(soup.title.string.split(" - ")[0])
    if not title and lines:
        title = normalize_text(lines[0])

    prereq_lines = collect_section_values(lines, "Prerequisite(s):")
    coreq_lines = collect_section_values(lines, "Corequisite(s):")

    def extract_codes(values: list[str]) -> list[str]:
        codes = []
        for value in values:
            codes.extend(COURSE_CODE_RE.findall(value))
        return sorted(set(codes))

    return {
        "coid": coid,
        "title": title,
        "prerequisite_lines": prereq_lines,
        "corequisite_lines": coreq_lines,
        "prerequisite_codes": extract_codes(prereq_lines),
        "corequisite_codes": extract_codes(coreq_lines),
    }


def main() -> None:
    programs = [program for program in load_programs() if program.get("catalog_url")]
    all_course_ids: set[str] = set()

    print(f"Scanning {len(programs)} program pages for course IDs...")
    for index, program in enumerate(programs, start=1):
        html = fetch(program["catalog_url"])
        all_course_ids.update(extract_course_ids(html))
        print(f"  [{index}/{len(programs)}] {program['name']}")

    print(f"Fetching {len(all_course_ids)} course detail pages...")
    requirements = {}
    for index, coid in enumerate(sorted(all_course_ids), start=1):
        url = f"https://catalog.fvcc.edu/preview_course_nopop.php?catoid=15&coid={coid}"
        html = fetch(url)
        course_info = parse_course_page(coid, html)
        key = course_info["title"].split(" - ")[0] if " - " in course_info["title"] else course_info["title"]
        requirements[key] = course_info
        if index % 50 == 0 or index == len(all_course_ids):
            print(f"  [{index}/{len(all_course_ids)}] fetched")

    payload = {
        "metadata": {
            "program_count": len(programs),
            "course_detail_count": len(requirements),
        },
        "courses": requirements,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(requirements)} course requirement entries to {OUT_PATH}")


if __name__ == "__main__":
    main()
"""Validate raw catalog HTML against browser-rendered FVCC catalog pages.

This answers a specific question: does the browser reveal additional course or
credit lines that are not present in the raw HTML used by the scraper?
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PROGRAMS_PATH = DATA / "program_courses.json"
REPORT_PATH = DATA / "rendered_catalog_validation.json"

COURSE_LINE_RE = re.compile(r"^[A-Z]{1,6}\s+\d+[~\w]*\s+-\s+")
TOTAL_CREDITS_RE = re.compile(r"Total Credits:\s*(\d+)(?:-(\d+))?", re.IGNORECASE)
SEMESTER_TOTAL_RE = re.compile(
    r"(?:First|Second|Third|Fourth|Fifth|Sixth|Prerequisites?)\s+Semester\s+Total:\s*\d+(?:-\d+)?"
    r"|(?:First|Second|Third|Fourth|Fifth|Sixth|Prerequisites?)\s+Total:\s*\d+(?:-\d+)?",
    re.IGNORECASE,
)


def load_programs() -> list[dict]:
    payload = json.loads(PROGRAMS_PATH.read_text(encoding="utf-8"))
    return payload["programs"]


def normalize_spaces(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = text.replace("á-á", " - ")
    text = text.replace("�-�", " - ")
    return re.sub(r"\s+", " ", text).strip()


def normalize_course_line(line: str) -> str:
    line = normalize_spaces(line)
    line = re.sub(r"\s+Credit\(s\):\s*\d+.*$", "", line, flags=re.IGNORECASE)
    line = re.sub(r"\s*\(Equivalent to .*?$", "", line, flags=re.IGNORECASE)
    line = re.sub(r"\s+may be taken .*?$", "", line, flags=re.IGNORECASE)
    line = re.sub(r"\s+\d+$", "", line)
    return line.strip()


def extract_visible_lines(text: str) -> dict:
    lines = [normalize_spaces(line) for line in text.splitlines() if normalize_spaces(line)]

    course_lines = [normalize_course_line(line) for line in lines if COURSE_LINE_RE.search(line)]
    semester_totals = [line for line in lines if SEMESTER_TOTAL_RE.search(line)]
    total_credit_lines = [line for line in lines if TOTAL_CREDITS_RE.search(line)]
    generic_credit_lines = []

    for line in lines:
        if COURSE_LINE_RE.search(line) or SEMESTER_TOTAL_RE.search(line) or TOTAL_CREDITS_RE.search(line):
            continue
        if re.search(r":\s*\d+(?:-\d+)?\s*$", line):
            lower = line.lower()
            if any(keyword in lower for keyword in [
                "elective",
                "requirement",
                "credit",
                "humanities",
                "science",
                "arts",
                "math",
                "social",
                "global",
                "natural",
                "communication",
                "course options",
                "prerequisites total",
            ]):
                generic_credit_lines.append(line)

    return {
        "course_lines": sorted(set(course_lines)),
        "generic_credit_lines": sorted(set(generic_credit_lines)),
        "semester_totals": sorted(set(semester_totals)),
        "total_credit_lines": sorted(set(total_credit_lines)),
    }


def compare_program(program: dict, raw_lines: dict, rendered_lines: dict) -> dict:
    rendered_total = ""
    if rendered_lines["total_credit_lines"]:
        match = TOTAL_CREDITS_RE.search(rendered_lines["total_credit_lines"][0])
        if match:
            rendered_total = int(match.group(1))

    return {
        "name": program["name"],
        "catalog_url": program.get("catalog_url", ""),
        "stored_total_credits": program.get("total_credits", ""),
        "rendered_total_credits": rendered_total,
        "raw_course_count": len(raw_lines["course_lines"]),
        "rendered_course_count": len(rendered_lines["course_lines"]),
        "raw_generic_count": len(raw_lines["generic_credit_lines"]),
        "rendered_generic_count": len(rendered_lines["generic_credit_lines"]),
        "raw_semester_total_count": len(raw_lines["semester_totals"]),
        "rendered_semester_total_count": len(rendered_lines["semester_totals"]),
        "extra_in_rendered_courses": sorted(set(rendered_lines["course_lines"]) - set(raw_lines["course_lines"])),
        "missing_in_rendered_courses": sorted(set(raw_lines["course_lines"]) - set(rendered_lines["course_lines"])),
        "extra_in_rendered_generics": sorted(set(rendered_lines["generic_credit_lines"]) - set(raw_lines["generic_credit_lines"])),
        "missing_in_rendered_generics": sorted(set(raw_lines["generic_credit_lines"]) - set(rendered_lines["generic_credit_lines"])),
        "extra_in_rendered_totals": sorted(set(rendered_lines["total_credit_lines"] + rendered_lines["semester_totals"]) - set(raw_lines["total_credit_lines"] + raw_lines["semester_totals"])),
        "missing_in_rendered_totals": sorted(set(raw_lines["total_credit_lines"] + raw_lines["semester_totals"]) - set(rendered_lines["total_credit_lines"] + rendered_lines["semester_totals"])),
        "generic_text_diff_only": (
            raw_lines["course_lines"] == rendered_lines["course_lines"]
            and raw_lines["semester_totals"] == rendered_lines["semester_totals"]
            and raw_lines["total_credit_lines"] == rendered_lines["total_credit_lines"]
            and raw_lines["generic_credit_lines"] != rendered_lines["generic_credit_lines"]
        ),
        "raw_matches_rendered": (
            raw_lines["course_lines"] == rendered_lines["course_lines"]
            and raw_lines["semester_totals"] == rendered_lines["semester_totals"]
            and raw_lines["total_credit_lines"] == rendered_lines["total_credit_lines"]
        ),
    }


def main() -> None:
    programs = [program for program in load_programs() if program.get("catalog_url") and program.get("semesters")]
    results = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        for index, program in enumerate(programs, start=1):
            url = program["catalog_url"]
            print(f"[{index}/{len(programs)}] {program['name']}")
            page.goto(url, wait_until="networkidle", timeout=60000)
            rendered_text = page.locator("body").inner_text()
            raw_html = requests.get(url, timeout=30)
            raw_html.raise_for_status()
            raw_text = BeautifulSoup(raw_html.text, "html.parser").get_text("\n", strip=True)

            raw_lines = extract_visible_lines(raw_text)
            rendered_lines = extract_visible_lines(rendered_text)
            results.append(compare_program(program, raw_lines, rendered_lines))

        browser.close()

    exact = sum(1 for item in results if item["raw_matches_rendered"])
    generic_only = sum(1 for item in results if item["generic_text_diff_only"])
    mismatches = [item for item in results if not item["raw_matches_rendered"]]

    report = {
        "summary": {
            "programs_checked": len(results),
            "raw_rendered_exact_matches": exact,
            "generic_text_only_differences": generic_only,
            "raw_rendered_mismatches": len(mismatches),
        },
        "mismatches": mismatches,
    }

    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nSummary")
    print(f"  Programs checked: {len(results)}")
    print(f"  Raw/rendered exact matches: {exact}")
    print(f"  Generic-text-only differences: {generic_only}")
    print(f"  Raw/rendered mismatches: {len(mismatches)}")
    print(f"  Report: {REPORT_PATH}")

    for item in mismatches[:20]:
        print(f"  - {item['name']}")
        print(f"    stored_total={item['stored_total_credits']} rendered_total={item['rendered_total_credits']}")
        print(f"    raw_courses={item['raw_course_count']} rendered_courses={item['rendered_course_count']}")
        print(f"    raw_generics={item['raw_generic_count']} rendered_generics={item['rendered_generic_count']}")


if __name__ == "__main__":
    main()
"""
Scrape FVCC catalog program pages (catalog.fvcc.edu) to extract structured
course requirements per semester for each program.

This fills in the 'courses' field that the main program scraper couldn't get
from the JS-rendered fvcc.edu pages.

Outputs: data/program_courses.json
"""

import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

HEADERS = {
    "User-Agent": "FVCC-DataCollector/1.0 (educational research)"
}

# Catalog program index page
CATALOG_INDEX = "https://catalog.fvcc.edu/content.php?catoid=15&navoid=1110"


def fetch_page(url: str) -> BeautifulSoup | None:
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            time.sleep(1.5)
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            time.sleep(3 * (attempt + 1))
    return None


def get_catalog_program_urls() -> list[dict]:
    """Fetch the catalog index and extract all program URLs."""
    soup = fetch_page(CATALOG_INDEX)
    if not soup:
        return []

    programs = []
    current_division = ""
    current_degree_type = ""

    # The page structure: h2 = division, then degree type headers, then bullet lists
    content = soup.find("td", class_="block_content_outer")
    if not content:
        content = soup.body

    for el in content.descendants:
        if el.name == "h2":
            current_division = el.get_text(strip=True)
        elif el.name in ("h3", "p", "strong"):
            text = el.get_text(strip=True)
            if any(dt in text for dt in [
                "Associate of Arts", "Associate of Science", "Associate of Applied Science",
                "Certificate of Applied Science", "Certificate of Technical Studies",
                "Certificate of General Studies", "Other"
            ]):
                current_degree_type = text
        elif el.name == "a" and el.get("href", "").startswith("preview_program.php"):
            href = el["href"]
            name = el.get_text(strip=True)
            if name and "catoid=" in href:
                full_url = f"https://catalog.fvcc.edu/{href}"
                programs.append({
                    "name": name,
                    "catalog_url": full_url,
                    "division": current_division,
                    "degree_type": current_degree_type,
                })

    return programs


def parse_catalog_text(text: str, name: str) -> dict:
    """Parse catalog page text for structured course requirements."""
    result = {
        "name": name,
        "total_credits": "",
        "prerequisites": [],
        "semesters": [],
        "admission_guidelines": "",
        "notes": [],
    }

    # Determine what degree type this page is for, from the name
    # e.g., "Electrical Technology, AAS" -> "AAS"
    degree_suffix = ""
    for sfx in ["AAS", "ASN", "CAS", "CTS", "AA", "AS"]:
        if sfx in name.upper().split(",")[-1] if "," in name else "":
            degree_suffix = sfx
            break

    # Extract total credits - prefer the one matching the program's degree type
    # Catalog pages may have: "CTS Total Credits: 17", "CAS Total Credits: 32", "AAS Total Credits: 63"
    # Some use ranges like "Total Credits: 21-22" — take the lower bound
    all_totals = re.findall(r'(?:(\w+)\s+)?Total Credits:\s*(\d+)(?:-\d+)?', text)
    if all_totals:
        best = None
        for prefix, credits in all_totals:
            if prefix and degree_suffix and prefix.upper() == degree_suffix.upper():
                best = int(credits)
            elif not prefix:
                best = int(credits)
        if best is None:
            best = int(all_totals[-1][1])
        result["total_credits"] = best

    # Parse the course structure from body text
    lines = text.split("\n")
    current_section = ""
    current_year = ""
    current_semester_label = ""
    current_courses = []
    current_semester_credits = ""
    pending_course = None  # course name parsed, waiting for Credit(s) line
    stop_parsing = False  # stop when we hit Recommended/Suggested/Admission sections
    have_seen_courses = False  # only activate stop patterns after we've parsed some courses

    # Sections that signal the end of required courses
    STOP_PATTERNS = [
        r'Recommended Course Offering',
        r'Suggested Elective',
        r'Suggested Course Offering',
        r'Elective Course',
        r'Restricted Elective',
        r'Admission Guidelines',
        r'Advising Information',
        r'Program Information',
        r'Additional Costs',
        r'If time permits',
        r'Upper Division Courses',
        r'General Education Courses',
        r'Opportunities after Graduation',
        r'[*]+ *Elective',
        r'Choose from.* following',
        r'Additional Course Options',
        r'Approved Electives',
    ]

    def flush_semester():
        nonlocal current_courses, current_semester_label, current_semester_credits, pending_course
        pending_course = None
        if current_courses and current_semester_label:
            sem = {
                "label": current_semester_label,
                "courses": current_courses,
            }
            if current_semester_credits:
                sem["semester_credits"] = current_semester_credits
            result["semesters"].append(sem)
        current_courses = []
        current_semester_credits = ""

    for line in lines:
        line = line.strip().replace("\xa0", " ")
        if not line:
            continue

        # Check for stop sections — these mark end of required courses
        # Only activate after we've seen at least one course, to avoid being stopped
        # by navigation/header text that appears before the course listing
        if have_seen_courses and any(re.match(pat, line, re.IGNORECASE) for pat in STOP_PATTERNS):
            stop_parsing = True
            flush_semester()
            continue

        if stop_parsing:
            # Check if a new Required Courses section restarts
            if re.match(r'Required Courses', line, re.IGNORECASE):
                stop_parsing = False
            continue

        # Check for intermediate degree totals (CAS Total Credits, CTS Total Credits)
        # These are NOT stop signals — they mark sub-milestones within a program
        intermediate_total = re.match(r'(CTS|CAS)\s+Total Credits:\s*\d+', line, re.IGNORECASE)
        if intermediate_total:
            continue  # skip it, don't confuse with semester totals

        # Check for section headers
        if re.match(r'Required Prerequisites', line, re.IGNORECASE):
            flush_semester()
            current_semester_label = "Prerequisites"
            current_section = "prereqs"
            continue

        # "Required Prerequisite Courses", "Program Prerequisites", etc.
        if re.match(r'(?:Required (?:Prerequisite )?|Program )(?:Courses|Prerequisites)', line, re.IGNORECASE):
            flush_semester()
            current_semester_label = "Prerequisites"
            continue

        # "Pre-Paramedicine Requirements:", "Pre-surgical Technology Courses", etc.
        pre_section = re.match(r'Pre-?\w+[\w\s]*(?:Requirements?|Courses)', line, re.IGNORECASE)
        if pre_section:
            flush_semester()
            current_semester_label = "Prerequisites"
            continue

        # Note about sub-program eligibility — skip
        if re.match(r'Note:', line, re.IGNORECASE):
            continue

        # BUG FIX 1: Combined year+semester on same line
        # e.g., "First Year - Fall Semester", "Second Year-Spring Semester"
        year_sem_match = re.match(
            r'(First|Second|Third|Fourth)\s+Year\s*[-–—]\s*(Fall|Spring|Summer)\s+Semester',
            line, re.IGNORECASE
        )
        if year_sem_match:
            flush_semester()
            current_year = year_sem_match.group(1).title()
            semester = year_sem_match.group(2).title()
            current_semester_label = f"{current_year} Year - {semester}"
            continue

        # Also handle "Second Year Fall Semester" (no dash)
        year_sem_nodash = re.match(
            r'(First|Second|Third|Fourth)\s+Year\s+(Fall|Spring|Summer)\s+Semester',
            line, re.IGNORECASE
        )
        if year_sem_nodash:
            flush_semester()
            current_year = year_sem_nodash.group(1).title()
            semester = year_sem_nodash.group(2).title()
            current_semester_label = f"{current_year} Year - {semester}"
            continue

        year_match = re.match(r'(First|Second|Third|Fourth)\s+Year', line, re.IGNORECASE)
        if year_match:
            current_year = year_match.group(1).title()
            continue

        sem_match = re.match(r'(Fall|Spring|Summer)\s+Semester', line, re.IGNORECASE)
        if sem_match:
            flush_semester()
            semester = sem_match.group(1).title()
            if current_year:
                current_semester_label = f"{current_year} Year - {semester}"
            else:
                current_semester_label = semester
            continue

        # "Second Semester (Summer)", "Third Semester (Fall)" pattern
        # Must not match "First Semester Total: 15"
        ordinal_sem = re.match(
            r'(First|Second|Third|Fourth|Fifth|Sixth)\s+Semester\s*\((\w+)\)\s*$',
            line, re.IGNORECASE
        )
        if ordinal_sem:
            flush_semester()
            ordinal = ordinal_sem.group(1).title()
            season = ordinal_sem.group(2).title()
            current_semester_label = f"{ordinal} Semester ({season})"
            continue

        # Generic "Semester N:" pattern
        gen_sem = re.match(r'Semester\s+(\d+)', line, re.IGNORECASE)
        if gen_sem:
            flush_semester()
            current_semester_label = f"Semester {gen_sem.group(1)}"
            continue

        # Check for semester total credits
        total_match = re.match(r'(?:.*?)(?:Semester\s+)?Total:\s*(\d+)', line)
        if total_match:
            current_semester_credits = int(total_match.group(1))
            continue

        # Program-level total credits line = stop parsing (everything after is supplemental)
        # But NOT intermediate totals (CAS/CTS Total Credits within an AAS program)
        if have_seen_courses:
            program_total_match = re.match(r'((?:AAS|ASN|AA|AS)\s+)?Total Credits:', line, re.IGNORECASE)
            if program_total_match:
                prefix = (program_total_match.group(1) or "").strip().upper()
                if not prefix or prefix == degree_suffix.upper():
                    flush_semester()
                    stop_parsing = True
                continue

        # Check for Credit(s) line — pairs with pending_course
        credit_match = re.match(r'Credit\(s\):\s*(\d+)', line)
        if credit_match and pending_course and current_semester_label:
            credits = int(credit_match.group(1))
            pending_course["credits"] = credits
            current_courses.append(pending_course)
            have_seen_courses = True
            pending_course = None
            continue

        # Parse course name lines
        # Format: "BIOH 201NL - Human Anatomy and Physiology I"
        # or: "M 121M - College Algebra"
        # or: "M 094~ - Quantitative Reasoning" (tilde in code)
        course_match = re.match(
            r'([A-Z]+\s+\d+[~\w]*)\s+-\s+(.+)',
            line
        )
        if course_match:
            code = course_match.group(1).strip()
            title = course_match.group(2).strip()
            # Remove trailing markers like "1", "R", "*"
            title = re.sub(r'\s+[1R*]+$', '', title).strip()
            normalized_code = code.replace(" ", "_")
            pending_course = {
                "code": code,
                "normalized_code": normalized_code,
                "title": title,
            }
            continue

        # Parse elective / general requirement lines (no specific course code)
        # These lines come in many formats on catalog pages:
        #   "Fine Arts (F) Requirement Credit(s): 3"
        #   "Social Sciences (A) Requirement Credits: 3"
        #   "Global Issues (G) Requirement: 3"
        #   "Elective Credits: 3"
        #   "Elective Credit: 1"
        #   "Elective(s) - ACTG, BFIN, CAPP: Credit(s): 4"
        #   "Elective Credits from ARTZ, DANC, or MUSI course options: 3"
        #   "ARTH, ARTZ, GDSN, or MART 200-level course credits: 3"
        #   "Any HSTA or HSTR course: 3 credits"
        #   "Natural Science (NL) course: 3-4 credits"
        #   "Humanities (H) or Fine Art (F) Requirement(s): 3"
        #   "Fine Arts (F)1 or Mathematics (M)2 or Natural Science (N/NL)2 Requirement(s): 3"
        if current_semester_label:
            # Pattern A: Line contains "Credit(s):" with a number after it (explicit credits marker)
            elective_credit = re.match(
                r'(.+?)\s*:?\s*Credit\(s\):\s*(\d+)',
                line
            )
            if elective_credit:
                desc = elective_credit.group(1).strip()
                credits = int(elective_credit.group(2))
                if not re.match(r'[A-Z]+\s+\d+', desc):
                    current_courses.append({
                        "code": "ELECTIVE",
                        "normalized_code": "ELECTIVE",
                        "title": desc,
                        "credits": credits,
                        "is_elective": True,
                    })
                    have_seen_courses = True
                    pending_course = None
                    continue

            # Pattern B: Line ends with ": N" where it contains requirement/elective keywords
            # Catches: "Requirement(s): 3", "Requirement Credits: 3", "course options: 3", etc.
            trailing_credits = re.search(r':\s*(\d+)\s*$', line)
            if trailing_credits:
                credits = int(trailing_credits.group(1))
                desc = line[:trailing_credits.start()].strip()
                # Only match if it looks like an elective/requirement, not a course code
                if not re.match(r'[A-Z]+\s+\d+', desc) and credits <= 10:
                    # Verify it's not a semester total or other numeric line
                    if any(kw in desc.lower() for kw in [
                        'requirement', 'elective', 'credit', 'course',
                        'humanities', 'science', 'arts', 'math', 'social',
                        'global', 'natural', 'fine art', 'communication',
                    ]):
                        current_courses.append({
                            "code": "ELECTIVE",
                            "normalized_code": "ELECTIVE",
                            "title": desc,
                            "credits": credits,
                            "is_elective": True,
                        })
                        have_seen_courses = True
                        pending_course = None
                        continue

            # Pattern C: "Any HSTA or HSTR course: 3 credits" (number before "credits")
            elective_n_credits = re.match(
                r'(.+?):\s*(\d+)(?:-\d+)?\s*credits?\s*$',
                line,
                re.IGNORECASE
            )
            if elective_n_credits:
                desc = elective_n_credits.group(1).strip()
                credits = int(elective_n_credits.group(2))
                if not re.match(r'[A-Z]+\s+\d+', desc):
                    current_courses.append({
                        "code": "ELECTIVE",
                        "normalized_code": "ELECTIVE",
                        "title": desc,
                        "credits": credits,
                        "is_elective": True,
                    })
                    have_seen_courses = True
                    pending_course = None
                    continue

        # Check for OR conditions
        if line.strip() == "OR" and current_courses:
            current_courses[-1]["or_next"] = True
            continue

    # Flush last semester
    flush_semester()

    return result


def parse_catalog_program(soup: BeautifulSoup, name: str) -> dict:
    """Parse a catalog program page for structured course requirements."""
    text = soup.get_text(separator="\n", strip=True)
    return parse_catalog_text(text, name)


def main():
    print("Fetching catalog program index...")
    programs = get_catalog_program_urls()
    print(f"Found {len(programs)} programs in catalog")

    all_programs = []
    for i, prog in enumerate(programs):
        print(f"  [{i+1}/{len(programs)}] {prog['name']}...")
        soup = fetch_page(prog["catalog_url"])
        if not soup:
            print(f"    FAILED")
            continue

        parsed = parse_catalog_program(soup, prog["name"])
        parsed["catalog_url"] = prog["catalog_url"]
        parsed["division"] = prog["division"]
        parsed["degree_type"] = prog["degree_type"]
        all_programs.append(parsed)
        
        total_courses = sum(len(s["courses"]) for s in parsed["semesters"])
        print(f"    -> {len(parsed['semesters'])} semesters, {total_courses} courses, {parsed['total_credits']} total credits")

    # Build a course-to-program mapping
    course_program_map = {}
    for prog in all_programs:
        for sem in prog["semesters"]:
            for c in sem["courses"]:
                code = c["normalized_code"]
                if code not in course_program_map:
                    course_program_map[code] = []
                course_program_map[code].append({
                    "program": prog["name"],
                    "semester": sem["label"],
                    "division": prog["division"],
                })

    output = {
        "metadata": {
            "source": "catalog.fvcc.edu (2026-2027 Academic Catalog)",
            "total_programs": len(all_programs),
            "programs_with_courses": sum(1 for p in all_programs if any(s["courses"] for s in p["semesters"])),
        },
        "programs": all_programs,
        "course_program_map": course_program_map,
    }

    DATA.mkdir(exist_ok=True)
    out_path = DATA / "program_courses.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved to {out_path}")
    print(f"  Programs: {len(all_programs)}")
    print(f"  With courses: {output['metadata']['programs_with_courses']}")
    print(f"  Course-program mappings: {len(course_program_map)}")


if __name__ == "__main__":
    main()

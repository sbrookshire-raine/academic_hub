"""
Scrape FVCC course schedules from elements.fvcc.edu into structured JSON.
Covers Spring 2026, Summer 2026, and Fall 2026.

Each section record includes:
  - course_code, section_id, full_code
  - title, credits, days, time, room
  - seats_available, instructor, additional_fee
  - location, delivery_mode, dates, notes
  - department, term

Outputs: data/schedules.json
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

SCHEDULE_URLS = {
    "Spring 2026": "https://elements.fvcc.edu/Schedules/sp26/index.asp",
    "Summer 2026": "https://elements.fvcc.edu/Schedules/su26/index.asp",
    "Fall 2026":   "https://elements.fvcc.edu/Schedules/fa26/index.asp",
}


def fetch_page(url: str) -> BeautifulSoup | None:
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            print(f"  Attempt {attempt+1} failed for {url}: {e}")
            time.sleep(2 * (attempt + 1))
    return None


def parse_delivery_mode(room: str, notes: str, title_block: str) -> str:
    """Infer delivery mode from room, notes, and title block."""
    combined = (room + " " + notes + " " + title_block).lower()
    if "online course" in combined or room.strip().lower() == "online":
        if "limited on-site" in combined:
            return "Limited On-Site"
        return "Online"
    if "hybrid" in combined:
        return "Hybrid"
    if "remote" in combined or room.strip().upper() == "REMOT Remote":
        return "Remote"
    if "hyflex" in combined:
        return "HyFlex"
    return "In-Person"


def parse_location(title_block: str, room: str) -> str:
    """Extract campus location from the title/meeting info block."""
    tb_lower = title_block.lower()
    room_lower = room.lower()
    # Use title_block primarily for campus info (it contains "Kalispell Campus", "Online Course", etc.)
    if "online course" in tb_lower:
        return "Online"
    if "lincoln county" in tb_lower or "libby" in tb_lower:
        return "Lincoln County"
    if "kalispell campus" in tb_lower:
        return "Kalispell"
    # Check for high school dual enrollment
    hs_match = re.search(r'for\s+(\w[\w\s]+?)\s+high school', tb_lower)
    if hs_match:
        return f"{hs_match.group(1).strip().title()} High School"
    # Fallback to room info
    if "online" in room_lower:
        return "Online"
    if "linb" in room_lower:
        return "Lincoln County"
    if "remot" in room_lower:
        return "Remote"
    return "Kalispell"


def parse_seats(seats_str: str) -> dict:
    """Parse seats available string into structured data."""
    seats_str = seats_str.strip()
    if seats_str.lower() == "closed":
        return {"available": 0, "status": "Closed"}
    # Handle format like "11" or "3 (w2)" or "-1 (w3)"
    m = re.match(r'(-?\d+)\s*(?:\(w(\d+)\))?', seats_str)
    if m:
        avail = int(m.group(1))
        waitlist = int(m.group(2)) if m.group(2) else 0
        status = "Open" if avail > 0 else ("Waitlist" if waitlist > 0 else "Full")
        return {"available": avail, "waitlist": waitlist, "status": status}
    return {"available": 0, "status": "Unknown", "raw": seats_str}


def parse_fee(text: str) -> str | None:
    """Extract additional fee from instructor/fee text."""
    m = re.search(r"Add'l Fee:\s*\$([0-9,.]+)", text)
    return f"${m.group(1)}" if m else None


def parse_instructor(text: str) -> str:
    """Extract instructor name, removing fee info."""
    cleaned = re.sub(r"Add'l Fee:\s*\$[0-9,.]+", "", text).strip()
    # Remove "- Staff" marker
    if cleaned == "- Staff":
        return "Staff"
    return cleaned


def parse_dates(title_block: str) -> str:
    """Extract meeting dates from title block."""
    m = re.search(r'Meets:\s*(\d{1,2}/\d{1,2}/\d{4})-(\d{1,2}/\d{1,2}/\d{4})', title_block)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return ""


def parse_notes(title_block: str) -> list[str]:
    """Extract all Note: entries from the title block."""
    notes = re.findall(r'Note:\s*(.+?)(?=Note:|$)', title_block)
    return [n.strip() for n in notes if n.strip()]


def parse_schedule_page(soup: BeautifulSoup, term: str) -> list[dict]:
    """Parse all course sections from a schedule page."""
    sections = []
    current_department = ""

    # The schedule is in HTML tables. Find all rows.
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if not cells:
                continue

            # Check if this is a department header row
            # Department headers have a specific pattern — first cell is empty/nbsp,
            # second cell has department name with the column headers
            cell_texts = [c.get_text(separator=" ", strip=True) for c in cells]

            # Detect department header: first cell is empty or has nav, 
            # and "Cred" appears in the row
            if len(cells) >= 3 and "Cred" in cell_texts[-6] if len(cell_texts) >= 6 else False:
                # Department name is in the second cell
                dept_text = cell_texts[1] if len(cell_texts) > 1 else ""
                # Remove the column header text
                dept_clean = re.sub(r'\s*(Cred|Days|Time|Room|Seats Avail|Instructor.*)', '', dept_text).strip()
                # Remove navigation hints and extra whitespace
                # The nav text is "(Click on a category...)" followed by category list
                # Just keep text before the first parenthesis
                if '(' in dept_clean:
                    dept_clean = dept_clean[:dept_clean.index('(')].strip()
                dept_clean = re.sub(r'\s+', ' ', dept_clean).strip()
                # Remove non-breaking spaces and clean
                dept_clean = dept_clean.replace('\xa0', ' ').strip()
                if dept_clean:
                    current_department = dept_clean
                continue

            # Check for course section row: first cell has a course code pattern
            if len(cells) >= 7:
                code_text = cell_texts[0].strip() if cell_texts else ""
                
                # Course code pattern: PREFIX_NUM_SECTION (e.g., ACTG_201_01, M_171M_01)
                if re.match(r'^[A-Z]+_\d+', code_text):
                    title_block = cell_texts[1] if len(cell_texts) > 1 else ""
                    cred_text = cell_texts[2] if len(cell_texts) > 2 else ""
                    days_text = cell_texts[3] if len(cell_texts) > 3 else ""
                    time_text = cell_texts[4] if len(cell_texts) > 4 else ""
                    room_text = cell_texts[5] if len(cell_texts) > 5 else ""
                    seats_text = cell_texts[6] if len(cell_texts) > 6 else ""
                    instructor_text = cell_texts[7] if len(cell_texts) > 7 else ""

                    # Parse course code into parts
                    # Handle codes like ACTG_201_01, M_171M_01, BIOH_201NL_90D
                    code_parts = code_text.split("_")
                    if len(code_parts) >= 3:
                        prefix = code_parts[0]
                        number = code_parts[1]
                        section_id = "_".join(code_parts[2:])
                        course_code = f"{prefix}_{number}"
                    elif len(code_parts) == 2:
                        prefix = code_parts[0]
                        number = code_parts[1]
                        section_id = ""
                        course_code = code_text
                    else:
                        continue

                    # Extract title (before "Meets:")
                    title = re.split(r'\s*Meets:', title_block)[0].strip()

                    # Parse credits
                    cred_match = re.search(r'(\d+(?:\.\d+)?)\s*cr', cred_text)
                    credits = float(cred_match.group(1)) if cred_match else 0
                    if credits == int(credits):
                        credits = int(credits)

                    section = {
                        "full_code": code_text,
                        "course_code": course_code,
                        "section_id": section_id,
                        "title": title,
                        "credits": credits,
                        "days": days_text,
                        "time": time_text,
                        "room": room_text,
                        "seats": parse_seats(seats_text),
                        "instructor": parse_instructor(instructor_text),
                        "additional_fee": parse_fee(instructor_text),
                        "location": parse_location(title_block, room_text),
                        "delivery_mode": parse_delivery_mode(room_text, " ".join(parse_notes(title_block)), title_block),
                        "dates": parse_dates(title_block),
                        "notes": parse_notes(title_block),
                        "department": current_department,
                        "term": term,
                    }
                    sections.append(section)

    return sections


def build_course_index(all_sections: list[dict]) -> dict:
    """Build a lookup index: course_code -> list of sections across terms."""
    index = {}
    for s in all_sections:
        code = s["course_code"]
        if code not in index:
            index[code] = {
                "course_code": code,
                "title": s["title"],
                "department": s["department"],
                "terms_offered": [],
                "sections": [],
            }
        term = s["term"]
        if term not in index[code]["terms_offered"]:
            index[code]["terms_offered"].append(term)
        index[code]["sections"].append({
            "full_code": s["full_code"],
            "section_id": s["section_id"],
            "term": term,
            "days": s["days"],
            "time": s["time"],
            "room": s["room"],
            "seats": s["seats"],
            "instructor": s["instructor"],
            "delivery_mode": s["delivery_mode"],
            "location": s["location"],
            "dates": s["dates"],
            "additional_fee": s["additional_fee"],
            "notes": s["notes"],
        })
    return index


def main():
    all_sections = []

    for term, url in SCHEDULE_URLS.items():
        print(f"\n{'='*60}")
        print(f"Scraping {term}: {url}")
        print(f"{'='*60}")

        soup = fetch_page(url)
        if not soup:
            print(f"  FAILED to fetch {term}")
            continue

        sections = parse_schedule_page(soup, term)
        print(f"  Found {len(sections)} sections for {term}")
        all_sections.extend(sections)
        time.sleep(2)  # Be polite

    # Build course index
    course_index = build_course_index(all_sections)

    # Stats
    terms = set(s["term"] for s in all_sections)
    departments = set(s["department"] for s in all_sections if s["department"])
    delivery_modes = {}
    for s in all_sections:
        dm = s["delivery_mode"]
        delivery_modes[dm] = delivery_modes.get(dm, 0) + 1

    schedule_data = {
        "metadata": {
            "scraped_from": "elements.fvcc.edu",
            "terms": sorted(terms),
            "total_sections": len(all_sections),
            "unique_courses": len(course_index),
            "departments": sorted(departments),
            "delivery_mode_counts": delivery_modes,
        },
        "sections": all_sections,
        "course_index": course_index,
    }

    # Save
    DATA.mkdir(exist_ok=True)
    out_path = DATA / "schedules.json"
    out_path.write_text(json.dumps(schedule_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{'='*60}")
    print(f"Saved {len(all_sections)} sections ({len(course_index)} unique courses) to {out_path}")
    print(f"Terms: {', '.join(sorted(terms))}")
    print(f"Departments: {len(departments)}")
    print(f"Delivery modes: {delivery_modes}")


if __name__ == "__main__":
    main()

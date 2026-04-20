"""
Scrape FVCC program and track pages into structured JSON.
Handles rate limiting, retries, and extracts:
  - Program name, degree type, division
  - Description, learning outcomes, requirements
  - Course lists with credits
  - Career/transfer info
  - Contact info

Outputs: data/programs.json, data/tracks.json
"""

import json
import re
import time
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MANIFEST = DATA / "url_manifest.json"

HEADERS = {
    "User-Agent": "FVCC-DataCollector/1.0 (educational research)"
}
DELAY = 1.5  # seconds between requests — be respectful


def fetch_page(url: str, retries: int = 3) -> BeautifulSoup | None:
    """Fetch a page with retries and polite delay."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            time.sleep(DELAY)
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            print(f"  Attempt {attempt+1} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(DELAY * (attempt + 1))
    return None


def clean_text(el) -> str:
    """Extract and clean text from a BeautifulSoup element."""
    if el is None:
        return ""
    text = el.get_text(separator="\n", strip=True)
    # collapse multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_section_text(soup: BeautifulSoup, heading_text: str) -> str:
    """Find a heading by text and return all content until the next heading."""
    for heading in soup.find_all(re.compile(r'^h[2-4]$')):
        if heading_text.lower() in heading.get_text(strip=True).lower():
            parts = []
            for sib in heading.next_siblings:
                if isinstance(sib, Tag) and sib.name and re.match(r'^h[2-4]$', sib.name):
                    break
                if isinstance(sib, Tag):
                    parts.append(clean_text(sib))
            return "\n".join(p for p in parts if p)
    return ""


def extract_courses_from_section(soup: BeautifulSoup) -> list[dict]:
    """Extract course info from tables or structured lists on the page."""
    courses = []
    # Look for tables with course data
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                code_name = clean_text(cells[0])
                credits = clean_text(cells[1]) if len(cells) > 1 else ""
                if code_name and code_name.lower() not in ("course", "course name", "courses"):
                    courses.append({
                        "course": code_name,
                        "credits": credits
                    })
    
    # Also look for course lists in divs/sections
    for el in soup.find_all(class_=re.compile(r'course|curriculum', re.I)):
        items = el.find_all("li")
        for item in items:
            text = clean_text(item)
            if text:
                # Try to split "COURSE 101 - Name (3 cr)"
                m = re.match(r'([A-Z]{2,5}\s*\d{3}[A-Z]?)\s*[-–]\s*(.*?)(?:\((\d+)\s*cr)', text, re.I)
                if m:
                    courses.append({
                        "course": f"{m.group(1)} - {m.group(2).strip()}",
                        "credits": m.group(3)
                    })
                else:
                    courses.append({"course": text, "credits": ""})
    
    return courses


def extract_links(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Extract important internal links from the page content area."""
    content = soup.find("main") or soup.find(class_="entry-content") or soup.find(id="content") or soup
    links = []
    for a in content.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if href.startswith("/"):
            href = f"https://www.fvcc.edu{href}"
        if "fvcc.edu" in href and text:
            links.append({"text": text, "url": href})
    return links


def scrape_program(url: str) -> dict | None:
    """Scrape a single program page."""
    soup = fetch_page(url)
    if not soup:
        return None

    data = {"url": url}
    
    # Title
    h1 = soup.find("h1")
    data["name"] = clean_text(h1) if h1 else ""
    
    # Try to get the page's main content area
    content = soup.find("main") or soup.find(class_="entry-content") or soup.find(id="content")
    if content:
        data["full_text"] = clean_text(content)
    else:
        data["full_text"] = ""
    
    # Degree type and division from breadcrumbs or page structure
    breadcrumbs = soup.find(class_=re.compile(r'breadcrumb', re.I))
    if breadcrumbs:
        data["breadcrumbs"] = clean_text(breadcrumbs)
    
    # Parse specific sections
    data["description"] = extract_section_text(soup, "program description") or extract_section_text(soup, "about") or extract_section_text(soup, "overview")
    data["learning_outcomes"] = extract_section_text(soup, "learning outcomes") or extract_section_text(soup, "program outcomes")
    data["requirements"] = extract_section_text(soup, "requirements") or extract_section_text(soup, "admission requirements")
    data["curriculum"] = extract_section_text(soup, "curriculum") or extract_section_text(soup, "program of study") or extract_section_text(soup, "coursework")
    data["careers"] = extract_section_text(soup, "career") or extract_section_text(soup, "employment")
    data["transfer"] = extract_section_text(soup, "transfer")
    data["contact"] = extract_section_text(soup, "contact") or extract_section_text(soup, "advisor")
    data["costs"] = extract_section_text(soup, "cost") or extract_section_text(soup, "tuition")
    
    # Courses table
    data["courses"] = extract_courses_from_section(soup)
    
    # Total credits if mentioned
    credits_match = re.search(r'(\d{2,3})\s*(?:total\s+)?credits?', data.get("full_text", ""), re.I)
    if credits_match:
        data["total_credits"] = credits_match.group(1)
    
    # Internal links for further scraping
    data["related_links"] = extract_links(soup, url)
    
    return data


def classify_program(url: str, name: str) -> dict:
    """Derive degree_type and division from URL patterns and program name."""
    info = {}
    
    # Degree type from name/URL
    name_lower = name.lower()
    if "aas" in name_lower or "associate of applied science" in name_lower:
        info["degree_type"] = "Associate of Applied Science (AAS)"
    elif "asn" in name_lower or "associate of science nursing" in name_lower:
        info["degree_type"] = "Associate of Science Nursing (ASN)"
    elif "associate of arts" in name_lower or ", aa" in name_lower:
        info["degree_type"] = "Associate of Arts (AA)"
    elif "associate of science" in name_lower:
        info["degree_type"] = "Associate of Science (AS)"
    elif "cas" in name_lower or "certificate of applied science" in name_lower:
        info["degree_type"] = "Certificate of Applied Science (CAS)"
    elif "cts" in name_lower or "certificate of technical studies" in name_lower:
        info["degree_type"] = "Certificate of Technical Studies (CTS)"
    elif "transfer" in name_lower:
        info["degree_type"] = "Transfer Program"
    elif "course" in name_lower or "training" in name_lower:
        info["degree_type"] = "Course/Training"
    else:
        info["degree_type"] = "Other"
    
    return info


def main():
    if not MANIFEST.exists():
        print("Run extract_urls.py first to generate the URL manifest.")
        sys.exit(1)
    
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    
    program_urls = manifest.get("program", [])
    track_urls = manifest.get("track", [])
    
    print(f"Scraping {len(program_urls)} programs and {len(track_urls)} tracks...")
    
    # Scrape programs
    programs = []
    for i, url in enumerate(program_urls, 1):
        print(f"[{i}/{len(program_urls)}] {url}")
        data = scrape_program(url)
        if data:
            classification = classify_program(url, data.get("name", ""))
            data.update(classification)
            programs.append(data)
        else:
            print(f"  FAILED: {url}")
    
    programs_out = DATA / "programs.json"
    programs_out.write_text(json.dumps(programs, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved {len(programs)} programs to {programs_out}")
    
    # Scrape tracks
    tracks = []
    for i, url in enumerate(track_urls, 1):
        print(f"[{i}/{len(track_urls)}] {url}")
        data = scrape_program(url)
        if data:
            data["degree_type"] = "Transfer Track"
            tracks.append(data)
        else:
            print(f"  FAILED: {url}")
    
    tracks_out = DATA / "tracks.json"
    tracks_out.write_text(json.dumps(tracks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(tracks)} tracks to {tracks_out}")


if __name__ == "__main__":
    main()

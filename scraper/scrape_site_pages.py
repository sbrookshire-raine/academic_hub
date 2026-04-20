"""
Scrape general FVCC site pages (academic areas, admissions, student services, etc.)
into structured markdown + metadata. These provide institutional context that agents need.

Outputs: data/site_pages.json
"""

import json
import re
import time
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MANIFEST = DATA / "url_manifest.json"

HEADERS = {
    "User-Agent": "FVCC-DataCollector/1.0 (educational research)"
}
DELAY = 1.5

# Which categories of pages to scrape (skip 'program' and 'track' — separate scraper)
CATEGORIES = [
    "academic_area",
    "academics",
    "admissions",
    "student_services",
    "community_education",
    "campus_life",
    "about",
]


def fetch_page(url: str, retries: int = 3):
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            time.sleep(DELAY)
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(DELAY * (attempt + 1))
    return None


def clean_text(el) -> str:
    if el is None:
        return ""
    text = el.get_text(separator="\n", strip=True)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def scrape_page(url: str) -> dict | None:
    soup = fetch_page(url)
    if not soup:
        return None

    h1 = soup.find("h1")
    title = clean_text(h1) if h1 else ""

    content = soup.find("main") or soup.find(class_="entry-content") or soup.find(id="content")
    full_text = clean_text(content) if content else ""

    # Extract all headings and their content for structured access
    sections = []
    if content:
        for heading in content.find_all(re.compile(r'^h[2-4]$')):
            heading_text = heading.get_text(strip=True)
            parts = []
            for sib in heading.next_siblings:
                if isinstance(sib, Tag) and sib.name and re.match(r'^h[2-4]$', sib.name):
                    break
                if isinstance(sib, Tag):
                    t = clean_text(sib)
                    if t:
                        parts.append(t)
            sections.append({
                "heading": heading_text,
                "content": "\n".join(parts)
            })

    # Extract internal links
    links = []
    target = content or soup
    for a in target.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if href.startswith("/"):
            href = f"https://www.fvcc.edu{href}"
        if "fvcc.edu" in href and text and href != url:
            links.append({"text": text, "url": href})

    return {
        "url": url,
        "title": title,
        "full_text": full_text,
        "sections": sections,
        "links": links,
    }


def main():
    if not MANIFEST.exists():
        print("Run extract_urls.py first.")
        sys.exit(1)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    all_pages = []
    for cat in CATEGORIES:
        urls = manifest.get(cat, [])
        print(f"\n=== {cat} ({len(urls)} pages) ===")
        for i, url in enumerate(urls, 1):
            print(f"  [{i}/{len(urls)}] {url}")
            data = scrape_page(url)
            if data:
                data["category"] = cat
                all_pages.append(data)
            else:
                print(f"    FAILED")

    out = DATA / "site_pages.json"
    out.write_text(json.dumps(all_pages, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved {len(all_pages)} pages to {out}")


if __name__ == "__main__":
    main()

"""
Deep FVCC Website Crawler
==========================
Crawls fvcc.edu comprehensively by following internal links starting from
key entry points. Unlike the targeted scrapers, this discovers pages
organically — every page the site links to is captured.

Respects rate limits, avoids duplicates, skips binary/media files.
Extracts structured content with topic classification so the knowledge
base can surface the right info to students and advisors.

Outputs: data/deep_pages.json

Usage:
    python scraper/crawl_site.py              # Full crawl
    python scraper/crawl_site.py --max 50     # Quick test (50 pages)
"""

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

HEADERS = {
    "User-Agent": "FVCC-DataCollector/1.0 (educational research)"
}
DELAY = 1.2  # seconds between requests

# Seed URLs — entry points that link to everything else
SEED_URLS = [
    "https://www.fvcc.edu",
    "https://www.fvcc.edu/current-students",
    "https://www.fvcc.edu/prospective-students",
    "https://www.fvcc.edu/parents-visitors",
    "https://www.fvcc.edu/academics",
    "https://www.fvcc.edu/admissions-financial-aid",
    "https://www.fvcc.edu/student-services",
    "https://www.fvcc.edu/community-education",
    "https://www.fvcc.edu/campus-life",
    "https://www.fvcc.edu/about",
    "https://www.fvcc.edu/lcc",
    "https://www.fvcc.edu/workforce",
    "https://www.fvcc.edu/academics/academic-resources",
    "https://www.fvcc.edu/academics/transfer",
    "https://www.fvcc.edu/academics/running-start",
    "https://www.fvcc.edu/academics/online-learning",
    "https://www.fvcc.edu/academics/honors-program",
    "https://www.fvcc.edu/admissions-financial-aid/financial-aid",
    "https://www.fvcc.edu/admissions-financial-aid/tuition-fees",
    "https://www.fvcc.edu/admissions-financial-aid/scholarships",
    "https://www.fvcc.edu/student-services/advising",
    "https://www.fvcc.edu/student-services/tutoring",
    "https://www.fvcc.edu/student-services/disability-services",
    "https://www.fvcc.edu/student-services/career-services",
    "https://www.fvcc.edu/student-services/veterans",
    "https://www.fvcc.edu/campus-life/student-housing",
    "https://www.fvcc.edu/campus-life/bookstore",
]

# Skip patterns — don't crawl these
SKIP_PATTERNS = [
    r"\.pdf$", r"\.docx?$", r"\.xlsx?$", r"\.pptx?$",
    r"\.jpg$", r"\.jpeg$", r"\.png$", r"\.gif$", r"\.svg$", r"\.webp$",
    r"\.mp4$", r"\.mp3$", r"\.zip$", r"\.csv$",
    r"/wp-content/uploads/",
    r"/wp-content/themes/.*/assets/",
    r"/wp-json/", r"/feed/", r"/xmlrpc",
    r"elements\.fvcc\.edu/student/",  # login portal
    r"elements\.fvcc\.edu/Schedules/", # handled by schedule scraper
    r"catalog\.fvcc\.edu/",  # handled by catalog scraper
    r"connect\.fvcc\.edu/",  # RSVP/event registration app
    r"campusce\.fvcc\.edu/",  # community ed registration app
    r"eaglemail\.fvcc\.edu",  # webmail
    r"^webcal://",  # calendar subscriptions
    r"\?s=",  # search queries
    r"#",  # anchors (strip before checking)
    r"mailto:", r"tel:",
    r"facebook\.com", r"instagram\.com", r"linkedin\.com", r"youtube\.com", r"twitter\.com",
    r"/events/list/page/\d+",  # paginated event listings (just noise)
    r"/events/month/\d{4}-\d{2}",  # month-by-month event archives
    r"/events/week/",  # week-by-week event archives
    r"/events/\d{4}-\d{2}-\d{2}",  # daily event calendar pages
    r"/event/.*/\d{4}-\d{2}-\d{2}",  # event instances by date
    r"/about/news/page/\d+",  # paginated news archives
    r"camsportal\.fvcc\.edu",  # student login portal (timeouts)
    r"slate\.fvcc\.edu",  # admissions CRM (limited content)
]

# Topic classification — maps URL patterns and content keywords to student-friendly topics
TOPIC_RULES = [
    ("Paying for College",       ["/tuition", "/financial-aid", "/scholarships", "/fafsa", "/costs"],
                                 ["tuition", "financial aid", "fafsa", "scholarship", "payment plan", "fee"]),
    ("Getting Started",          ["/admissions", "/apply", "/prospective", "/getting-started", "/placement"],
                                 ["apply", "admission", "enrollment", "placement test", "orientation", "new student"]),
    ("Registration",             ["/registration", "/register", "/add-drop", "/waitlist"],
                                 ["register", "registration", "add/drop", "waitlist", "enrollment"]),
    ("Transfer",                 ["/transfer", "/core-complete", "/articulation"],
                                 ["transfer", "articulation", "core complete"]),
    ("Academic Support",         ["/tutoring", "/academic-support", "/learning-center", "/library"],
                                 ["tutoring", "tutor", "study skills", "learning center", "library"]),
    ("Advising",                 ["/advising", "/advisor", "/academic-planning"],
                                 ["advising", "advisor", "academic plan"]),
    ("Career & Jobs",            ["/career", "/employment", "/workforce", "/internship"],
                                 ["career", "employment", "job", "internship", "workforce"]),
    ("Student Life",             ["/campus-life", "/clubs", "/activities", "/housing", "/bookstore", "/food"],
                                 ["campus life", "club", "student government", "housing", "bookstore"]),
    ("Veterans",                 ["/veterans", "/va-benefits", "/military"],
                                 ["veteran", "military", "gi bill", "va benefits"]),
    ("Accessibility",            ["/disability", "/accessibility", "/accommodations"],
                                 ["disability", "accommodation", "accessibility", "ada"]),
    ("Running Start",            ["/running-start", "/dual-enrollment", "/high-school"],
                                 ["running start", "dual enrollment", "high school"]),
    ("Online Learning",          ["/online-learning", "/distance", "/remote"],
                                 ["online learning", "online class", "distance education", "remote"]),
    ("Important Dates",          ["/calendar", "/academic-calendar", "/deadlines"],
                                 ["academic calendar", "deadline", "important date", "semester start"]),
    ("Graduation",               ["/graduation", "/commencement", "/degree-completion"],
                                 ["graduation", "commencement", "cap and gown", "diploma"]),
    ("Safety & Policies",        ["/safety", "/security", "/title-ix", "/privacy", "/policy"],
                                 ["safety", "security", "title ix", "privacy policy"]),
    ("About FVCC",               ["/about", "/mission", "/history", "/foundation", "/board"],
                                 ["mission", "history", "foundation", "board of trustees", "accreditation"]),
    ("Lincoln County Campus",    ["/lcc"],
                                 ["lincoln county", "libby"]),
    ("Community Education",      ["/community-education", "/continuing-education", "/non-credit"],
                                 ["community education", "continuing education", "non-credit", "lifelong"]),
]


def normalize_url(url: str, base: str = "") -> str | None:
    """Normalize a URL, resolve relative paths, strip fragments/tracking params."""
    if not url:
        return None
    for pattern in [r"^mailto:", r"^tel:", r"^javascript:"]:
        if re.match(pattern, url, re.I):
            return None

    if base:
        url = urljoin(base, url)

    parsed = urlparse(url)

    # Only fvcc.edu domains
    if not parsed.hostname or "fvcc.edu" not in parsed.hostname:
        return None

    # Strip fragment
    cleaned = urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))

    # Skip binary/media/external
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, cleaned, re.I):
            return None

    return cleaned


def classify_topic(url: str, text: str) -> list[str]:
    """Assign topic tags based on URL and page content."""
    url_lower = url.lower()
    text_lower = text.lower()[:3000]  # only check beginning for speed
    topics = []

    for topic_name, url_patterns, content_keywords in TOPIC_RULES:
        for pat in url_patterns:
            if pat in url_lower:
                topics.append(topic_name)
                break
        else:
            # Check content keywords if URL didn't match
            for kw in content_keywords:
                if kw in text_lower:
                    topics.append(topic_name)
                    break

    return topics if topics else ["General"]


def extract_key_facts(sections: list[dict], full_text: str) -> list[str]:
    """Pull out actionable facts — dates, phone numbers, locations, hours, dollar amounts."""
    facts = []
    text = full_text

    # Dollar amounts (tuition, fees)
    for match in re.finditer(r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:per|/)\s*\w+)?', text):
        context_start = max(0, match.start() - 40)
        context_end = min(len(text), match.end() + 40)
        context = text[context_start:context_end].strip()
        # Clean up
        context = re.sub(r'\s+', ' ', context)
        if len(context) > 20:
            facts.append(context)

    # Phone numbers
    for match in re.finditer(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text):
        context_start = max(0, match.start() - 30)
        context_end = min(len(text), match.end() + 10)
        context = text[context_start:context_end].strip()
        context = re.sub(r'\s+', ' ', context)
        if len(context) > 10:
            facts.append(context)

    # Email addresses
    for match in re.finditer(r'[\w.+-]+@fvcc\.edu', text):
        facts.append(match.group())

    # Hours/schedules (e.g., "Monday-Friday 8am-5pm")
    for match in re.finditer(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[\w\s,-]*\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)', text, re.I):
        fact = match.group().strip()
        if len(fact) > 10:
            facts.append(fact)

    # Deduplicate
    seen = set()
    unique = []
    for f in facts:
        key = re.sub(r'\s+', '', f.lower())
        if key not in seen:
            seen.add(key)
            unique.append(f)

    return unique[:15]  # cap at 15 facts per page


def fetch_page(url: str, retries: int = 3) -> BeautifulSoup | None:
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 404:
                return None  # don't retry 404s
            resp.raise_for_status()
            time.sleep(DELAY)
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            print(f"    Attempt {attempt+1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(DELAY * (attempt + 1))
    return None


def clean_text(el) -> str:
    if el is None:
        return ""
    text = el.get_text(separator="\n", strip=True)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def scrape_page(url: str) -> dict | None:
    """Scrape a single page, extracting structure, topics, and facts."""
    soup = fetch_page(url)
    if not soup:
        return None

    h1 = soup.find("h1")
    title = clean_text(h1) if h1 else ""

    content = soup.find("main") or soup.find(class_="entry-content") or soup.find(id="content")
    full_text = clean_text(content) if content else ""

    if not full_text or len(full_text) < 30:
        return None  # skip empty/stub pages

    # Extract structured sections
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
            sections.append({"heading": heading_text, "content": "\n".join(parts)})

    # Discover internal links
    discovered = []
    target = content or soup
    for a in target.find_all("a", href=True):
        href = a["href"]
        link_text = a.get_text(strip=True)
        normalized = normalize_url(href, url)
        if normalized and normalized != url:
            discovered.append({"url": normalized, "text": link_text})

    # Classify topics
    topics = classify_topic(url, full_text)

    # Extract key facts
    facts = extract_key_facts(sections, full_text)

    # Build a student-friendly summary (first meaningful paragraph)
    summary = ""
    for para in full_text.split("\n"):
        para = para.strip()
        if len(para) > 60 and not para.startswith("©") and not para.startswith("FVCC"):
            summary = para[:300]
            break

    return {
        "url": url,
        "title": title,
        "summary": summary,
        "topics": topics,
        "full_text": full_text,
        "sections": sections,
        "key_facts": facts,
        "links_found": len(discovered),
        "_discovered_urls": [d["url"] for d in discovered],
    }


def crawl(max_pages: int = 0) -> list[dict]:
    """Breadth-first crawl starting from seed URLs."""
    queue = list(SEED_URLS)
    visited = set()
    pages = []

    print(f"Starting crawl with {len(queue)} seed URLs")
    if max_pages:
        print(f"Limiting to {max_pages} pages")

    while queue:
        if max_pages and len(pages) >= max_pages:
            break

        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        print(f"  [{len(pages)+1}] {url}")
        page = scrape_page(url)

        if page:
            # Add discovered links to queue
            for discovered_url in page.pop("_discovered_urls", []):
                if discovered_url not in visited:
                    queue.append(discovered_url)

            pages.append(page)
        else:
            print(f"    (skipped)")

    return pages


def main():
    max_pages = 0
    if "--max" in sys.argv:
        idx = sys.argv.index("--max")
        if idx + 1 < len(sys.argv):
            max_pages = int(sys.argv[idx + 1])

    pages = crawl(max_pages)

    # Sort by topic for readability
    pages.sort(key=lambda p: (p["topics"][0] if p["topics"] else "", p["url"]))

    # Stats
    topic_counts = {}
    for page in pages:
        for topic in page["topics"]:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

    result = {
        "metadata": {
            "total_pages": len(pages),
            "topics": topic_counts,
            "seed_urls": SEED_URLS,
        },
        "pages": pages,
    }

    out = DATA / "deep_pages.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved {len(pages)} pages to {out}")
    print(f"Topics: {json.dumps(topic_counts, indent=2)}")


if __name__ == "__main__":
    main()

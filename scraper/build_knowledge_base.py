"""
Build the unified FVCC knowledge base from scraped data.
Normalizes, indexes, and creates queryable structures.

Outputs:
  data/fvcc_knowledge_base.json  — master knowledge base
  data/program_index.json        — quick-lookup index by name, degree, division
  data/search_index.json         — flattened text index for keyword search
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def load_json(name: str) -> list | dict:
    p = DATA / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return []


def normalize_division(program: dict) -> str:
    """Infer division from URL, breadcrumbs, or content."""
    url = program.get("url", "").lower()
    name = program.get("name", "").lower()
    text = (program.get("breadcrumbs", "") + " " + program.get("full_text", "")).lower()

    # Check URL path first — most reliable signal
    url_division_map = {
        "/nursing": "Nursing",
        "/trades-institute": "Trades Institute",
        "/culinary-arts": "Culinary Arts",
        "/health-sciences": "Health Sciences",
        "/humanities": "Humanities",
        "/business-technology": "Business and Technology",
        "/mathematics-computer-science": "Math and Computer Science",
        "/science-engineering": "Science and Engineering",
        "/social-sciences": "Social Sciences",
    }
    for url_part, div in url_division_map.items():
        if url_part in url:
            return div

    # Ordered division rules — checked against program name first, then full text.
    # More specific patterns come first to avoid false matches.
    # Each rule: (division, name_keywords, text_keywords)
    rules = [
        ("Nursing", ["nursing", "nurse aide", "registered nurs", "practical nurs"], []),
        ("Trades Institute", ["electrical", "electronics", "firearms", "industrial machine",
            "surveying", "welding", "hvac", "heavy equipment", "commercial driver", "apprentice"], []),
        ("Culinary Arts", ["culinary", "catering"], []),
        ("General Studies", ["exploring", "general studies"], []),
        ("Health Sciences", ["medical", "paramedicine", "paramedic", "physical therapist",
            "radiologic", "surgical", "phlebotomy", "emt", "emergency medical",
            "healthcare core", "health and human performance"], []),
        ("Science and Engineering", ["natural resources", "agriculture", "forestry", "biology",
            "biotechnology", "chemistry", "engineering", "environmental", "geology", "physics",
            "pre-dental", "pre-medicine", "pre-pharmacy", "pre-veterinary", "wildlife",
            "earth science", "geography", "forensic", "parks", "pre-physical therapy"], []),
        ("Social Sciences", ["criminal justice", "criminology", "early childhood", "education",
            "elementary education", "secondary education", "substance abuse", "social work",
            "pre-social work", "economics", "history", "psychology", "sociology"], []),
        ("Math and Computer Science", ["programming", "software development", "web development",
            "computer science", "mathematics"], []),
        ("Business and Technology", ["business", "accounting", "information technology",
            "payroll", "social media marketing", "office technology"], []),
        ("Humanities", ["goldsmithing", "graphic design", "media arts", "theatre", "art",
            "english", "music", "liberal studies"], []),
    ]

    for div, name_kws, text_kws in rules:
        for kw in name_kws:
            if kw in name:
                return div
        for kw in text_kws:
            if kw in text:
                return div

    # Fallback: check full text with the name keywords too
    for div, name_kws, _ in rules:
        for kw in name_kws:
            if kw in text:
                return div

    return "Unknown"


def build_program_record(raw: dict) -> dict:
    """Normalize a raw scraped program into a clean record."""
    name = raw.get("name", "").strip()
    
    record = {
        "name": name,
        "url": raw.get("url", ""),
        "degree_type": raw.get("degree_type", ""),
        "division": normalize_division(raw),
        "description": raw.get("description", ""),
        "learning_outcomes": raw.get("learning_outcomes", ""),
        "requirements": raw.get("requirements", ""),
        "curriculum": raw.get("curriculum", ""),
        "courses": raw.get("courses", []),
        "total_credits": raw.get("total_credits", ""),
        "careers": raw.get("careers", ""),
        "transfer_info": raw.get("transfer", ""),
        "contact": raw.get("contact", ""),
        "costs": raw.get("costs", ""),
        "full_text": raw.get("full_text", ""),
    }
    
    # If description is empty, try to extract first meaningful paragraph from full_text
    if not record["description"] and record["full_text"]:
        paragraphs = [p.strip() for p in record["full_text"].split("\n") if len(p.strip()) > 50]
        if paragraphs:
            record["description"] = paragraphs[0]
    
    return record


def build_search_entry(record: dict, record_type: str) -> dict:
    """Create a flat text entry for keyword searching."""
    searchable = " ".join([
        record.get("name", ""),
        record.get("degree_type", ""),
        record.get("division", ""),
        record.get("description", ""),
        record.get("learning_outcomes", ""),
        record.get("careers", ""),
    ]).lower()
    
    # Remove excessive whitespace
    searchable = re.sub(r'\s+', ' ', searchable).strip()
    
    return {
        "name": record.get("name", ""),
        "type": record_type,
        "url": record.get("url", ""),
        "degree_type": record.get("degree_type", ""),
        "division": record.get("division", ""),
        "text": searchable,
    }


def main():
    programs_raw = load_json("programs.json")
    tracks_raw = load_json("tracks.json")
    site_pages_raw = load_json("site_pages.json")
    deep_pages_raw = load_json("deep_pages.json")
    
    # Build normalized program records
    programs = [build_program_record(p) for p in programs_raw]
    tracks = [build_program_record(t) for t in tracks_raw]
    
    # Build site pages records
    site_pages = []
    for page in site_pages_raw:
        site_pages.append({
            "title": page.get("title", ""),
            "url": page.get("url", ""),
            "category": page.get("category", ""),
            "full_text": page.get("full_text", ""),
            "sections": page.get("sections", []),
        })

    # Merge deep-crawled pages (avoid duplicates with site_pages by URL)
    existing_urls = {p["url"] for p in site_pages}
    deep_pages = []
    if isinstance(deep_pages_raw, dict):
        raw_deep = deep_pages_raw.get("pages", [])
    else:
        raw_deep = deep_pages_raw if isinstance(deep_pages_raw, list) else []
    for page in raw_deep:
        url = page.get("url", "")
        if url and url not in existing_urls:
            deep_pages.append({
                "title": page.get("title", ""),
                "url": url,
                "category": "deep_crawl",
                "topics": page.get("topics", []),
                "summary": page.get("summary", ""),
                "full_text": page.get("full_text", ""),
                "sections": page.get("sections", []),
                "key_facts": page.get("key_facts", []),
            })
            existing_urls.add(url)
    
    # === Student-Friendly Topic Index ===
    # Maps topics like "Paying for College" → list of relevant pages with summaries
    topic_index = {}
    for page in deep_pages:
        for topic in page.get("topics", []):
            topic_index.setdefault(topic, []).append({
                "title": page["title"],
                "url": page["url"],
                "summary": page.get("summary", ""),
                "key_facts": page.get("key_facts", [])[:5],
            })
    # Also index site_pages by running them through topic classification
    for page in site_pages:
        url_lower = page.get("url", "").lower()
        text_lower = page.get("full_text", "").lower()[:2000]
        matched_topics = []
        topic_rules = [
            ("Paying for College",  ["/tuition", "/financial-aid", "/scholarships"],
                                    ["tuition", "financial aid", "scholarship"]),
            ("Getting Started",     ["/admissions", "/apply", "/prospective"],
                                    ["apply", "admission", "enrollment"]),
            ("Academic Support",    ["/tutoring", "/academic-support", "/library"],
                                    ["tutoring", "tutor", "library"]),
            ("Career & Jobs",       ["/career", "/employment", "/workforce"],
                                    ["career", "employment", "workforce"]),
            ("Registration",        ["/registration", "/register"],
                                    ["register", "registration"]),
            ("Transfer",            ["/transfer", "/core-complete"],
                                    ["transfer"]),
            ("Important Dates",     ["/calendar"],
                                    ["academic calendar", "deadline"]),
            ("Veterans",            ["/veterans"],
                                    ["veteran", "gi bill"]),
            ("Accessibility",       ["/disability", "/accessibility"],
                                    ["disability", "accommodation"]),
        ]
        for topic_name, url_pats, kws in topic_rules:
            for pat in url_pats:
                if pat in url_lower:
                    matched_topics.append(topic_name)
                    break
            else:
                for kw in kws:
                    if kw in text_lower:
                        matched_topics.append(topic_name)
                        break
        for topic in matched_topics:
            topic_index.setdefault(topic, []).append({
                "title": page["title"],
                "url": page["url"],
                "summary": page.get("full_text", "")[:200],
                "key_facts": [],
            })

    all_site_pages = site_pages + deep_pages
    
    # === Master Knowledge Base ===
    kb = {
        "institution": {
            "name": "Flathead Valley Community College",
            "abbreviation": "FVCC",
            "location": "777 Grandview Drive, Kalispell, MT 59901",
            "phone": "(406) 756-3822",
            "lincoln_county_campus": {
                "location": "225 Commerce Way, Libby, MT 59923",
                "phone": "(406) 293-2721"
            },
            "website": "https://www.fvcc.edu",
            "academic_year": "2025-2026",
            "scraped_date": "2026-04-14"
        },
        "tuition": load_json("tuition.json").get("summary", {}) if isinstance(load_json("tuition.json"), dict) else {},
        "student_essentials": "See data/student_essentials.json for plain-language student guide",
        "divisions": sorted(set(p["division"] for p in programs + tracks)),
        "degree_types": sorted(set(p["degree_type"] for p in programs if p["degree_type"])),
        "programs": programs,
        "tracks": tracks,
        "site_pages": all_site_pages,
        "topic_index": topic_index,
        "stats": {
            "total_programs": len(programs),
            "total_tracks": len(tracks),
            "total_site_pages": len(all_site_pages),
            "total_deep_pages": len(deep_pages),
            "topics": sorted(topic_index.keys()),
            "programs_by_division": {},
            "programs_by_degree_type": {},
        }
    }
    
    # Compute stats
    for p in programs:
        div = p["division"]
        dt = p["degree_type"]
        kb["stats"]["programs_by_division"][div] = kb["stats"]["programs_by_division"].get(div, 0) + 1
        kb["stats"]["programs_by_degree_type"][dt] = kb["stats"]["programs_by_degree_type"].get(dt, 0) + 1
    
    # Save knowledge base
    kb_path = DATA / "fvcc_knowledge_base.json"
    kb_path.write_text(json.dumps(kb, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Knowledge base: {kb_path} ({len(programs)} programs, {len(tracks)} tracks, {len(all_site_pages)} pages)")
    
    # === Quick-Lookup Index ===
    index = {
        "by_name": {},
        "by_division": {},
        "by_degree_type": {},
    }
    
    for i, p in enumerate(programs):
        index["by_name"][p["name"].lower()] = i
        div = p["division"]
        index["by_division"].setdefault(div, []).append(i)
        dt = p["degree_type"]
        index["by_degree_type"].setdefault(dt, []).append(i)
    
    idx_path = DATA / "program_index.json"
    idx_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"Program index: {idx_path}")
    
    # === Search Index ===
    search_entries = []
    for p in programs:
        search_entries.append(build_search_entry(p, "program"))
    for t in tracks:
        search_entries.append(build_search_entry(t, "track"))
    for page in site_pages:
        search_entries.append({
            "name": page.get("title", ""),
            "type": "page",
            "url": page.get("url", ""),
            "degree_type": "",
            "division": "",
            "text": (page.get("title", "") + " " + page.get("full_text", "")).lower()[:2000],
        })
    for page in deep_pages:
        topics_str = " ".join(page.get("topics", []))
        search_entries.append({
            "name": page.get("title", ""),
            "type": "page",
            "url": page.get("url", ""),
            "degree_type": "",
            "division": "",
            "topics": page.get("topics", []),
            "text": (page.get("title", "") + " " + topics_str + " " + page.get("full_text", "")).lower()[:2000],
        })
    
    search_path = DATA / "search_index.json"
    search_path.write_text(json.dumps(search_entries, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Search index: {search_path} ({len(search_entries)} entries)")

    # === Topic Index (for student portal) ===
    topic_path = DATA / "topic_index.json"
    topic_path.write_text(json.dumps(topic_index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Topic index: {topic_path} ({len(topic_index)} topics)")


if __name__ == "__main__":
    main()

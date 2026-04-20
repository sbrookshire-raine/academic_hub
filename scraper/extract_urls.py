"""
Extract all unique FVCC URLs from the scraped markdown source document.
Categorizes them by type: program, track, academic-area, general site pages.
Outputs: data/url_manifest.json
"""

import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_MD = next(ROOT.glob("www.fvcc.edu_academics_programs-courses_programs*.md"))
OUT = ROOT / "data" / "url_manifest.json"


def extract_urls(text: str) -> list[str]:
    """Pull every URL from markdown link syntax and bare URLs."""
    md_links = re.findall(r'\[.*?\]\((https?://[^)]+)\)', text)
    bare = re.findall(r'(?<!\()(https?://(?:www\.)?fvcc\.edu/[^\s\)]+)', text)
    return list(dict.fromkeys(md_links + bare))  # dedupe, preserve order


def categorize(url: str) -> str:
    if "/program/" in url:
        return "program"
    if "/track/" in url:
        return "track"
    if "/academics/academic-areas/" in url:
        return "academic_area"
    if "/academics/" in url:
        return "academics"
    if "/admissions-financial-aid/" in url:
        return "admissions"
    if "/student-services/" in url:
        return "student_services"
    if "/community-education/" in url:
        return "community_education"
    if "/campus-life/" in url:
        return "campus_life"
    if "/about/" in url:
        return "about"
    return "other"


def main():
    text = SOURCE_MD.read_text(encoding="utf-8")
    urls = extract_urls(text)

    # Only keep fvcc.edu URLs
    fvcc_urls = [u for u in urls if "fvcc.edu" in u]

    manifest = {}
    for url in fvcc_urls:
        cat = categorize(url)
        manifest.setdefault(cat, [])
        if url not in manifest[cat]:
            manifest[cat].append(url)

    # Summary
    total = sum(len(v) for v in manifest.values())
    summary = {cat: len(urls) for cat, urls in manifest.items()}
    print(f"Total unique FVCC URLs: {total}")
    for cat, count in sorted(summary.items()):
        print(f"  {cat}: {count}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nWritten to {OUT}")


if __name__ == "__main__":
    main()

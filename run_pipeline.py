"""
Master pipeline: Run ALL data collection and processing steps in sequence.
This is the single entry point to rebuild the entire knowledge base from scratch.

Usage: python run_pipeline.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = [
    ("Extract URLs from source document", ROOT / "scraper" / "extract_urls.py"),
    ("Scrape program & track pages", ROOT / "scraper" / "scrape_programs.py"),
    ("Scrape site pages (admissions, services, etc.)", ROOT / "scraper" / "scrape_site_pages.py"),
    ("Deep crawl fvcc.edu (all linked pages)", ROOT / "scraper" / "crawl_site.py"),
    ("Scrape course schedules (SP26, SU26, FA26)", ROOT / "scraper" / "scrape_schedules.py"),
    ("Scrape catalog course requirements", ROOT / "scraper" / "scrape_catalog.py"),
    ("Scrape tuition & fee schedule", ROOT / "scraper" / "scrape_tuition.py"),
    ("Build student essentials guide", ROOT / "scraper" / "build_student_essentials.py"),
    ("Build knowledge base & indexes", ROOT / "scraper" / "build_knowledge_base.py"),
    ("Export Markdown reference", None),  # handled via query tool
]


def run_step(desc: str, script: Path):
    print(f"\n{'='*60}")
    print(f"STEP: {desc}")
    print(f"{'='*60}")
    result = subprocess.run([sys.executable, str(script)], cwd=str(ROOT))
    if result.returncode != 0:
        print(f"FAILED: {desc}")
        sys.exit(1)
    print(f"DONE: {desc}")


def main():
    print("FVCC Data Pipeline — Full Rebuild")
    print("=" * 60)

    for desc, script in SCRIPTS:
        if script is None:
            # Export markdown via query tool
            print(f"\n{'='*60}")
            print(f"STEP: {desc}")
            print(f"{'='*60}")
            subprocess.run(
                [sys.executable, str(ROOT / "tools" / "fvcc_query.py"), "export-markdown"],
                cwd=str(ROOT)
            )
            continue
        run_step(desc, script)

    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE")
    print(f"{'='*60}")
    # Show final stats
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "fvcc_query.py"), "stats"],
        cwd=str(ROOT)
    )


if __name__ == "__main__":
    main()

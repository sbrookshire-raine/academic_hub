# FVCC Intelligence Package — Agent Instructions

## What This Is
A complete, structured knowledge base of **Flathead Valley Community College (FVCC)** academic programs, transfer tracks, **course schedules**, and institutional information. Scraped directly from fvcc.edu, catalog.fvcc.edu, and elements.fvcc.edu on 2026-04-14.

## Data Files

| File | Description |
|------|-------------|
| `data/fvcc_knowledge_base.json` | **Master KB** — all programs, tracks, site pages, institution info, and stats in one file |
| `data/programs.json` | Raw scraped data for all 67 degree/certificate programs |
| `data/tracks.json` | Raw scraped data for all 43 transfer tracks |
| `data/site_pages.json` | Scraped content from admissions, student services, campus life, and about pages |
| `data/schedules.json` | **Course schedules** — 1,135 sections across Spring/Summer/Fall 2026 |
| `data/program_courses.json` | **Catalog course requirements** — per-semester course plans for 58 programs |
| `data/search_index.json` | Flat text index for fast keyword search |
| `data/program_index.json` | Lookup index by name, division, and degree type |
| `data/url_manifest.json` | Complete URL catalog extracted from source document |
| `data/fvcc_programs_reference.md` | Full Markdown export of all programs (human-readable) |
| `data/tuition.json` | **Tuition & fees** — per-credit rates for all residency tiers, plain-English breakdown |
| `data/student_essentials.json` | **Student guide** — plain-language getting-started, costs, financial aid, calendar, support services, and jargon translations |

## Query Tool

The CLI tool `tools/fvcc_query.py` provides instant access to all data:

```bash
# Search across everything
python tools/fvcc_query.py search "nursing"

# Get full details on a specific program
python tools/fvcc_query.py program "Registered Nursing"

# List all programs in a division
python tools/fvcc_query.py division "Health Science"

# Filter by degree type
python tools/fvcc_query.py degree-type "AAS"

# List everything
python tools/fvcc_query.py list-programs
python tools/fvcc_query.py list-tracks
python tools/fvcc_query.py list-divisions

# Search institutional pages
python tools/fvcc_query.py page "financial aid"

# View stats
python tools/fvcc_query.py stats

# Export full markdown reference
python tools/fvcc_query.py export-markdown

# --- Schedule & Advising ---

# Full advising report (all terms, all sections, open seats)
python tools/fvcc_query.py advise "Registered Nursing"

# Advising filtered to a specific term
python tools/fvcc_query.py advise-term "Welding" "Fall 2026"

# Find all sections for a course across all terms
python tools/fvcc_query.py schedule "BIOH 201"

# See delivery modes, times, locations for a course
python tools/fvcc_query.py course-options "BIOH 211"

# Find open seats by department and term
python tools/fvcc_query.py open-seats NRSG "Spring 2026"

# List all courses in a term
python tools/fvcc_query.py schedule-term "Fall 2026"

# --- Student Essentials ---

# Show tuition breakdown (plain English)
python tools/fvcc_query.py tuition

# Browse student essentials guide
python tools/fvcc_query.py essentials
python tools/fvcc_query.py essentials getting_started
python tools/fvcc_query.py essentials costs
python tools/fvcc_query.py essentials financial_aid
python tools/fvcc_query.py essentials support_services

# Translate FVCC jargon to English
python tools/fvcc_query.py translate "SAP"
python tools/fvcc_query.py translate
```

### As a Python Module
```python
from tools.fvcc_query import FVCCQuery
q = FVCCQuery()

# Search
results = q.search("welding certification")

# Get program details
program = q.get_program("Welding and Fabrication Technology, AAS")

# List and filter
nursing_programs = q.list_programs(division="Nursing")
all_aas = q.list_programs(degree_type="AAS")

# Compare programs
comparison = q.compare_programs("Electrical Technology, AAS", "Electronics Technician, AAS")

# Export
markdown = q.export_program_markdown("Graphic Design, AAS")

# --- Schedule & Advising ---

# Full advising report with schedule data
report = q.advise_program("Registered Nursing", "Fall 2026")
# Returns: program courses by semester, with real-time schedule availability

# Human-readable advising report
print(q.format_advising_report("Welding", "Fall 2026"))

# Course schedule lookup
sections = q.get_course_schedule("BIOH 201", "Spring 2026")

# All options for a course
options = q.get_course_options("BIOH 211")

# Open seats by prefix
open_nrsg = q.get_open_sections("NRSG", "Spring 2026")
```

## Data Schema

### Program Record
Each program in `fvcc_knowledge_base.json → programs[]` has:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Official program name |
| `url` | string | Source page URL |
| `degree_type` | string | AAS, CAS, CTS, AA, AS, ASN, Transfer, Course/Training, Other |
| `division` | string | Academic division (e.g., "Health Science", "Trades Institute") |
| `description` | string | Program overview |
| `learning_outcomes` | string | What students will learn/achieve |
| `requirements` | string | Admission/prerequisite requirements |
| `curriculum` | string | Coursework description |
| `courses` | array | List of `{course, credits}` objects |
| `total_credits` | string | Credit total for the program |
| `careers` | string | Career/employment opportunities |
| `transfer_info` | string | Transfer pathway details |
| `contact` | string | Advisor/department contact info |
| `costs` | string | Tuition/cost information |
| `full_text` | string | Complete page text (for deep search) |

### Divisions
- Business and Technology
- Culinary Arts
- General Studies
- Health Sciences
- Humanities
- Math and Computer Science
- Nursing
- Science and Engineering
- Social Sciences
- Trades Institute

### Degree Types
- **Associate of Applied Science (AAS)** — 2-year career-ready degrees
- **Associate of Arts (AA)** — 2-year liberal arts degrees
- **Associate of Science (AS)** — 2-year science-focused degrees (transfer)
- **Associate of Science Nursing (ASN)** — Nursing degree
- **Certificate of Applied Science (CAS)** — ~1-year applied certificates
- **Certificate of Technical Studies (CTS)** — Short technical certificates
- **Transfer Program** — Designed to transfer to specific 4-year institutions
- **Transfer Track** — General guidance for transferring in a subject area
- **Course/Training** — Individual courses (CDL, CNA, EMT, Phlebotomy)

## Rebuilding the Data

To re-scrape and rebuild everything from scratch:
```bash
python run_pipeline.py
```

Or run steps individually:
```bash
python scraper/extract_urls.py        # Step 1: Extract URLs
python scraper/scrape_programs.py     # Step 2: Scrape programs & tracks
python scraper/scrape_site_pages.py   # Step 3: Scrape site pages
python scraper/scrape_schedules.py    # Step 4: Scrape course schedules (SP26, SU26, FA26)
python scraper/scrape_catalog.py      # Step 5: Scrape catalog course requirements
python scraper/build_knowledge_base.py # Step 6: Build KB & indexes
python tools/fvcc_query.py export-markdown  # Step 7: Export reference doc
```

## Agent Use Cases

This data package supports:

1. **Academic Advising** — "Show me what Nursing courses are available next fall with open seats" → `advise-term`
2. **Schedule Planning** — "When is BIOH 211 offered and what delivery modes?" → `course-options`
3. **Seat Availability** — "Are there open nursing sections for spring?" → `open-seats`
4. **Program Discovery** — "What programs does FVCC offer in healthcare?" → search by division
5. **Transfer Planning** — "How do I transfer to UM for forestry?" → get transfer program details
6. **Curriculum Documentation** — Generate program brochures, course maps with real schedule data
7. **Comparison** — "Compare welding CAS vs AAS" → use `compare_programs()`
8. **Institutional Q&A** — "What are FVCC's admissions requirements?" → search site pages
9. **Career Guidance** — "What can I do with a criminal justice degree?" → check careers field

## FVCC Quick Facts
- **Location:** Kalispell, Montana (Flathead Valley)
- **Second campus:** Lincoln County Campus in Libby, MT
- **Phone:** (406) 756-3822
- **Website:** https://www.fvcc.edu
- **Programs:** 67 degree/certificate programs across 10 divisions
- **Transfer tracks:** 43 tracks for transfer to 4-year schools
- **Schedule data:** 1,135 sections across Spring/Summer/Fall 2026 (615 unique courses)
- **Catalog data:** Structured course requirements for 58 programs (471 course-program links)
- **Data sources:** fvcc.edu, catalog.fvcc.edu, elements.fvcc.edu

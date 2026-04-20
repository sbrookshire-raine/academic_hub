"""
FVCC Knowledge Base Query Tool
===============================
Agent-ready CLI and importable module for querying FVCC data.

Usage as CLI:
    python fvcc_query.py search "nursing"
    python fvcc_query.py program "Registered Nursing"
    python fvcc_query.py division "Health Science"
    python fvcc_query.py degree-type "AAS"
    python fvcc_query.py list-programs
    python fvcc_query.py list-tracks
    python fvcc_query.py list-divisions
    python fvcc_query.py page "financial aid"
    python fvcc_query.py stats
    python fvcc_query.py export-markdown

  Schedule & Advising Commands:
    python fvcc_query.py schedule "BIOH 201"              -- Find all sections for a course
    python fvcc_query.py schedule-term "Fall 2026"        -- List all courses in a term
    python fvcc_query.py advise "Registered Nursing"      -- Show program courses + schedule availability
    python fvcc_query.py advise-term "Registered Nursing" "Fall 2026"  -- Program courses available next term
    python fvcc_query.py open-seats "NRSG" "Spring 2026"  -- Find open seats by prefix + term
    python fvcc_query.py course-options "BIOH 211"        -- All delivery modes/times for a course

Usage as module:
    from fvcc_query import FVCCQuery
    q = FVCCQuery()
    results = q.search("welding")
    program = q.get_program("Welding and Fabrication Technology, AAS")
    advising = q.advise_program("Registered Nursing", "Fall 2026")
"""

import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


class FVCCQuery:
    """Query interface for the FVCC knowledge base."""

    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir) if data_dir else DATA
        self._kb = None
        self._search_index = None
        self._schedules = None
        self._program_courses = None
        self._tuition = None
        self._essentials = None

    @property
    def kb(self) -> dict:
        if self._kb is None:
            kb_path = self.data_dir / "fvcc_knowledge_base.json"
            self._kb = json.loads(kb_path.read_text(encoding="utf-8"))
        return self._kb

    @property
    def search_index(self) -> list:
        if self._search_index is None:
            si_path = self.data_dir / "search_index.json"
            self._search_index = json.loads(si_path.read_text(encoding="utf-8"))
        return self._search_index

    @property
    def schedules(self) -> dict:
        if self._schedules is None:
            p = self.data_dir / "schedules.json"
            self._schedules = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"sections": [], "course_index": {}, "metadata": {}}
        return self._schedules

    @property
    def program_courses(self) -> dict:
        if self._program_courses is None:
            p = self.data_dir / "program_courses.json"
            self._program_courses = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"programs": [], "course_program_map": {}}
        return self._program_courses

    @property
    def tuition(self) -> dict:
        if self._tuition is None:
            p = self.data_dir / "tuition.json"
            self._tuition = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        return self._tuition

    @property
    def essentials(self) -> dict:
        if self._essentials is None:
            p = self.data_dir / "student_essentials.json"
            self._essentials = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        return self._essentials

    # -- Core Queries --

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Full-text keyword search across programs, tracks, and pages."""
        terms = query.lower().split()
        results = []
        for entry in self.search_index:
            text = entry.get("text", "")
            score = sum(1 for t in terms if t in text)
            # Boost exact phrase match
            if query.lower() in text:
                score += len(terms) * 2
            if score > 0:
                results.append({**entry, "_score": score})
        results.sort(key=lambda x: -x["_score"])
        # Remove internal text blob from output
        for r in results:
            r.pop("text", None)
        return results[:limit]

    def get_program(self, name: str) -> dict | None:
        """Get full program details by exact or fuzzy name match."""
        name_lower = name.lower()
        for p in self.kb["programs"]:
            if p["name"].lower() == name_lower:
                return p
        # Fuzzy: check if query is contained in name
        for p in self.kb["programs"]:
            if name_lower in p["name"].lower():
                return p
        return None

    def get_track(self, name: str) -> dict | None:
        """Get full track details by exact or fuzzy name match."""
        name_lower = name.lower()
        for t in self.kb["tracks"]:
            if t["name"].lower() == name_lower:
                return t
        for t in self.kb["tracks"]:
            if name_lower in t["name"].lower():
                return t
        return None

    def list_programs(self, division: str | None = None, degree_type: str | None = None) -> list[dict]:
        """List programs, optionally filtered by division and/or degree type."""
        results = self.kb["programs"]
        if division:
            results = [p for p in results if division.lower() in p["division"].lower()]
        if degree_type:
            results = [p for p in results if degree_type.lower() in p["degree_type"].lower()]
        return [{"name": p["name"], "degree_type": p["degree_type"], "division": p["division"], "url": p["url"]} for p in results]

    def list_tracks(self, division: str | None = None) -> list[dict]:
        """List transfer tracks, optionally filtered by division."""
        results = self.kb["tracks"]
        if division:
            results = [t for t in results if division.lower() in t["division"].lower()]
        return [{"name": t["name"], "division": t["division"], "url": t["url"]} for t in results]

    def list_divisions(self) -> list[str]:
        """List all academic divisions."""
        return self.kb["divisions"]

    def list_degree_types(self) -> list[str]:
        """List all degree types offered."""
        return self.kb["degree_types"]

    def get_page(self, query: str) -> list[dict]:
        """Search site pages (admissions, student services, etc.)."""
        query_lower = query.lower()
        results = []
        for page in self.kb.get("site_pages", []):
            title = page.get("title", "").lower()
            text = page.get("full_text", "").lower()
            if query_lower in title or query_lower in text:
                results.append({
                    "title": page["title"],
                    "url": page["url"],
                    "category": page.get("category", ""),
                    "sections": [s["heading"] for s in page.get("sections", [])],
                    "excerpt": page.get("full_text", "")[:500],
                })
        return results

    def get_institution_info(self) -> dict:
        """Get basic institution information."""
        return self.kb["institution"]

    def get_stats(self) -> dict:
        """Get knowledge base statistics."""
        return self.kb["stats"]

    def get_program_curriculum(self, name: str) -> dict | None:
        """Get just the curriculum/course info for a program."""
        p = self.get_program(name)
        if not p:
            return None
        return {
            "name": p["name"],
            "degree_type": p["degree_type"],
            "total_credits": p.get("total_credits", ""),
            "curriculum": p.get("curriculum", ""),
            "courses": p.get("courses", []),
        }

    def compare_programs(self, name1: str, name2: str) -> dict:
        """Compare two programs side by side."""
        p1 = self.get_program(name1)
        p2 = self.get_program(name2)
        if not p1 or not p2:
            return {"error": f"Could not find one or both programs: '{name1}', '{name2}'"}
        
        fields = ["name", "degree_type", "division", "total_credits", "description", "careers"]
        comparison = {}
        for f in fields:
            comparison[f] = {
                "program_1": p1.get(f, ""),
                "program_2": p2.get(f, ""),
            }
        return comparison

    def export_program_markdown(self, name: str) -> str:
        """Export a single program as formatted Markdown."""
        p = self.get_program(name) or self.get_track(name)
        if not p:
            return f"Program '{name}' not found."
        
        md = [f"# {p['name']}\n"]
        if p.get("degree_type"):
            md.append(f"**Degree Type:** {p['degree_type']}  ")
        if p.get("division"):
            md.append(f"**Division:** {p['division']}  ")
        if p.get("total_credits"):
            md.append(f"**Total Credits:** {p['total_credits']}  ")
        if p.get("url"):
            md.append(f"**URL:** {p['url']}  ")
        md.append("")
        
        for section, key in [
            ("Description", "description"),
            ("Learning Outcomes", "learning_outcomes"),
            ("Requirements", "requirements"),
            ("Curriculum", "curriculum"),
            ("Career Opportunities", "careers"),
            ("Transfer Information", "transfer_info"),
            ("Costs", "costs"),
            ("Contact", "contact"),
        ]:
            content = p.get(key, "")
            if content:
                md.append(f"## {section}\n")
                md.append(content)
                md.append("")
        
        if p.get("courses"):
            md.append("## Courses\n")
            md.append("| Course | Credits |")
            md.append("|--------|---------|")
            for c in p["courses"]:
                md.append(f"| {c.get('course', '')} | {c.get('credits', '')} |")
            md.append("")
        
        return "\n".join(md)

    def export_all_markdown(self) -> str:
        """Export the full knowledge base as a Markdown document."""
        sections = []
        sections.append("# FVCC Academic Programs Knowledge Base\n")
        sections.append(f"**Academic Year:** {self.kb['institution']['academic_year']}  ")
        sections.append(f"**Scraped:** {self.kb['institution']['scraped_date']}  ")
        sections.append(f"**Programs:** {self.kb['stats']['total_programs']}  ")
        sections.append(f"**Transfer Tracks:** {self.kb['stats']['total_tracks']}  \n")
        
        # Group programs by division
        by_div = {}
        for p in self.kb["programs"]:
            by_div.setdefault(p["division"], []).append(p)
        
        for div in sorted(by_div.keys()):
            sections.append(f"## {div}\n")
            # Group by degree type within division
            by_dt = {}
            for p in by_div[div]:
                by_dt.setdefault(p["degree_type"], []).append(p)
            
            for dt in sorted(by_dt.keys()):
                sections.append(f"### {dt}\n")
                for p in by_dt[dt]:
                    sections.append(f"#### {p['name']}\n")
                    if p.get("description"):
                        sections.append(p["description"][:500])
                    if p.get("total_credits"):
                        sections.append(f"\n**Credits:** {p['total_credits']}")
                    sections.append(f"\n**URL:** {p['url']}\n")
        
        # Tracks
        sections.append("## Transfer Tracks\n")
        for t in self.kb["tracks"]:
            sections.append(f"- **{t['name']}** ({t['division']}) — {t['url']}")
        
        return "\n".join(sections)

    # -- Schedule & Advising Queries --

    def _normalize_course_code(self, code: str) -> str:
        """Normalize a course code for matching: 'BIOH 201NL' -> 'BIOH_201NL', 'BIOH_201NL' unchanged."""
        return code.strip().replace(" ", "_")

    def _match_schedule_code(self, program_code: str) -> list[str]:
        """Find schedule course_index keys that match a program course code.
        Handles suffixes like NL, M, W that may differ between catalog and schedule."""
        norm = self._normalize_course_code(program_code)
        index = self.schedules.get("course_index", {})
        if norm in index:
            return [norm]
        # Try without common suffixes (NL, N, M, W, L, etc.)
        base = re.sub(r'[A-Z]+$', '', norm)
        if base and base != norm:
            matches = [k for k in index if k == base or k.startswith(base)]
            if matches:
                return matches
        # Fuzzy: try prefix match
        prefix = norm.split("_")[0] + "_" + norm.split("_")[1] if "_" in norm else norm
        matches = [k for k in index if k.startswith(prefix)]
        return matches

    def get_course_schedule(self, course_code: str, term: str | None = None) -> list[dict]:
        """Get all schedule sections for a course code, optionally filtered by term."""
        matches = self._match_schedule_code(course_code)
        results = []
        index = self.schedules.get("course_index", {})
        for key in matches:
            entry = index[key]
            for section in entry["sections"]:
                if term and term.lower() not in section["term"].lower():
                    continue
                results.append({
                    "course_code": key,
                    "title": entry["title"],
                    "department": entry["department"],
                    **section,
                })
        return results

    def get_open_sections(self, prefix: str, term: str | None = None) -> list[dict]:
        """Find all open sections for courses matching a prefix (e.g., 'NRSG', 'WLDG')."""
        prefix_upper = prefix.upper().replace(" ", "_")
        results = []
        for s in self.schedules.get("sections", []):
            if not s["course_code"].startswith(prefix_upper):
                continue
            if term and term.lower() not in s["term"].lower():
                continue
            if s["seats"]["available"] > 0:
                results.append(s)
        return results

    def get_course_options(self, course_code: str) -> dict:
        """Get all delivery modes, times, and locations for a course across all terms."""
        sections = self.get_course_schedule(course_code)
        if not sections:
            return {"course_code": course_code, "message": "No sections found in schedule"}
        
        result = {
            "course_code": course_code,
            "title": sections[0].get("title", ""),
            "terms_available": sorted(set(s["term"] for s in sections)),
            "delivery_modes": sorted(set(s["delivery_mode"] for s in sections)),
            "locations": sorted(set(s["location"] for s in sections)),
            "sections": [],
        }
        for s in sections:
            result["sections"].append({
                "full_code": s["full_code"],
                "term": s["term"],
                "days": s["days"],
                "time": s["time"],
                "room": s["room"],
                "delivery_mode": s["delivery_mode"],
                "location": s["location"],
                "instructor": s["instructor"],
                "seats": s["seats"],
                "additional_fee": s.get("additional_fee"),
                "notes": s.get("notes", []),
            })
        return result

    def get_catalog_program(self, name: str) -> dict | None:
        """Get catalog program with structured course requirements."""
        name_lower = name.lower()
        for p in self.program_courses.get("programs", []):
            if p["name"].lower() == name_lower:
                return p
        for p in self.program_courses.get("programs", []):
            if name_lower in p["name"].lower():
                return p
        return None

    def advise_program(self, program_name: str, term: str | None = None) -> dict:
        """Main advising function: show program courses with real-time schedule availability.
        
        Returns structured advising data:
        - Program info and semesters
        - For each required course: schedule availability, open seats, delivery modes
        - Warnings about courses not offered in the requested term
        """
        catalog = self.get_catalog_program(program_name)
        if not catalog:
            return {"error": f"Program '{program_name}' not found in catalog"}

        result = {
            "program": catalog["name"],
            "division": catalog.get("division", ""),
            "degree_type": catalog.get("degree_type", ""),
            "total_credits": catalog.get("total_credits", ""),
            "catalog_url": catalog.get("catalog_url", ""),
            "semesters": [],
            "summary": {
                "total_required_courses": 0,
                "courses_available_this_term": 0,
                "courses_with_open_seats": 0,
                "courses_not_scheduled": 0,
            },
        }

        for sem in catalog.get("semesters", []):
            sem_data = {
                "label": sem["label"],
                "semester_credits": sem.get("semester_credits", ""),
                "courses": [],
            }

            for course in sem["courses"]:
                norm_code = course["normalized_code"]
                sections = self.get_course_schedule(norm_code, term)
                all_sections = self.get_course_schedule(norm_code)

                course_data = {
                    "code": course["code"],
                    "title": course["title"],
                    "credits": course.get("credits", ""),
                    "or_next": course.get("or_next", False),
                    "terms_offered": sorted(set(s["term"] for s in all_sections)) if all_sections else [],
                    "sections_this_term": [],
                    "has_open_seats": False,
                    "delivery_modes": sorted(set(s["delivery_mode"] for s in sections)) if sections else [],
                }

                result["summary"]["total_required_courses"] += 1

                if sections:
                    result["summary"]["courses_available_this_term"] += 1
                    for s in sections:
                        sec_info = {
                            "full_code": s["full_code"],
                            "days": s["days"],
                            "time": s["time"],
                            "room": s["room"],
                            "delivery_mode": s["delivery_mode"],
                            "location": s["location"],
                            "instructor": s["instructor"],
                            "seats": s["seats"],
                            "additional_fee": s.get("additional_fee"),
                            "notes": s.get("notes", []),
                        }
                        course_data["sections_this_term"].append(sec_info)
                        if s["seats"]["available"] > 0:
                            course_data["has_open_seats"] = True

                    if course_data["has_open_seats"]:
                        result["summary"]["courses_with_open_seats"] += 1
                elif not all_sections:
                    result["summary"]["courses_not_scheduled"] += 1

                sem_data["courses"].append(course_data)

            result["semesters"].append(sem_data)

        return result

    def format_advising_report(self, program_name: str, term: str | None = None) -> str:
        """Generate a human-readable advising report for a program."""
        data = self.advise_program(program_name, term)
        if "error" in data:
            return data["error"]

        lines = []
        lines.append(f"# Advising Report: {data['program']}")
        lines.append(f"**Division:** {data['division']}  |  **Degree:** {data['degree_type']}  |  **Credits:** {data['total_credits']}")
        if term:
            lines.append(f"**Showing availability for:** {term}")
        lines.append(f"**Catalog:** {data['catalog_url']}")
        lines.append("")

        s = data["summary"]
        lines.append(f"## Summary")
        lines.append(f"- Required courses: {s['total_required_courses']}")
        if term:
            lines.append(f"- Available in {term}: {s['courses_available_this_term']}")
            lines.append(f"- With open seats: {s['courses_with_open_seats']}")
        lines.append(f"- Not in any schedule: {s['courses_not_scheduled']}")
        lines.append("")

        for sem in data["semesters"]:
            lines.append(f"## {sem['label']}")
            if sem.get("semester_credits"):
                lines.append(f"*Semester credits: {sem['semester_credits']}*\n")

            for c in sem["courses"]:
                or_marker = " *(OR alternative below)*" if c.get("or_next") else ""
                status = ""
                if c["sections_this_term"]:
                    open_count = sum(1 for s in c["sections_this_term"] if s["seats"]["available"] > 0)
                    total = len(c["sections_this_term"])
                    status = f" -- **{open_count}/{total} sections open**"
                    modes = ", ".join(c["delivery_modes"])
                    status += f" ({modes})"
                elif c["terms_offered"]:
                    status = f" -- [!] Not offered this term (available: {', '.join(c['terms_offered'])})"
                else:
                    status = " -- [X] Not found in schedule"

                lines.append(f"### {c['code']} - {c['title']} ({c['credits']}cr){or_marker}")
                lines.append(f"  {status}")

                if c["sections_this_term"]:
                    lines.append("")
                    lines.append("  | Section | Days | Time | Room | Mode | Instructor | Seats | Fee |")
                    lines.append("  |---------|------|------|------|------|------------|-------|-----|")
                    for sec in c["sections_this_term"]:
                        seats = sec["seats"]
                        seat_str = str(seats["available"])
                        if seats.get("waitlist"):
                            seat_str += f" (w{seats['waitlist']})"
                        if seats["status"] == "Full":
                            seat_str = "**FULL**"
                        elif seats["available"] < 0:
                            seat_str = f"**OVER ({seats['available']})**"
                        fee = sec.get("additional_fee") or ""
                        notes_str = ""
                        if sec.get("notes"):
                            notes_str = " [*]"
                        lines.append(
                            f"  | {sec['full_code']} | {sec['days']} | {sec['time']} | {sec['room']} "
                            f"| {sec['delivery_mode']} | {sec['instructor']} | {seat_str} | {fee} |{notes_str}"
                        )
                lines.append("")

        return "\n".join(lines)

    def schedule_search(self, query: str, term: str | None = None) -> list[dict]:
        """Search schedule by course code, title, instructor, or department."""
        query_lower = query.lower().replace(" ", "_")
        results = []
        for s in self.schedules.get("sections", []):
            if term and term.lower() not in s["term"].lower():
                continue
            searchable = f"{s['course_code']} {s['full_code']} {s['title']} {s['instructor']} {s['department']}".lower()
            if query_lower.replace("_", " ") in searchable or query_lower in searchable:
                results.append(s)
        return results


# -- CLI Interface --

def format_results(results: list[dict], compact: bool = False) -> str:
    if not results:
        return "No results found."
    if compact:
        return "\n".join(f"  - {r.get('name', r.get('title', '?'))} [{r.get('degree_type', r.get('category', ''))}]" for r in results)
    return json.dumps(results, indent=2, ensure_ascii=False)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    q = FVCCQuery()
    cmd = sys.argv[1].lower()
    arg = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""

    if cmd == "search":
        results = q.search(arg)
        print(f"Found {len(results)} results for '{arg}':\n")
        print(format_results(results, compact=True))
        print(f"\n(Use 'program <name>' for full details)")

    elif cmd == "program":
        p = q.get_program(arg)
        if p:
            print(q.export_program_markdown(arg))
        else:
            print(f"Program '{arg}' not found. Try: search {arg}")

    elif cmd == "track":
        t = q.get_track(arg)
        if t:
            print(q.export_program_markdown(arg))
        else:
            print(f"Track '{arg}' not found.")

    elif cmd == "division":
        programs = q.list_programs(division=arg)
        print(f"Programs in '{arg}':\n")
        print(format_results(programs, compact=True))

    elif cmd == "degree-type":
        programs = q.list_programs(degree_type=arg)
        print(f"Programs with degree type '{arg}':\n")
        print(format_results(programs, compact=True))

    elif cmd == "list-programs":
        programs = q.list_programs()
        print(f"All {len(programs)} programs:\n")
        print(format_results(programs, compact=True))

    elif cmd == "list-tracks":
        tracks = q.list_tracks()
        print(f"All {len(tracks)} transfer tracks:\n")
        print(format_results(tracks, compact=True))

    elif cmd == "list-divisions":
        for d in q.list_divisions():
            print(f"  - {d}")

    elif cmd == "page":
        pages = q.get_page(arg)
        print(f"Found {len(pages)} pages matching '{arg}':\n")
        for p in pages:
            print(f"  [{p['category']}] {p['title']}")
            print(f"    {p['url']}")
            if p.get('sections'):
                print(f"    Sections: {', '.join(p['sections'][:5])}")
            print()

    elif cmd == "stats":
        stats = q.get_stats()
        info = q.get_institution_info()
        print(f"FVCC Knowledge Base - {info['academic_year']}")
        print(f"{'='*50}")
        print(f"Programs: {stats['total_programs']}")
        print(f"Tracks: {stats['total_tracks']}")
        print(f"Site Pages: {stats['total_site_pages']}")
        print(f"\nBy Division:")
        for d, c in sorted(stats['programs_by_division'].items()):
            print(f"  {d}: {c}")
        print(f"\nBy Degree Type:")
        for d, c in sorted(stats['programs_by_degree_type'].items()):
            print(f"  {d}: {c}")

    elif cmd == "export-markdown":
        md = q.export_all_markdown()
        out = q.data_dir / "fvcc_programs_reference.md"
        out.write_text(md, encoding="utf-8")
        print(f"Exported to {out}")

    elif cmd == "schedule":
        if not arg:
            print("Usage: schedule <course_code>  (e.g., 'BIOH 201' or 'BIOH_201NL')")
            sys.exit(1)
        options = q.get_course_options(arg)
        if "message" in options:
            print(options["message"])
        else:
            print(f"Course: {options['course_code']} - {options['title']}")
            print(f"Terms: {', '.join(options['terms_available'])}")
            print(f"Delivery: {', '.join(options['delivery_modes'])}")
            print(f"Locations: {', '.join(options['locations'])}")
            print(f"\nSections ({len(options['sections'])}):")
            for s in options["sections"]:
                seats = s["seats"]
                seat_str = f"{seats['available']} open"
                if seats.get("waitlist"):
                    seat_str += f", {seats['waitlist']} waitlisted"
                print(f"  {s['full_code']} | {s['term']} | {s['days']} {s['time']} | {s['room']} | {s['delivery_mode']} | {s['instructor']} | {seat_str}")

    elif cmd == "schedule-term":
        if not arg:
            terms = q.schedules.get("metadata", {}).get("terms", [])
            print(f"Available terms: {', '.join(terms)}")
            print("Usage: schedule-term <term>  (e.g., 'Fall 2026')")
            sys.exit(1)
        sections = [s for s in q.schedules.get("sections", []) if arg.lower() in s["term"].lower()]
        depts = {}
        for s in sections:
            depts.setdefault(s["department"], []).append(s)
        print(f"{arg}: {len(sections)} sections across {len(depts)} departments\n")
        for dept in sorted(depts.keys()):
            secs = depts[dept]
            print(f"  {dept} ({len(secs)} sections)")

    elif cmd == "advise":
        if not arg:
            print("Usage: advise <program_name>  (e.g., 'Registered Nursing')")
            sys.exit(1)
        report = q.format_advising_report(arg)
        print(report)

    elif cmd == "advise-term":
        parts = arg.rsplit('" "', 1) if '" "' in arg else arg.rsplit(" ", 2)
        # Parse: program_name term  (e.g., "Registered Nursing" "Fall 2026")
        # Or try splitting on known term patterns
        term_match = re.search(r'(Spring|Summer|Fall)\s+\d{4}', arg, re.IGNORECASE)
        if term_match:
            term = term_match.group(0)
            prog_name = arg[:term_match.start()].strip().strip('"')
        else:
            print("Usage: advise-term <program_name> <term>  (e.g., advise-term \"Registered Nursing\" \"Fall 2026\")")
            sys.exit(1)
        report = q.format_advising_report(prog_name, term)
        print(report)

    elif cmd == "open-seats":
        # Parse prefix and optional term
        term_match = re.search(r'(Spring|Summer|Fall)\s+\d{4}', arg, re.IGNORECASE)
        if term_match:
            term = term_match.group(0)
            prefix = arg[:term_match.start()].strip().strip('"')
        else:
            prefix = arg.strip().strip('"')
            term = None
        sections = q.get_open_sections(prefix, term)
        term_label = f" in {term}" if term else ""
        print(f"Open sections for {prefix}*{term_label}: {len(sections)}\n")
        for s in sections:
            print(f"  {s['full_code']} | {s['title']} | {s['term']} | {s['days']} {s['time']} | {s['delivery_mode']} | {s['seats']['available']} seats | {s['instructor']}")

    elif cmd == "course-options":
        if not arg:
            print("Usage: course-options <course_code>  (e.g., 'BIOH 211')")
            sys.exit(1)
        options = q.get_course_options(arg)
        if "message" in options:
            print(options["message"])
        else:
            print(f"\n{'='*70}")
            print(f"  {options['course_code']} - {options['title']}")
            print(f"  Terms: {', '.join(options['terms_available'])}")
            print(f"  Delivery modes: {', '.join(options['delivery_modes'])}")
            print(f"  Locations: {', '.join(options['locations'])}")
            print(f"{'='*70}\n")
            for term_name in options["terms_available"]:
                term_secs = [s for s in options["sections"] if s["term"] == term_name]
                print(f"  {term_name} ({len(term_secs)} sections):")
                for s in term_secs:
                    seats = s["seats"]
                    seat_str = f"{seats['available']} seats"
                    if seats["status"] != "Open":
                        seat_str = f"[{seats['status']}]"
                    print(f"    {s['full_code']}: {s['days']} {s['time']} | {s['delivery_mode']} | {s['location']} | {s['instructor']} | {seat_str}")
                print()

    elif cmd == "tuition":
        t = q.tuition
        plain = t.get("plain_english", {})
        print("FVCC Tuition & Fees (2025-2026)")
        print("=" * 50)
        print(plain.get("bottom_line", "No tuition data. Run: python scraper/scrape_tuition.py"))
        print()
        sem = plain.get("typical_semester_15_credits", {})
        if sem:
            print("Typical semester (15 credits):")
            for k, v in sem.items():
                print(f"  {k.replace('_', ' ').title()}: ${v:,.2f}")
        yr = plain.get("typical_year_30_credits", {})
        if yr:
            print("\nFull year (30 credits):")
            for k, v in yr.items():
                print(f"  {k.replace('_', ' ').title()}: ${v:,.2f}")
        gotchas = plain.get("things_they_dont_tell_you_upfront", [])
        if gotchas:
            print("\nThings they don't tell you upfront:")
            for g in gotchas:
                print(f"  - {g}")

    elif cmd == "essentials":
        e = q.essentials
        if not e:
            print("No essentials data. Run: python scraper/build_student_essentials.py")
        elif arg:
            # Show specific section
            section = e.get(arg.lower().replace(" ", "_"))
            if section:
                print(json.dumps(section, indent=2))
            else:
                print(f"Section '{arg}' not found. Available: {', '.join(k for k in e.keys() if k != 'metadata')}")
        else:
            print("Student Essentials — Available Sections:")
            print("=" * 50)
            for k, v in e.items():
                if k == "metadata":
                    continue
                title = v.get("title", k) if isinstance(v, dict) else k
                print(f"  {k}: {title}")
            print(f"\nUse: essentials <section>  (e.g., 'essentials getting_started')")

    elif cmd == "translate":
        e = q.essentials
        translations = e.get("website_translation", {}).get("translations", {})
        if arg:
            matches = {k: v for k, v in translations.items() if arg.lower() in k.lower()}
            if matches:
                for k, v in matches.items():
                    print(f"  {k}: {v}")
            else:
                print(f"No translation for '{arg}'. Try: translate")
        else:
            print("Website-to-English Translations:")
            print("=" * 50)
            for k, v in translations.items():
                print(f"  {k}")
                print(f"    → {v}")
                print()

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: search, program, track, division, degree-type, list-programs,")
        print("          list-tracks, list-divisions, page, stats, export-markdown,")
        print("          schedule, schedule-term, advise, advise-term, open-seats, course-options,")
        print("          tuition, essentials, translate")


if __name__ == "__main__":
    main()

"""
FVCC Knowledge Search
Search everything scraped from fvcc.edu — programs, pages, policies,
financial aid, support services, calendar, and more.
One search bar. Plain answers.
"""

import json
import re
from pathlib import Path

import streamlit as st

DATA = Path(__file__).resolve().parent.parent / "data"


@st.cache_data
def _load(name):
    p = DATA / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


@st.cache_data
def build_search_db():
    """Build a flat list of searchable entries from all scraped data."""
    entries = []

    # 1. Programs
    kb = _load("fvcc_knowledge_base.json")
    for prog in kb.get("programs", []):
        entries.append({
            "type": "Program",
            "title": prog.get("name", ""),
            "subtitle": f"{prog.get('degree_type', '')} · {prog.get('division', '')}",
            "content": prog.get("full_text", "")[:1000],
            "url": prog.get("catalog_url", "") or prog.get("url", ""),
            "tags": [prog.get("division", ""), prog.get("degree_type", ""), "program", "degree"],
        })

    # 2. Transfer tracks
    for track in kb.get("tracks", []):
        entries.append({
            "type": "Transfer Track",
            "title": track.get("name", ""),
            "subtitle": track.get("division", ""),
            "content": track.get("full_text", "")[:1000],
            "url": track.get("url", ""),
            "tags": ["transfer", "track", track.get("division", "")],
        })

    # 3. Site pages (admissions, student services, etc.)
    for page in kb.get("site_pages", []):
        section_text = ""
        for sec in page.get("sections", []):
            if isinstance(sec, dict):
                section_text += f" {sec.get('heading', '')} {sec.get('content', '')}"
            elif isinstance(sec, str):
                section_text += f" {sec}"

        entries.append({
            "type": "Website Page",
            "title": page.get("title", ""),
            "subtitle": page.get("category", "").replace("_", " ").title(),
            "content": (page.get("full_text", "") + section_text)[:1500],
            "url": page.get("url", ""),
            "tags": [page.get("category", ""), "website"],
        })

    # 4. Deep crawl pages
    dp = _load("deep_pages.json")
    for page in dp.get("pages", []) if isinstance(dp, dict) else dp:
        entries.append({
            "type": "Website Page",
            "title": page.get("title", ""),
            "subtitle": ", ".join(page.get("topics", [])) if page.get("topics") else "General",
            "content": page.get("full_text", "")[:1500],
            "url": page.get("url", ""),
            "tags": page.get("topics", []) + ["website"],
        })

    # 5. FAQ entries (from student_essentials)
    ess = _load("student_essentials.json")

    # Getting started steps
    gs = ess.get("getting_started", {})
    if gs:
        steps_text = gs.get("summary", "") + "\n"
        for step in gs.get("steps", []):
            steps_text += f"\nStep {step.get('step', '')}: {step.get('action', '')} — {step.get('details', '')}"
        entries.append({
            "type": "Guide",
            "title": "Getting Started at FVCC",
            "subtitle": gs.get("summary", ""),
            "content": steps_text,
            "url": "",
            "tags": ["getting started", "apply", "application", "new student", "admission"],
        })

    # Costs
    costs = ess.get("costs", {})
    if costs:
        cost_text = json.dumps(costs, indent=2)
        entries.append({
            "type": "Guide",
            "title": "Tuition & Costs",
            "subtitle": "What FVCC actually costs — per credit, per semester, hidden fees",
            "content": cost_text[:2000],
            "url": "https://www.fvcc.edu/admissions-financial-aid/tuition-fees",
            "tags": ["tuition", "cost", "fees", "money", "payment", "price"],
        })

    # Financial aid
    fa = ess.get("financial_aid", {})
    if fa:
        fa_text = fa.get("summary", "") + "\n" + json.dumps(fa, indent=2)
        entries.append({
            "type": "Guide",
            "title": "Financial Aid",
            "subtitle": fa.get("summary", ""),
            "content": fa_text[:2000],
            "url": "https://www.fvcc.edu/admissions-financial-aid/financial-aid-scholarships",
            "tags": ["financial aid", "FAFSA", "pell", "grant", "loan", "scholarship", "work study", "money"],
        })

    # Support services
    services = ess.get("support_services", {}).get("services", {})
    for svc_key, svc in services.items():
        entries.append({
            "type": "Service",
            "title": svc.get("what", svc_key),
            "subtitle": svc.get("where", ""),
            "content": f"{svc.get('what', '')}. {svc.get('where', '')}. {svc.get('tip', '')}. Phone: {svc.get('phone', '')}. Cost: {svc.get('cost', '')}.",
            "url": "",
            "tags": ["support", "help", "service", svc_key.replace("_", " ")],
        })

    # Calendar
    cal = ess.get("calendar", {})
    for term_key, term_data in cal.items():
        if not isinstance(term_data, dict):
            continue
        cal_text = ""
        for k, v in term_data.items():
            if isinstance(v, str):
                cal_text += f"{k.replace('_', ' ').title()}: {v}\n"
            elif isinstance(v, dict):
                for sk, sv in v.items():
                    cal_text += f"{k.replace('_', ' ').title()} — {sk}: {sv}\n"
        entries.append({
            "type": "Calendar",
            "title": f"Key Dates — {term_key.replace('_', ' ').title()}",
            "subtitle": "Registration deadlines, drop dates, finals",
            "content": cal_text,
            "url": "",
            "tags": ["calendar", "dates", "deadline", "registration", "drop", term_key.replace("_", " ")],
        })

    # Registration info
    reg = ess.get("registration", {})
    if reg:
        entries.append({
            "type": "Guide",
            "title": "Registration",
            "subtitle": reg.get("summary", "How to register for classes"),
            "content": json.dumps(reg, indent=2)[:2000],
            "url": "",
            "tags": ["registration", "register", "sign up", "enroll", "classes"],
        })

    # Degree types
    dt = ess.get("degree_types", {})
    if dt:
        dt_text = ""
        for dtype, info in dt.get("types", {}).items():
            dt_text += f"{dtype}: {info.get('full_name', '')} — {info.get('purpose', '')}\n"
        entries.append({
            "type": "Guide",
            "title": "Degree Types Explained",
            "subtitle": "AA, AS, AAS, CAS, CTS — what they mean",
            "content": dt_text,
            "url": "",
            "tags": ["degree", "certificate", "AA", "AS", "AAS", "CAS", "CTS", "transfer"],
        })

    # Jargon translations
    translations = ess.get("website_translation", {}).get("translations", {})
    if translations:
        trans_text = ""
        for term, meaning in translations.items():
            trans_text += f"{term}: {meaning}\n"
            entries.append({
                "type": "Definition",
                "title": term,
                "subtitle": meaning[:100],
                "content": meaning,
                "url": "",
                "tags": ["jargon", "definition", "glossary", term.lower()],
            })

    # 6. Course requirements
    cr = _load("course_requirements.json")
    for code, info in cr.get("courses", {}).items():
        prereqs = info.get("prerequisite_codes", [])
        coreqs = info.get("corequisite_codes", [])
        prereq_text = f"Prerequisites: {', '.join(prereqs)}" if prereqs else "No prerequisites"
        coreq_text = f"Corequisites: {', '.join(coreqs)}" if coreqs else ""
        entries.append({
            "type": "Course",
            "title": info.get("title", code),
            "subtitle": prereq_text,
            "content": f"{prereq_text}. {coreq_text}. " + " ".join(info.get("prerequisite_lines", [])),
            "url": "",
            "tags": ["course", "prerequisite", "prereq", code.split()[0] if " " in code else code],
        })

    return entries


def search_entries(entries, query):
    """Simple relevance-ranked search."""
    if not query or not query.strip():
        return entries[:20]

    words = query.lower().split()
    scored = []

    for entry in entries:
        score = 0
        title_lower = entry["title"].lower()
        content_lower = entry["content"].lower()
        tags_lower = " ".join(entry["tags"]).lower()
        subtitle_lower = entry["subtitle"].lower()
        all_text = f"{title_lower} {subtitle_lower} {content_lower} {tags_lower}"

        for word in words:
            if word in title_lower:
                score += 10
            if word in subtitle_lower:
                score += 5
            if word in tags_lower:
                score += 5
            if word in content_lower:
                score += 1
                # Boost for multiple occurrences
                score += min(content_lower.count(word), 5)

        # Exact phrase match bonus
        if query.lower() in title_lower:
            score += 20
        if query.lower() in content_lower:
            score += 5

        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: -x[0])
    return [entry for _, entry in scored[:30]]


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="FVCC Search", page_icon="🔍", layout="wide")

st.title("🔍 Search FVCC")
st.caption("Search everything — programs, courses, policies, financial aid, dates, support services, and more.")

all_entries = build_search_db()

query = st.text_input(
    "What are you looking for?",
    placeholder="financial aid, nursing prerequisites, drop deadline, tutoring, WRIT 101...",
    key="knowledge_search",
)

# Type filter
type_filter = st.multiselect(
    "Filter by type",
    options=sorted(set(e["type"] for e in all_entries)),
    default=[],
    key="type_filter",
)

results = search_entries(all_entries, query)

if type_filter:
    results = [r for r in results if r["type"] in type_filter]

st.caption(f"{len(results)} result(s)" + (f" for '{query}'" if query else " — showing recent"))

for entry in results:
    icon_map = {
        "Program": "🎓", "Transfer Track": "🔄", "Website Page": "📄",
        "Guide": "📖", "Service": "🆘", "Calendar": "📅",
        "Definition": "🔤", "Course": "📘",
    }
    icon = icon_map.get(entry["type"], "📌")

    header = f"{icon} **{entry['title']}**"
    if entry["subtitle"]:
        header += f" — {entry['subtitle'][:80]}"

    with st.expander(header):
        st.caption(f"Type: {entry['type']}")

        # Show content in readable chunks
        content = entry["content"].strip()
        if content:
            # Try to render as markdown, fall back to plain text
            if content.startswith("{") or content.startswith("["):
                try:
                    parsed = json.loads(content)
                    # Render dicts/lists as readable text
                    if isinstance(parsed, dict):
                        for k, v in parsed.items():
                            if k in ("metadata",):
                                continue
                            if isinstance(v, str):
                                st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")
                            elif isinstance(v, (int, float)):
                                st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")
                            elif isinstance(v, dict):
                                st.markdown(f"**{k.replace('_', ' ').title()}:**")
                                for sk, sv in v.items():
                                    st.caption(f"  {sk.replace('_', ' ').title()}: {sv}")
                            elif isinstance(v, list):
                                st.markdown(f"**{k.replace('_', ' ').title()}:**")
                                for item in v[:10]:
                                    st.caption(f"  - {item}")
                    else:
                        st.text(content[:1000])
                except (json.JSONDecodeError, TypeError):
                    st.markdown(content[:1000])
            else:
                st.markdown(content[:1000])

        if entry.get("url"):
            st.markdown(f"[🔗 View on FVCC website]({entry['url']})")

        if entry.get("tags"):
            st.caption(f"Tags: {', '.join(t for t in entry['tags'] if t)}")

"""
FVCC Program Explorer
Browse every program. See what it costs, how long it takes,
what you build, and what classes are available right now.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parent.parent / "data"


@st.cache_data
def _load(name):
    p = DATA / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


st.set_page_config(page_title="FVCC Programs", page_icon="📋", layout="wide")

kb = _load("fvcc_knowledge_base.json")
pc = _load("program_courses.json")
sched = _load("schedules.json")
tuition = _load("tuition.json")
essentials = _load("student_essentials.json")

programs = kb.get("programs", [])
programs_with_courses = {p["name"]: p for p in pc.get("programs", []) if any(s["courses"] for s in p["semesters"])}
course_index = sched.get("course_index", {})
terms = sorted(sched.get("metadata", {}).get("terms", []))
breakdown = essentials.get("costs", {}).get("per_credit_breakdown", {})
fc_rate = breakdown.get("flathead_county_resident", {}).get("total_per_credit", 205.16)

degree_labels = {
    "AAS": "Associate of Applied Science — Career degree, go to work",
    "AA": "Associate of Arts — Transfer to a 4-year school",
    "AS": "Associate of Science — Transfer to a 4-year school",
    "ASN": "Associate of Science in Nursing — Become an RN",
    "CAS": "Certificate of Applied Science — ~1 year career certificate",
    "CTS": "Certificate of Technical Studies — Short credential",
}

st.title("📋 Program Explorer")
st.caption("Browse programs. See real costs. Check what's available now.")

# ── Filters ──────────────────────────────────────────────────────────────────

filter_col1, filter_col2, filter_col3 = st.columns(3)

divisions = sorted(set(p.get("division", "") for p in programs if p.get("division")))
degree_types = sorted(set(p.get("degree_type", "") for p in programs if p.get("degree_type")))

with filter_col1:
    search = st.text_input("🔍 Search programs", placeholder="nursing, welding, business...")

with filter_col2:
    sel_div = st.selectbox("Division", ["All"] + divisions)

with filter_col3:
    sel_dt = st.selectbox("Degree Type", ["All"] + degree_types)

# ── Filter programs ──────────────────────────────────────────────────────────

filtered = programs
if search:
    s = search.lower()
    filtered = [p for p in filtered if s in p.get("name", "").lower() or s in p.get("division", "").lower() or s in p.get("full_text", "").lower()]
if sel_div != "All":
    filtered = [p for p in filtered if p.get("division") == sel_div]
if sel_dt != "All":
    filtered = [p for p in filtered if p.get("degree_type") == sel_dt]

st.caption(f"Showing {len(filtered)} of {len(programs)} programs")

# ── Program cards ────────────────────────────────────────────────────────────

if not filtered:
    st.info("No programs match your filters. Try a different search.")
    st.stop()

for prog in sorted(filtered, key=lambda p: p.get("name", "")):
    name = prog.get("name", "")
    dt = prog.get("degree_type", "")
    division = prog.get("division", "")
    credits = prog.get("total_credits", "")
    catalog_url = prog.get("catalog_url", "")

    # Cost estimate
    cr_int = int(credits) if str(credits).isdigit() else 0
    est_cost = round(fc_rate * cr_int, 2) if cr_int else 0

    # Header line
    dt_short = degree_labels.get(dt, dt)
    header = f"**{name}** · {dt}"
    if credits:
        header += f" · {credits} credits"
    if est_cost:
        header += f" · ~${est_cost:,.0f}"
    header += f" · {division}"

    with st.expander(header):
        info_col1, info_col2 = st.columns([2, 1])

        with info_col1:
            st.markdown(f"**Division:** {division}")
            st.markdown(f"**Degree:** {dt_short}")
            if credits:
                st.markdown(f"**Credits:** {credits}")
            if catalog_url:
                st.markdown(f"[📄 Full details on FVCC website]({catalog_url})")

            # Description from scraped content
            full_text = prog.get("full_text", "")
            if full_text:
                # Show first meaningful paragraph (skip the header/breadcrumb noise)
                paragraphs = [p.strip() for p in full_text.split("\n") if len(p.strip()) > 50]
                # Skip paragraphs that are just the program name or breadcrumbs
                desc_paragraphs = [p for p in paragraphs if name.lower() not in p.lower()[:len(name)+10]]
                if desc_paragraphs:
                    st.markdown(f"*{desc_paragraphs[0][:300]}{'...' if len(desc_paragraphs[0]) > 300 else ''}*")

        with info_col2:
            if est_cost:
                st.metric("Estimated Total Cost", f"${est_cost:,.0f}")
                st.caption(f"Flathead County rate · ${fc_rate:.2f}/credit")
                if cr_int:
                    semesters = max(1, cr_int // 15)
                    st.caption(f"~{semesters} semesters at 15 credits each")

        # Course plan if available
        course_plan = programs_with_courses.get(name)
        if course_plan:
            st.markdown("---")
            st.markdown("**Semester-by-Semester Plan:**")

            for sem in course_plan.get("semesters", []):
                courses = sem.get("courses", [])
                if not courses:
                    continue

                sem_label = sem.get("label", "")
                sem_credits = sem.get("semester_credits", "")

                courses_with_availability = []
                for course_group in courses:
                    if isinstance(course_group, list):
                        course = course_group[0] if course_group else {}
                    else:
                        course = course_group

                    code = course.get("code", "")
                    title = course.get("title", "")
                    cr = course.get("credits", "")

                    # Check availability
                    available_terms = []
                    for term in terms:
                        key = code.replace(" ", "_").upper()
                        entry = course_index.get(key)
                        if entry and isinstance(entry, dict):
                            secs = [s for s in entry.get("sections", []) if s.get("term") == term]
                            if secs:
                                open_ct = sum(1 for s in secs if s.get("seats", {}).get("available", 0) > 0)
                                available_terms.append(f"{term} ({open_ct} open)")

                    avail_str = " · ".join(available_terms) if available_terms else "Check schedule"

                    courses_with_availability.append({
                        "Course": code,
                        "Title": title,
                        "Credits": cr,
                        "Available": avail_str,
                    })

                if courses_with_availability:
                    cr_label = f" · {sem_credits} credits" if sem_credits else ""
                    st.markdown(f"**{sem_label}{cr_label}**")
                    st.dataframe(
                        pd.DataFrame(courses_with_availability),
                        hide_index=True,
                        use_container_width=True,
                    )

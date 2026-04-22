"""
FVCC Advisor Dashboard — Student-First Design

The advisor's workspace starts with their students:
  1. Roster overview — every student, their program, where they are
  2. Select a student → see their full pathway, edit their courses, respond to questions
  3. All program/schedule data flows from the student's program automatically
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from course_ui import render_course_schedule
from eligibility import analyze_schedule_registration_notes, evaluate_catalog_prerequisites
from planner_helpers import (
    build_completed_course_codes,
    build_program_site_index,
    build_unlock_map,
    placement_equivalent_codes,
    PLACEMENT_OPTIONS,
    count_completed_credits,
    count_program_credits,
    count_remaining_slots,
    count_required_courses,
    dedupe_alerts,
    extract_poid,
    get_sections_for_course,
    get_selected_course_for_slot,
    iter_course_slots,
    make_student_id,
    merge_completed_course_codes,
    recommended_course_items,
    lcc_access_summary,
    slot_display_label,
    slot_is_completed,
    summarize_program_notes,
    sync_completed_slot_terms,
    completion_rows,
    canonical_course_title,
    manual_course_rows,
    term_status_badge,
    term_status_group,
    term_status_rank,
)
from progress_store import build_progress_store
from student_dashboard import format_audit_entries

DATA = Path(__file__).resolve().parent.parent / "data"
DB = Path(__file__).resolve().parent.parent / "db"
USER_PROGRESS_DB_PATH = DATA / "user_progress.db"
USER_PROGRESS_PATH = DATA / "user_progress.json"
PROGRESS_STORE = build_progress_store("sqlite", USER_PROGRESS_DB_PATH, USER_PROGRESS_PATH, DB / "migrations")


@st.cache_data
def _load_json(path_str: str, mtime_ns: int):
    del mtime_ns
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def _load(filename: str):
    p = DATA / filename
    if not p.exists():
        return {}
    return _load_json(str(p), p.stat().st_mtime_ns)


def save_progress(progress: dict) -> None:
    PROGRESS_STORE.save(progress)


# ── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="FVCC Advisor Dashboard", page_icon="🎓", layout="wide")

# ── Load Data ────────────────────────────────────────────────────────────────

pc = _load("program_courses.json")
sched = _load("schedules.json")
program_site_data = _load("programs.json")
course_requirements_data = _load("course_requirements.json")
progress = PROGRESS_STORE.load()
course_requirements = course_requirements_data.get("courses", {})
unlock_map = build_unlock_map(course_requirements)
course_index = sched.get("course_index", {})
terms = sorted(sched.get("metadata", {}).get("terms", []))
programs_with_courses = [p for p in pc.get("programs", []) if any(s["courses"] for s in p["semesters"])]
program_site_index = build_program_site_index(program_site_data if isinstance(program_site_data, list) else [])
program_lookup = {p["name"]: p for p in programs_with_courses}

# Program display names
DEGREE_CATEGORIES = {
    "Associate of Applied Science (AAS)": ["Associate of Applied Science", "Associate of Science Nursing"],
    "Transfer Degrees (AA/AS)": ["Associate of Arts (Transfer)", "Associate of Science (Transfer)", "Associate of Arts"],
    "Certificates (CAS/CTS)": ["Certificate of Applied Science", "Certificate of Technical Studies"],
}
program_options = []
for cat_label in DEGREE_CATEGORIES:
    for p in sorted(
        [p for p in programs_with_courses if p.get("degree_type", "") in DEGREE_CATEGORIES[cat_label]],
        key=lambda p: p["name"],
    ):
        program_options.append((f"{p['name']}  [{p.get('degree_type', '')}]", p["name"]))
# Add "Other" that didn't match any category
known_types = {t for types in DEGREE_CATEGORIES.values() for t in types}
for p in sorted([p for p in programs_with_courses if p.get("degree_type", "") not in known_types], key=lambda p: p["name"]):
    program_options.append((f"{p['name']}  [{p.get('degree_type', '')}]", p["name"]))

display_names = [d for d, _ in program_options]
real_names = [r for _, r in program_options]

open_questions = PROGRESS_STORE.get_open_questions()

# ── Helper: compute student progress against their program ───────────────────

def compute_student_progress(student: dict) -> dict:
    """Compute all progress metrics for a student against their assigned program."""
    program_name = student.get("program_name", "")
    program = program_lookup.get(program_name)
    if not program:
        return {
            "program": None, "total_credits": 0, "completed_credits": 0,
            "total_slots": 0, "completed_slot_count": 0, "remaining_slots": 0,
            "progress_pct": 0, "program_slots": [], "completed_slot_ids": set(),
            "completed_course_codes": set(), "saved_or_choices": {},
            "effective_completed_course_codes": set(), "placement_scores": {
                "writing": {"taken": False, "level": ""},
                "math": {"taken": False, "level": ""},
                "chemistry": {"taken": False, "level": ""},
            },
            "manual_completed_courses": {}, "completed_labels": [],
            "completion_options": [], "completion_lookup": {},
        }

    program_slots = iter_course_slots(program["semesters"])
    for slot_idx, slot in enumerate(program_slots):
        slot["slot_id"] = f"{program['name']}::{slot_idx}::{slot['semester_label']}::{slot['group_idx']}"

    completion_options = [slot_display_label(slot) for slot in program_slots]
    completion_lookup = {
        slot_display_label(slot): slot["slot_id"]
        for slot in program_slots
    }

    completed_labels = [label for label in student.get("completed_slots", []) if label in completion_options]
    completed_slot_ids = {completion_lookup[label] for label in completed_labels}
    saved_or_choices = student.get("selected_or_courses", {})
    manual_completed_courses = student.get("manual_completed_courses", {})
    placement_scores = student.get("placement_scores", {
        "writing": {"taken": False, "level": ""},
        "math": {"taken": False, "level": ""},
        "chemistry": {"taken": False, "level": ""},
    })

    slot_codes = build_completed_course_codes(program_slots, completed_slot_ids, saved_or_choices)
    completed_course_codes = merge_completed_course_codes(slot_codes, manual_completed_courses)
    effective_completed_course_codes = set(completed_course_codes) | placement_equivalent_codes(placement_scores)
    completed_credits = count_completed_credits(program_slots, completed_slot_ids, saved_or_choices)
    remaining = count_remaining_slots(program_slots, completed_slot_ids)

    catalog_credits = program.get("total_credits", "")
    computed = count_program_credits(program["semesters"])
    total_credits = int(catalog_credits) if str(catalog_credits).isdigit() else computed
    total_slots = len(program_slots)
    completed_slot_count = len(completed_slot_ids)
    pct = int((completed_slot_count / total_slots) * 100) if total_slots > 0 else 0

    return {
        "program": program, "total_credits": total_credits,
        "completed_credits": completed_credits, "total_slots": total_slots,
        "completed_slot_count": completed_slot_count, "remaining_slots": remaining,
        "progress_pct": pct, "program_slots": program_slots,
        "completed_slot_ids": completed_slot_ids,
        "completed_course_codes": completed_course_codes,
        "effective_completed_course_codes": effective_completed_course_codes,
        "placement_scores": placement_scores,
        "saved_or_choices": saved_or_choices,
        "manual_completed_courses": manual_completed_courses,
        "completed_labels": completed_labels,
        "completion_options": completion_options,
        "completion_lookup": completion_lookup,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ── SIDEBAR — simplified: add student, term, question alert ─────────────────
# ══════════════════════════════════════════════════════════════════════════════

student_records = progress.get("students", {})
student_ids = sorted(student_records.keys(), key=lambda sid: student_records[sid]["name"].lower())

st.sidebar.markdown("### 🎓 Advisor Workspace")

# Quick-add student
with st.sidebar.expander("➕ Add New Student", expanded=not bool(student_records)):
    new_name = st.text_input("Student name", key="add_student_name")
    new_prog_display = st.selectbox("Program", options=display_names, index=0 if display_names else None, key="add_student_prog")
    if st.button("Create Student", use_container_width=True, key="btn_add_student"):
        cleaned = new_name.strip()
        if cleaned:
            new_id = make_student_id(cleaned, set(student_records.keys()))
            new_prog = real_names[display_names.index(new_prog_display)] if display_names else ""
            progress.setdefault("students", {})[new_id] = {
                "id": new_id, "name": cleaned, "program_name": new_prog,
                "completed_slots": [], "completed_slot_terms": {},
                "manual_completed_courses": {}, "selected_or_courses": {},
                "placement_scores": {
                    "writing": {"taken": False, "level": ""},
                    "math": {"taken": False, "level": ""},
                    "chemistry": {"taken": False, "level": ""},
                },
                "campus_preference": "",
                "notes": "",
            }
            progress["active_student_id"] = new_id
            save_progress(progress)
            st.rerun()
        else:
            st.warning("Enter a name.")

# Term selector
st.sidebar.markdown("### 📅 Term")
default_term_idx = terms.index("Fall 2026") if "Fall 2026" in terms else 0
selected_term = st.sidebar.selectbox("Schedule term", terms, index=default_term_idx, key="advisor_term")

# Question alert
if open_questions:
    st.sidebar.markdown("---")
    st.sidebar.warning(f"💬 {len(open_questions)} unanswered question(s)")

st.sidebar.divider()
st.sidebar.caption(
    f"{sched.get('metadata', {}).get('total_sections', 0)} sections · "
    f"{len(course_index)} courses · {len(programs_with_courses)} programs"
)

# ══════════════════════════════════════════════════════════════════════════════
# ── MAIN CONTENT ─────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

st.title("🎓 Advisor Dashboard")

if not student_records:
    st.info("No students yet. Add your first student using the sidebar.")
    st.stop()

# ── STUDENT ROSTER ───────────────────────────────────────────────────────────────

st.markdown("### Your Students")
st.caption("Everyone you advise, at a glance. Pick a student below to see their full picture.")

# Build roster rows with real progress data
roster_rows = []
for sid in student_ids:
    s = student_records[sid]
    sp = compute_student_progress(s)
    student_questions = [q for q in open_questions if q.get("student_id") == sid]
    roster_rows.append({
        "Name": s["name"],
        "Program": s.get("program_name", "") or "—",
        "Credits": f"{sp['completed_credits']}/{sp['total_credits']}" if sp["program"] else "—",
        "Classes Done": f"{sp['completed_slot_count']}/{sp['total_slots']}" if sp["program"] else "—",
        "Progress": f"{sp['progress_pct']}%" if sp["program"] else "—",
        "Questions": len(student_questions),
        "_id": sid,
    })

# Display roster table (without internal _id column)
roster_df = pd.DataFrame(roster_rows)
st.dataframe(
    roster_df[["Name", "Program", "Credits", "Classes Done", "Progress", "Questions"]],
    width="stretch",
    hide_index=True,
    column_config={
        "Questions": st.column_config.NumberColumn("💬", help="Unanswered questions", width="small"),
    },
)

# ── Student selector (below roster) ─────────────────────────────────────────

student_name_list = [student_records[sid]["name"] for sid in student_ids]
active_id = progress.get("active_student_id", "")
default_student_idx = 0
if active_id in student_records:
    try:
        default_student_idx = student_ids.index(active_id)
    except ValueError:
        pass

selected_student_name = st.selectbox(
    "Select a student to work with",
    student_name_list,
    index=default_student_idx,
    key="roster_student_select",
)
selected_sid = student_ids[student_name_list.index(selected_student_name)]

# Save active student if changed
if selected_sid != active_id:
    progress["active_student_id"] = selected_sid
    save_progress(progress)

student = progress["students"][selected_sid]
sp = compute_student_progress(student)
program = sp["program"]

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# ── STUDENT DETAIL VIEW ──────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

# Header with student name and quick stats
header_col, prog_col = st.columns([2, 1])
with header_col:
    st.markdown(f"## {student['name']}")
    if program:
        st.caption(f"{student['program_name']} · {sp['total_credits']} credits · {sp['progress_pct']}% complete")
    else:
        st.warning("No program assigned yet. Set one in the Profile tab below.")

with prog_col:
    if program:
        st.metric("Completed", f"{sp['completed_credits']} / {sp['total_credits']} cr")
        st.progress(min(sp["progress_pct"] / 100, 1.0))

# ── Tabs for this student ────────────────────────────────────────────────────

student_q_count = len([q for q in open_questions if q.get("student_id") == selected_sid])
q_badge = f" ({student_q_count})" if student_q_count else ""

tab_pathway, tab_term, tab_courses, tab_profile, tab_questions = st.tabs([
    "🗺️ Their Path",
    f"🗓️ {selected_term}",
    "📝 What They've Done",
    "👤 Profile & Notes",
    f"💬 Questions{q_badge}",
])

# ── Tab: Pathway ─────────────────────────────────────────────────────────────
# Shows the student's full program map semester by semester, with completion
# status and prerequisite flow visible at a glance.

with tab_pathway:
    if not program:
        st.info("Assign a program in the Profile tab to see the pathway.")
    else:
        st.caption(
            "Full program map. ✅ = done, 🟢 = open seats now, "
            "🔴 = full, 🟡 = different term, ⚪ = not scheduled."
        )

        program_slots = sp["program_slots"]
        completed_slot_ids = sp["completed_slot_ids"]
        completed_course_codes = sp["completed_course_codes"]
        effective_completed_course_codes = sp["effective_completed_course_codes"]
        saved_or_choices = sp["saved_or_choices"]
        program_course_codes = {
            c["code"] for slot in program_slots for c in slot["group"] if not c.get("is_elective")
        }
        program_poid = extract_poid(program.get("catalog_url", ""))
        program_notes = summarize_program_notes(program_site_index.get(program_poid))

        for sem in program["semesters"]:
            if not sem["courses"]:
                continue

            sem_label = sem["label"]
            sem_credits = sem.get("semester_credits", "")
            semester_slots = [slot for slot in program_slots if slot["semester_label"] == sem_label]

            sem_done = sum(1 for s in semester_slots if slot_is_completed(s, completed_slot_ids))
            sem_total = len(semester_slots)

            if sem_done == sem_total and sem_total > 0:
                sem_icon = "✅"
            elif sem_done > 0:
                sem_icon = "🟦"
            else:
                sem_icon = "⬛"

            sem_header = f"{sem_icon} **{sem_label}**"
            if sem_credits:
                sem_header += f" · {sem_credits} cr"
            sem_header += f" · {sem_done}/{sem_total} done"

            with st.expander(sem_header, expanded=(sem_done < sem_total)):
                for slot in semester_slots:
                    group = slot["group"]
                    is_done = slot_is_completed(slot, completed_slot_ids)
                    is_or_group = len(group) > 1

                    # For OR groups, show radio selector
                    if is_or_group:
                        options_labels = [f"{c['code']} - {c['title']} ({c.get('credits', '')}cr)" for c in group]
                        saved_code = saved_or_choices.get(slot["slot_id"])
                        default_idx = next((i for i, c in enumerate(group) if c["code"] == saved_code), 0)
                        selected_idx = st.radio(
                            "Choose one:",
                            range(len(group)),
                            format_func=lambda i, opts=options_labels: opts[i],
                            key=f"pathway_or_{slot['slot_id']}",
                            index=default_idx,
                            horizontal=True,
                        )
                        course = group[selected_idx]
                        if saved_or_choices.get(slot["slot_id"]) != course["code"]:
                            progress["students"][selected_sid].setdefault("selected_or_courses", {})[slot["slot_id"]] = course["code"]
                            save_progress(progress)
                            saved_or_choices[slot["slot_id"]] = course["code"]
                    else:
                        course = group[0]

                    if course.get("is_elective"):
                        elective_text = f"Elective — {course['title']} ({course.get('credits', '')}cr)"
                        if is_done:
                            st.markdown(f"&nbsp;&nbsp;✅ ~~{elective_text}~~ · Completed")
                        else:
                            st.markdown(f"&nbsp;&nbsp;🟣 {elective_text} · Not marked complete")
                        continue

                    code = course["code"]
                    title = canonical_course_title(code, course["title"], course_requirements)
                    credits = course.get("credits", "")

                    # Status
                    sections = get_sections_for_course(code, selected_term, course_index)
                    open_seats = sum(1 for s in sections if s.get("seats", {}).get("available", 0) > 0)

                    if is_done:
                        icon = "✅"
                        status_text = "Completed"
                    elif sections and open_seats > 0:
                        icon = "🟢"
                        status_text = f"{open_seats} open in {selected_term}"
                    elif sections:
                        icon = "🔴"
                        status_text = f"Full in {selected_term}"
                    else:
                        all_secs = get_sections_for_course(code, "", course_index)
                        offered = sorted(set(s["term"] for s in all_secs)) if all_secs else []
                        if offered:
                            icon = "🔴"
                            status_text = f"Not offered in {selected_term} (offered in: {', '.join(offered)})"
                        else:
                            icon = "⚪"
                            status_text = "Not scheduled"

                    # Prerequisite info
                    prereq_info = ""
                    reqs = course_requirements.get(code, {})
                    prereq_codes = reqs.get("prerequisite_codes", [])
                    if prereq_codes:
                        prereq_eval = evaluate_catalog_prerequisites(reqs, effective_completed_course_codes)
                        unmet = prereq_eval["unmet_codes"]
                        if unmet and not is_done:
                            prereq_info = f" · ⚠️ needs {', '.join(unmet)}"
                        elif not unmet and not is_done:
                            placement_only = [c for c in prereq_codes if c not in completed_course_codes and c in effective_completed_course_codes]
                            if placement_only:
                                prereq_info = " · ✓ prereqs met by placement"
                            else:
                                prereq_info = " · ✓ prereqs met"

                    # Keep pathway language aligned with term eligibility logic
                    schedule_gate = analyze_schedule_registration_notes(code, sections, effective_completed_course_codes)
                    caution_info = ""
                    if not is_done:
                        if schedule_gate["blocking"]:
                            caution_info = " · ⛔ registration block noted"

                    # Unlock info
                    unlocks = unlock_map.get(code, [])
                    relevant_unlocks = [u for u in unlocks if u in program_course_codes and u not in completed_course_codes]
                    unlock_info = ""
                    if relevant_unlocks and not is_done:
                        unlock_info = f" · unlocks {', '.join(relevant_unlocks[:3])}"

                    if is_done:
                        st.markdown(
                            f"&nbsp;&nbsp;{icon} ~~**{code}** — {title} ({credits}cr)~~ · "
                            f"{status_text}{prereq_info}{unlock_info}"
                        )
                    else:
                        st.markdown(
                            f"&nbsp;&nbsp;{icon} **{code}** — {title} ({credits}cr) · "
                            f"{status_text}{prereq_info}{unlock_info}{caution_info}"
                        )

                    # Show section details for available courses (collapsible)
                    if sections and not is_done:
                        with st.popover(f"View {len(sections)} section(s)"):
                            rows = []
                            for sec in sections:
                                rows.append({
                                    "Section": sec["full_code"],
                                    "Days": sec["days"],
                                    "Time": sec["time"],
                                    "Room": sec["room"],
                                    "Mode": sec["delivery_mode"],
                                    "Instructor": sec["instructor"],
                                    "Seats": sec.get("seats", {}).get("available", 0),
                                })
                            st.dataframe(pd.DataFrame(rows), hide_index=True)


# ── Tab: This Term ───────────────────────────────────────────────────────────
# Courses from this student's program available in the selected term,
# grouped by eligibility — what they can register for right now.

with tab_term:
    if not program:
        st.info("Assign a program in the Profile tab first.")
    else:
        program_slots = sp["program_slots"]
        completed_slot_ids = sp["completed_slot_ids"]
        completed_course_codes = sp["completed_course_codes"]
        effective_completed_course_codes = sp["effective_completed_course_codes"]
        saved_or_choices = sp["saved_or_choices"]
        program_course_codes = {
            c["code"] for slot in program_slots for c in slot["group"] if not c.get("is_elective")
        }
        program_poid = extract_poid(program.get("catalog_url", ""))
        program_notes = summarize_program_notes(program_site_index.get(program_poid))

        available_now = []
        campus_pref = student.get("campus_preference", "")
        for slot_idx, slot in enumerate(program_slots):
            if slot_is_completed(slot, completed_slot_ids):
                continue
            for course in slot["group"]:
                if course.get("is_elective"):
                    continue
                sections = get_sections_for_course(course["code"], selected_term, course_index)
                if not sections:
                    continue
                requirements = course_requirements.get(course["code"], {})
                prereq_eval = evaluate_catalog_prerequisites(requirements, effective_completed_course_codes)
                unmet_prereqs = prereq_eval["unmet_codes"]
                schedule_gate = analyze_schedule_registration_notes(course["code"], sections, effective_completed_course_codes)
                if schedule_gate["has_schedule_gate"]:
                    likely_eligible = not schedule_gate["blocking"]
                else:
                    likely_eligible = prereq_eval["satisfied"]
                access = lcc_access_summary(sections)
                delivery_caution = campus_pref == "LCC / Libby" and not access["has_lcc_sections"]
                available_now.append({
                    "slot": slot, "course": course, "semester_label": slot["semester_label"],
                    "completed": False, "unmet_prior_slots": 0,
                    "schedule_block": schedule_gate["blocking"],
                    "catalog_prereq_block": bool(unmet_prereqs) and not schedule_gate["has_schedule_gate"],
                    "delivery_caution": delivery_caution,
                    "likely_eligible": likely_eligible,
                    "open_count": sum(1 for s in sections if s.get("seats", {}).get("available", 0) > 0),
                    "section_count": len(sections),
                })

        st.subheader(f"{student['name']} — {selected_term}")

        # Recommended
        recommended = recommended_course_items(available_now)
        if recommended:
            st.markdown("**🧭 Recommended Next**")
            for item in recommended[:5]:
                c = item["course"]
                st.caption(f"🧭 {c['code']} · {c['title']} · {item['open_count']}/{item['section_count']} open · from {item['semester_label']}")

        if available_now:
            available_now.sort(key=lambda item: (term_status_rank(item), item["course"]["code"]))
            for group_name in ["Likely eligible now", "Delivery cautions", "Catalog prerequisite cautions", "Registration blocks noted", "Needs review"]:
                group_items = [item for item in available_now if term_status_group(item) == group_name]
                if not group_items:
                    continue
                st.markdown(f"**{group_name}**")
                for item in group_items:
                    st.caption(f"{term_status_badge(item)} · from {item['semester_label']}")
                    if item.get("delivery_caution"):
                        st.markdown("<span style='color:#d97706;'>⚠️ LCC/Libby caution: this term has no clearly local/remote-designated section (60s, 80s, 90s, D, 22, 23). Student may need travel or instructor accommodation.</span>", unsafe_allow_html=True)
                    render_course_schedule(
                        item["course"], selected_term, course_index,
                        completed=False, context_label=item["semester_label"],
                        unmet_prior_slots=item["unmet_prior_slots"],
                        program_notes=program_notes, course_requirements=course_requirements,
                        completed_course_codes=effective_completed_course_codes,
                        unlock_map=unlock_map, program_course_codes=program_course_codes,
                    )
        else:
            st.info(f"No remaining required courses are scheduled in {selected_term}.")


# ── Tab: Completed Work ──────────────────────────────────────────────────────
# Fast interface to mark requirements done and add transfer/manual courses.

with tab_courses:
    if not program:
        st.info("Assign a program in the Profile tab first.")
    else:
        program_slots = sp["program_slots"]
        completed_slot_ids = sp["completed_slot_ids"]
        completed_labels = sp["completed_labels"]
        saved_or_choices = sp["saved_or_choices"]
        completion_options = sp["completion_options"]
        completion_lookup = sp["completion_lookup"]
        completed_course_codes = sp["completed_course_codes"]
        effective_completed_course_codes = sp["effective_completed_course_codes"]
        placement_scores = sp["placement_scores"]
        manual_completed_courses = sp["manual_completed_courses"]

        st.subheader("Mark What's Done")
        st.caption("Check off classes by semester. Completed classes automatically unlock prerequisites — including in other programs.")

        # Semester-grouped checkboxes
        changed = False
        new_completed = list(completed_labels)

        for sem in program["semesters"]:
            if not sem["courses"]:
                continue
            sem_label = sem["label"]
            sem_slots = [s for s in program_slots if s["semester_label"] == sem_label]
            if not sem_slots:
                continue

            # Count completed in this semester
            sem_done = sum(1 for s in sem_slots if slot_display_label(s) in completed_labels)
            sem_total = len(sem_slots)
            sem_icon = "✅" if sem_done == sem_total and sem_total > 0 else ("🔵" if sem_done > 0 else "⬜")

            with st.expander(f"{sem_icon} {sem_label} — {sem_done}/{sem_total} done", expanded=(sem_done > 0 and sem_done < sem_total)):
                for slot in sem_slots:
                    course = get_selected_course_for_slot(slot, saved_or_choices)
                    if not course:
                        course = slot["group"][0]
                    if course.get("is_elective"):
                        continue

                    label = slot_display_label(slot)
                    code = course["code"]
                    title = course["title"]
                    credits = course.get("credits", "")
                    is_done = label in completed_labels

                    # Show what this course unlocks (across ALL programs)
                    unlocks = unlock_map.get(code, [])
                    unlock_str = ""
                    if unlocks:
                        unlock_str = f" → unlocks: {', '.join(unlocks[:5])}"
                        if len(unlocks) > 5:
                            unlock_str += f" +{len(unlocks)-5} more"

                    cb = st.checkbox(
                        f"{code} — {title} ({credits}cr){unlock_str}",
                        value=is_done,
                        key=f"cb_{slot['slot_id']}",
                    )

                    if cb and label not in new_completed:
                        new_completed.append(label)
                        changed = True
                    elif not cb and label in new_completed:
                        new_completed.remove(label)
                        changed = True

        if changed:
            progress["students"][selected_sid]["completed_slots"] = new_completed
            progress["students"][selected_sid]["completed_slot_terms"] = sync_completed_slot_terms(
                progress["students"][selected_sid], new_completed,
            )
            save_progress(progress)
            st.rerun()

        st.markdown("---")
        st.subheader("Placement Tests")
        st.caption("Placement can satisfy eligibility logic but does not award course credits.")

        def _render_placement_row(test_key: str, label: str, options: list[str]):
            current = placement_scores.get(test_key, {"taken": False, "level": ""})
            row_col1, row_col2 = st.columns([1, 4])
            with row_col1:
                taken = st.checkbox(label, value=bool(current.get("taken")), key=f"placement_taken_{test_key}")
            with row_col2:
                try:
                    idx = options.index(current.get("level", ""))
                except ValueError:
                    idx = 0
                level = st.selectbox(
                    f"{label} level",
                    options=options,
                    index=idx,
                    key=f"placement_level_{test_key}",
                    disabled=not taken,
                    label_visibility="collapsed",
                )

            new_level = level if taken else ""
            return {"taken": taken, "level": new_level}

        placement_draft = {
            "writing": _render_placement_row("writing", "Writing", PLACEMENT_OPTIONS["writing"]),
            "math": _render_placement_row("math", "Math", PLACEMENT_OPTIONS["math"]),
            "chemistry": _render_placement_row("chemistry", "Chemistry", PLACEMENT_OPTIONS["chemistry"]),
        }

        if st.button("Save Placement Scores", key="save_placement_scores", use_container_width=True):
            if placement_draft != placement_scores:
                progress["students"][selected_sid]["placement_scores"] = placement_draft
                save_progress(progress)
                st.rerun()

        placement_only = sorted(c for c in effective_completed_course_codes if c not in completed_course_codes)
        if placement_only:
            st.caption("Placement-equivalent eligibility codes: " + ", ".join(placement_only))

        # Completion history table (editable terms)
        history_terms = sync_completed_slot_terms(student, new_completed)
        history_rows = completion_rows(new_completed, history_terms, completion_lookup, program_slots, saved_or_choices)
        if history_rows:
            st.markdown("#### Completion Details")
            history_df = pd.DataFrame(history_rows)
            edited_history = st.data_editor(
                history_df, width="stretch", hide_index=True,
                disabled=["Requirement", "Course", "Credits"],
                column_config={
                    "Completion Term": st.column_config.SelectboxColumn("Completion Term", options=[""] + terms)
                },
                key="adv_completion_editor",
            )
            updated_terms = {row["Requirement"]: row["Completion Term"] for _, row in edited_history.iterrows()}
            if updated_terms != history_terms:
                progress["students"][selected_sid]["completed_slot_terms"] = updated_terms
                save_progress(progress)
                st.rerun()

        if completed_course_codes:
            st.caption("All recognized completed classes: " + ", ".join(sorted(completed_course_codes)))

        st.markdown("---")

        # Manual / transfer courses
        st.subheader("Transfer & Other Classes")
        st.caption("Add classes taken elsewhere (transfer, AP, dual enrollment, etc.). These count toward prerequisites even if they're not in the program.")

        # Non-program prereqs that still matter for this student's remaining courses
        program_codes = {
            c["code"] for slot in program_slots for c in slot["group"]
            if not c.get("is_elective") and c.get("code") != "ELECTIVE"
        }
        needed_external_prereqs = set()
        for slot in program_slots:
            if slot_is_completed(slot, completed_slot_ids):
                continue
            for c in slot["group"]:
                if c.get("is_elective"):
                    continue
                reqs = course_requirements.get(c["code"], {})
                for prereq in reqs.get("prerequisite_codes", []):
                    if prereq not in program_codes:
                        needed_external_prereqs.add(prereq)

        if needed_external_prereqs:
            st.markdown("#### External Prereqs Not In Program Map")
            st.caption("These classes may not be degree requirements, but still satisfy prereq options for required classes.")
            st.markdown("- " + "\n- ".join(sorted(needed_external_prereqs)))

            add_prereq = st.multiselect(
                "Quick add external prereq completions",
                options=sorted(needed_external_prereqs),
                default=[p for p in sorted(needed_external_prereqs) if p in manual_completed_courses],
                key="adv_external_prereqs",
            )
            if set(add_prereq) != {k for k in manual_completed_courses.keys() if k in needed_external_prereqs}:
                for prereq in needed_external_prereqs:
                    if prereq in add_prereq and prereq not in manual_completed_courses:
                        progress["students"][selected_sid].setdefault("manual_completed_courses", {})[prereq] = "Transfer/Other"
                    elif prereq not in add_prereq and prereq in manual_completed_courses and manual_completed_courses.get(prereq) == "Transfer/Other":
                        progress["students"][selected_sid]["manual_completed_courses"].pop(prereq, None)
                save_progress(progress)
                st.rerun()

        st.markdown("#### Add Transfer Course")

        add_col, term_col, btn_col = st.columns([2, 1, 1])
        with add_col:
            manual_options = sorted(course_index.keys())
            manual_display = [code.replace("_", " ") for code in manual_options]
            manual_pick = st.selectbox("Course code", options=manual_display, key="adv_manual_code")
            manual_code = manual_pick.replace(" ", "_")
        with term_col:
            manual_term = st.selectbox("When completed", options=[""] + terms, key="adv_manual_term")
        with btn_col:
            st.write("")
            st.write("")
            if st.button("Add", use_container_width=True, key="adv_add_manual"):
                progress["students"][selected_sid].setdefault("manual_completed_courses", {})[manual_code.replace("_", " ")] = manual_term
                save_progress(progress)
                st.rerun()

        manual_rows_data = manual_course_rows(student.get("manual_completed_courses", {}))
        if manual_rows_data:
            manual_df = pd.DataFrame(manual_rows_data)
            edited_manual = st.data_editor(
                manual_df, width="stretch", hide_index=True, num_rows="dynamic",
                column_config={
                    "Completion Term": st.column_config.SelectboxColumn("Completion Term", options=[""] + terms)
                },
                key="adv_manual_editor",
            )
            updated_manual = {
                str(row["Course"]): row.get("Completion Term", "")
                for _, row in edited_manual.iterrows() if str(row.get("Course", "")).strip()
            }
            if updated_manual != student.get("manual_completed_courses", {}):
                progress["students"][selected_sid]["manual_completed_courses"] = updated_manual
                save_progress(progress)
                st.rerun()
        else:
            st.info("No transfer or manual courses recorded yet.")

        # Cross-program prereq display (moved to bottom; collapsed unless needed)
        if effective_completed_course_codes:
            st.markdown("---")
            with st.expander("🔗 What These Unlock in Other Programs (Optional)", expanded=False):
                st.caption("Use this only when planning program changes or transfer pathways.")

                cross_program_unlocks = {}
                all_programs = pc.get("programs", [])
                current_program_name = student.get("program_name", "")

                for other_prog in all_programs:
                    if other_prog["name"] == current_program_name:
                        continue
                    if not any(s["courses"] for s in other_prog["semesters"]):
                        continue

                    for sem in other_prog["semesters"]:
                        for course_entry in sem["courses"]:
                            if isinstance(course_entry, list):
                                course_entry = course_entry[0] if course_entry else {}
                            other_code = course_entry.get("code", "")
                            reqs = course_requirements.get(other_code, {})
                            prereq_codes = reqs.get("prerequisite_codes", [])
                            satisfied = [p for p in prereq_codes if p in effective_completed_course_codes]
                            if satisfied:
                                cross_program_unlocks.setdefault(other_prog["name"], []).append({
                                    "course": other_code,
                                    "title": course_entry.get("title", ""),
                                    "prereqs_met": satisfied,
                                })

                if cross_program_unlocks:
                    for prog_name, unlocked in sorted(cross_program_unlocks.items()):
                        with st.expander(f"**{prog_name}** — {len(unlocked)} course(s) unlocked"):
                            for u in unlocked:
                                met = ", ".join(u["prereqs_met"])
                                st.markdown(f"- **{u['course']}** — {u['title']} *(prereq met: {met})*")
                else:
                    st.caption("No cross-program prerequisites are satisfied yet.")


# ── Tab: Profile ─────────────────────────────────────────────────────────────
# Edit student name, program assignment, notes. Also delete student.

with tab_profile:
    st.subheader(f"Profile — {student['name']}")

    with st.form("adv_profile_form"):
        edited_name = st.text_input("Student name", value=student["name"])

        current_prog = student.get("program_name", "")
        if current_prog in real_names:
            prog_idx = real_names.index(current_prog)
        else:
            prog_idx = 0

        edited_prog_display = st.selectbox("Assigned program", options=display_names, index=prog_idx)
        campus_options = ["", "LCC / Libby", "Main / Kalispell", "No Preference"]
        current_campus = student.get("campus_preference", "")
        campus_idx = campus_options.index(current_campus) if current_campus in campus_options else 0
        edited_campus = st.selectbox("Campus/Delivery designation", options=campus_options, index=campus_idx)
        edited_notes = st.text_area("Advisor notes", value=student.get("notes", ""), height=150,
                                    help="Private notes about this student — goals, concerns, advising history, etc.")

        if st.form_submit_button("Save Profile", use_container_width=True):
            edited_prog = real_names[display_names.index(edited_prog_display)] if display_names else ""
            progress["students"][selected_sid]["name"] = edited_name.strip() or student["name"]
            progress["students"][selected_sid]["program_name"] = edited_prog
            progress["students"][selected_sid]["campus_preference"] = edited_campus
            progress["students"][selected_sid]["notes"] = edited_notes
            save_progress(progress)
            st.rerun()

    # Quick stats
    if program:
        st.markdown("#### Where They Stand")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Credits Done", f"{sp['completed_credits']}/{sp['total_credits']}")
        c2.metric("Classes Done", f"{sp['completed_slot_count']}/{sp['total_slots']}")
        c3.metric("Left to Go", sp["remaining_slots"])
        c4.metric("Progress", f"{sp['progress_pct']}%")

    # Delete
    st.markdown("---")
    delete_confirm = st.checkbox("I want to delete this student record.", key="adv_delete_confirm")
    if st.button("Delete Student", type="secondary", disabled=not delete_confirm, use_container_width=True):
        progress["students"].pop(selected_sid, None)
        if progress.get("active_student_id") == selected_sid:
            progress["active_student_id"] = ""
        save_progress(progress)
        st.rerun()

    # Audit log
    st.markdown("---")
    st.markdown("#### Recent Activity")
    recent = PROGRESS_STORE.get_recent_audit_entries(15)
    if recent:
        st.dataframe(pd.DataFrame(format_audit_entries(recent)), width="stretch", hide_index=True)


# ── Tab: Questions ───────────────────────────────────────────────────────────
# Show this student's questions and all open questions from any student.

with tab_questions:
    st.subheader(f"Questions — {student['name']}")

    # This student's questions
    student_qs = PROGRESS_STORE.get_questions_for_student(selected_sid)
    open_student_qs = [q for q in student_qs if q["status"] == "open"]

    if open_student_qs:
        for q in open_student_qs:
            with st.expander(f"📨 {q['question'][:80]}{'...' if len(q['question']) > 80 else ''} · {q['created_at'][:10]}", expanded=True):
                st.markdown(f"**Question:** {q['question']}")
                if q.get("context"):
                    st.caption(f"Topic: {q['context']}")
                st.caption(f"Asked {q['created_at']}")

                reply = st.text_area("Reply", key=f"adv_reply_{q['id']}", height=80)
                r_col, c_col = st.columns(2)
                with r_col:
                    if st.button("Send Reply", key=f"adv_send_{q['id']}", use_container_width=True):
                        if reply.strip():
                            PROGRESS_STORE.reply_to_question(q["id"], reply.strip())
                            st.success("Reply sent.")
                            st.rerun()
                        else:
                            st.warning("Type a reply first.")
                with c_col:
                    if st.button("Close", key=f"adv_close_{q['id']}", use_container_width=True, type="secondary"):
                        PROGRESS_STORE.close_question(q["id"])
                        st.rerun()
    else:
        st.success(f"No open questions from {student['name']}.")

    # History
    answered_qs = [q for q in student_qs if q["status"] in ("replied", "closed")]
    if answered_qs:
        st.markdown("#### Previous Questions")
        for q in answered_qs[:10]:
            icon = "✅" if q["status"] == "replied" else "📁"
            with st.expander(f"{icon} {q['question'][:60]}... · {q['created_at'][:10]}"):
                st.markdown(f"**Q:** {q['question']}")
                if q.get("advisor_reply"):
                    st.markdown(f"**A:** {q['advisor_reply']}")

    # All open questions (from any student)
    other_open = [q for q in open_questions if q.get("student_id") != selected_sid]
    if other_open:
        st.markdown("---")
        st.markdown(f"#### Other Students' Open Questions ({len(other_open)})")
        for q in other_open:
            with st.expander(f"📨 **{q['student_name']}** — {q['question'][:60]}... · {q['created_at'][:10]}"):
                st.markdown(f"**Student:** {q['student_name']} ({q.get('program_name', '')})")
                st.markdown(f"**Q:** {q['question']}")
                if q.get("context"):
                    st.caption(f"Topic: {q['context']}")
                reply = st.text_area("Reply", key=f"adv_other_reply_{q['id']}", height=80)
                r2, c2 = st.columns(2)
                with r2:
                    if st.button("Send", key=f"adv_other_send_{q['id']}", use_container_width=True):
                        if reply.strip():
                            PROGRESS_STORE.reply_to_question(q["id"], reply.strip())
                            st.rerun()
                with c2:
                    if st.button("Close", key=f"adv_other_close_{q['id']}", use_container_width=True, type="secondary"):
                        PROGRESS_STORE.close_question(q["id"])
                        st.rerun()

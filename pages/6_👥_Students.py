"""
FVCC Student Manager
Add students, assign programs, edit info, manage progress.
The place where student records get created and maintained.
"""

import json
import re
import uuid
from pathlib import Path

import streamlit as st

from progress_store import build_progress_store

DATA = Path(__file__).resolve().parent.parent / "data"
DB = Path(__file__).resolve().parent.parent / "db"
USER_PROGRESS_DB_PATH = DATA / "user_progress.db"
USER_PROGRESS_PATH = DATA / "user_progress.json"
PROGRESS_STORE = build_progress_store("sqlite", USER_PROGRESS_DB_PATH, USER_PROGRESS_PATH, DB / "migrations")


@st.cache_data
def _load(name):
    p = DATA / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def make_id(name: str, existing: set) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:30]
    if not base:
        base = "student"
    candidate = base
    i = 2
    while candidate in existing:
        candidate = f"{base}_{i}"
        i += 1
    return candidate


st.set_page_config(page_title="FVCC Student Manager", page_icon="👥", layout="wide")

pc = _load("program_courses.json")
programs_with_courses = [p for p in pc.get("programs", []) if any(s["courses"] for s in p["semesters"])]
program_names = sorted(p["name"] for p in programs_with_courses)

# Load progress
progress = PROGRESS_STORE.load()
student_records = progress.get("students", {})


def save_progress(p):
    PROGRESS_STORE.save(p)


st.title("👥 Student Manager")
st.caption(f"{len(student_records)} student(s) in the system")

# ═════════════════════════════════════════════════════════════════════════════
# ADD NEW STUDENT
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("### ➕ Add a New Student")

add_col1, add_col2 = st.columns(2)

with add_col1:
    new_name = st.text_input("Student Name", placeholder="First Last", key="mgr_new_name")
    new_program = st.selectbox("Program", options=["— Select a program —"] + program_names, key="mgr_new_program")

with add_col2:
    new_notes = st.text_area("Advisor Notes (optional)", placeholder="Transfer student, needs math placement, etc.", key="mgr_new_notes", height=108)

if st.button("Create Student", use_container_width=True, type="primary", key="mgr_create"):
    cleaned = new_name.strip()
    if not cleaned:
        st.error("Enter a student name.")
    elif new_program == "— Select a program —":
        st.error("Select a program.")
    else:
        new_id = make_id(cleaned, set(student_records.keys()))
        progress.setdefault("students", {})[new_id] = {
            "id": new_id,
            "name": cleaned,
            "program_name": new_program,
            "completed_slots": [],
            "completed_slot_terms": {},
            "manual_completed_courses": {},
            "selected_or_courses": {},
            "placement_scores": {
                "writing": {"taken": False, "level": ""},
                "math": {"taken": False, "level": ""},
                "chemistry": {"taken": False, "level": ""},
            },
            "campus_preference": "",
            "notes": new_notes.strip(),
        }
        progress["active_student_id"] = new_id
        save_progress(progress)
        st.success(f"Created student: **{cleaned}** → {new_program}")
        st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# STUDENT LIST & EDIT
# ═════════════════════════════════════════════════════════════════════════════

if student_records:
    st.markdown("---")
    st.markdown("### 📋 All Students")

    for sid in sorted(student_records.keys(), key=lambda s: student_records[s]["name"].lower()):
        student = student_records[sid]
        name = student.get("name", sid)
        prog = student.get("program_name", "No program")
        completed = len(student.get("completed_slots", []))
        manual = len(student.get("manual_completed_courses", {}))
        notes = student.get("notes", "")

        header = f"**{name}** · {prog}"
        if completed > 0 or manual > 0:
            header += f" · {completed} slots done"
            if manual > 0:
                header += f", {manual} transfer credits"

        with st.expander(header):
            edit_col1, edit_col2 = st.columns(2)

            with edit_col1:
                edited_name = st.text_input("Name", value=name, key=f"edit_name_{sid}")

                current_prog_idx = 0
                if prog in program_names:
                    current_prog_idx = program_names.index(prog) + 1
                edited_program = st.selectbox(
                    "Program",
                    options=["— Select a program —"] + program_names,
                    index=current_prog_idx,
                    key=f"edit_prog_{sid}",
                )

            with edit_col2:
                edited_notes = st.text_area("Advisor Notes", value=notes, key=f"edit_notes_{sid}", height=108)

            # Manual completed courses
            st.markdown("**Transfer / Manual Credits:**")
            manual_courses = student.get("manual_completed_courses", {})
            if manual_courses:
                for code, term in manual_courses.items():
                    st.caption(f"  ✅ {code} — {term if term else 'no term recorded'}")

            mc_col1, mc_col2 = st.columns(2)
            with mc_col1:
                add_course_code = st.text_input("Course code (e.g., WRIT 101)", key=f"mc_code_{sid}", placeholder="WRIT 101")
            with mc_col2:
                add_course_term = st.text_input("Completed when", key=f"mc_term_{sid}", placeholder="Transfer / Spring 2025")

            btn_col1, btn_col2, btn_col3 = st.columns(3)

            with btn_col1:
                if st.button("Save Changes", key=f"save_{sid}", use_container_width=True, type="primary"):
                    student["name"] = edited_name.strip() if edited_name.strip() else name
                    if edited_program != "— Select a program —":
                        student["program_name"] = edited_program
                    student["notes"] = edited_notes.strip()
                    save_progress(progress)
                    st.success(f"Updated {student['name']}")
                    st.rerun()

            with btn_col2:
                if add_course_code:
                    if st.button("Add Credit", key=f"add_mc_{sid}", use_container_width=True):
                        code = add_course_code.strip().upper()
                        term = add_course_term.strip()
                        student.setdefault("manual_completed_courses", {})[code] = term
                        save_progress(progress)
                        st.success(f"Added {code}")
                        st.rerun()

            with btn_col3:
                if st.button("Delete Student", key=f"del_{sid}", use_container_width=True):
                    st.session_state[f"confirm_del_{sid}"] = True

                if st.session_state.get(f"confirm_del_{sid}"):
                    st.warning(f"Are you sure you want to delete **{name}**? This cannot be undone.")
                    confirm_col1, confirm_col2 = st.columns(2)
                    with confirm_col1:
                        if st.button("Yes, delete", key=f"confirm_yes_{sid}", type="primary"):
                            del progress["students"][sid]
                            if progress.get("active_student_id") == sid:
                                remaining = list(progress["students"].keys())
                                progress["active_student_id"] = remaining[0] if remaining else ""
                            save_progress(progress)
                            st.rerun()
                    with confirm_col2:
                        if st.button("Cancel", key=f"confirm_no_{sid}"):
                            st.session_state[f"confirm_del_{sid}"] = False
                            st.rerun()

    # Bulk stats
    st.markdown("---")
    st.markdown("### 📊 Quick Stats")
    stat_col1, stat_col2, stat_col3 = st.columns(3)

    programs_in_use = {}
    for s in student_records.values():
        p = s.get("program_name", "None")
        programs_in_use[p] = programs_in_use.get(p, 0) + 1

    with stat_col1:
        st.metric("Total Students", len(student_records))

    with stat_col2:
        st.metric("Programs Represented", len(programs_in_use))

    with stat_col3:
        avg_completed = sum(len(s.get("completed_slots", [])) for s in student_records.values()) / max(len(student_records), 1)
        st.metric("Avg Slots Completed", f"{avg_completed:.1f}")

    if programs_in_use:
        st.markdown("**Students by Program:**")
        for prog_name, count in sorted(programs_in_use.items(), key=lambda x: -x[1]):
            st.caption(f"  {prog_name}: {count} student(s)")
else:
    st.info("No students yet. Add your first student above.")

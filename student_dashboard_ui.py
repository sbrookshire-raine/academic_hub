from __future__ import annotations

import pandas as pd
import streamlit as st

from planner_helpers import completion_rows, manual_course_rows, sync_completed_slot_terms
from student_dashboard import build_student_roster_rows, build_student_snapshot, format_audit_entries


def render_student_dashboard(
    *,
    user_progress: dict,
    save_user_progress,
    student_records: dict,
    active_student: dict | None,
    selected_student_id: str,
    selected_display: str,
    display_names: list[str],
    real_names: list[str],
    completed_credits: int,
    display_credits,
    completed_labels: list[str],
    remaining_slots: int,
    manual_completed_courses: dict,
    available_now: list[dict],
    completion_options: list[str],
    completion_lookup: dict,
    program_slots: list[dict],
    saved_or_choices: dict,
    terms: list[str],
    completed_course_codes: set[str],
    course_index: dict,
    recent_audit_entries: list[dict] | None = None,
) -> None:
    st.subheader("👤 Student Dashboard")
    st.caption("Manage student records, assign programs, and mark completed requirements so the planner reflects an individual student.")

    if student_records:
        st.dataframe(pd.DataFrame(build_student_roster_rows(student_records)), width="stretch", hide_index=True)

    if not active_student:
        st.info("Create or select a student from the sidebar to start student-specific planning.")
        return

    student_profile_tab, student_history_tab, student_record_tab, student_actions_tab = st.tabs(["Profile", "Completed Work", "Academic Record", "Actions"])

    with student_profile_tab:
        profile_col, notes_col = st.columns([2, 1])
        snapshot = build_student_snapshot(
            active_student,
            completed_credits,
            display_credits,
            len(completed_labels),
            remaining_slots,
            manual_completed_courses,
            available_now,
        )
        with profile_col:
            with st.form("student_profile_form"):
                edited_name = st.text_input("Student name", value=active_student["name"])
                current_program_display = selected_display if selected_display in display_names else display_names[0]
                edited_program_display = st.selectbox(
                    "Assigned program",
                    options=display_names,
                    index=display_names.index(current_program_display) if current_program_display in display_names else 0,
                )
                edited_notes = st.text_area("Notes", value=active_student.get("notes", ""), height=120)
                if st.form_submit_button("Save student profile", use_container_width=True):
                    edited_program_name = real_names[display_names.index(edited_program_display)] if display_names else ""
                    user_progress["students"][selected_student_id]["name"] = edited_name.strip() or active_student["name"]
                    user_progress["students"][selected_student_id]["program_name"] = edited_program_name
                    user_progress["students"][selected_student_id]["notes"] = edited_notes
                    save_user_progress(user_progress)
                    st.rerun()

        with notes_col:
            st.metric("Active Student", snapshot["student_name"])
            st.metric("Assigned Program", snapshot["program_name"] or "Not set")
            st.metric("Completed Credits", snapshot["completed_credits"])
            st.metric("Estimated Remaining Credits", snapshot["remaining_credits"])

        snap1, snap2, snap3 = st.columns(3)
        snap1.metric("Likely Eligible Now", snapshot["likely_eligible_now"])
        snap2.metric("Open Options Now", snapshot["open_options_now"])
        snap3.metric("Registration Blocks Now", snapshot["registration_blocks_now"])

        snap4, snap5, snap6 = st.columns(3)
        snap4.metric("Completed Requirement Slots", snapshot["completed_requirement_slots"])
        snap5.metric("Remaining Requirement Slots", snapshot["remaining_requirement_slots"])
        snap6.metric("Manual Completed Courses", snapshot["manual_completed_courses"])

    with student_history_tab:
        dashboard_completed = st.multiselect(
            "Completed requirement slots",
            options=completion_options,
            default=completed_labels,
            key="dashboard_completed_slots",
            help="Mark all requirement slots this student has already completed.",
        )
        if dashboard_completed != completed_labels:
            user_progress["students"][selected_student_id]["completed_slots"] = dashboard_completed
            user_progress["students"][selected_student_id]["completed_slot_terms"] = sync_completed_slot_terms(
                user_progress["students"][selected_student_id],
                dashboard_completed,
            )
            save_user_progress(user_progress)
            st.rerun()

        active_student = user_progress["students"].get(selected_student_id, active_student)
        history_terms = sync_completed_slot_terms(active_student, dashboard_completed)
        history_rows = completion_rows(dashboard_completed, history_terms, completion_lookup, program_slots, saved_or_choices)
        if history_rows:
            history_df = pd.DataFrame(history_rows)
            edited_history = st.data_editor(
                history_df,
                width="stretch",
                hide_index=True,
                disabled=["Requirement", "Course", "Credits"],
                column_config={
                    "Completion Term": st.column_config.SelectboxColumn(
                        "Completion Term",
                        options=[""] + terms,
                    )
                },
                key="student_completion_history_editor",
            )
            updated_terms = {
                row["Requirement"]: row["Completion Term"]
                for _, row in edited_history.iterrows()
            }
            if updated_terms != history_terms:
                user_progress["students"][selected_student_id]["completed_slot_terms"] = updated_terms
                save_user_progress(user_progress)
                st.rerun()
        else:
            st.info("No completed requirements recorded for this student yet.")

        if completed_course_codes:
            st.caption("Completed courses currently recognized: " + ", ".join(sorted(completed_course_codes)))

    with student_record_tab:
        st.caption("Add completed courses that should count for prerequisite checking even if they are not currently marked through the program map.")
        add_col, term_col, button_col = st.columns([2, 1, 1])
        with add_col:
            manual_course_code = st.selectbox(
                "Course code",
                options=sorted(course_index.keys()),
                key="manual_course_code",
                help="Add a completed course from the schedule/course index.",
            )
        with term_col:
            manual_course_term = st.selectbox(
                "Completion term",
                options=[""] + terms,
                key="manual_course_term",
            )
        with button_col:
            st.write("")
            st.write("")
            if st.button("Add course", use_container_width=True):
                user_progress["students"][selected_student_id].setdefault("manual_completed_courses", {})[manual_course_code.replace("_", " ")] = manual_course_term
                save_user_progress(user_progress)
                st.rerun()

        manual_rows = manual_course_rows(active_student.get("manual_completed_courses", {}))
        if manual_rows:
            manual_df = pd.DataFrame(manual_rows)
            edited_manual = st.data_editor(
                manual_df,
                width="stretch",
                hide_index=True,
                num_rows="dynamic",
                column_config={
                    "Completion Term": st.column_config.SelectboxColumn(
                        "Completion Term",
                        options=[""] + terms,
                    )
                },
                key="manual_completed_courses_editor",
            )
            updated_manual = {
                str(row["Course"]): row.get("Completion Term", "")
                for _, row in edited_manual.iterrows()
                if str(row.get("Course", "")).strip()
            }
            if updated_manual != active_student.get("manual_completed_courses", {}):
                user_progress["students"][selected_student_id]["manual_completed_courses"] = updated_manual
                save_user_progress(user_progress)
                st.rerun()
        else:
            st.info("No manual completed courses recorded yet.")

    with student_actions_tab:
        delete_confirm = st.checkbox("I understand deleting this student removes the saved dashboard record.", key="confirm_delete_student")
        if st.button("Delete active student", type="secondary", use_container_width=True, disabled=not delete_confirm):
            user_progress["students"].pop(selected_student_id, None)
            if user_progress.get("active_student_id") == selected_student_id:
                user_progress["active_student_id"] = ""
            save_user_progress(user_progress)
            st.rerun()

        if recent_audit_entries:
            st.markdown("**Recent Advising Activity**")
            st.dataframe(
                pd.DataFrame(format_audit_entries(recent_audit_entries)),
                width="stretch",
                hide_index=True,
            )
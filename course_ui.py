from __future__ import annotations

import pandas as pd
import streamlit as st

from eligibility import analyze_schedule_registration_notes, collect_course_alerts
from planner_helpers import dedupe_alerts, get_sections_for_course


def seat_status_display(seats: dict) -> str:
    avail = seats.get("available", 0)
    waitlist = seats.get("waitlist", 0)
    status = seats.get("status", "")
    if status == "Full" or avail <= 0:
        if waitlist > 0:
            return f"Full (w{waitlist})"
        return "Full"
    return str(avail)


def render_course_schedule(
    course: dict,
    selected_term: str,
    course_index: dict,
    completed: bool = False,
    context_label: str = "",
    unmet_prior_slots: int = 0,
    program_notes: list[str] | None = None,
    course_requirements: dict | None = None,
    completed_course_codes: set[str] | None = None,
    unlock_map: dict | None = None,
    program_course_codes: set[str] | None = None,
) -> None:
    code = course["code"]
    title = course["title"]
    credits = course.get("credits", "")
    program_notes = program_notes or []
    course_requirements = course_requirements or {}
    completed_course_codes = completed_course_codes or set()
    unlock_map = unlock_map or {}
    program_course_codes = program_course_codes or set()

    if course.get("is_elective"):
        st.markdown(f"📘 **Elective** — {title} ({credits}cr)")
        return

    sections = get_sections_for_course(code, selected_term, course_index)
    all_sections = get_sections_for_course(code, "", course_index)
    all_terms = sorted(set(section["term"] for section in all_sections)) if all_sections else []

    open_count = sum(1 for section in sections if section.get("seats", {}).get("available", 0) > 0)
    total_sections = len(sections)
    context_suffix = f" · listed under {context_label}" if context_label else ""
    schedule_gate = analyze_schedule_registration_notes(
        course["code"],
        sections or all_sections,
        completed_course_codes,
    )
    alerts = collect_course_alerts(
        course,
        sections,
        all_sections,
        context_label,
        unmet_prior_slots,
        program_notes,
        course_requirements,
        completed_course_codes,
    )
    alerts = dedupe_alerts(alerts)
    reasons = list(schedule_gate.get("reasons", []))
    if unmet_prior_slots > 0 and not context_label.lower().startswith("prereq"):
        reasons.append("earlier program requirements still unfinished")

    requirements = course_requirements.get(course["code"], {})
    if not schedule_gate.get("has_schedule_gate"):
        unmet_catalog_prereqs = [code for code in requirements.get("prerequisite_codes", []) if code not in completed_course_codes]
        if unmet_catalog_prereqs:
            reasons.append("catalog prerequisite courses not yet marked complete")

    if completed:
        status_emoji = "✅"
    elif alerts:
        status_emoji = "🟠"
    elif sections:
        status_emoji = "🟢" if open_count > 0 else "🔴"
    elif all_terms:
        status_emoji = "🟡"
    else:
        status_emoji = "⚪"

    if completed:
        exp_label = f"{status_emoji} **{code}** - {title} ({credits}cr) · marked completed{context_suffix}"
    elif sections:
        exp_label = f"{status_emoji} **{code}** - {title} ({credits}cr) · {open_count}/{total_sections} sections open in {selected_term}{context_suffix}"
    elif all_terms:
        offered_in = ", ".join(all_terms)
        exp_label = f"🟡 **{code}** - {title} ({credits}cr) · Not offered in {selected_term} (available: {offered_in}){context_suffix}"
    else:
        exp_label = f"⚪ **{code}** - {title} ({credits}cr) · Not in schedule{context_suffix}"

    with st.expander(exp_label, expanded=bool(sections)):
        if completed:
            st.success("Marked completed. This requirement can be hidden from future options using the sidebar filter.")

        if reasons:
            st.caption("Why blocked/cautioned: " + "; ".join(sorted(set(reasons))))

        unlocked_courses = [
            unlocked for unlocked in unlock_map.get(code, [])
            if unlocked in program_course_codes and unlocked not in completed_course_codes
        ]
        if unlocked_courses:
            st.caption("Unlocks or supports later program courses: " + ", ".join(unlocked_courses[:8]))

        for level, message in alerts:
            if level == "warning":
                st.warning(message)
            else:
                st.info(message)

        if sections:
            rows = []
            for section in sections:
                rows.append({
                    "Section": section["full_code"],
                    "Days": section["days"],
                    "Time": section["time"],
                    "Room": section["room"],
                    "Mode": section["delivery_mode"],
                    "Instructor": section["instructor"],
                    "Seats": seat_status_display(section["seats"]),
                    "Fee": section.get("additional_fee") or "",
                })
            df = pd.DataFrame(rows)

            def color_seats(value):
                if value == "Full" or value.startswith("Full"):
                    return "color: #dc3545; font-weight: bold"
                try:
                    seat_count = int(value)
                    if seat_count <= 3:
                        return "color: #fd7e14; font-weight: bold"
                    return "color: #198754"
                except ValueError:
                    return ""

            styled = df.style.map(color_seats, subset=["Seats"])
            st.dataframe(styled, width="stretch", hide_index=True)

            notes_sections = [(section["full_code"], section.get("notes", [])) for section in sections if section.get("notes")]
            if notes_sections:
                for sec_code, notes in notes_sections:
                    for note in notes:
                        st.caption(f"📌 **{sec_code}:** {note}")
        elif all_terms:
            st.info(f"This course is offered in: {', '.join(all_terms)}")
        else:
            st.warning("This course does not appear in the Spring/Summer/Fall 2026 schedules.")
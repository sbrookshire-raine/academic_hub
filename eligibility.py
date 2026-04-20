from __future__ import annotations

import re


def analyze_schedule_registration_notes(
    course_code: str,
    sections: list[dict],
    completed_course_codes: set[str],
) -> dict:
    note_pool = []
    for section in sections:
        note_pool.extend(section.get("notes", []))

    alerts = []
    reasons = []
    has_schedule_gate = False
    blocking = False

    for note in note_pool:
        lower = note.lower()
        codes_in_note = sorted(set(re.findall(r"[A-Z]{1,6}\s+\d+[~\w]*", note)))
        codes_in_note = [code for code in codes_in_note if code != course_code]

        if "prerequisite" in lower:
            has_schedule_gate = True
            if codes_in_note:
                unmet = [code for code in codes_in_note if code not in completed_course_codes]
                if unmet:
                    alerts.append(("warning", "Schedule prerequisites not yet marked complete: " + ", ".join(unmet)))
                    reasons.append("missing prerequisite course")
                    blocking = True
                else:
                    alerts.append(("info", "Schedule prerequisites appear satisfied: " + ", ".join(codes_in_note)))
            else:
                alerts.append(("warning", "Registration block: prerequisite required. See section note below."))
                reasons.append("prerequisite requirement in schedule note")
                blocking = True
            continue

        if "corequisite" in lower:
            has_schedule_gate = True
            if codes_in_note:
                unmet = [code for code in codes_in_note if code not in completed_course_codes]
                if unmet:
                    alerts.append(("info", "Schedule corequisites not yet marked complete: " + ", ".join(unmet)))
                    reasons.append("corequisite may still be needed")
                else:
                    alerts.append(("info", "Schedule corequisites appear satisfied: " + ", ".join(codes_in_note)))
            else:
                alerts.append(("info", "Schedule lists a corequisite requirement. See section note below."))
                reasons.append("corequisite requirement in schedule note")
            continue

        if "instructor consent" in lower or "consent" in lower:
            has_schedule_gate = True
            alerts.append(("warning", "Registration block: instructor consent required."))
            reasons.append("instructor consent required")
            blocking = True
            continue

        if "background check" in lower:
            has_schedule_gate = True
            alerts.append(("warning", "Registration block: background check or program clearance required."))
            reasons.append("background check or clearance required")
            blocking = True
            continue

        if "drug test" in lower or "drug screen" in lower:
            has_schedule_gate = True
            alerts.append(("warning", "Registration block: drug screen required."))
            reasons.append("drug screen required")
            blocking = True
            continue

        if "immunization" in lower:
            has_schedule_gate = True
            alerts.append(("warning", "Registration block: immunization documentation required."))
            reasons.append("immunization documentation required")
            blocking = True
            continue

        if "cpr" in lower:
            has_schedule_gate = True
            alerts.append(("warning", "Registration block: CPR certification required."))
            reasons.append("CPR certification required")
            blocking = True
            continue

        if "insurance" in lower:
            has_schedule_gate = True
            alerts.append(("warning", "Registration block: proof of insurance required."))
            reasons.append("proof of insurance required")
            blocking = True
            continue

        if "driver" in lower and "license" in lower:
            has_schedule_gate = True
            alerts.append(("warning", "Registration block: valid driver license required."))
            reasons.append("valid driver license required")
            blocking = True
            continue

        if "18 years of age" in lower or "at least 18" in lower or "must be 18" in lower:
            has_schedule_gate = True
            alerts.append(("warning", "Registration block: minimum age requirement."))
            reasons.append("minimum age requirement")
            blocking = True
            continue

        if "accepted into" in lower or "application process" in lower or "must apply" in lower or "interview" in lower or "entrance exam" in lower:
            has_schedule_gate = True
            alerts.append(("warning", "Registration block: program admission process required."))
            reasons.append("program admission process required")
            blocking = True
            continue

        if "must be" in lower:
            has_schedule_gate = True
            alerts.append(("warning", note))
            reasons.append("section note includes an eligibility restriction")
            blocking = True

    return {
        "alerts": alerts,
        "reasons": sorted(set(reasons)),
        "has_schedule_gate": has_schedule_gate,
        "blocking": blocking,
    }


def collect_course_alerts(
    course: dict,
    sections: list[dict],
    all_sections: list[dict],
    context_label: str,
    unmet_prior_slots: int,
    program_notes: list[str],
    course_requirements: dict,
    completed_course_codes: set[str],
) -> list[tuple[str, str]]:
    alerts = []

    if context_label.lower().startswith("prereq"):
        alerts.append(("info", "Program lists this requirement in a prerequisites block."))

    if unmet_prior_slots > 0 and not context_label.lower().startswith("prereq"):
        alerts.append((
            "warning",
            f"This is listed later in the catalog sequence. {unmet_prior_slots} earlier requirement slot(s) are still unfinished, so earlier coursework may be needed before registration.",
        ))

    schedule_note_result = analyze_schedule_registration_notes(
        course["code"],
        sections or all_sections,
        completed_course_codes,
    )
    for alert in schedule_note_result["alerts"]:
        if alert not in alerts:
            alerts.append(alert)

    requirements = course_requirements.get(course["code"], {})
    prereq_codes = requirements.get("prerequisite_codes", [])
    coreq_codes = requirements.get("corequisite_codes", [])

    unmet_prereqs = [code for code in prereq_codes if code not in completed_course_codes]
    unmet_coreqs = [code for code in coreq_codes if code not in completed_course_codes and code != course["code"]]

    if unmet_prereqs and not schedule_note_result["has_schedule_gate"]:
        alerts.append((
            "info",
            "Catalog course page lists prerequisites not yet marked complete: " + ", ".join(unmet_prereqs),
        ))

    if unmet_coreqs and not schedule_note_result["has_schedule_gate"]:
        alerts.append((
            "info",
            "Catalog course page lists corequisites not yet marked complete: " + ", ".join(unmet_coreqs),
        ))

    if course["code"].startswith("M "):
        for note in program_notes:
            if "placement" in note.lower() and ("info", note) not in alerts:
                alerts.append(("info", note))
                break

    return alerts
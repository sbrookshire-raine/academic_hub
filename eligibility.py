from __future__ import annotations

import re


def evaluate_catalog_prerequisites(requirements: dict, completed_course_codes: set[str]) -> dict:
    """
    Evaluate catalog prerequisites with basic AND/OR parsing.

    Returns:
      {
        "satisfied": bool,
        "unmet_codes": list[str],
        "rule": str,  # and | or | mixed
      }
    """
    prereq_codes = requirements.get("prerequisite_codes", []) or []
    if not prereq_codes:
        return {"satisfied": True, "unmet_codes": [], "rule": "none"}

    lines = [str(line).strip().lower() for line in (requirements.get("prerequisite_lines", []) or [])[:25]]

    # Build token stream from the prerequisite block, preserving code order and and/or markers.
    tokens: list[str] = []
    code_map = {code.lower(): code for code in prereq_codes}
    for line in lines:
        if line in ("and", "or"):
            tokens.append(line)
            continue
        if line in code_map:
            tokens.append(code_map[line])

    has_and = "and" in tokens or "and" in lines
    has_or = "or" in tokens or "or" in lines

    # Fallback strategy if scrape noise prevented a clean token stream.
    if not any(tok not in ("and", "or") for tok in tokens):
        if has_or and not has_and:
            satisfied = any(code in completed_course_codes for code in prereq_codes)
            unmet = [] if satisfied else prereq_codes[:]
            return {"satisfied": satisfied, "unmet_codes": unmet, "rule": "or"}
        satisfied = all(code in completed_course_codes for code in prereq_codes)
        unmet = [code for code in prereq_codes if code not in completed_course_codes]
        return {"satisfied": satisfied, "unmet_codes": unmet, "rule": "and"}

    # Parse as OR-of-AND-groups ("A and B or C" => (A and B) or C)
    groups: list[list[str]] = []
    current_group: list[str] = []
    for tok in tokens:
        if tok == "or":
            if current_group:
                groups.append(current_group)
                current_group = []
            continue
        if tok == "and":
            continue
        current_group.append(tok)
    if current_group:
        groups.append(current_group)

    # If parsing collapsed badly, recover with simple all-codes AND.
    if not groups:
        satisfied = all(code in completed_course_codes for code in prereq_codes)
        unmet = [code for code in prereq_codes if code not in completed_course_codes]
        return {"satisfied": satisfied, "unmet_codes": unmet, "rule": "and"}

    missing_by_group = []
    for group in groups:
        unique_group = list(dict.fromkeys(group))
        missing = [code for code in unique_group if code not in completed_course_codes]
        missing_by_group.append(missing)

    satisfied = any(len(missing) == 0 for missing in missing_by_group)
    if satisfied:
        unmet = []
    else:
        unmet = min(missing_by_group, key=len) if missing_by_group else prereq_codes[:]

    rule = "mixed" if has_and and has_or else ("or" if has_or else "and")
    return {"satisfied": satisfied, "unmet_codes": unmet, "rule": rule}


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

    prereq_eval = evaluate_catalog_prerequisites(requirements, completed_course_codes)
    unmet_prereqs = prereq_eval["unmet_codes"]
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
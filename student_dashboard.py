from __future__ import annotations


def build_student_roster_rows(student_records: dict) -> list[dict]:
    rows = []
    for student_id in sorted(student_records.keys(), key=lambda sid: student_records[sid]["name"].lower()):
        record = student_records[student_id]
        rows.append(
            {
                "Student": record["name"],
                "Program": record.get("program_name", ""),
                "Completed Slots": len(record.get("completed_slots", [])),
                "Manual Courses": len(record.get("manual_completed_courses", {})),
            }
        )
    return rows


def build_student_snapshot(
    active_student: dict | None,
    completed_credits: int,
    display_credits,
    completed_slot_count: int,
    remaining_slots: int,
    manual_completed_courses: dict,
    available_now: list[dict],
) -> dict:
    likely_eligible_now = sum(1 for item in available_now if item.get("likely_eligible") and not item.get("completed"))
    blocked_now = sum(1 for item in available_now if item.get("schedule_block") and not item.get("completed"))
    open_now = sum(1 for item in available_now if item.get("open_count", 0) > 0 and not item.get("completed"))
    remaining_credits = ""
    if str(display_credits).isdigit():
        remaining_credits = max(int(display_credits) - completed_credits, 0)

    return {
        "student_name": active_student.get("name", "") if active_student else "",
        "program_name": active_student.get("program_name", "") if active_student else "",
        "completed_credits": completed_credits,
        "remaining_credits": remaining_credits,
        "completed_requirement_slots": completed_slot_count,
        "remaining_requirement_slots": remaining_slots,
        "manual_completed_courses": len(manual_completed_courses),
        "likely_eligible_now": likely_eligible_now,
        "registration_blocks_now": blocked_now,
        "open_options_now": open_now,
    }


def format_audit_entries(entries: list[dict]) -> list[dict]:
    formatted = []
    for entry in entries:
        action = entry.get("action", "")
        payload = entry.get("payload", {})
        summary = action.replace("_", " ")

        if action == "student_created":
            summary = "Student created"
        elif action == "student_deleted":
            summary = "Student deleted"
        elif action == "student_updated":
            changed_fields = payload.get("changed_fields", [])
            summary = "Student updated"
            if changed_fields:
                summary += ": " + ", ".join(changed_fields)
        elif action == "active_student_changed":
            summary = "Active student changed"
        elif action == "global_completed_slots_updated":
            summary = "Global completed-slot cache updated"
        elif action == "global_or_choices_updated":
            summary = "Global OR-choice cache updated"

        formatted.append(
            {
                "When": entry.get("created_at", ""),
                "Type": entry.get("entity_type", ""),
                "Record": entry.get("entity_id", ""),
                "Summary": summary,
            }
        )
    return formatted
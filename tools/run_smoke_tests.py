import json
import gc
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "db"
sys.path.insert(0, str(ROOT))

from eligibility import analyze_schedule_registration_notes, collect_course_alerts
from planner_helpers import (
    build_completed_course_codes,
    count_completed_credits,
    count_remaining_slots,
    iter_course_slots,
    merge_completed_course_codes,
    recommended_course_items,
    slot_display_label,
)
from progress_store import build_progress_store
from student_dashboard import build_student_roster_rows, build_student_snapshot


def assert_equal(actual, expected, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def run_store_migration_test(temp_dir: Path) -> None:
    legacy_path = temp_dir / "legacy_progress.json"
    db_path = temp_dir / "test_progress.db"
    legacy_payload = {
        "active_student_id": "alex-test",
        "completed_slots": {"Accounting Technology, AAS": ["First Semester — ACTG 101 - Accounting Procedures I (3cr)"]},
        "selected_or_courses": {"Accounting Technology, AAS": {"slot-1": "ACTG 101"}},
        "students": {
            "alex-test": {
                "id": "alex-test",
                "name": "Alex Test",
                "program_name": "Accounting Technology, AAS",
                "completed_slots": ["First Semester — ACTG 101 - Accounting Procedures I (3cr)"],
                "completed_slot_terms": {"First Semester — ACTG 101 - Accounting Procedures I (3cr)": "Fall 2025"},
                "manual_completed_courses": {"WRIT 101W": "Fall 2025"},
                "selected_or_courses": {"slot-1": "ACTG 101"},
                "notes": "Migrated student",
            }
        },
    }
    legacy_path.write_text(json.dumps(legacy_payload, indent=2), encoding="utf-8")

    store = build_progress_store("sqlite", db_path, legacy_path, DB / "migrations")
    migrated = store.load()
    assert_equal(migrated["active_student_id"], "alex-test", "active student migrated")
    assert_equal(len(migrated["students"]), 1, "student count migrated")
    assert_equal(migrated["students"]["alex-test"]["notes"], "Migrated student", "student notes migrated")

    migrated["students"]["alex-test"]["manual_completed_courses"]["M 121"] = "Spring 2026"
    store.save(migrated)
    reloaded = store.load()
    assert_equal(reloaded["students"]["alex-test"]["manual_completed_courses"]["M 121"], "Spring 2026", "manual course persisted")
    audit_entries = store.get_recent_audit_entries(10)
    if not any(entry["action"] == "student_updated" and entry["entity_id"] == "alex-test" for entry in audit_entries):
        raise AssertionError("audit log should record student updates")
    del reloaded
    del migrated
    del store
    gc.collect()


def run_planner_helper_test() -> None:
    semesters = [
        {
            "label": "First Semester",
            "courses": [
                {"code": "ACTG 101", "title": "Accounting Procedures I", "credits": 3},
                {"code": "BMGT 205", "title": "Human Relations", "credits": 3, "or_next": True},
                {"code": "COMX 115", "title": "Interpersonal Communication", "credits": 3},
            ],
        },
        {
            "label": "Second Semester",
            "courses": [
                {"code": "ACTG 180", "title": "Payroll Accounting", "credits": 3},
            ],
        },
    ]
    slots = iter_course_slots(semesters)
    for index, slot in enumerate(slots, start=1):
        slot["slot_id"] = f"slot-{index}"

    completed_labels = {slot_display_label(slots[0]): slots[0]["slot_id"], slot_display_label(slots[1]): slots[1]["slot_id"]}
    completed_slot_ids = set(completed_labels.values())
    saved_or_choices = {slots[1]["slot_id"]: "COMX 115"}

    codes = build_completed_course_codes(slots, completed_slot_ids, saved_or_choices)
    assert_equal(codes, {"ACTG 101", "COMX 115"}, "completed course codes built")
    assert_equal(count_completed_credits(slots, completed_slot_ids, saved_or_choices), 6, "completed credits counted")
    assert_equal(count_remaining_slots(slots, completed_slot_ids), 1, "remaining slots counted")
    assert_equal(merge_completed_course_codes(codes, {"WRIT 101W": "Fall 2025"}), {"ACTG 101", "COMX 115", "WRIT 101W"}, "manual course codes merged")

    recommended = recommended_course_items([
        {"completed": False, "likely_eligible": True, "open_count": 0, "course": {"code": "ACTG 180"}},
        {"completed": False, "likely_eligible": True, "open_count": 2, "course": {"code": "ACTG 101"}},
        {"completed": True, "likely_eligible": True, "open_count": 5, "course": {"code": "WRIT 101W"}},
    ])
    assert_equal([item["course"]["code"] for item in recommended], ["ACTG 101", "ACTG 180"], "recommended items ranked")


def run_eligibility_test() -> None:
    sections = [{
        "notes": [
            "Prerequisite: ACTG 101.",
            "Students may only register for this course with instructor consent.",
        ]
    }]
    schedule_gate = analyze_schedule_registration_notes("ACTG 180", sections, {"WRIT 101W"})
    assert_equal(schedule_gate["blocking"], True, "schedule gate blocks unmet prereq and consent")

    alerts = collect_course_alerts(
        {"code": "ACTG 180"},
        sections,
        sections,
        "Second Semester",
        1,
        [],
        {"ACTG 180": {"prerequisite_codes": ["ACTG 101"], "corequisite_codes": []}},
        {"WRIT 101W"},
    )
    joined = " | ".join(message for _, message in alerts)
    if "Schedule prerequisites not yet marked complete" not in joined:
        raise AssertionError("eligibility alerts should include schedule prerequisite warning")


def run_student_snapshot_test() -> None:
    roster = build_student_roster_rows(
        {
            "alex-test": {"name": "Alex Test", "program_name": "Accounting Technology, AAS", "completed_slots": ["a"], "manual_completed_courses": {"WRIT 101W": "Fall 2025"}},
            "jamie-demo": {"name": "Jamie Demo", "program_name": "Nursing: Practical Nursing, CAS", "completed_slots": [], "manual_completed_courses": {}},
        }
    )
    assert_equal(len(roster), 2, "roster rows built")

    snapshot = build_student_snapshot(
        {"name": "Alex Test", "program_name": "Accounting Technology, AAS"},
        12,
        60,
        2,
        8,
        {"WRIT 101W": "Fall 2025"},
        [
            {"likely_eligible": True, "completed": False, "schedule_block": False, "open_count": 2},
            {"likely_eligible": False, "completed": False, "schedule_block": True, "open_count": 0},
        ],
    )
    assert_equal(snapshot["remaining_credits"], 48, "remaining credits calculated")
    assert_equal(snapshot["likely_eligible_now"], 1, "likely eligible count calculated")
    assert_equal(snapshot["registration_blocks_now"], 1, "block count calculated")


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        run_store_migration_test(temp_dir)
    run_planner_helper_test()
    run_eligibility_test()
    run_student_snapshot_test()
    print("All smoke tests passed.")


if __name__ == "__main__":
    main()
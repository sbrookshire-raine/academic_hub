import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB = ROOT / "db"
sys.path.insert(0, str(ROOT))

from progress_store import build_progress_store


def main() -> None:
    store = build_progress_store(
        "sqlite",
        DATA / "user_progress.db",
        DATA / "user_progress.json",
        DB / "migrations",
    )
    progress = store.load()

    progress["students"]["alex-test"] = {
        "id": "alex-test",
        "name": "Alex Test",
        "program_name": "Accounting Technology, AAS",
        "completed_slots": [],
        "completed_slot_terms": {},
        "manual_completed_courses": {"WRIT 101W": "Fall 2025"},
        "selected_or_courses": {},
        "notes": "Sample advising record.",
    }
    progress["students"]["jamie-demo"] = {
        "id": "jamie-demo",
        "name": "Jamie Demo",
        "program_name": "Nursing: Practical Nursing, CAS",
        "completed_slots": [],
        "completed_slot_terms": {},
        "manual_completed_courses": {"BIOH 104NL": "Spring 2025", "PSYX 100A": "Spring 2025"},
        "selected_or_courses": {},
        "notes": "Demo student with prerequisite coursework completed.",
    }
    progress["students"]["sam-transfer"] = {
        "id": "sam-transfer",
        "name": "Sam Transfer",
        "program_name": "Programming and Software Development, AAS",
        "completed_slots": [],
        "completed_slot_terms": {},
        "manual_completed_courses": {"WRIT 101W": "Spring 2024", "M 121": "Spring 2024", "CSCI 127": "Fall 2024"},
        "selected_or_courses": {},
        "notes": "Transfer-in student with prior gen ed and intro programming completed.",
    }
    progress["students"]["taylor-blocked"] = {
        "id": "taylor-blocked",
        "name": "Taylor Blocked",
        "program_name": "Firearms Technologies, CTS",
        "completed_slots": [],
        "completed_slot_terms": {},
        "manual_completed_courses": {},
        "selected_or_courses": {},
        "notes": "Demo student intended to surface program-admission and compliance blocks in the planner.",
    }
    if not progress.get("active_student_id"):
        progress["active_student_id"] = "alex-test"

    store.save(progress)
    print("Seeded sample student records into SQLite progress database.")


if __name__ == "__main__":
    main()
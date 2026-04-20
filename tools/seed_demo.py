"""
Seed demo students for demonstration purposes.
Creates 5 students at different stages of progress across different programs.
Run: python tools/seed_demo.py
Clear: python tools/seed_demo.py --clear
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from progress_store import build_progress_store

DATA = ROOT / "data"
DB = ROOT / "db"

DEMO_IDS = [
    "demo-maria", "demo-jake", "demo-sarah", "demo-tyler", "demo-priya",
]

DEMO_STUDENTS = {
    # ── 1. Maria: Business Admin, just finished Year 1 ──────────────────────
    "demo-maria": {
        "id": "demo-maria",
        "name": "Maria Gonzalez",
        "program_name": "Business: Business Administration, AAS",
        "completed_slots": [
            "First Year - Fall — ACTG 201 - Principles of Financial Accounting (4cr)",
            "First Year - Fall — BGEN 204B - Business Fundamentals (3cr)",
            "First Year - Fall — BMGT 205C - Business Communication (3cr)",
            "First Year - Fall — CAPP 156 - MS Excel (3cr)",
            "First Year - Fall — ECNS 201B - Principles of Microeconomics (3cr)",
            "First Year - Spring — ACTG 202 - Principles of Managerial Accounting (4cr)",
            "First Year - Spring — BFIN 205 - Personal Finance (3cr)",
            "First Year - Spring — BMGT 215 - Human Resource Management (3cr)",
            "First Year - Spring — BMKT 225 - Marketing (3cr)",
            "First Year - Spring — ECNS 202B - Principles of Macroeconomics (3cr)",
        ],
        "completed_slot_terms": {
            "First Year - Fall — ACTG 201 - Principles of Financial Accounting (4cr)": "Fall 2025",
            "First Year - Fall — BGEN 204B - Business Fundamentals (3cr)": "Fall 2025",
            "First Year - Fall — BMGT 205C - Business Communication (3cr)": "Fall 2025",
            "First Year - Fall — CAPP 156 - MS Excel (3cr)": "Fall 2025",
            "First Year - Fall — ECNS 201B - Principles of Microeconomics (3cr)": "Fall 2025",
            "First Year - Spring — ACTG 202 - Principles of Managerial Accounting (4cr)": "Spring 2026",
            "First Year - Spring — BFIN 205 - Personal Finance (3cr)": "Spring 2026",
            "First Year - Spring — BMGT 215 - Human Resource Management (3cr)": "Spring 2026",
            "First Year - Spring — BMKT 225 - Marketing (3cr)": "Spring 2026",
            "First Year - Spring — ECNS 202B - Principles of Macroeconomics (3cr)": "Spring 2026",
        },
        "manual_completed_courses": {},
        "selected_or_courses": {},
        "notes": "Strong student, 3.7 GPA. Interested in entrepreneurship track after graduation. Planning to take full load Fall 2026.",
    },

    # ── 2. Jake: Welding, halfway through Year 1 ────────────────────────────
    "demo-jake": {
        "id": "demo-jake",
        "name": "Jake Thompson",
        "program_name": "Welding and Fabrication Technology, AAS",
        "completed_slots": [
            "First Year - Fall — DDSN 113 - Technical Drafting (3cr)",
            "First Year - Fall — M 114 - Extended Technical Mathematics (3cr)",
            "First Year - Fall — WLDG 110 - Welding Theory I (2cr)",
            "First Year - Fall — WLDG 111 - Welding Theory I Practical (3cr)",
            "First Year - Fall — WLDG 145 - Fabrication Basics I (3cr)",
        ],
        "completed_slot_terms": {
            "First Year - Fall — DDSN 113 - Technical Drafting (3cr)": "Fall 2025",
            "First Year - Fall — M 114 - Extended Technical Mathematics (3cr)": "Fall 2025",
            "First Year - Fall — WLDG 110 - Welding Theory I (2cr)": "Fall 2025",
            "First Year - Fall — WLDG 111 - Welding Theory I Practical (3cr)": "Fall 2025",
            "First Year - Fall — WLDG 145 - Fabrication Basics I (3cr)": "Fall 2025",
        },
        "manual_completed_courses": {},
        "selected_or_courses": {},
        "notes": "Doing well in hands-on work. Needs to register for Spring classes ASAP — welding sections fill fast.",
    },

    # ── 3. Sarah: Criminal Justice, brand new ───────────────────────────────
    "demo-sarah": {
        "id": "demo-sarah",
        "name": "Sarah Chen",
        "program_name": "Criminal Justice, AAS",
        "completed_slots": [],
        "completed_slot_terms": {},
        "manual_completed_courses": {
            "WRIT 101W": "Spring 2025",
            "PSYX 100A": "Spring 2025",
        },
        "selected_or_courses": {},
        "notes": "Transfer student from UM Western. Has gen ed writing and psych done. Starting CJ courses Fall 2026. Interested in law enforcement.",
    },

    # ── 4. Tyler: Nursing prereqs, working toward admission ─────────────────
    "demo-tyler": {
        "id": "demo-tyler",
        "name": "Tyler Martinez",
        "program_name": "Nursing: Practical Nursing, CAS",
        "completed_slots": [
            "Prerequisites — BIOH 104NL - Basic Human Biology with Lab (4cr)",
            "Prerequisites — PSYX 100A - Introduction to Psychology (4cr)",
            "Prerequisites — WRIT 101W - College Writing I (3cr)",
        ],
        "completed_slot_terms": {
            "Prerequisites — BIOH 104NL - Basic Human Biology with Lab (4cr)": "Fall 2025",
            "Prerequisites — PSYX 100A - Introduction to Psychology (4cr)": "Spring 2025",
            "Prerequisites — WRIT 101W - College Writing I (3cr)": "Spring 2025",
        },
        "manual_completed_courses": {},
        "selected_or_courses": {},
        "notes": "Needs M 094 (Quantitative Reasoning) to complete prereqs. Then apply for nursing admission. Has CNA certification already.",
    },

    # ── 5. Priya: Accounting, almost done ───────────────────────────────────
    "demo-priya": {
        "id": "demo-priya",
        "name": "Priya Patel",
        "program_name": "Accounting Technology, AAS",
        "completed_slots": [
            "First Year - Fall — ACTG 201 - Principles of Financial Accounting (4cr)",
            "First Year - Fall — BGEN 122 - Business Math (3cr)",
            "First Year - Fall — BMGT 205C - Business Communication (3cr)",
            "First Year - Fall — BMGT 215 - Human Resource Management (3cr)",
            "First Year - Fall — COMX 115C - Introduction to Interpersonal Communication (3cr)",
            "First Year - Spring — ACTG 180 - Payroll Accounting (2cr)",
            "First Year - Spring — ACTG 202 - Principles of Managerial Accounting (4cr)",
            "First Year - Spring — BGEN 235 - Business Law (4cr)",
            "First Year - Spring — CAPP 156 - MS Excel (3cr)",
            "First Year - Spring — ECNS 201B - Principles of Microeconomics (3cr)",
            "Second Year - Fall — ACTG 210 - Income Tax Fundamentals (3cr)",
            "Second Year - Fall — ACTG 215 - Quickbooks (3cr)",
            "Second Year - Fall — ACTG 221 - Cost Accounting (3cr)",
            "Second Year - Fall — ACTG 260 - Advanced Computer Applications in Accounting (3cr)",
            "Second Year - Fall — BMGT 235 - Management (3cr)",
        ],
        "completed_slot_terms": {
            "First Year - Fall — ACTG 201 - Principles of Financial Accounting (4cr)": "Fall 2024",
            "First Year - Fall — BGEN 122 - Business Math (3cr)": "Fall 2024",
            "First Year - Fall — BMGT 205C - Business Communication (3cr)": "Fall 2024",
            "First Year - Fall — BMGT 215 - Human Resource Management (3cr)": "Fall 2024",
            "First Year - Fall — COMX 115C - Introduction to Interpersonal Communication (3cr)": "Fall 2024",
            "First Year - Spring — ACTG 180 - Payroll Accounting (2cr)": "Spring 2025",
            "First Year - Spring — ACTG 202 - Principles of Managerial Accounting (4cr)": "Spring 2025",
            "First Year - Spring — BGEN 235 - Business Law (4cr)": "Spring 2025",
            "First Year - Spring — CAPP 156 - MS Excel (3cr)": "Spring 2025",
            "First Year - Spring — ECNS 201B - Principles of Microeconomics (3cr)": "Spring 2025",
            "Second Year - Fall — ACTG 210 - Income Tax Fundamentals (3cr)": "Fall 2025",
            "Second Year - Fall — ACTG 215 - Quickbooks (3cr)": "Fall 2025",
            "Second Year - Fall — ACTG 221 - Cost Accounting (3cr)": "Fall 2025",
            "Second Year - Fall — ACTG 260 - Advanced Computer Applications in Accounting (3cr)": "Fall 2025",
            "Second Year - Fall — BMGT 235 - Management (3cr)": "Fall 2025",
        },
        "manual_completed_courses": {"WRIT 101W": "Fall 2023"},
        "selected_or_courses": {},
        "notes": "On track to graduate Spring 2026. 3.9 GPA. Has a job offer at Glacier Bancorp pending completion. 5 classes left.",
    },
}

# Demo questions
DEMO_QUESTIONS = [
    ("demo-maria", "Can I take BGEN 298 Internship and BGEN 299 Capstone in the same semester?", "Course selection"),
    ("demo-maria", "Is there a summer option for any of my remaining classes?", "Schedule / timing"),
    ("demo-jake", "Do I need COMX 115C before I can take the second year welding classes?", "Prerequisites"),
    ("demo-sarah", "My WRIT 101W was at UM Western — will it transfer?", "Transfer credits"),
    ("demo-tyler", "When is the next nursing admission deadline?", "Registration"),
    ("demo-priya", "What do I need to do to apply for graduation?", "General"),
]


def seed():
    store = build_progress_store("sqlite", DATA / "user_progress.db", DATA / "user_progress.json", DB / "migrations")
    progress = store.load()

    for sid, student in DEMO_STUDENTS.items():
        progress.setdefault("students", {})[sid] = student

    if not progress.get("active_student_id"):
        progress["active_student_id"] = "demo-maria"

    store.save(progress)

    # Add demo questions
    for sid, question, context in DEMO_QUESTIONS:
        try:
            store.add_question(sid, question, context)
        except Exception:
            pass  # Questions table might not exist yet

    print(f"Seeded {len(DEMO_STUDENTS)} demo students:")
    for sid, s in DEMO_STUDENTS.items():
        done = len(s["completed_slots"])
        manual = len(s["manual_completed_courses"])
        print(f"  {s['name']:20s} — {s['program_name']:45s} — {done} slots done, {manual} transfer")
    print(f"\nAdded {len(DEMO_QUESTIONS)} demo questions.")
    print("\nRun the app: python -m streamlit run app.py")
    print("Clear demo data: python tools/seed_demo.py --clear")


def clear():
    store = build_progress_store("sqlite", DATA / "user_progress.db", DATA / "user_progress.json", DB / "migrations")
    progress = store.load()

    removed = 0
    for sid in DEMO_IDS:
        if sid in progress.get("students", {}):
            del progress["students"][sid]
            removed += 1

    if progress.get("active_student_id") in DEMO_IDS:
        remaining = list(progress.get("students", {}).keys())
        progress["active_student_id"] = remaining[0] if remaining else ""

    store.save(progress)
    print(f"Removed {removed} demo students. Your real data is untouched.")


if __name__ == "__main__":
    if "--clear" in sys.argv:
        clear()
    else:
        seed()

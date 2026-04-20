from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Protocol


def normalize_progress(progress: dict) -> dict:
    progress.setdefault("completed_slots", {})
    progress.setdefault("selected_or_courses", {})
    progress.setdefault("students", {})
    progress.setdefault("active_student_id", "")
    for student_id, student in progress["students"].items():
        student.setdefault("id", student_id)
        student.setdefault("name", student_id)
        student.setdefault("program_name", "")
        student.setdefault("completed_slots", [])
        student.setdefault("completed_slot_terms", {})
        student.setdefault("manual_completed_courses", {})
        student.setdefault("selected_or_courses", {})
        student.setdefault("notes", "")
    return progress


class SQLiteProgressStore:
    def __init__(self, db_path: Path, legacy_json_path: Path | None = None, migrations_dir: Path | None = None):
        self.db_path = Path(db_path)
        self.legacy_json_path = Path(legacy_json_path) if legacy_json_path else None
        self.migrations_dir = Path(migrations_dir) if migrations_dir else self.db_path.parent.parent / "db" / "migrations"
        self._initialize()
        self._migrate_legacy_json_if_needed()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._apply_migrations(conn)

    def _apply_migrations(self, conn: sqlite3.Connection) -> None:
        if not self.migrations_dir.exists():
            raise FileNotFoundError(f"Migration directory not found: {self.migrations_dir}")

        applied = {
            row[0]
            for row in conn.execute("SELECT version FROM schema_migrations ORDER BY version")
        }
        migration_files = sorted(self.migrations_dir.glob("*.sql"))
        for migration_file in migration_files:
            version = migration_file.stem
            if version in applied:
                continue
            sql = migration_file.read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))

    def _is_empty(self) -> bool:
        with self._connect() as conn:
            student_count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            global_count = conn.execute("SELECT COUNT(*) FROM global_completed_slots").fetchone()[0]
            return student_count == 0 and global_count == 0

    def _migrate_legacy_json_if_needed(self) -> None:
        if not self.legacy_json_path or not self.legacy_json_path.exists() or not self._is_empty():
            return
        legacy_progress = json.loads(self.legacy_json_path.read_text(encoding="utf-8"))
        self.save(legacy_progress)

    def load(self) -> dict:
        progress = normalize_progress({})
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM app_state WHERE key = 'active_student_id'").fetchone()
            progress["active_student_id"] = row[0] if row else ""

            for row in conn.execute("SELECT program_name, slot_label FROM global_completed_slots ORDER BY program_name, slot_label"):
                progress["completed_slots"].setdefault(row["program_name"], []).append(row["slot_label"])

            for row in conn.execute("SELECT program_name, slot_id, course_code FROM global_selected_or_courses ORDER BY program_name, slot_id"):
                progress["selected_or_courses"].setdefault(row["program_name"], {})[row["slot_id"]] = row["course_code"]

            for row in conn.execute("SELECT id, name, program_name, notes FROM students ORDER BY name"):
                progress["students"][row["id"]] = {
                    "id": row["id"],
                    "name": row["name"],
                    "program_name": row["program_name"],
                    "completed_slots": [],
                    "completed_slot_terms": {},
                    "manual_completed_courses": {},
                    "selected_or_courses": {},
                    "notes": row["notes"],
                }

            for row in conn.execute("SELECT student_id, slot_label, completion_term FROM student_completed_slots ORDER BY student_id, slot_label"):
                student = progress["students"].get(row["student_id"])
                if not student:
                    continue
                student["completed_slots"].append(row["slot_label"])
                student["completed_slot_terms"][row["slot_label"]] = row["completion_term"]

            for row in conn.execute("SELECT student_id, slot_id, course_code FROM student_selected_or_courses ORDER BY student_id, slot_id"):
                student = progress["students"].get(row["student_id"])
                if student:
                    student["selected_or_courses"][row["slot_id"]] = row["course_code"]

            for row in conn.execute("SELECT student_id, course_code, completion_term FROM student_manual_completed_courses ORDER BY student_id, course_code"):
                student = progress["students"].get(row["student_id"])
                if student:
                    student["manual_completed_courses"][row["course_code"]] = row["completion_term"]

        return normalize_progress(progress)

    def save(self, progress: dict) -> None:
        progress = normalize_progress(progress)
        previous_progress = self.load()
        with self._connect() as conn:
            conn.execute("BEGIN")
            conn.execute("DELETE FROM app_state")
            conn.execute("DELETE FROM global_completed_slots")
            conn.execute("DELETE FROM global_selected_or_courses")
            conn.execute("DELETE FROM student_completed_slots")
            conn.execute("DELETE FROM student_selected_or_courses")
            conn.execute("DELETE FROM student_manual_completed_courses")
            conn.execute("DELETE FROM students")

            conn.execute(
                "INSERT INTO app_state(key, value) VALUES (?, ?)",
                ("active_student_id", progress.get("active_student_id", "")),
            )

            for program_name, slot_labels in progress.get("completed_slots", {}).items():
                conn.executemany(
                    "INSERT INTO global_completed_slots(program_name, slot_label) VALUES (?, ?)",
                    [(program_name, label) for label in slot_labels],
                )

            global_or_rows = []
            for program_name, choices in progress.get("selected_or_courses", {}).items():
                for slot_id, course_code in choices.items():
                    global_or_rows.append((program_name, slot_id, course_code))
            if global_or_rows:
                conn.executemany(
                    "INSERT INTO global_selected_or_courses(program_name, slot_id, course_code) VALUES (?, ?, ?)",
                    global_or_rows,
                )

            student_rows = []
            completed_rows = []
            student_or_rows = []
            manual_rows = []
            for student_id, student in progress.get("students", {}).items():
                student_rows.append(
                    (
                        student_id,
                        student.get("name", student_id),
                        student.get("program_name", ""),
                        student.get("notes", ""),
                    )
                )
                slot_terms = student.get("completed_slot_terms", {})
                for slot_label in student.get("completed_slots", []):
                    completed_rows.append((student_id, slot_label, slot_terms.get(slot_label, "")))
                for slot_id, course_code in student.get("selected_or_courses", {}).items():
                    student_or_rows.append((student_id, slot_id, course_code))
                for course_code, completion_term in student.get("manual_completed_courses", {}).items():
                    manual_rows.append((student_id, course_code, completion_term))

            if student_rows:
                conn.executemany(
                    "INSERT INTO students(id, name, program_name, notes) VALUES (?, ?, ?, ?)",
                    student_rows,
                )
            if completed_rows:
                conn.executemany(
                    "INSERT INTO student_completed_slots(student_id, slot_label, completion_term) VALUES (?, ?, ?)",
                    completed_rows,
                )
            if student_or_rows:
                conn.executemany(
                    "INSERT INTO student_selected_or_courses(student_id, slot_id, course_code) VALUES (?, ?, ?)",
                    student_or_rows,
                )
            if manual_rows:
                conn.executemany(
                    "INSERT INTO student_manual_completed_courses(student_id, course_code, completion_term) VALUES (?, ?, ?)",
                    manual_rows,
                )

            self._write_audit_entries(conn, previous_progress, progress)

            conn.commit()

    def _write_audit_entries(self, conn: sqlite3.Connection, previous_progress: dict, current_progress: dict) -> None:
        audit_rows = []

        if previous_progress.get("active_student_id") != current_progress.get("active_student_id"):
            audit_rows.append((
                "app_state",
                "active_student_id",
                "active_student_changed",
                json.dumps({
                    "before": previous_progress.get("active_student_id", ""),
                    "after": current_progress.get("active_student_id", ""),
                }),
            ))

        previous_students = previous_progress.get("students", {})
        current_students = current_progress.get("students", {})
        all_student_ids = sorted(set(previous_students.keys()) | set(current_students.keys()))
        for student_id in all_student_ids:
            prev = previous_students.get(student_id)
            curr = current_students.get(student_id)
            if prev is None and curr is not None:
                audit_rows.append(("student", student_id, "student_created", json.dumps(curr, sort_keys=True)))
            elif prev is not None and curr is None:
                audit_rows.append(("student", student_id, "student_deleted", json.dumps(prev, sort_keys=True)))
            elif prev != curr:
                changed_fields = sorted(
                    field for field in set(prev.keys()) | set(curr.keys())
                    if prev.get(field) != curr.get(field)
                )
                audit_rows.append((
                    "student",
                    student_id,
                    "student_updated",
                    json.dumps({"changed_fields": changed_fields}, sort_keys=True),
                ))

        if previous_progress.get("completed_slots") != current_progress.get("completed_slots"):
            audit_rows.append((
                "global_progress",
                "completed_slots",
                "global_completed_slots_updated",
                json.dumps({"programs": sorted(current_progress.get("completed_slots", {}).keys())}, sort_keys=True),
            ))
        if previous_progress.get("selected_or_courses") != current_progress.get("selected_or_courses"):
            audit_rows.append((
                "global_progress",
                "selected_or_courses",
                "global_or_choices_updated",
                json.dumps({"programs": sorted(current_progress.get("selected_or_courses", {}).keys())}, sort_keys=True),
            ))

        if audit_rows:
            conn.executemany(
                "INSERT INTO audit_log(entity_type, entity_id, action, payload_json) VALUES (?, ?, ?, ?)",
                audit_rows,
            )

    def get_recent_audit_entries(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT entity_type, entity_id, action, payload_json, created_at FROM audit_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        entries = []
        for row in rows:
            entries.append({
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "action": row["action"],
                "payload": json.loads(row["payload_json"] or "{}"),
                "created_at": row["created_at"],
            })
        return entries

    def add_question(self, student_id: str, question: str, context: str = "") -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO student_questions(student_id, question, context) VALUES (?, ?, ?)",
                (student_id, question, context),
            )
            return cursor.lastrowid

    def reply_to_question(self, question_id: int, reply: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE student_questions SET advisor_reply = ?, status = 'replied', replied_at = datetime('now') WHERE id = ?",
                (reply, question_id),
            )

    def close_question(self, question_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE student_questions SET status = 'closed' WHERE id = ?",
                (question_id,),
            )

    def get_questions_for_student(self, student_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, question, context, advisor_reply, status, created_at, replied_at "
                "FROM student_questions WHERE student_id = ? ORDER BY created_at DESC",
                (student_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_open_questions(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT q.id, q.student_id, s.name AS student_name, s.program_name, "
                "q.question, q.context, q.status, q.created_at "
                "FROM student_questions q JOIN students s ON q.student_id = s.id "
                "WHERE q.status = 'open' ORDER BY q.created_at ASC",
            ).fetchall()
        return [dict(row) for row in rows]

    def get_all_questions(self, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT q.id, q.student_id, s.name AS student_name, s.program_name, "
                "q.question, q.context, q.advisor_reply, q.status, q.created_at, q.replied_at "
                "FROM student_questions q JOIN students s ON q.student_id = s.id "
                "ORDER BY q.created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]


class ProgressStore(Protocol):
    def load(self) -> dict:
        ...

    def save(self, progress: dict) -> None:
        ...

    def get_recent_audit_entries(self, limit: int = 20) -> list[dict]:
        ...


def build_progress_store(backend: str, db_path: Path, legacy_json_path: Path | None = None, migrations_dir: Path | None = None) -> ProgressStore:
    if backend == "sqlite":
        return SQLiteProgressStore(db_path, legacy_json_path, migrations_dir)
    if backend == "postgres":
        raise NotImplementedError("PostgreSQL backend not implemented yet. The app now uses the ProgressStore interface so it can be added later without changing app-level persistence calls.")
    raise ValueError(f"Unsupported progress backend: {backend}")
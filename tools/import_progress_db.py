import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB = ROOT / "db"
sys.path.insert(0, str(ROOT))

from progress_store import build_progress_store, normalize_progress


def main() -> None:
    import_path = DATA / "user_progress_export.json"
    if len(sys.argv) > 1:
        import_path = Path(sys.argv[1]).resolve()

    if not import_path.exists():
        raise FileNotFoundError(f"Import file not found: {import_path}")

    payload = json.loads(import_path.read_text(encoding="utf-8"))
    progress = normalize_progress(payload)

    store = build_progress_store(
        "sqlite",
        DATA / "user_progress.db",
        DATA / "user_progress.json",
        DB / "migrations",
    )
    store.save(progress)
    print(f"Imported progress data from {import_path}")
    print(f"  Students: {len(progress.get('students', {}))}")
    print(f"  Active student: {progress.get('active_student_id', '')}")


if __name__ == "__main__":
    main()
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
    print("Progress DB ready")
    print(f"  Students: {len(progress.get('students', {}))}")
    print(f"  Active student: {progress.get('active_student_id', '')}")


if __name__ == "__main__":
    main()
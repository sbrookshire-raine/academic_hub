import json
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
    export_path = DATA / "user_progress_export.json"
    export_path.write_text(json.dumps(progress, indent=2), encoding="utf-8")
    print(f"Exported progress data to {export_path}")


if __name__ == "__main__":
    main()
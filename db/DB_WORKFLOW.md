# Progress DB Workflow

This project now uses a local SQLite database for student planning data.

Database file:
- `data/user_progress.db`

Legacy file:
- `data/user_progress.json`

The app automatically migrates legacy JSON data into SQLite on first use if needed.

## Schema Migrations

Migration files live in:
- `db/migrations/`

Run migrations manually:

```powershell
python tools/migrate_progress_db.py
```

## Seed Demo Data

Load demo student records:

```powershell
python tools/seed_progress_db.py
```

## Export / Backup

Export the current database contents to JSON:

```powershell
python tools/export_progress_db.py
```

Default export path:
- `data/user_progress_export.json`

## Import / Restore

Restore from an exported JSON file:

```powershell
python tools/import_progress_db.py
```

Restore from a specific file:

```powershell
python tools/import_progress_db.py path\to\backup.json
```

## Smoke Tests

Run the integrated smoke tests:

```powershell
python tools/run_smoke_tests.py
```

## Future PostgreSQL Path

The app now uses a storage abstraction in `progress_store.py`.

To move to PostgreSQL later:
1. Add a PostgreSQL-backed implementation of the `ProgressStore` interface.
2. Recreate the migration files in a PostgreSQL-compatible form.
3. Switch the app's store factory from `sqlite` to `postgres`.

The application-level persistence calls should not need major changes because the app already talks through the storage abstraction.
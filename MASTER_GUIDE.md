# FVCC Planner Master Guide

This is the living reference for the FVCC advising and student planning system in this workspace.

It is intended to answer four questions:

1. What has been built?
2. How does it help advisors and students?
3. How does it work operationally?
4. What should be extended next?

## Product Purpose

This project is evolving from a scraped-program explorer into an advising-oriented planning system that can:

- browse FVCC programs and required course sequences
- show currently offered required courses by term
- interpret schedule notes and catalog prerequisites to estimate registration feasibility
- track student-specific progress
- persist student records and planning state in SQLite
- support advisor workflows through a dashboard, history, and operational tooling

The system is designed for local-first use today, with a clear path toward a future shared or hosted model.

## What Exists Now

### Core Planner

The app can:

- load structured program requirements from catalog-derived data
- surface required courses that are offered in the selected term
- group results by planning status
- show schedule-level warnings and registration blockers
- show likely eligible options first
- show courses that unlock later program requirements

### Eligibility Engine

The planner uses a layered registration-feasibility model:

1. Schedule section notes are treated as the primary source of registration truth.
2. Catalog course prerequisite/corequisite data is used as a fallback when schedule notes are silent.
3. Catalog sequence order adds softer caution about earlier required work.

This is important because actual registration blocks often appear in section notes rather than only in catalog prose.

### Student Dashboard

The system now supports student records with:

- active student selection
- assigned program
- notes
- completed requirement slots
- completion terms for those slots
- manual completed courses for transfer or off-map coursework
- OR-course choice persistence
- dashboard metrics and advising snapshot
- recent advising activity based on audit history

### Persistence Layer

Student planning data is no longer centered on a flat JSON workflow.

Current persistence model:

- primary storage: SQLite database in `data/user_progress.db`
- legacy compatibility: automatic migration from `data/user_progress.json`
- export/import support through JSON backup files
- formal schema migrations in `db/migrations/`

### Tooling

Operational tools now exist for:

- schema migration
- seeding demo/test data
- export/backup
- import/restore
- smoke testing

## Current File Architecture

### Main App Composition

- [app.py](c:/Users/m69nr/OneDrive/Desktop/fvccdata/app.py)

This is now mainly page composition and app workflow wiring.

### Storage

- [progress_store.py](c:/Users/m69nr/OneDrive/Desktop/fvccdata/progress_store.py)

Responsibilities:

- SQLite persistence
- migration application
- legacy JSON migration
- audit logging
- backend abstraction for future PostgreSQL support

### Planner Helpers

- [planner_helpers.py](c:/Users/m69nr/OneDrive/Desktop/fvccdata/planner_helpers.py)

Responsibilities:

- course/slot grouping
- progress calculations
- schedule matching
- recommendation helpers
- shared formatting helpers

### Eligibility Engine

- [eligibility.py](c:/Users/m69nr/OneDrive/Desktop/fvccdata/eligibility.py)

Responsibilities:

- schedule-note parsing
- registration-block logic
- warning generation

### Course Rendering

- [course_ui.py](c:/Users/m69nr/OneDrive/Desktop/fvccdata/course_ui.py)

Responsibilities:

- course expander rendering
- seat display
- in-panel warnings and requirement context

### Student Snapshot Logic

- [student_dashboard.py](c:/Users/m69nr/OneDrive/Desktop/fvccdata/student_dashboard.py)

Responsibilities:

- student roster rows
- advising snapshot calculations
- audit entry formatting

### Student Dashboard UI

- [student_dashboard_ui.py](c:/Users/m69nr/OneDrive/Desktop/fvccdata/student_dashboard_ui.py)

Responsibilities:

- dashboard tabs
- profile editing
- completed-work management
- academic record editing
- recent advising activity view

## Database and Operations

### Database Choice

The system currently uses SQLite because it matches the product stage:

- local-first
- low concurrency
- simple deployment
- strong enough structure for students, completions, notes, and audit history

This is the correct choice before introducing real multi-user behavior.

### PostgreSQL Path

The app already uses a storage abstraction.

That means PostgreSQL can be added later by:

1. implementing a PostgreSQL-backed `ProgressStore`
2. adapting migrations for PostgreSQL
3. switching the backend in one place instead of rewriting the app

### Migrations

Migrations live in:

- [db/migrations/001_initial_progress_schema.sql](c:/Users/m69nr/OneDrive/Desktop/fvccdata/db/migrations/001_initial_progress_schema.sql)
- [db/migrations/002_audit_log.sql](c:/Users/m69nr/OneDrive/Desktop/fvccdata/db/migrations/002_audit_log.sql)

### Operational Commands

Run migrations:

```powershell
python tools/migrate_progress_db.py
```

Seed demo students:

```powershell
python tools/seed_progress_db.py
```

Export progress:

```powershell
python tools/export_progress_db.py
```

Import progress:

```powershell
python tools/import_progress_db.py
```

Run smoke tests:

```powershell
python tools/run_smoke_tests.py
```

## Advisor Productivity

This system is already useful for advisors in several ways.

### 1. Faster Registration Conversations

Instead of manually checking program pages, schedules, and prerequisites separately, the system consolidates:

- program sequence
- offered sections
- seat visibility
- schedule-note registration blockers
- student-specific progress

That shortens the time from “What can this student take?” to a working answer.

### 2. Better Eligibility Triage

The grouped term-first list lets an advisor quickly separate:

- likely eligible now
- blocked by prerequisites or program rules
- earlier-program-work cautions
- catalog fallback cautions

That is much more actionable than reading raw schedule text.

### 3. Student-Specific Context

Advisors can keep lightweight records for:

- completed work
- transfer/manual coursework
- current program assignment
- notes
- recent changes

That allows the planner to become student-aware rather than just catalog-aware.

### 4. Operational Safety

The addition of:

- SQLite
- exports/imports
- migrations
- smoke tests
- audit log

means the project is now safer to use and evolve.

## Student Productivity

The current build is also beginning to support direct student-facing value.

### 1. Clearer Next-Step Visibility

Students can see:

- what is offered now
- what is likely eligible now
- what is blocked and why
- what each course unlocks later

### 2. Better Self-Tracking

Students or advisors can record:

- completed requirement slots
- completion terms
- transfer or manual completed courses

### 3. Snapshot View

Students can get a compact picture of their current state:

- completed credits
- remaining credits estimate
- likely eligible options now
- blocked options now
- open options now

### 4. Money & Costs Transparency

The Student Portal now includes a dedicated Money & Costs tab that:

- shows actual per-credit tuition for all residency tiers (no marketing fluff)
- provides an interactive cost estimator (pick credits + residency = semester cost)
- surfaces hidden costs the website doesn't advertise (lab fees, books, program supplies)
- explains payment rules including deferred plans and consequences of non-payment
- consolidates financial aid info: Pell, loans, work-study, scholarships

### 5. Plain-Language Support

The Help & Links tab now includes:

- support services directory (12 services, all free, with locations and contacts)
- jargon-to-English translator (21 terms the website uses that confuse normal people)
- key academic dates by term
- degree type explanations (what AA vs AAS vs CAS actually means for your life)

### 6. Data Layer

New data files power the student experience:

- `data/tuition.json` — scraped directly from the rate schedule, per-credit for all tiers
- `data/student_essentials.json` — 9-section plain-language guide built from all scraped data
- Tuition scraper: `scraper/scrape_tuition.py`
- Essentials builder: `scraper/build_student_essentials.py`
- New CLI commands: `tuition`, `essentials`, `translate`

## Testing and Validation

The project now includes an integrated smoke-test runner:

- [tools/run_smoke_tests.py](c:/Users/m69nr/OneDrive/Desktop/fvccdata/tools/run_smoke_tests.py)

It currently validates:

- legacy JSON migration into SQLite
- SQLite save/load persistence
- planner helper calculations
- eligibility logic
- student snapshot logic
- audit logging on real state changes

This does not replace deeper UI or integration testing, but it provides a solid system-level regression check.

## Demo/Test Data

The seed script creates multiple student scenarios intended to exercise different advising states, including:

- a general demo student
- a nursing demo student with prerequisite work
- a transfer-style student with manual completions
- a blocked/student-admission scenario

See:

- [tools/seed_progress_db.py](c:/Users/m69nr/OneDrive/Desktop/fvccdata/tools/seed_progress_db.py)

## What Still Needs Work

The project is stronger now, but not finished.

The highest-value next steps are:

### 1. In-Progress / Planned Coursework

Right now the model is strongest for completed work.

Adding in-progress and planned terms would let the advisor answer:

- “If the student takes these fall courses, what opens in spring?”

### 2. More Explicit Eligibility States

The app should eventually distinguish:

- eligible now
- eligible with concurrent enrollment
- blocked by program admission/compliance
- blocked by missing prerequisite
- advisory caution only

### 3. Remaining App Composition Refactor

`app.py` is much smaller in responsibility than before, but it can still be split further into:

- sidebar / student-selection flow
- planner-page composition
- term-first list composition

### 4. Postgres Backend

This is not required yet, but is the next major infrastructure milestone once shared multi-user access becomes important.

### 5. Better Import/Seed Controls

Eventually the project should support:

- CSV student imports
- seeded scenario resets
- advisor-safe restore flows with confirmation/preview

## How To Update This Guide

Treat this as the authoritative project guide.

When major changes are made, update these sections:

1. `What Exists Now`
2. `Current File Architecture`
3. `Database and Operations`
4. `Advisor Productivity`
5. `Student Productivity`
6. `What Still Needs Work`

If a new module or operational tool is added, add it here immediately so the project documentation remains ahead of future onboarding confusion.

## Recommended Current Workflow

For ongoing development:

1. Run migrations.
2. Seed test/demo data if needed.
3. Open the planner and test flows manually.
4. Run smoke tests before considering the change stable.
5. Export the DB if the test run produced valuable student/demo states.

## Bottom Line

This project is no longer just a scraped catalog viewer.

It is becoming a real advising support system with:

- structured course planning
- student-specific progress tracking
- local database persistence
- operational tooling
- test coverage
- audit history

That is already valuable for advisor workflows, and the current foundation is strong enough to keep extending without needing to start over.
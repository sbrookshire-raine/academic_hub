CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    program_name TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS student_completed_slots (
    student_id TEXT NOT NULL,
    slot_label TEXT NOT NULL,
    completion_term TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (student_id, slot_label),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_selected_or_courses (
    student_id TEXT NOT NULL,
    slot_id TEXT NOT NULL,
    course_code TEXT NOT NULL,
    PRIMARY KEY (student_id, slot_id),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_manual_completed_courses (
    student_id TEXT NOT NULL,
    course_code TEXT NOT NULL,
    completion_term TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (student_id, course_code),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS global_completed_slots (
    program_name TEXT NOT NULL,
    slot_label TEXT NOT NULL,
    PRIMARY KEY (program_name, slot_label)
);

CREATE TABLE IF NOT EXISTS global_selected_or_courses (
    program_name TEXT NOT NULL,
    slot_id TEXT NOT NULL,
    course_code TEXT NOT NULL,
    PRIMARY KEY (program_name, slot_id)
);
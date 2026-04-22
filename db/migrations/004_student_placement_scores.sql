CREATE TABLE IF NOT EXISTS student_placement_scores (
    student_id TEXT NOT NULL,
    test_type TEXT NOT NULL,
    taken INTEGER NOT NULL DEFAULT 0,
    level TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (student_id, test_type),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

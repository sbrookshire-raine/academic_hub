CREATE TABLE IF NOT EXISTS student_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    context TEXT NOT NULL DEFAULT '',
    advisor_reply TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    replied_at TEXT,
    CONSTRAINT valid_status CHECK (status IN ('open', 'replied', 'closed'))
);

CREATE INDEX IF NOT EXISTS idx_student_questions_student_id ON student_questions(student_id);
CREATE INDEX IF NOT EXISTS idx_student_questions_status ON student_questions(status);

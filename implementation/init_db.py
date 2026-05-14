from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  cohort TEXT NOT NULL,
  score REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS courses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS enrollments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id INTEGER NOT NULL,
  course_id INTEGER NOT NULL,
  grade REAL,
  FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
  FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
);
"""


SEED_SQL = """
INSERT INTO students (name, cohort, score) VALUES
  ('An', 'A1', 87.5),
  ('Binh', 'A1', 91.0),
  ('Chi', 'B2', 78.0),
  ('Dung', 'B2', 84.0);

INSERT INTO courses (code, title) VALUES
  ('DB101', 'Intro to Databases'),
  ('AI201', 'Applied ML'),
  ('SE110', 'Software Engineering');

INSERT INTO enrollments (student_id, course_id, grade) VALUES
  (1, 1, 88.0),
  (1, 3, 90.0),
  (2, 1, 95.0),
  (2, 2, 92.0),
  (3, 3, 80.0),
  (4, 2, 85.0);
"""


def create_database(db_path: str | Path) -> str:
    db_path = str(db_path)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA_SQL)

        # Seed only if empty
        cur = conn.execute("SELECT COUNT(*) FROM students")
        if cur.fetchone()[0] == 0:
            conn.executescript(SEED_SQL)

        conn.commit()
    finally:
        conn.close()
    return db_path


if __name__ == "__main__":
    default_path = Path(__file__).resolve().parent / "data" / "lab.sqlite3"
    print(create_database(default_path))


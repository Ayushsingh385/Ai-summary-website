"""
Migration: Add case_type, status, and brief_type columns if missing.
"""
import sqlite3

DB_PATH = "app.db"

COLUMNS = {
    "status": "TEXT DEFAULT 'new'",
    "brief_type": "TEXT",
    "case_type": "TEXT",  # stored as JSON string
}

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

existing = [row[1] for row in cursor.execute("PRAGMA table_info(cases)").fetchall()]

for col, definition in COLUMNS.items():
    if col in existing:
        print(f"  Column '{col}' already exists — skipping.")
    else:
        cursor.execute(f"ALTER TABLE cases ADD COLUMN {col} {definition}")
        print(f"  Added column '{col}'.")

conn.commit()
conn.close()
print("Migration complete.")

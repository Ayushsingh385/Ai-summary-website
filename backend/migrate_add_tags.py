"""
Migration script to add columns to existing cases table.
Run once: python migrate_add_tags.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "app.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(cases)")
    columns = [col[1] for col in cursor.fetchall()]

    migrations = []
    if "tags" not in columns:
        cursor.execute("ALTER TABLE cases ADD COLUMN tags TEXT DEFAULT '[]'")
        migrations.append("'tags'")
    if "status" not in columns:
        cursor.execute("ALTER TABLE cases ADD COLUMN status TEXT DEFAULT 'new'")
        migrations.append("'status'")
    if "brief_type" not in columns:
        cursor.execute("ALTER TABLE cases ADD COLUMN brief_type TEXT")
        migrations.append("'brief_type'")

    conn.commit()
    conn.close()

    if migrations:
        print(f"Migration complete: columns added — {', '.join(migrations)}")
    else:
        print("All columns already exist. No changes needed.")

if __name__ == "__main__":
    migrate()


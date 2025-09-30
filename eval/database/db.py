import sqlite3
from .static.vals import (DB_PATH)
import pandas as pd

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def ensure_category_column():
    cursor.execute("PRAGMA table_info(qa_table)")
    columns = [col[1] for col in cursor.fetchall()]
    if "category" not in columns:
        cursor.execute("ALTER TABLE qa_table ADD COLUMN category TEXT")
        conn.commit()

ensure_category_column()

def _reindex_ids():
    """Compact IDs to 1..N and reset AUTOINCREMENT."""
    rows = cursor.execute(
        "SELECT category, question, answer, expected_answer FROM qa_table ORDER BY id"
    ).fetchall()

    cursor.execute("DELETE FROM qa_table")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='qa_table'")

    if rows:
        cursor.executemany(
            "INSERT INTO qa_table (category, question, answer, expected_answer) VALUES (?, ?, ?, ?)",
            rows
        )
    conn.commit()

def add_entry(category, question, answer, expected_answer):
    cursor.execute(
        "INSERT INTO qa_table (category, question, answer, expected_answer) VALUES (?, ?, ?, ?)",
        (category, question, answer, expected_answer)
    )
    conn.commit()
    _reindex_ids()
    print("Entry added and IDs compacted.")

def delete_entry(entry_id):
    cursor.execute("DELETE FROM qa_table WHERE id = ?", (entry_id,))
    conn.commit()
    _reindex_ids()
    print(f"Deleted ID {entry_id} and reindexed.")

def delete_entries(entry_ids):
    cursor.executemany("DELETE FROM qa_table WHERE id = ?", [(i,) for i in entry_ids])
    conn.commit()
    _reindex_ids()
    print(f"Deleted IDs {entry_ids} and reindexed.")

def delete_all_entries():
    cursor.execute("DELETE FROM qa_table")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='qa_table'")
    conn.commit()
    print("Entries deleted and index reset.")

def view_entries():
    rows = cursor.execute("SELECT * FROM qa_table ORDER BY id").fetchall()
    if not rows:
        print("(empty)")
    for r in rows:
        print(r)

def add_df_entries(path):
    df = pd.read_csv(path, encoding="utf-8")

    for _, row in df.iterrows():
        category = row[df.columns[0]]
        question = row[df.columns[1]]
        answer = row[df.columns[2]]
        expected_answer = row[df.columns[3]]

        add_entry(category, question, answer, expected_answer)

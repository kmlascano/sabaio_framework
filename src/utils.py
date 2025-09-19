import sqlite3
from static.vals import (DB_PATH)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def _reindex_ids():
    """Compact IDs to 1..N and reset AUTOINCREMENT."""
    rows = cursor.execute(
        "SELECT question, answer, expected_answer FROM qa_table ORDER BY id"
    ).fetchall()

    cursor.execute("DELETE FROM qa_table")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='qa_table'")

    if rows:
        cursor.executemany(
            "INSERT INTO qa_table (question, answer, expected_answer) VALUES (?, ?, ?)",
            rows
        )
    conn.commit()

def add_entry(question, answer, expected_answer):
    cursor.execute(
        "INSERT INTO qa_table (question, answer, expected_answer) VALUES (?, ?, ?)",
        (question, answer, expected_answer)
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
import sqlite3
import pandas as pd
import spacy
import re
import os
from .static.vals import DB_PATH

# temporary 'categoriser' model using SpaCy similarity
# future classifier would be through manually labeled data 
nlp = spacy.load("en_core_web_lg")
CANDIDATE_LABELS = [
    "contract law", "tort law", "property law", "trust law", "family law",
    "employment law", "consumer protection", "commercial law", "corporate law",
    "intellectual property law", "real estate law", "landlord-tenant law",
    "insurance law", "tax law", "banking and finance law", "environmental law",
    "administrative law", "constitutional law", "international law",
    "human rights law", "defamation law", "privacy law", "immigration law",
    "education law", "health law", "maritime law", "probate law",
    "wills and estates", "construction law", "competition law",
    "criminal law", "white collar crime", "fraud", "theft", "assault",
    "homicide", "sexual offenses", "drug offenses", "cybercrime",
    "public order offenses", "traffic law"
]

def get_conn_cursor():
    """Connect to the SQLite database and return (conn, cursor)."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    return conn, conn.cursor()


def predict_category(text: str) -> str:
    """Predict best legal category for given text using SpaCy similarity."""
    if not text or not text.strip():
        return "uncategorized"
    doc = nlp(text)
    return max(CANDIDATE_LABELS, key=lambda label: doc.similarity(nlp(label)))


def ensure_eval_table_exists():
    """Create eval_table if it doesn't already exist."""
    conn, cursor = get_conn_cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eval_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT,
            gold_binary INTEGER,
            gold_response TEXT,
            llm_binary INTEGER,
            llm_response TEXT,
            category TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("Ensured eval_table exists in database.")


def parse_answer(ans: str):
    """
    Extract binary (1/0) and explanation from an answer string.
    Returns (binary_int, explanation_text).
    """
    if not ans or not isinstance(ans, str):
        return None, ""
    ans = ans.strip()
    match = re.match(r'^(True|False)\.?\s*(.*)$', ans, re.IGNORECASE)
    if match:
        binary = 1 if match.group(1).lower() == "true" else 0
        explanation = match.group(2).strip()
        return binary, explanation
    return None, ans


def create_eval_table_from_csv(csv_path: str):
    """
    Create (or recreate) eval_table with columns:
    prompt, gold_binary, gold_response, llm_binary, llm_response, category
    - Automatically detects True/False and converts to 1/0
    - Predicts legal category for each prompt using SpaCy
    """
    ensure_eval_table_exists()

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    print(f"Loaded CSV: {csv_path} ({len(df)} rows)")
    print("Detected columns:", df.columns.tolist())

    col_map = {}
    for col in df.columns:
        if "prompt" in col:
            col_map["prompt"] = col
        elif "gold" in col and ("answer" in col or "response" in col):
            col_map["gold_answer"] = col
        elif "llm" in col and ("answer" in col or "response" in col):
            col_map["llm_answer"] = col

    if not {"prompt", "gold_answer", "llm_answer"}.issubset(col_map):
        raise ValueError(f"Missing required columns. Found: {df.columns.tolist()}")

    records = []
    for _, row in df.iterrows():
        prompt = str(row[col_map["prompt"]]).strip()
        gold_ans = str(row[col_map["gold_answer"]]).strip()
        llm_ans = str(row[col_map["llm_answer"]]).strip()

        gold_binary, gold_resp = parse_answer(gold_ans)
        llm_binary, llm_resp = parse_answer(llm_ans)
        category = predict_category(prompt)

        gold_binary = int(gold_binary) if gold_binary is not None else None
        llm_binary = int(llm_binary) if llm_binary is not None else None

        records.append((prompt, gold_binary, gold_resp, llm_binary, llm_resp, category))

    conn, cursor = get_conn_cursor()
    cursor.executemany("""
        INSERT INTO eval_table (prompt, gold_binary, gold_response, llm_binary, llm_response, category)
        VALUES (?, ?, ?, ?, ?, ?)
    """, records)
    conn.commit()
    conn.close()

    print(f"Created and populated eval_table with {len(records)} rows from '{csv_path}'.")


def view_eval_table(limit: int = 10):
    """View first few rows of eval_table."""
    conn, cursor = get_conn_cursor()
    cursor.execute("SELECT * FROM eval_table LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("(empty eval_table)")
        return

    for r in rows:
        print(r)
        
def delete_eval_entries():
    """Delete all rows from eval_table (keeps schema)."""
    conn, cursor = get_conn_cursor()
    cursor.execute("DELETE FROM eval_table")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='eval_table'")
    conn.commit()
    conn.close()
    print("All entries deleted from eval_table and index reset.")


def drop_eval_table():
    """Completely remove eval_table from the database."""
    conn, cursor = get_conn_cursor()
    cursor.execute("DROP TABLE IF EXISTS eval_table")
    conn.commit()
    conn.close()
    print("eval_table dropped from database.")


def drop_all_tables():
    conn, cursor = get_conn_cursor()
    cursor.execute("DROP TABLE IF EXISTS qa_table")
    cursor.execute("DROP TABLE IF EXISTS eval_table")
    cursor.execute("DELETE FROM sqlite_sequence")
    conn.commit()
    conn.close()
    print("All tables (qa_table + eval_table) dropped from database.")

def delete_eval_entry(entry_id):
    """
    Delete a single entry from eval_table by its ID.
    Example:
        delete_eval_entry(5)
    """
    conn, cursor = get_conn_cursor()
    cursor.execute("DELETE FROM eval_table WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    print(f"Deleted entry with ID {entry_id} from eval_table.")


def delete_qa_entry(entry_id):
    """
    Delete a single entry from qa_table by its ID.
    Example:
        delete_qa_entry(7)
    """
    conn, cursor = get_conn_cursor()
    cursor.execute("DELETE FROM qa_table WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    print(f"Deleted entry with ID {entry_id} from qa_table.")


def delete_qa_entries(entry_ids):
    """
    Delete multiple entries from qa_table by their IDs.
    Example:
        delete_qa_entries([2, 4, 6])
    """
    if not entry_ids:
        print("⚠️ No entry IDs provided.")
        return

    conn, cursor = get_conn_cursor()
    cursor.executemany("DELETE FROM qa_table WHERE id = ?", [(i,) for i in entry_ids])
    conn.commit()
    conn.close()
    print(f"Deleted entries with IDs: {entry_ids} from qa_table.")

def add_eval_entry(prompt, gold_response, llm_response, category=None):
    """
    Add a single evaluation entry to eval_table.
    Automatically parses True/False → binary and ensures the table exists.
    """
    ensure_eval_table_exists()

    gold_binary, gold_text = parse_answer(gold_response)
    llm_binary, llm_text = parse_answer(llm_response)

    conn, cursor = get_conn_cursor()
    cursor.execute("""
        INSERT INTO eval_table (prompt, gold_binary, gold_response, llm_binary, llm_response, category)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (prompt, gold_binary, gold_text, llm_binary, llm_text, category or "uncategorized"))
    conn.commit()
    conn.close()
    print(f"Added 1 entry for prompt: {prompt[:60]}...")


def add_eval_entries(entries):
    """
    Add multiple evaluation entries at once.
    Example:
        add_eval_entries([
            ("Prompt text 1", "True. Explanation...", "False. Explanation...", "administrative law"),
            ("Prompt text 2", "False. ...", "False. ...", "criminal law")
        ])
    """
    ensure_eval_table_exists()

    conn, cursor = get_conn_cursor()
    to_insert = []
    for entry in entries:
        if len(entry) < 3:
            print("Skipped invalid entry:", entry)
            continue
        prompt, gold_resp, llm_resp = entry[0], entry[1], entry[2]
        category = entry[3] if len(entry) > 3 else "uncategorized"
        gold_bin, gold_text = parse_answer(gold_resp)
        llm_bin, llm_text = parse_answer(llm_resp)
        to_insert.append((prompt, gold_bin, gold_text, llm_bin, llm_text, category))

    cursor.executemany("""
        INSERT INTO eval_table (prompt, gold_binary, gold_response, llm_binary, llm_response, category)
        VALUES (?, ?, ?, ?, ?, ?)
    """, to_insert)
    conn.commit()
    conn.close()
    print(f"Added {len(to_insert)} new entries to eval_table.")

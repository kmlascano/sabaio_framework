import sqlite3
from collections import defaultdict

def analyse_pattern(fail_positions, total_count):
    if not fail_positions:
        return {"avg_gap": None, "gaps": [], "region": None, "longest_streak": 0}

    gaps = [j - i for i, j in zip(fail_positions, fail_positions[1:])]
    avg_gap = sum(gaps) / len(gaps) if gaps else None

    third = total_count / 3.0
    counts = {
        "beginning": sum(p <= third for p in fail_positions),
        "middle": sum(third < p <= 2 * third for p in fail_positions),
        "end": sum(p > 2 * third for p in fail_positions),
    }

    dominant_region, dominant_count = max(counts.items(), key=lambda kv: kv[1])
    total_f = len(fail_positions)
    region = (
        dominant_region if total_f and dominant_count / total_f >= 0.6 else "spread"
    )

    longest_streak = 1
    current = 1
    for g in gaps:
        if g == 1:
            current += 1
            longest_streak = max(longest_streak, current)
        else:
            current = 1

    return {
        "avg_gap": avg_gap,
        "gaps": gaps,
        "region": region,
        "longest_streak": longest_streak,
    }

def normalize_binary(value):
    """Normalize any binary-like input to 0/1 or None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("1", "true", "t", "yes"):
            return 1
        if v in ("0", "false", "f", "no"):
            return 0
    return None


def get_eval_scores(db):
    """Read eval_table, compute per-category accuracy and print formatted report."""
    # ---- Connect to DB ----
    if isinstance(db, str):
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        close_after = True
    else:
        conn, cursor = db.get_conn_cursor()
        close_after = True
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='eval_table';"
    )
    if not cursor.fetchone():
        if close_after:
            conn.close()
        raise RuntimeError("Table 'eval_table' not found in database.")
    records = []
    for row in cursor.execute(
        "SELECT id, prompt, gold_binary, llm_binary, category FROM eval_table ORDER BY id"
    ):
        rid, prompt, gold_bin, llm_bin, category = row
        gold_bin = normalize_binary(gold_bin)
        llm_bin = normalize_binary(llm_bin)
        match = gold_bin == llm_bin if (gold_bin is not None and llm_bin is not None) else False
        records.append((rid, category or "uncategorized", match))

    if close_after:
        conn.close()

    if not records:
        print("No data found in eval_table.")
        return

    cat_stats = defaultdict(lambda: {"total": 0, "correct": 0, "fails": []})
    all_fails = []
    total_count = len(records)
    total_correct = 0

    for idx, (rid, category, match) in enumerate(records, start=1):
        cat_stats[category]["total"] += 1
        if match:
            cat_stats[category]["correct"] += 1
        else:
            cat_stats[category]["fails"].append(cat_stats[category]["total"])
            all_fails.append(idx)
        if match:
            total_correct += 1
    overall_accuracy = total_correct / total_count if total_count else 0.0
    deficiency_score = 1 - overall_accuracy

    print(f"\nOverall deficiency Similarity Score: {deficiency_score:.2f}\n")
    print("Category Accuracy & Failure Positions:")
    for cat, stats in cat_stats.items():
        total = stats["total"]
        correct = stats["correct"]
        acc = (correct / total * 100) if total else 0.0
        fails = stats["fails"]
        print(f"  {cat}: {correct}/{total} correct ({acc:.2f}%)")
        print(f"    Failures at Q#: {fails if fails else 'None'}")

    for cat, stats in cat_stats.items():
        fails = stats["fails"]
        total = stats["total"]
        print(f"\n{cat.capitalize()} Failure Pattern Analysis:")
        if not fails:
            print("  - No failures in this category.")
            continue
        if len(fails) == 1:
            print("  - Only one failure, no gap pattern to analyze.")
            if fails[0] > (total * 2 / 3):
                print("  - Failures are mostly at the end of the dataset.")
            elif fails[0] < (total / 3):
                print("  - Failures are mostly at the beginning of the dataset.")
            else:
                print("  - Failures are mostly in the middle of the dataset.")
            continue

        pattern = analyse_pattern(fails, total)
        print(f"  - Average gap between failures: {pattern['avg_gap']:.2f} questions" if pattern['avg_gap'] else "  - No gap pattern available.")
        print(f"  - Gaps sequence: {pattern['gaps']}")
        region = pattern['region'] or 'unknown'
        print(f"  - Failures are mostly at the {region} of the dataset")
        print(f"  - Longest consecutive-failure streak: {pattern['longest_streak']}")

    print("\nGlobal Failure Positions (by order in dataset):")
    print(f"  {all_fails if all_fails else 'None'}")

    if all_fails:
        global_pattern = analyse_pattern(all_fails, total_count)
        print("\nGlobal Failure Pattern Analysis:")
        if global_pattern["avg_gap"] is not None:
            print(f"  - Average gap between failures: {global_pattern['avg_gap']:.2f} questions")
        else:
            print("  - Not enough data to calculate gap.")
        print(f"  - Gaps sequence: {global_pattern['gaps']}")
        print(f"  - Failures are mostly at the {global_pattern['region']} of the dataset")
        print(f"  - Longest consecutive-failure streak: {global_pattern['longest_streak']}")

    return {
        "overall_accuracy": overall_accuracy,
        "deficiency_score": deficiency_score,
        "category_stats": cat_stats,
        "global_fails": all_fails,
    }

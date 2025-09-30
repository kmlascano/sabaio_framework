from difflib import SequenceMatcher
from collections import defaultdict

def analyse_pattern(fail_positions, total_count):
    """Analyse failure positions within a sequence."""
    if not fail_positions:
        return {
            "avg_gap": None,
            "gaps": [],
            "region": None,
            "longest_streak": 0
        }

    gaps = [j - i for i, j in zip(fail_positions, fail_positions[1:])]
    avg_gap = sum(gaps) / len(gaps) if gaps else None

    # Identify where the errors are concentrated
    third = total_count / 3.0
    counts = {
        "beginning": sum(p <= third for p in fail_positions),
        "middle": sum(third < p <= 2 * third for p in fail_positions),
        "end": sum(p > 2 * third for p in fail_positions),
    }

    dominant_region, dominant_count = max(counts.items(), key=lambda kv: kv[1])
    total_f = len(fail_positions)
    region = (
        dominant_region if total_f and dominant_count / total_f >= 0.6
        else "spread"
    )

    # Longest consecutive streak
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


def get_scores(db):
    """Compute scores and failure patterns from QA table."""
    scores = []
    category_results = defaultdict(lambda: {"correct": 0, "total": 0, "fail_positions": []})
    failure_positions = []
    total_rows = 0

    # Preserve category order
    category_order = [
        row[0] for row in db.cursor.execute(
            "SELECT DISTINCT category, MIN(id) "
            "FROM qa_table GROUP BY category ORDER BY MIN(id)"
        )
    ]

    # Process dataset
    for idx, row in enumerate(db.cursor.execute("SELECT * FROM qa_table ORDER BY id"), start=1):
        total_rows = idx
        _, _, answer, expected, category = row
        answer, expected = answer or "", expected or ""

        ratio = SequenceMatcher(None, answer, expected).ratio()
        scores.append(ratio)

        is_correct = (answer.strip().lower() == expected.strip().lower())
        if is_correct:
            category_results[category]["correct"] += 1
        else:
            category_results[category]["fail_positions"].append(category_results[category]["total"] + 1)
            failure_positions.append(idx)

        category_results[category]["total"] += 1

    avg_deficiency = 1 - (sum(scores) / len(scores) if scores else 0.0)

    # Summarize results
    summary = {
        "overall_deficiency": avg_deficiency,
        "categories": {},
        "global_failures": failure_positions,
    }

    for category in category_order:
        result = category_results[category]
        total = result["total"]
        accuracy = result["correct"] / total if total else 0.0
        pattern = analyse_pattern(result["fail_positions"], total or 1)

        summary["categories"][category] = {
            "accuracy": accuracy,
            "correct": result["correct"],
            "total": total,
            "fail_positions": result["fail_positions"],
            "pattern": pattern,
        }

    summary["global_pattern"] = analyse_pattern(failure_positions, total_rows or 1)

    return summary

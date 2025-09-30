from difflib import SequenceMatcher
from collections import defaultdict

def analyze_pattern(fail_positions, total_count, label="Global"):
    print(f"\n{label} Failure Pattern Analysis:")
    if not fail_positions:
        print("  - No failures recorded.")
        return

    gaps = [j - i for i, j in zip(fail_positions, fail_positions[1:])]
    if gaps:
        avg_gap = sum(gaps) / len(gaps)
        print(f"  - Average gap between failures: {avg_gap:.2f} questions")
        print(f"  - Gaps sequence: {gaps}")
    else:
        print("  - Only one failure, no gap pattern to analyze.")

    third = total_count / 3.0
    early = sum(p <= third for p in fail_positions)
    middle = sum(third < p <= 2 * third for p in fail_positions)
    late = sum(p > 2 * third for p in fail_positions)
    total_f = len(fail_positions)

    parts = {"beginning": early, "middle": middle, "end": late}
    dominant_region, dominant_count = max(parts.items(), key=lambda kv: kv[1])
    if total_f and dominant_count / total_f >= 0.6:
        region_text = f"mostly at the {dominant_region}"
    else:
        region_text = "spread throughout"
    print(f"  - Failures are {region_text} of the dataset")

    longest_streak = 1
    current = 1
    for g in gaps:
        if g == 1:
            current += 1
            longest_streak = max(longest_streak, current)
        else:
            current = 1
    if total_f > 1:
        print(f"  - Longest consecutive-failure streak: {longest_streak}")


def get_scores(db):
    scores = []
    category_results = defaultdict(lambda: {"correct": 0, "total": 0, "fail_positions": []})
    failure_positions = []
    total_rows = 0

    category_order = []
    for row in db.cursor.execute("SELECT DISTINCT category, MIN(id) FROM qa_table GROUP BY category ORDER BY MIN(id)"):
        category_order.append(row[0])
        _ = category_results[row[0]]

    for idx, row in enumerate(db.cursor.execute("SELECT * FROM qa_table ORDER BY id"), start=1):
        total_rows = idx
        id_, question, answer, expected, category = row
        answer = answer or ""
        expected = expected or ""
        ratio = SequenceMatcher(None, answer, expected).ratio()
        scores.append(ratio)

        is_correct = (answer.strip().lower() == expected.strip().lower())
        if is_correct:
            category_results[category]["correct"] += 1
        else:
            category_results[category]["fail_positions"].append(category_results[category]["total"] + 1)
            failure_positions.append(idx)

        category_results[category]["total"] += 1

    avg_score = 1 - (sum(scores) / len(scores) if scores else 0.0)
    print(f"\nOverall deficiency Similarity Score: {avg_score:.2f}")

    print(f"\nCategory Accuracy & Failure Positions:")
    for category in category_order:
        result = category_results[category]
        correct = result["correct"]
        total = result["total"]
        accuracy = correct / total if total > 0 else 0.0
        print(f"  {category}: {correct}/{total} correct ({accuracy:.2%})")
        print(f"    Failures at Q#: {result['fail_positions']}")

    for category in category_order:
        result = category_results[category]
        analyze_pattern(result["fail_positions"], result["total"] if result["total"] > 0 else 1, label=f"{category}")

    print(f"\nGlobal Failure Positions (by order in dataset):")
    print(f"  {failure_positions}")
    analyze_pattern(failure_positions, total_rows if total_rows > 0 else 1, label="Global")

    return avg_score, dict(category_results), failure_positions

from difflib import SequenceMatcher
from collections import defaultdict

def get_scores(db):
    scores = []
    category_results = defaultdict(lambda: {"correct": 0, "total": 0, "fail_positions": []})
    failure_positions = []  
    
    for idx, row in enumerate(db.cursor.execute("SELECT * FROM qa_table ORDER BY id"), start=1):
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
    for category, result in category_results.items():
        correct = result["correct"]
        total = result["total"]
        accuracy = correct / total if total > 0 else 0
        print(f"  {category}: {correct}/{total} correct ({accuracy:.2%})")
        if result["fail_positions"]:
            print(f"    Failures at Q#: {result['fail_positions']}")

    if failure_positions:
        print(f"\nGlobal Failure Positions (by order in dataset):")
        print(f"  {failure_positions}")
    
    return avg_score, dict(category_results), failure_positions


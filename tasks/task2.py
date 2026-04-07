def grade(result):
    score = result.get("score", 0.4) if isinstance(result, dict) else 0.4
    return max(0.01, min(float(score), 0.99))
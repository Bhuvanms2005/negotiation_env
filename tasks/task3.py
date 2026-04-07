def grade(result):
    score = result.get("score", 0.3) if isinstance(result, dict) else 0.3
    return max(0.01, min(float(score), 0.99))
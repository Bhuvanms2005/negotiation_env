def grade(result):
    """Grade task2 (medium): score strictly in (0, 1)"""
    if isinstance(result, dict):
        raw = float(result.get("score", 0.5))
    else:
        raw = 0.5
    return max(0.01, min(raw, 0.99))

def grade(result):
    """Grade task1 (easy): score strictly in (0, 1)"""
    if isinstance(result, dict):
        raw = float(result.get("score", 0.6))
    else:
        raw = 0.6
    return max(0.01, min(raw, 0.99))

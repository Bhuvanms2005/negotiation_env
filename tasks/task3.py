def grade(result):
    """Grade task3 (hard): score strictly in (0, 1)"""
    if isinstance(result, dict):
        raw = float(result.get("score", 0.4))
    else:
        raw = 0.4
    return max(0.01, min(raw, 0.99))

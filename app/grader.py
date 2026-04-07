def grade(action, task, rounds):
    score = 0.0
    
    if action["price_offer"] >= task["min_accept"]:
        score += 0.5
    
    profit = action["price_offer"] - task["client_budget"]
    if profit > 0:
        score += 0.3
    
    if rounds <= 5:
        score += 0.2
    
    # Clamp strictly between 0 and 1 (never exactly 0.0 or 1.0)
    return max(0.01, min(score, 0.99))
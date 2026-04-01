def grade(action, task, rounds):
    score = 0.0
    
    if action["price_offer"] >= task["min_accept"]:
        score += 0.5
    
    profit = action["price_offer"] - task["client_budget"]
    if profit > 0:
        score += 0.3
    
    if rounds <= 5:
        score += 0.2
    
    return min(score, 1.0)
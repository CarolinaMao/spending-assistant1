from datetime import datetime
from analytics import (
    get_daily_totals_by_category,
    get_totals_by_category,
    get_consecutive_overspend,
    linear_forecast,
)

def check_daily_caps(transactions, budget_rules):
    today = datetime.now().strftime("%Y-%m-%d")
    alerts = []
    for rule in budget_rules:
        limit = rule.get("daily_cap")
        if limit is None: continue
        
        cat = rule["category"]
        day_total = get_daily_totals_by_category(transactions, cat).get(today, 0)
        
        if day_total > limit:
            alerts.append({
                "type": "daily_exceeded",
                "category": cat,
                "spent": day_total,
                "cap": limit,
                "message": f"{cat}: Daily limit exceeded! (HK${day_total:.2f} / HK${limit:.2f})",
            })
    return alerts

def check_percentage_thresholds(transactions, budget_rules):
    totals = get_totals_by_category(transactions)
    grand_total = sum(totals.values())
    if grand_total <= 0: return []
    
    alerts = []
    for rule in budget_rules:
        threshold = rule.get("pct_threshold")
        if threshold is None: continue
        
        cat = rule["category"]
        pct = (totals.get(cat, 0) / grand_total * 100)
        if pct > threshold:
            alerts.append({
                "type": "pct_exceeded",
                "category": cat,
                "pct": pct,
                "threshold": threshold,
                "message": f"{cat}: {pct:.1f}% of total (limit: {threshold}%)",
            })
    return alerts

def check_consecutive_overspend(transactions, budget_rules):
    alerts = []
    for rule in budget_rules:
        limit = rule.get("daily_cap")
        if limit is None: continue
        
        cat = rule["category"]
        streak = get_consecutive_overspend(transactions, cat, limit)
        if streak >= 3:
            alerts.append({
                "type": "consecutive_overspend",
                "category": cat,
                "streak": streak,
                "message": f"{cat}: Budget exceeded for {streak} consecutive days!",
            })
    return alerts

def check_forecast_alerts(transactions, budget_rules):

    projected_total = linear_forecast(transactions)
    monthly_limit = 5000 
    
    alerts = []
    if projected_total > monthly_limit:
        alerts.append({
            "type": "forecast_warning",
            "message": f"Trend Alert: Projected monthly spend (HK${projected_total:.2f}) exceeds budget!",
        })
    return alerts

def check_uncategorized(transactions, categories):
    alerts = []
    for t in transactions:
        cat = t.get("category", "Uncategorized")
        if cat == "Uncategorized" or cat not in categories:
            alerts.append({
                "type": "uncategorized",
                "id": t["id"],
                "category": cat,
                "message": f"Transaction #{t['id']} has invalid/unknown category: '{cat}'",
            })
    return alerts

def get_all_alerts(transactions, budget_rules, categories):
    res = []
    res += check_daily_caps(transactions, budget_rules)
    res += check_percentage_thresholds(transactions, budget_rules)
    res += check_consecutive_overspend(transactions, budget_rules)
    res += check_forecast_alerts(transactions, budget_rules)
    res += check_uncategorized(transactions, categories)
    return res

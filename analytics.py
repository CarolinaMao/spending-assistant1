import calendar
from collections import defaultdict
from datetime import datetime, timedelta

def parse_date(date_string):
    """
    Convert a date string (YYYY-MM-DD) into a datetime object.
    """
    return datetime.strptime(date_string, "%Y-%m-%d")

def filter_by_date(transactions, start=None, end=None):
    """
    Filter the transaction list based on a specific start and end date range.
    """
    def check_range(tx):
        d = parse_date(tx["date"])
        if start and d < start: return False
        if end and d > end: return False
        return True
    return [tx for tx in transactions if check_range(tx)]

def get_totals_by_category(transactions, start=None, end=None):
    """
    Aggregate total spending for each category within an optional date range.
    """
    subset = filter_by_date(transactions, start, end)
    mapping = defaultdict(float)
    for row in subset:
        mapping[row["category"]] += row["amount"]
    return dict(mapping)

def get_top_n_categories(transactions, n=3, start=None, end=None):
    """
    Identify the top N categories with the highest spending and calculate their percentage share.
    """
    cat_vals = get_totals_by_category(transactions, start, end)
    overall = sum(cat_vals.values())
    ordered = sorted(cat_vals.items(), key=lambda x: x[1], reverse=True)
    
    return [
        (k, v, (v / overall * 100) if overall > 0 else 0)
        for k, v in ordered[:n]
    ]

def get_spending_trends(transactions):
    """
    Compare average daily spending from the last 7 days vs. the last 30 days.
    """
    ref_day = datetime.now()
    w_data = filter_by_date(transactions, ref_day - timedelta(days=7), ref_day)
    m_data = filter_by_date(transactions, ref_day - timedelta(days=30), ref_day)
    
    w_avg = sum(i["amount"] for i in w_data) / 7 if w_data else 0
    m_avg = sum(i["amount"] for i in m_data) / 30 if m_data else 0
    return w_avg, m_avg

def get_daily_totals_by_category(transactions, category_name):
    """
    Map out total spending per day for a specific category.
    """
    daily_map = {}
    for entry in transactions:
        if entry["category"] == category_name:
            day = entry["date"]
            daily_map[day] = daily_map.get(day, 0.0) + entry["amount"]
    return daily_map

def get_consecutive_overspend(transactions, category, daily_cap):
    """
    Calculate the number of consecutive days the user has exceeded their daily cap for a category.
    """
    usage = get_daily_totals_by_category(transactions, category)
    timeline = sorted(usage.keys(), reverse=True)
    
    consecutive = 0
    for day_key in timeline:
        if usage[day_key] > daily_cap:
            consecutive += 1
        else:
            break
    return consecutive

def get_savings_progress(transactions, target, total_income):
    """
    Calculate current month's outflow, surplus, and progress toward a savings target.
    """
    today = datetime.now()
    month_start = datetime(today.year, today.month, 1)
    current_tx = filter_by_date(transactions, month_start, today)
    
    outflow = sum(obj["amount"] for obj in current_tx)
    surplus = total_income - outflow
    net = surplus - target
    return outflow, surplus, net

def linear_forecast(transactions):
    """
    Predict total spending for the current month using linear projection based on daily average.
    """
    now = datetime.now()
    start_point = datetime(now.year, now.month, 1)
    records = filter_by_date(transactions, start_point, now)
    
    if not records:
        return 0.0
        
    passed = (now - start_point).days + 1
    accumulated = sum(r["amount"] for r in records)
    _, days_in_month = calendar.monthrange(now.year, now.month)
    
    return (accumulated / passed) * days_in_month

def spending_heatmap(transactions):
    """
    Generate a heatmap visualization data by comparing daily spending to the monthly average.
    """
    now = datetime.now()
    start = datetime(now.year, now.month, 1)
    history = filter_by_date(transactions, start, now)

    daily_bins = defaultdict(float)
    for h in history:
        daily_bins[h["date"]] += h["amount"]

    if not daily_bins:
        return {}

    avg_val = sum(daily_bins.values()) / len(daily_bins)
    viz = {}
    
    for dt_str, val in daily_bins.items():
        ratio = val / avg_val if avg_val > 0 else 0
        # Assign different density characters based on spending intensity
        if ratio >= 1.5: icon = "█"
        elif ratio >= 1.0: icon = "▓"
        elif ratio >= 0.5: icon = "▒"
        else: icon = "░"
        viz[dt_str] = (icon, val)
    return viz

def get_spending_outliers(transactions, top_percent=0.05):
    """
    Retrieve the top X% (default 5%) of transactions by amount to identify major expenses.
    """
    if not transactions:
        return []
    
    # Sort transactions in descending order by amount
    ordered = sorted(transactions, key=lambda x: x["amount"], reverse=True)
    
    # Determine the number of outliers to return (at least one if transactions exist)
    count = max(1, int(len(ordered) * top_percent))
    
    return ordered[:count]
